"""
slowapi 限流器
按照tenant_id分桶
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from infra.settings import get_settings


def _tenant_key(request)->str:
    """限流维度，把apikey映射到租户，按照tenant_id分桶 """
    api_key = request.headers.get('X-API-Key')
    tenant = get_settings().api_keys.get(api_key) if api_key else None
    return f'tenant:{tenant}' if tenant else get_remote_address(request)

limiter = Limiter(
    key_func=_tenant_key,
    storage_uri=get_settings().redis_url,
    default_limits=[]
)