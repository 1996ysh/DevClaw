from uuid import uuid4

from fastapi import APIRouter, Depends
from starlette.requests import Request

from api.deps import get_store, get_checkpointer
from api.schema import IssueResponse, IssueRequest
from channels.base import InboundMessage
from channels.handler import handle_message
from gateway.auth import require_api_key
from main import build_agent

# 定义路由
router = APIRouter(prefix="/issues", tags=["业务相关issues"])

# 使用装饰器将当前函数注册为一个POST请求路由
@router.post('',response_model=IssueResponse)
async  def submit_issue(
        req:IssueRequest,
        checkpointer = Depends(get_checkpointer),
        store=Depends(get_store),
)-> IssueResponse:
    # thread_id：客户端传了就用它（续聊/断点续跑），没传就新建
    thread_id = req.thread_id or uuid4().hex
    # 构建 agent（轻组装），传入共享的持久化资源
    agent =  build_agent(
        checkpointer=checkpointer,
        store=store,
        user_id=req.user_id,
        channel=req.channel,
    )
    # 异步调用，带 thread_id —— 同一 thread_id 下次请求会带着历史上下文继续
    result =  await agent.ainvoke(
        {"messages": [{"role": "user", "content": req.issue}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    reply = result["messages"][-1].content if result.get("messages") else ""
    return IssueResponse(thread_id=thread_id, reply=reply)

@router.post('/secure')
async def submit_issue_secure(
        req:IssueRequest,
        request: Request,
        tenant_id:str = Depends(require_api_key)
):
    """需要X-API-Key的端点；租户身份贯穿到会话隔离"""
    inbound = InboundMessage(
        channel=req.channel,
        user_id=req.user_id,
        text=req.issue,
        conversation_id=req.thread_id or req.user_id,
    )
    reply = await handle_message(
        inbound,
        request.app.state.checkpointer,
        request.app.state.store,
        tenant_id=tenant_id,
    )
    return {'reply': reply,'tenant':tenant_id}