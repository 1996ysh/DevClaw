"""
工具审计中间件
"""
import time
from typing import Callable

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from infra.logging import get_logger
from obs.metrics import AGENT_TOOL_DURATION, AGENT_TOOL_CALLS

logger= get_logger()

class ToolAuditMiddleware(AgentMiddleware):
    """
    每次调用工具前后打印审计日志
    """
    async def awrap_tool_call(
            self,
            request:ToolCallRequest,
            handler:Callable[[ToolCallRequest],"Command | ToolMessage"]
                )->"Command | ToolMessage":
        tool_name = request.tool_call["name"]
        start = time.perf_counter()
        status = "ok"
        try:
            return await handler(request)
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - start
            AGENT_TOOL_CALLS.labels(tool_name, status).inc()        # 埋点
            AGENT_TOOL_DURATION.labels(tool_name).observe(elapsed)  # 埋点
            logger.info("🔧 工具 {} {}（{:.0f} ms）", tool_name, status, elapsed * 1000)