"""
隔离优先的沙箱池(面向BaseSandbox接口)
并发上限：信号量包装同时存在的沙箱不超过max_size
隔离优先：每个任务拿到干净沙箱，release时销毁(用完即弃)，不串数据
交回可用上下文(backend,workdir) 不是裸sandbox

"""
from asyncio import Semaphore
from contextlib import asynccontextmanager

from infra.logging import get_logger
from infra.settings import get_settings
from sandbox.docker_manager import create_one_sandbox, seed_project, destroy_sandbox

logger = get_logger()

class SandboxPool:
    def __init__(self,max_size:int):
        #并发上限
        self._sem = Semaphore(max_size)
        self._max = max_size
    @asynccontextmanager
    async def acquire(self):
        """借一个干净沙箱；用完销毁(隔离优先)"""
        await self._sem.acquire()
        sandbox = None
        try:
            #全新 加固 隔离
            sandbox = await create_one_sandbox()
            await seed_project(sandbox)
            yield sandbox,sandbox.workdir
        finally:
            if sandbox is not None:
                await destroy_sandbox(sandbox)
            self._sem.release()

_pool:SandboxPool | None = None

def get_sandbox_pool():
    global _pool
    if _pool is None:
        _pool = SandboxPool(max_size=get_settings().sandbox_pool_size)
    return _pool