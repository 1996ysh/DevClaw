---
name: fast-api-endpoint
description: 当需要在订单服务里新增或修改fastapi接口(路由、请求/响应模型、错误处理)时使用本规范
---
# Fastapi接口编码规范


## 路由

- 用APIRouter按资源分模块，前缀清晰(/orders,/users)
- 路径用名词复数；动作交给HTTP方法表达，不在URL里写动词

## 请求 / 响应模型

- 入参与出参一律用pydantic模型，禁止裸dict
- 用response_model = 显式声明响应模型，避免泄露内部字段

## 错误处理

- 业务错误抛出HTTPException,带明确status_code与简短detail。
- 不把内部异常信息透露给客户端
