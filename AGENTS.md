# 订单微服务 团队约定 (常驻记忆)


## 项目

- 技术栈：python 3.14 + FastAPI；包管理器用uv
- 目录：源码在app/，测试在tests/，定价逻辑集中在app/pricing.py
- Windows 本地启动 API：`uv run python -m api`（勿直接 `uvicorn api.app:app`，Proactor 与 psycopg 异步不兼容）

## 必须遵守

- 金额一律用Decimal计算，**禁止使用float做货币运算**
- 所有公开函数带类型注解和docstring
- 任何代码改动都必须附带对应的pytest测试

## 风格

- 内部命名使用snake_case；对外API字段用camelCase(有pydantic alias处理)
- 提交信息使用祈使句，一行概述+可选正文
