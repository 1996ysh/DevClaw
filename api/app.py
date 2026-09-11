"""
fastaAPI+lifespan(建池、持久化、挂资源)
-在lifespan建一个AsyncConnectionPool，同时构造AsyncPostgreSaver
+AsyncPostgresStore
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from fastapi.responses import JSONResponse
from langgraph.store.postgres import AsyncPostgresStore
from starlette.requests import Request


from api.schema import HealthResponse
from infra.db import build_pg_pool
from infra.logging import get_logger
from infra.redis import build_redis
from profiles import register_all_profiles
from api.routes.issues import router as issues_router
logger = get_logger()
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
    redis = build_redis()
    #挂到app.state 共所有请求复用
    app.state.pg_pool = pool
    app.state.checkpointer = checkpointer
    app.state.store = store
    app.state.redis = redis
    try:
        yield
    finally:
        await redis.aclose()
        await pool.close()
        logger.info("连接池已关闭")
app = FastAPI(title="ShanYangClaw DevMate API", lifespan=lifespan)
app.include_router(issues_router)
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