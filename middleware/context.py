#用 abefore_agent 在每次运行开始时注入 request_id / user_id / 渠道来源。
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime
from typing_extensions import NotRequired
import uuid
from infra.logging import get_logger

logger = get_logger()
class RequestContextState(AgentState):
    """扩展状态：把请求身份带进 agent（NotRequired，调用方可不传）。"""
    request_id: NotRequired[str]
    user_id: NotRequired[str]
    channel: NotRequired[str]

class RequestContextMiddleware(AgentMiddleware):
    """注入/补全请求上下文。"""
    def __init__(self, user_id: str = "anonymous", channel: str = "cli") -> None:
        super().__init__()
        #初始化新增字段
        self.user_id = user_id
        self.channel = channel

    async def abefore_agent(self, state: RequestContextState, runtime: Runtime) -> dict[str, Any] | None:
        request_id = uuid.uuid4().hex[:12]
        logger.info(
            "▶ 开始运行：request_id={} user={} channel={}",
            request_id, self.user_id, self.channel,
        )
        # 节点式钩子：直接 return dict，按 reducer 合并进状态
        return {
            "request_id": request_id,
            "user_id": self.user_id,
            "channel": self.channel,
        }