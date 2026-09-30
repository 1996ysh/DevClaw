"""
用 @tool 把对 git 的封装暴露成工具。docstring 写清楚用途，模型据此决定何时调用。
本地开发阶段先用 subprocess 演示。
"""
from __future__ import annotations

import asyncio
import re

from langchain_core.tools import tool

from infra.logging import get_logger

logger = get_logger()

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_./\\-]+$")


async def run_git(cmd: list[str], cwd: str = ".") -> str:
    """异步执行一条 git/gh 命令，返回 stdout；失败时返回 stderr 摘要。

    Args:
        cmd: 命令参数列表，例如 ``["git", "status", "--short"]``。
        cwd: 工作目录。

    Returns:
        标准输出文本；失败时以 ``[git error]`` 开头。
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        detail = err.decode(errors="replace").strip() or out.decode(errors="replace").strip()
        return f"[git error] {detail}"
    return out.decode(errors="replace").strip() or "(ok)"


@tool
async def git_status() -> str:
    """查看当前 Git 仓库的状态（git status），返回有哪些改动、是否干净。"""
    return await run_git(["git", "status", "--short"])


@tool
async def git_diff(path: str = "") -> str:
    """查看 Git 改动的具体内容（git diff）。可选 path 只看某个文件/目录的 diff。"""
    cmd = ["git", "diff"]
    target = (path or "").strip()
    if target:
        if not _SAFE_PATH.match(target) or ".." in target.split("/"):
            return "[git error] path 含非法字符或路径穿越"
        cmd.append(target)
    return await run_git(cmd)


@tool
async def git_commit(message: str) -> str:
    """把当前已暂存的改动提交（git add -A && git commit）。message 是提交信息。
    用于在完成一处代码改动、并希望记录一个提交点时调用。"""
    msg = (message or "").strip()
    if not msg:
        return "[git error] commit message 不能为空"
    if "\x00" in msg:
        return "[git error] commit message 含非法字符"
    staged = await run_git(["git", "add", "-A"])
    if staged.startswith("[git error]"):
        return staged
    return await run_git(["git", "commit", "-m", msg])


@tool
async def open_pull_request(title: str, body: str = "") -> str:
    """在当前分支创建一个 Pull Request（gh pr create）。title 是标题，body 是内容。"""
    pr_title = (title or "").strip()
    if not pr_title:
        return "[git error] PR title 不能为空"
    cmd = [
        "gh",
        "pr",
        "create",
        "--title",
        pr_title,
        "--body",
        (body or pr_title).strip(),
    ]
    return await run_git(cmd)
