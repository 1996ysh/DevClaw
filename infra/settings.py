"""
infra/settings.py —— 配置中枢

- 所有 API Key / Base URL / 连接串统一从这里取，不散落在业务代码里
- Pydantic Settings 做类型校验，缺失关键项时给清晰报错
- 字段前缀 SYC_（ShanYangClaw 缩写），避免与系统其他环境变量撞名
"""
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
# 以 settings.py 所在目录为基准定位 .env，避免工作目录不同导致找不到
_BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SYC_",
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 模型 =====
    model_name: str = "glm-5.2"
    model_provider: str = "openai"
    api_key: SecretStr                    # 用 SecretStr，避免密钥被 print/log 泄露
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ===== 连接弹性 =====
    max_retries: int = 12
    timeout: int = 60
    pg_pool_min: int = 2
    pg_pool_max:int = 20
    redis_pool_max:int = 20
    # ===== 持久化底座 =====
    postgres_url: str = "postgresql://root:2005@localhost:5432/DevClaw"
    redis_url: str = "redis://localhost:6379/0"

    # ===== 运行 =====
    log_level: str = "INFO"
    mcp_servers: dict[str, dict] = {}
    model_tiers: dict[str, str] = {
        "strong": "qwen3.8-max",        # 难任务：规划、写代码、审查
        "standard": "glm5.2",     # 中等任务：测试
        "cheap": "qwen-plus",       # 简单任务：读代码、总结
    }
@lru_cache
def get_settings() -> Settings:
    """全进程单例。业务代码统一通过它拿配置。"""
    return Settings()