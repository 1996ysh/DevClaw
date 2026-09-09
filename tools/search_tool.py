from langchain_core.tools import tool


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """联网搜索，返回与 query 最相关的若干结果摘要。
    用于需要查阅外部最新信息（如某库的最新用法、报错原因）时。"""

    return f"[web_search 占位] 这里应返回关于「{query}」的前 {max_results} 条结果。"


@tool
async def fetch_url(url: str) -> str:
    """抓取给定 URL 的网页正文，用于阅读某个具体文档/页面。"""
    return f"[fetch_url 占位] 这里应返回 {url} 的正文内容。"