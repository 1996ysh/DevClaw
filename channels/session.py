"""channels/session.py —— 会话归属：(渠道, 会话) → 稳定的 thread_id

同一个 (channel, conversation_id) 永远映射到同一个 thread_id，
这样：① 同一飞书群的连续对话能续上；② 不同渠道/不同群互不串台。
"""
import hashlib

from channels.base import InboundMessage


def thread_id_for(msg: InboundMessage) -> str:
    """由 (渠道, 会话 id) 稳定派生 thread_id（同输入恒等同输出）。

    用哈希而非拼接，是为了得到定长、无特殊字符的 id（适合做 checkpointer 的 key）。
    """
    raw = f"{msg.channel}:{msg.conversation_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]