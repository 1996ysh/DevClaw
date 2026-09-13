"""
fastaAPI+lifespan(建池、持久化、挂资源)
-在lifespan建一个AsyncConnectionPool，同时构造AsyncPostgreSaver
+AsyncPostgresStore

Windows 本地请用：uv run python -m api
（直接 uvicorn api.app:app 会踩 ProactorEventLoop + psycopg 不兼容。）
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from fastapi.responses import JSONResponse
from langgraph.store.postgres import AsyncPostgresStore
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from api.schema import HealthResponse
from infra.db import build_pg_pool
from infra.logging import get_logger
from infra.redis import build_redis
from profiles import register_all_profiles
from api.routes.issues import router as issues_router
from channels.webhook import router as webhook_router
from tasks.queue import get_arq_redis
from tasks.store import init_task_table
from api.routes.task_bg import router as tasks_bg_router
from api.routes.jobs import router as jobs_router
logger = get_logger()

#整个fastapi应用程序的生命周期
@asynccontextmanager
async def lifespan(app:FastAPI):
    #注册harness profile
    register_all_profiles()
    #打开postgres连接池
    pool = build_pg_pool()

    await pool.open()
    logger.info("postgres连接池已打开")
    #用同一个池构造异步saver/store并setup建表
    checkpointer = AsyncPostgresSaver(pool)
    store = AsyncPostgresStore(pool)
    await checkpointer.setup()
    await store.setup()

    logger.info("postgres checkpoint和store已初始化")
    await init_task_table(pool)
    redis = build_redis()
    arq_redis = await get_arq_redis()
    #挂到app.state 共所有请求复用
    app.state.arq_redis = arq_redis
    app.state.pg_pool = pool
    app.state.checkpointer = checkpointer
    app.state.store = store
    app.state.redis = redis
    try:
        yield
    finally:
        #应用程序关闭时统一释放
        await redis.aclose()
        await pool.close()
        await arq_redis.close()
        logger.info("连接池已关闭")

#下面这里的路由只不过是把子路由合并过来，并不影响下面的app.get的路由路径
app = FastAPI(title="ShanYangClaw DevMate API", lifespan=lifespan)
#dev开发期开放
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(issues_router)
app.include_router(webhook_router)
app.include_router(tasks_bg_router)
app.include_router(jobs_router)
# 统一异常处理：不把内部堆栈暴露给客户端
@app.exception_handler(Exception)
async def unhandled_exc_handler(request: Request, exc: Exception):
    logger.exception("未处理异常：{}", exc)
    return JSONResponse(status_code=500, content={"detail": "内部错误，请稍后重试"})


# 健康检查：liveness（纯探活）
@app.get("/healthz", response_model=HealthResponse)
async def healthz():
    return HealthResponse(status="ok")


# 健康检查：readiness（依赖就绪才 OK）
@app.get("/readyz", response_model=HealthResponse)
async def readyz(request: Request):
    pool = getattr(request.app.state, "pg_pool", None)
    if pool is None:
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": "pool 未就绪"})
    return HealthResponse(status="ready")