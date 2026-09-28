# 电商售后多智能体系统

基于 LangGraph、DeepSeek、PostgreSQL 和 pgvector 实现的电商售后 Agent 项目。

系统可以识别用户售后意图，并将请求路由到物流、退款或退换货专业 Agent。各 Agent 通过 Function Calling 查询订单和政策、创建内部工单，并通过 PostgreSQL 保存业务数据及多轮会话状态。

## 核心能力

- 多智能体路由：物流、退款、退换货和人工兜底
- DeepSeek Function Calling 工具调用
- LangGraph 状态图与条件路由
- PostgreSQL 工单持久化
- 待处理工单幂等控制
- PostgreSQL Checkpointer 多轮会话记忆
- 基于 `user_id` 和 pgvector 的跨会话长期记忆
- 只从可信工具结果中提取记忆，支持幂等更新、过期和删除
- pgvector 售后政策 RAG
- 订单状态元数据过滤与向量检索
- FastAPI HTTP 接口
- MCP Streamable HTTP 工具服务
- 请求 ID、耗时和工具轨迹结构化日志
- 单元测试、集成测试和 Agent 评测

## 系统架构

```text
用户请求
   │
   ▼
FastAPI / MCP
   │
   ▼
售后问题分流 Agent
   ├── logistics       → 物流 Agent
   ├── refund          → 退款 Agent
   ├── return_exchange → 退换货 Agent
   └── human_handoff   → 人工客服兜底
          │
          ▼
订单、物流、政策和工单工具
          │
          ├── PostgreSQL：工单与会话状态
          └── pgvector：售后政策与用户长期记忆检索
```

## 业务流程

### 物流催办

```text
验证订单
→ 查询真实物流状态
→ 仅 delayed 状态允许创建催办工单
→ 返回内部工单结果
```

### 退款申请

```text
验证订单
→ 根据真实订单状态检索退款政策
→ 创建或复用退款审核工单
→ 明确说明退款尚未完成
```

### 退换货申请

```text
验证订单
→ 根据真实订单状态检索退换货政策
→ 有适用政策时创建审核工单
→ 明确说明仍需工作人员审核
```

## 技术栈

- Python 3.13
- LangGraph
- LangChain
- DeepSeek
- FastAPI
- MCP Python SDK
- PostgreSQL 17
- pgvector
- SQLAlchemy 2
- Alembic
- Sentence Transformers
- Docker Compose
- pytest

## 项目结构

```text
app/
├── api.py                       # FastAPI 接口
├── multi_agent.py               # 多智能体路由
├── persistent_multi_agent.py    # PostgreSQL 会话持久化入口
├── long_term_memory.py           # 跨会话长期记忆存储与检索
├── agent.py                     # 物流 Agent
├── refund_agent.py              # 退款 Agent
├── return_exchange_agent.py     # 退换货 Agent
├── triage.py                    # 售后问题分类与路由
├── tools.py                     # Function Calling 工具
├── policy_service.py            # 政策向量检索
├── ticket_service.py            # 工单持久化与幂等控制
├── mcp_server.py                # MCP 工具服务
└── observability.py             # 结构化运行日志

data/                            # 模拟政策数据
evaluation/                      # Agent 与 RAG 评测
migrations/                      # Alembic 数据库迁移
scripts/                         # 初始化及验证脚本
tests/                           # 单元测试和集成测试
```

## 本地运行

### 1. 创建虚拟环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例配置：

```powershell
Copy-Item ".env.example" ".env"
```

编辑 `.env`，填写 DeepSeek API Key 和 PostgreSQL 密码。

### 3. 启动 PostgreSQL

```powershell
docker compose up -d
docker compose ps
```

### 4. 初始化数据库

```powershell
python -m alembic upgrade head
python -m scripts.setup_checkpointer
python -m scripts.index_policies
```

首次执行政策索引时会下载 Embedding 模型。

### 5. 启动 FastAPI

```powershell
python -m uvicorn app.api:app --reload
```

接口文档：

- Swagger UI：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- Agent 接口：`POST /api/v1/chat`

请求示例：

```json
{
  "message": "订单 ORD-1001 我不想要了，帮我退款",
  "thread_id": "demo-thread-001",
  "user_id": "demo-user-001"
}
```

- 相同 `thread_id` 会复用 PostgreSQL Checkpoint 中的当前会话状态。
- 相同 `user_id` 可以跨不同 `thread_id` 检索已验证的历史工单记忆。
- 长期记忆只从可信工具结果中提取，不直接保存模型推测。

## MCP 服务

启动 MCP Streamable HTTP 服务：

```powershell
$env:PYTHONPATH = (Get-Location).Path
mcp run app/mcp_server.py:mcp --transport streamable-http
```

验证服务：

```powershell
python -m scripts.check_mcp_http
```

当前暴露 8 个 MCP 工具：

- `get_order`
- `get_logistics`
- `get_ticket_status`
- `search_refund_policy`
- `search_return_exchange_policy`
- `create_logistics_expedite_ticket`
- `create_refund_review_ticket`
- `create_return_exchange_review_ticket`

写工具具有业务校验和幂等保护，不直接代表外部业务操作已经完成。

## 测试

运行单元测试：

```powershell
python -m pytest -q
```

运行集成测试前需要启动 PostgreSQL，并配置有效的 DeepSeek API Key：

```powershell
python -m pytest tests/integration/check_ticket_service.py -q
python -m pytest tests/integration/check_memory_agent.py -q
python -m pytest tests/integration/check_persistent_memory_agent.py -q
python -m pytest tests/integration/check_long_term_memory.py -q
python -m pytest tests/integration/check_deepseek.py -q
```

## 评测

多智能体评测：

```powershell
python -m evaluation.evaluate_multi_agent
```

政策检索评测：

```powershell
python -m evaluation.evaluate_policy_retrieval evaluation/policy_retrieval_cases.json
python -m evaluation.evaluate_policy_retrieval evaluation/policy_retrieval_holdout_cases.json
```

项目评测覆盖：

- 路由是否正确
- 工具名称与参数是否正确
- 是否发生越权工具调用
- 是否出现无依据的业务承诺
- 政策检索 Hit@1、Hit@3 和 MRR
- 响应耗时和工具调用次数

## 安全与业务边界

- 用户输入不能跳过订单和物流状态验证
- 物流状态不是 `delayed` 时不能创建催办工单
- 退款与退换货操作只创建内部审核工单
- Agent 不得声称退款、换货或物流催办已经实际完成
- 写工具使用数据库约束与应用层查询实现幂等
- API Key 和数据库密码只保存在本地 `.env` 中
