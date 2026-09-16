"""
主模型限流or报错时，自动推到备用模型保证可用性
"""
from langchain.agents.middleware import ModelFallbackMiddleware

from infra.llm_router import get_model


def build_fallback_middleware()->ModelFallbackMiddleware:
    """strong->standard->cheap """
    return ModelFallbackMiddleware(
        get_model('standard'),
        get_model('cheap'),
    )