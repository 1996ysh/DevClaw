"""
agent/main.py —— 构建 DevMate 主 Agent
- 用官方唯一的工厂 create_deep_agent 构建；
- system_prompt 是 DevMate 的"领域人设"，会追加到 DeepAgents 内置提示词之后
"""
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from infra.logging import get_logger
from infra.settings import get_settings
from middleware.audit import ToolAuditMiddleware
from middleware.context import RequestContextMiddleware
from middleware.cost import CostMeterMiddleware
from sandbox.docker_manager import create_one_sandbox, seed_project
from sandbox.manager import get_or_create_sandbox_backend
from subagents.profile import build_subagents
from tools.mcp import MCPManager
from tools.registry import get_tools
load_dotenv()
logger = get_logger()
# 项目根目录（agent 的文件读写圈在这里，virtual_mode 挡掉越权）
PROJECT_ROOT = Path(__file__).resolve().parent
def build_backend():
    """本地开发用 FilesystemBackend，圈在项目根目录内"""
    return FilesystemBackend(root_dir=PROJECT_ROOT, virtual_mode=True)
logger = get_logger()
DEVMATE_SYSTEM_PROMPT = """你是 DevMate，一个严谨的研发助手，服务于一个 Python / FastAPI 订单微服务团队。

工作准则：
- 动手前先用 write_todos 写出清晰的任务清单，并随进展更新它。
- 写代码遵循团队规范：类型注解齐全、函数职责单一、关键逻辑配 docstring。
- 不臆测：信息不足时先用 read_file / grep 读相关文件再动手。
- 每次改动后，用一两句话说明"改了什么、为什么这么改"。
"""
##构建沙箱
async def build_sandbox_backend():
    """
    按照SYC_SANDBOX_PROVIDER 选用沙箱后端 返回(backend,workdir)
    docker ->子托管加固容器
    daytona->外部托管沙箱
    """
    s = get_settings()
    if s.sandbox_provider == "docker":
        sb = await create_one_sandbox()
        await seed_project(sb)
        return sb, s.sandbox_workdir
    else:
        backend,sandbox,client,workdir = get_or_create_sandbox_backend("default")
        return backend,workdir


def build_model():
    s = get_settings()
    return init_chat_model(
        model=s.model_name,
        model_provider=s.model_provider,
        api_key=s.api_key.get_secret_value(),  # SecretStr 在真正用时才解开
        base_url=s.base_url,
        temperature=0,
        max_retries=s.max_retries,
        timeout=s.timeout,
    )
async def build_sandbox_agent(thread_id:str,user_id: str = "anonymous", channel: str = "cli"):
    """构建 DevMate 主 Agent，返回一个已编译的 LangGraph 图。

    注意：创建只用 create_deep_agent（官方唯一工厂）。
    "异步"体现在调用阶段——我们之后用 agent.ainvoke / agent.astream。
    """
    #这里的virtual_mode参数为是否允许agent读写文件
    #本地文件back
    # backend = FilesystemBackend(root_dir=str(PROJECT_ROOT),virtual_mode=True)
    mcp_tools = await MCPManager.from_settings().get_tools()
    # workdir 是沙箱工作目录（Daytona 默认 /home/daytona），项目就 seed 在它下面
    sandbox_backend, sandbox, client, workdir = get_or_create_sandbox_backend(thread_id)
    agent = create_deep_agent(
        model=build_model(),
        system_prompt=DEVMATE_SYSTEM_PROMPT+(
            f"\n\n【执行环境与路径规则——必须严格遵守】"
            f"\n你运行在一个沙箱里，项目代码已位于 `{workdir}/` 下（含 `{workdir}/app/`、`{workdir}/tests/`）。"
            f"\n⚠️ 所有文件操作（write_file/edit_file/read_file）和命令（execute）都【必须】使用以 `{workdir}/` 开头的【绝对路径】。"
            f"\n✅ 正确：写测试到 `{workdir}/tests/test_pricing.py`、改代码 `{workdir}/app/pricing.py`、"
            f"跑测试 `cd {workdir} && python -m pytest -q`。"
            f"\n❌ 错误（会因权限被拒绝，绝不要这样）：`/test_pricing.py`、`test_pricing.py`、`/app/pricing.py` 这类根路径或相对路径。"
            f"\n如果你不确定某文件在哪，先用 `ls {workdir}` 查看，再用绝对路径操作。"
            "\n\n你是团队负责人：对复杂 Issue，先用 task() 委派给 planner 规划，"
            "再依次委派 researcher/coder/tester/reviewer。你只做协调，不亲自写大量代码。"
            "委派时，把上面的【绝对路径规则】一并转达给子代理。"
        ),
        backend=sandbox_backend,
        # backend=  build_sandbox_backend(),
        subagents=build_subagents(workdir),
        tools=get_tools("git", "search", "test")+mcp_tools,
        skills=[f"{workdir}/skills"],
        memory=[f"{workdir}/AGENTS.md"],
        middleware=[
            RequestContextMiddleware(user_id=user_id, channel=channel),
            ToolAuditMiddleware(),
            CostMeterMiddleware(),
        ],
        #memorySaver()是把数据存放到Python 进程的内存
        #如果运行进程结束这个数据就会丢失
        checkpointer=MemorySaver(),
    )
    logger.info("DevMate 主 Agent 构建完成：model={}", get_settings().model_name)
    logger.info("DevMate 团队版构建完成：5 子代理 + 沙箱后端（项目已 seed 到 {}）", workdir)
    return agent,sandbox, client
# agent/main.py（节选：build_agent 接收外部 checkpointer/store）
def build_agent(checkpointer=None, store=None, user_id="anonymous", channel="api"):
    """服务化版：checkpointer/store 由外部（lifespan）传入并复用。

    不传时退化为内存（仅供脚本/测试），传入则用 Postgres 持久化。
    """
    backend = FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True)
    return create_deep_agent(
        model=build_model(),
        system_prompt=DEVMATE_SYSTEM_PROMPT,
        backend=backend,
        skills=[str(PROJECT_ROOT / "skills")],
        memory=[str(PROJECT_ROOT / "AGENTS.md")],
        tools=get_tools("git", "search"),
        middleware=[
            RequestContextMiddleware(user_id=user_id, channel=channel),
            ToolAuditMiddleware(),
            CostMeterMiddleware(),
        ],
        checkpointer=checkpointer,      # ← 外部传入（lifespan 的 AsyncPostgresSaver）
        store=store,                    # ← 外部传入（lifespan 的 AsyncPostgresStore）
    )
