"""
用 @tool 把对 git 的封装暴露成工具。docstring 写清楚用途，模型据此决定何时调用。
本地开发阶段先用 subprocess 演示。
"""
from langchain_core.tools import tool

from infra.logging import get_logger
import asyncio
logger = get_logger()
async def _run(cmd: list[str], cwd: str = ".") -> str:
    """异步跑一条命令，返回 stdout（出错则返回 stderr）。
    cmd：命令参数
    cwd：工作目录
    """

    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        return f"[git error] {err.decode().strip()}"
    return out.decode().strip() or "(ok)"
@tool
async def git_status() -> str:
    """查看当前 Git 仓库的状态（git status），返回有哪些改动、是否干净。"""
    return await _run(["git", "status", "--short"])


@tool
async def git_diff(path: str = "") -> str:
    """查看 Git 改动的具体内容（git diff）。可选 path 只看某个文件/目录的 diff。"""
    cmd = ["git", "diff"]
    if path:
        cmd.append(path)
    return await _run(cmd)


@tool
async def git_commit(message: str) -> str:
    """把当前已暂存的改动提交（git add -A && git commit）。message 是提交信息。
    用于在完成一处代码改动、并希望记录一个提交点时调用。"""
    await _run(["git", "add", "-A"])
    return await _run(["git", "commit", "-m", message])


@tool
async def open_pull_request(title: str, body: str = "") -> str:
    """在当前分支创建一个 Pull Request（gh pr create）。title 是标题，body 是内容。"""
    cmd = ["gh", "pr", "create", "--title", title, "--body", body or title]
    return await _run(cmd)