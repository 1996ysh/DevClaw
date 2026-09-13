"""tasks/worker.py —— arq worker + 任务定义（方案二：生产级）

三进程里的"worker"：独立运行，从 Redis 取任务执行。
启动：uv run arq tasks.worker.WorkerSettings

"""
import sys
import asyncio
from arq.connections import RedisSettings

from channels.base import InboundMessage
from channels.handler import handle_message
from infra.persistence import open_persistence
from infra.settings import get_settings
from infra.logging import get_logger
logger = get_logger()
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def process_issue(ctx: dict, payload: dict) -> dict:
    """arq 任务：处理一个 Issue。返回值会被 arq 存为任务结果（job.result() 可取）。"""
    inbound = InboundMessage(
        channel=payload["channel"], user_id=payload["user_id"],
        text=payload["text"], conversation_id=payload["conversation_id"],
    )
    checkpointer = ctx["checkpointer"]   # on_startup 放进 ctx 的共享资源
    store = ctx["store"]
    logger.info("worker 处理任务：conv={}", inbound.conversation_id)
    reply = await handle_message(inbound, checkpointer, store,
                                 tenant_id=payload.get("tenant_id", "default"))
    # 飞书等"推"型渠道：跑完主动发回；webhook/web"拉"型：靠 job 结果查询
    if inbound.channel == "feishu":
        from channels.feishu import FeishuChannel
        await FeishuChannel().send(inbound.conversation_id, reply)
    return {"reply": reply, "conversation_id": inbound.conversation_id}


async def on_startup(ctx: dict):
    pool, checkpointer, store = await open_persistence()
    ctx["pg_pool"], ctx["checkpointer"], ctx["store"] = pool, checkpointer, store
    logger.info("arq worker 启动：持久化资源就绪")


async def on_shutdown(ctx: dict):
    if ctx.get("pg_pool"):
        await ctx["pg_pool"].close()


class WorkerSettings:
    """arq 通过这个类发现配置。跑：uv run arq tasks.worker.WorkerSettings"""
    functions = [process_issue]
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)  # 用已有 Redis