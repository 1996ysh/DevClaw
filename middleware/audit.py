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
        tool_name = request.tool_call['name']
        start = time.perf_counter()
        logger.info(f"调用工具 {tool_name} 开始")
        #放行工具
        result = await handler(request)
        cost = (time.perf_counter() - start) * 1000
        logger.info(f"调用工具 {tool_name} 结束，耗时 {cost:.2f} ms")
        return result