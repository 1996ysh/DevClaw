import time
from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware, ExtendedModelResponse, ModelResponse, ModelRequest
from langgraph.types import Command
from typing_extensions import NotRequired

from infra.logging import get_logger
from obs.metrics import AGENT_LLM_CALLS, AGENT_LLM_DURATION, record_llm_cost

logger = get_logger()
class CostState(AgentState):
    """在 agent 状态里加三个累计字段（用 NotRequired，调用方无需初始化）。"""
    total_input_tokens: NotRequired[int]
    total_output_tokens: NotRequired[int]

class CostMeterMiddleware(AgentMiddleware):
    """统计每次模型调用的 token 用量，累加进状态。"""

    # 声明扩展状态（官方做法）
    state_schema = CostState
    def __init__(self, tier: str = "strong") -> None:    # ← 新增 tier，用于给指标打标签
        super().__init__()
        self.tier = tier
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ExtendedModelResponse:
        start = time.perf_counter()
        try:
            response = await handler(request)
            AGENT_LLM_CALLS.labels(self.tier, "ok").inc()  # 埋点：调用成功
        except Exception:
            AGENT_LLM_CALLS.labels(self.tier, "error").inc()  # 埋点：调用失败
            raise  # 失败也计数，再抛给 fallback 处理
        finally:
            AGENT_LLM_DURATION.labels(self.tier).observe(time.perf_counter() - start)  # 埋点：耗时
        #放行
        in_tok, out_tok = self._extract_usage(response)
        record_llm_cost(self.tier, in_tok, out_tok)
        # 从当前状态读累计值（NotRequired，默认 0），再累加
        prev_in = request.state.get("total_input_tokens", 0)
        prev_out = request.state.get("total_output_tokens", 0)
        #这里是extract ai的每一个最后一条消息 然后把这个消息消耗的token加进原来消耗里
        new_in, new_out = prev_in + in_tok, prev_out + out_tok
        return ExtendedModelResponse(
            model_response=response,
            command=Command(update={
                "total_input_tokens": new_in,
                "total_output_tokens": new_out,
            }),
        )
    @staticmethod
    def _extract_usage(response: ModelResponse) -> tuple[int, int]:
        """从 ModelResponse 里挖出最后一条 AIMessage 的 usage_metadata。
        usage_metadata 是 LangChain 统一的用量字段，含 input_tokens / output_tokens。"""
        msgs = getattr(response, "result", None) or getattr(response, "messages", None) or []
        for msg in reversed(msgs):
            usage = getattr(msg, "usage_metadata", None)
            if usage:
                return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
        return 0, 0