"""联网搜索与网页抓取工具。

默认走 DuckDuckGo HTML 结果页（无需 API Key，适合自托管）；
抓取侧用 httpx + 标准库 HTMLParser，并对私网地址做 SSRF 防护。
"""
from __future__ import annotations

import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from langchain_core.tools import tool

from infra.logging import get_logger
from infra.settings import get_settings

logger = get_logger()

_DEFAULT_UA = (
    "Mozilla/5.0 (compatible; DevClawBot/0.1; +https://github.com/devclaw)"
)
_SKIP_TAGS = frozenset({"script", "style", "noscript", "svg", "iframe"})


class _TextExtractor(HTMLParser):
    """从 HTML 中抽取可见文本，跳过 script/style 等噪声标签。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        """返回合并后的可见文本。"""
        return "\n".join(self._chunks)


class _DuckDuckGoResultParser(HTMLParser):
    """解析 DuckDuckGo HTML 结果页中的标题、链接与摘要。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.results: list[dict[str, str]] = []
        self._in_title = False
        self._in_snippet = False
        self._current: dict[str, str] | None = None
        self._title_buf: list[str] = []
        self._snippet_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        classes = set(attr_map.get("class", "").split())
        if tag == "a" and "result__a" in classes:
            href = attr_map.get("href", "")
            self._current = {
                "title": "",
                "url": _unwrap_ddg_redirect(href),
                "snippet": "",
            }
            self._in_title = True
            self._title_buf = []
        elif tag in {"a", "td"} and (
            "result__snippet" in classes or "result-snippet" in classes
        ):
            self._in_snippet = True
            self._snippet_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title and self._current is not None:
            self._current["title"] = "".join(self._title_buf).strip()
            self._in_title = False
            if self._current["url"] and self._current["title"]:
                self.results.append(self._current)
            self._current = None
        elif tag in {"a", "td"} and self._in_snippet:
            snippet = "".join(self._snippet_buf).strip()
            self._in_snippet = False
            if self.results and not self.results[-1].get("snippet"):
                self.results[-1]["snippet"] = snippet

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_buf.append(data)
        elif self._in_snippet:
            self._snippet_buf.append(data)


def _unwrap_ddg_redirect(href: str) -> str:
    """把 DuckDuckGo 跳转链接还原为真实目标 URL。"""
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return unquote(qs["uddg"][0])
    return href


def html_to_text(html: str) -> str:
    """将 HTML 转为可见纯文本。

    Args:
        html: 原始 HTML 字符串。

    Returns:
        去除脚本/样式后的纯文本；连续空行会被压缩。
    """
    extractor = _TextExtractor()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:  # noqa: BLE001 坏 HTML 时尽量返回已解析部分
        logger.warning("HTML 解析不完整，返回已抽取文本")
    text = extractor.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_private_or_local(host: str) -> bool:
    """判断主机名是否指向回环/链路本地/私网地址。"""
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        return True
    try:
        addr = ipaddress.ip_address(lowered)
        return bool(
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        )
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(lowered, None)
    except socket.gaierror:
        return True  # 解析失败一律拒绝，避免绕过
    for info in infos:
        ip_str = info[4][0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
        ):
            return True
    return False


def assert_public_http_url(url: str, *, allow_private: bool = False) -> str:
    """校验 URL 方案与主机，默认拒绝私网目标以防 SSRF。

    Args:
        url: 待校验 URL。
        allow_private: 为 True 时允许 localhost/私网（仅测试/内网场景）。

    Returns:
        规范化后的 URL 字符串。

    Raises:
        ValueError: URL 非法或命中私网防护时抛出。
    """
    raw = (url or "").strip()
    if not raw:
        raise ValueError("url 不能为空")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("仅支持 http/https URL")
    host = parsed.hostname
    if not host:
        raise ValueError("URL 缺少主机名")
    if not allow_private and _is_private_or_local(host):
        raise ValueError(f"拒绝访问私网/回环地址：{host}")
    return raw


def format_search_results(results: list[dict[str, str]]) -> str:
    """把搜索结果列表格式化为模型易读的多行文本。

    Args:
        results: 每项含 title / url / snippet。

    Returns:
        编号列表文本；空结果时返回提示语。
    """
    if not results:
        return "未找到相关搜索结果。"
    lines: list[str] = []
    for i, item in enumerate(results, start=1):
        title = item.get("title") or "(无标题)"
        url = item.get("url") or ""
        snippet = item.get("snippet") or ""
        block = f"{i}. {title}\n   URL: {url}"
        if snippet:
            block += f"\n   摘要: {snippet}"
        lines.append(block)
    return "\n\n".join(lines)


async def search_duckduckgo(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """通过 DuckDuckGo HTML 接口检索，返回结构化结果列表。

    Args:
        query: 搜索关键词。
        max_results: 最多返回条数（会被配置上限截断）。

    Returns:
        ``[{"title", "url", "snippet"}, ...]``。
    """
    q = (query or "").strip()
    if not q:
        return []
    settings = get_settings()
    cap = max(1, min(int(max_results), settings.search_max_results_cap))
    timeout = httpx.Timeout(settings.search_timeout)
    headers = {"User-Agent": _DEFAULT_UA}
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": q},
        )
        resp.raise_for_status()
        parser = _DuckDuckGoResultParser()
        parser.feed(resp.text)
        parser.close()
        # 去重保序
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for item in parser.results:
            url = item.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)
            if len(unique) >= cap:
                break
        return unique


async def fetch_url_text(url: str, *, max_chars: int | None = None) -> str:
    """抓取 URL 并返回正文纯文本（截断到 max_chars）。

    Args:
        url: 目标页面地址。
        max_chars: 返回正文最大字符数；默认读配置 ``fetch_max_chars``。

    Returns:
        可读纯文本；失败时返回以 ``[fetch_url error]`` 开头的说明。
    """
    settings = get_settings()
    try:
        safe_url = assert_public_http_url(
            url, allow_private=settings.fetch_allow_private
        )
    except ValueError as exc:
        return f"[fetch_url error] {exc}"

    limit = settings.fetch_max_chars if max_chars is None else max_chars
    limit = max(500, int(limit))
    timeout = httpx.Timeout(settings.search_timeout)
    headers = {"User-Agent": _DEFAULT_UA, "Accept": "text/html,application/xhtml+xml,*/*"}
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            headers=headers,
            follow_redirects=True,
        ) as client:
            resp = await client.get(safe_url)
            resp.raise_for_status()
            content_type = (resp.headers.get("content-type") or "").lower()
            # 限制体积，避免把超大页面灌进上下文
            raw = resp.content[: settings.fetch_max_bytes]
            text_body = raw.decode(resp.encoding or "utf-8", errors="replace")
            if "html" in content_type or "<html" in text_body[:200].lower():
                body = html_to_text(text_body)
            else:
                body = text_body.strip()
            if len(body) > limit:
                body = body[:limit] + "\n…(已截断)"
            final_url = str(resp.url)
            return f"来源: {final_url}\n\n{body}" if body else f"来源: {final_url}\n\n(页面无可见正文)"
    except httpx.HTTPError as exc:
        logger.warning("fetch_url 失败：{} → {}", url, exc)
        return f"[fetch_url error] 请求失败：{exc}"


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """联网搜索，返回与 query 最相关的若干结果摘要。
    用于需要查阅外部最新信息（如某库的最新用法、报错原因）时。"""
    q = (query or "").strip()
    if not q:
        return "[web_search error] query 不能为空"
    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        return "[web_search error] max_results 必须是整数"
    if max_results <= 0:
        return "[web_search error] max_results 必须为正整数"
    try:
        results = await search_duckduckgo(q, max_results=max_results)
    except httpx.HTTPError as exc:
        logger.warning("web_search 失败：{} → {}", q, exc)
        return f"[web_search error] 搜索请求失败：{exc}"
    except Exception as exc:  # noqa: BLE001
        logger.warning("web_search 异常：{} → {}", q, exc)
        return f"[web_search error] {exc}"
    return format_search_results(results)


@tool
async def fetch_url(url: str) -> str:
    """抓取给定 URL 的网页正文，用于阅读某个具体文档/页面。"""
    return await fetch_url_text(url)
