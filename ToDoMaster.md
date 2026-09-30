# DevClaw 掌握清单（ToDoMaster）

> 目标：系统掌握本仓库从「本地 Agent」到「可部署多渠道服务」所需的知识与技能。  
> 用法：按章节推进；完成一项把 `- [ ]` 改成 `- [x]`。详细架构与 FAQ 见 [`架构设计与FAQ.md`](./架构设计与FAQ.md)。

---

## 0. 环境与工程基础

- [ ] 安装并会用 **Python 3.14** + **uv**（`uv sync` / `uv run` / `uv add`）
- [ ] 读懂并维护根目录 `.env`（前缀 `SYC_`），知道哪些是密钥、不能提交
- [ ] 本地起依赖：**PostgreSQL**、**Redis**（与 `infra/settings.py` 默认值对齐）
- [ ] Windows 本地用正确入口：`uv run python -m api`（理解 Proactor vs Selector + psycopg）
- [ ] 会跑测试：`uv run pytest`，并遵守「改代码必带测试」

---

## 1. 团队靶场约定（订单微服务规范）

- [ ] 读透 [`AGENTS.md`](./AGENTS.md)：Decimal 金额、类型注解与 docstring、snake_case / camelCase
- [ ] 熟悉 `app/` 与 `tests/` 作为 Agent 演练靶场的角色
- [ ] 能按规范手写一版定价 / 简单 FastAPI 接口，并补 pytest

---

## 2. Agent / LLM 编排核心

- [ ] 理解 **DeepAgents**：`create_deep_agent`、backend、skills、memory、subagents
- [ ] 理解 **LangChain**：`init_chat_model`、工具、messages、OpenAI 兼容端点
- [ ] 理解 **LangGraph**：`ainvoke` / `astream`、`thread_id`、checkpointer、store
- [ ] 分清 `build_agent`（本地文件后端）与 `build_sandbox_agent`（沙箱团队版）
- [ ] 会读 `main.py` 里 system_prompt / middleware / tools 的拼装方式

---

## 3. 多角色子代理与工具

- [ ] 掌握五角色分工：planner / researcher / coder / tester / reviewer（`subagents/profile.py`）
- [ ] 理解「子代理不继承主 prompt」→ 为何要重复路径规则
- [ ] 会用 `tools/registry.py` 按组取工具（git / search / test）
- [ ] 了解 **Skills**（`skills/*/SKILL.md`）与 **MCP**（`tools/mcp.py`）的差异与接入点
- [ ] 了解 Reviewer **结构化输出**（`response_format` / `ReviewResult`）

---

## 4. 多模型路由与弹性

- [ ] 掌握档位概念：`strong` / `standard` / `cheap`（`infra/llm_router.py`）
- [ ] 掌握角色 → 档位映射，换模型只改配置不改业务代码
- [ ] 理解 `ModelFallbackMiddleware` 降级链（`infra/fallback.py`）
- [ ] 理解 `LLMConcurrencyMiddleware` 进程内并发上限

---

## 5. 中间件与可观测

- [ ] 工具审计：`ToolAuditMiddleware`
- [ ] Token / 成本：`CostMeterMiddleware`
- [ ] 请求上下文：`RequestContextMiddleware`
- [ ] Prometheus：`obs/metrics.py`、`/metrics`、多进程 `PROMETHEUS_MULTIPROC_DIR`
- [ ] （可选）LangSmith：`export_langsmith_env` 开关与项目名配置

---

## 6. 渠道与会话模型

- [ ] 掌握 `InboundMessage` 归一化设计（`channels/base.py`）
- [ ] 掌握 `handle_message` 为渠道无关核心（`channels/handler.py`）
- [ ] 掌握 `thread_id_for(tenant, channel, conversation)` 防串台（`channels/session.py`）
- [ ] 至少跟通一条渠道：CLI / Webhook / 飞书（WS 或回调）之一

---

## 7. FastAPI 服务化

- [ ] 读懂 `api/app.py` 的 **lifespan**：PG 池、checkpointer、store、Redis、arq
- [ ] 掌握依赖注入：`Depends(get_checkpointer/get_store)`、`app.state`
- [ ] 同步接口：`POST /issues`、续聊 `thread_id`
- [ ] 鉴权：`gateway/auth.py` 的 `X-API-Key` → `tenant_id`
- [ ] 限流：`gateway/limiter.py` + Redis + 按租户分桶
- [ ] 健康检查：`/healthz`、`/readyz`；统一异常不泄漏堆栈

---

## 8. 异步任务两种方案

- [ ] 方案一：`POST /tasks` + FastAPI BackgroundTasks + PG 任务表（`tasks/store.py`）
- [ ] 方案二：`POST /jobs` + **arq** Worker（`tasks/worker.py`），会独立启动 Worker
- [ ] 能说清两种方案的扩缩与适用场景（演示 vs 生产）

---

## 9. 沙箱隔离执行

- [ ] 理解「沙箱即手脚」：宿主机干净、密钥不进沙箱
- [ ] 掌握 seed 流程：上传 `app/`、`tests/`、`skills/`、`AGENTS.md` 到 workdir
- [ ] 掌握绝对路径约束与常见坑（`permission denied`、`path_not_found`）
- [ ] 了解 Docker 自托管 vs Daytona；会看 `SYC_SANDBOX_*` 配置
- [ ] 理解按 `thread_id` 隔离 + `finally` 回收（`agent/dispatcher.py`）

---

## 10. 部署与运维

- [ ] 读懂 `Dockerfile` 与 `docker-compose.prod.yml`（web / worker / feishu / pg / redis / 监控）
- [ ] 理解为何监控端口绑 `127.0.0.1`、业务端口可用非常见端口
- [ ] （可选）Gunicorn 多 worker 与 Prometheus 多进程指标
- [ ] （可选）Locust 压测目录 `loadtest/`

---

## 11. 评测与质量

- [ ] 会跑 `uv run python -m eval.run_eval`
- [ ] 区分编码题（沙箱执行评分）与开放题（LLM 裁判）
- [ ] 理解多次采样、均值/方差与 baseline 对照的意义

---

## 12. 建议掌握的「外部知识」清单

下列不专属于本仓库文件，但是做 DevClaw 类项目的硬前置：

### 语言与工程

- [ ] Python 异步（`async/await`、事件循环、连接池）
- [ ] 类型注解与 Pydantic v2 / `pydantic-settings`
- [ ] pytest 基础与异步测试习惯
- [ ] Git 工作流与 PR 习惯（祈使句 commit）

### Web 与数据

- [ ] FastAPI：路由、Depends、lifespan、中间件、CORS
- [ ] PostgreSQL 基础；知道 checkpoint/store 表由框架 setup
- [ ] Redis 基础：作为限流存储与任务队列后端

### Agent 生态

- [ ] LLM API 调用模式、温度、重试、超时
- [ ] Tool Calling / Function Calling 概念
- [ ] Agent = 模型 + 工具 + 状态 + 编排（与本仓库中间件对应）
- [ ] 多 Agent / 子代理委派的成本与边界

### 安全与生产意识

- [ ] API Key / 租户隔离 / 限流
- [ ] 沙箱与最小权限；密钥管理（SecretStr、.env）
- [ ] 可观测：日志（loguru）、指标、链路（可选 LangSmith）
- [ ] 长任务：队列、超时、失败状态、资源回收

---

## 13. 推荐实践路径（按周）

| 阶段 | 建议动作 | 对应章节 |
|------|----------|----------|
| 第 1 周 | 环境跑通 + 读 AGENTS + 改 `app/` 小功能并加测 | 0、1 |
| 第 2 周 | 跟通 `build_agent` 与 `/issues` 续聊 | 2、7 |
| 第 3 周 | 子代理 + 工具 + 模型档位 | 3、4 |
| 第 4 周 | 渠道归一化 + 租户鉴权限流 | 6、7 |
| 第 5 周 | 沙箱 Issue 全流程 + 回收 | 9 |
| 第 6 周 | arq Worker + Compose 部署 + metrics | 8、10 |
| 持续 | Eval 基线、中间件埋点、Skills 扩展 | 5、11 |

---

## 14. 完成标准（自检）

当你能够不看文档独立完成下面几件事，可视为「已掌握本项目主干」：

1. 本地 `uv run python -m api`，用 API Key 调通安全 Issue，并验证同 `thread_id` 续聊。  
2. 改一处订单靶场逻辑，补 pytest，并说明为何用 Decimal。  
3. 讲清一次沙箱 Issue：seed → 委派 → 测试 → stop。  
4. 把一个长任务改成 arq 入队，并能查 `job_id` 结果。  
5. 指出换模型、加渠道、加工具各自应该改哪几个文件。  

更细的架构图、链路与 FAQ 请直接查阅：[`架构设计与FAQ.md`](./架构设计与FAQ.md)。
