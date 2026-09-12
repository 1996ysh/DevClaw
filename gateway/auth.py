"""
网关鉴权
用FastAPI依赖注入
"""
from fastapi import Header, HTTPException
from starlette import status

from infra.settings import get_settings


async def require_api_key(x_api_key:str | None = Header(None)):
    """
    校验请求头X-API-KEY 返回它对应的租户表示(这里就仅仅只是返回了租户的标识)
    生产里：key->租户的映射查数据库/配置；这里用settings里配的允许列表演示
    """
    s = get_settings()
    allowed = s.api_keys
    if not x_api_key or x_api_key not in allowed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的api_key"
        )
    return allowed[x_api_key] #返回租户id，供下游使用
