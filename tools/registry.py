"""
工具注册中心：按用途分组登记，供主 Agent / 子代理按需取用。
"""
from tools.git_tools import git_commit, git_diff, git_status, open_pull_request
from tools.search_tool import fetch_url, web_search
from tools.test_tools import run_pytest

# 按用途分组登记
_GROUPS: dict[str, list] = {
    "git": [git_status, git_diff, git_commit, open_pull_request],
    "search": [web_search, fetch_url],
    "test": [run_pytest],
}


def get_tools(*groups: str) -> list:
    """按组名取工具列表。例如 get_tools("git", "search")。

    不传参则返回所有已登记工具。

    Args:
        *groups: 工具组名；合法值见 ``_GROUPS`` 的键。

    Returns:
        LangChain Tool 对象列表。

    Raises:
        KeyError: 传入未知组名时抛出。
    """
    if not groups:
        return [t for ts in _GROUPS.values() for t in ts]
    out: list = []
    for g in groups:
        if g not in _GROUPS:
            raise KeyError(f"未知工具组：{g}，可选：{list(_GROUPS)}")
        out.extend(_GROUPS[g])
    return out


def list_tool_groups() -> list[str]:
    """返回已登记的工具组名列表。"""
    return sorted(_GROUPS.keys())
