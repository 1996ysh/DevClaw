"""
在llm调用层限并发
"""
from typing import Callable, Awaitable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ExtendedModelResponse
from langchain.agents.middleware.types import ResponseT
from langchain_core.messages import AIMessage
from langgraph.typing import ContextT

from infra.settings import get_settings
import asyncio
_llm_sem = asyncio.Semaphore(get_settings().max_concurrent_llm)

class LLMConcurrencyMiddleware(AgentMiddleware):
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        #卡住llm并发调用
        async with _llm_sem:
            return await handler(request)

