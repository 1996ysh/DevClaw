"""
工具注册中心
"""
from test.test_tool import run_pytest
from tools.git_tools import git_status, git_commit, open_pull_request, git_diff
from tools.search_tool import web_search, fetch_url

# 按用途分组登记
_GROUPS: dict[str, list] = {
    "git": [git_status, git_diff, git_commit, open_pull_request],
    "search": [web_search, fetch_url],
    "test": [run_pytest],
}
def get_tools(*groups: str) -> list:
    """按组名取工具列表。例如 get_tools("git", "search")。
    不传参则返回所有已登记工具。"""
    if not groups:
        # 扁平化一个二维列表 eg{'a':[1, 2], 'b': [3, 4]} -> [1, 2, 3, 4]
        return [t for ts in _GROUPS.values() for t in ts]
    out: list = []
    for g in groups:
        if g not in _GROUPS:
            raise KeyError(f"未知工具组：{g}，可选：{list(_GROUPS)}")
        out.extend(_GROUPS[g])
    return out