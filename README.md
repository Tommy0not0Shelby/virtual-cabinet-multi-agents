# 虚拟内阁 (Virtual Cabinet) - Multi-Agent System 🏛️

这是一个轻量级、高度可扩展的基于大模型 (LLM) 的**多智能体 (Multi-Agent System) 架构**项目。
它的设计灵感来源于古代朝廷的“内阁制度”，其中由“大内总管”(Router) 负责意图识别与任务分发，由“六部尚书”(Workers) 并发处理各类专业任务（如写代码、写文案、分析数据等）。

整个系统最终挂载于 **Supabase (Serverless + Worker)** 架构上。通过 Supabase Edge Function 接收飞书的 Webhook 回调指令，并通过 Python 后台 Worker 异步处理并返回具有【处理人】标识的综合交互卡片。

## 🌟 核心特性
1. **Supervisor-Worker 模式**：任务按需被划分为多个子任务，交给不同的专用 Prompt 生成器处理。
2. **异步并发处理 (Async Execution)**：集成 `AsyncOpenAI` 与 `asyncio.gather`，并发触发多个部门协作，极大提升响应速度。
3. **Serverless 消息总线解耦**：移除原有的 FastAPI 依赖，利用 Supabase Edge Function 承接高并发 Webhook 请求，通过 PostgreSQL 数据库表 (`feishu_messages`) 实现可靠的消息队列。
4. **隔离长记忆 (Session Memory)**：拥有 `memory_manager.py`，根据用户的 `user_id`（飞书 OpenID）隔离聊天上下文，支持多轮自然对话与追问。
5. **功能挂载体系 (Tools/Function Calling)**：所有的 Agent 都可以调用本地的 Python 函数（如联网搜索、获取时间、读取文件），通过 JSON Schema 实现技能无缝扩充。
6. **高度解耦设计**：
    - `agents/`：纯粹的 Markdown 提示词集，热更新无需重启服务。
    - `config/agents_config.json`：定义处理者所用的模型型号及能力介绍。
    - `notion_client.py`：与外部 Notion 交互的逻辑收拢于此。

## 📁 目录结构

```text
/
├── agents                 # 各级官员（Agent）的人格与能力定义 (Prompt)
│   ├── router.md          # [大内总管] 负责分发和汇总
│   ├── coder.md           # [兵部尚书] 负责代码撰写
│   ├── marketer.md        # [礼部尚书] 负责文宣起草
│   └── analyst.md         # [户部尚书] 负责报表与商业分析
├── config
│   └── agents_config.json # 定义各类 Agent 所依赖的模型和对应的 prompt
├── supabase/functions/     
│   └── feishu-webhook/    # ⚡ Supabase Edge Function 接收 Webhook 并存入数据库
├── agent_manager.py       # 👑 核心调度控制层（含 Pydantic 数据结构与 Async 并发分发）
├── memory_manager.py      # 🧠 会话长记忆管理器
├── tools.py               # 🛠️ 供 Agent 驱动的外部扩展能力集 (Function Calling)
├── notion_client.py       # 📝 Notion 操作封装层
├── schema.sql             # 🗄️ Supabase 数据库表结构定义
└── worker.py              # 🚀 后台 Python Worker，轮询 Supabase 消息并处理
```

## 🚀 起步指南

**1. 准备数据库环境**
- 登录 [Supabase](https://supabase.com/) 控制台，在 SQL Editor 中运行本项目中的 `schema.sql`，建立 `feishu_messages` 消息表。
- 获取你的 Supabase 项目 URL 和 Service Role Key。

**2. 部署 Webhook Node 函数**
- 安装 [Supabase CLI](https://supabase.com/docs/guides/cli)。
- 登录后执行部署命令将 Edge Function 部署至云端：
```bash
supabase functions deploy feishu-webhook
```
- 在飞书开放平台将回调地址配置为该 Edge Function 的 URL。

**3. 配置环境变量与启动 Worker**
推荐使用 Python 3.10+。请确保你已安装依赖：
```bash
pip install openai requests pydantic supabase httpx
```

在使用之前，设置以下环境变量：
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
export FEISHU_APP_ID="your-feishu-app-id"
export FEISHU_APP_SECRET="your-feishu-app-secret"
```

启动本地内阁处理引擎：
```bash
python3 worker.py
```

## 🧪 测试与验证

你可以直接在 Supabase 表中插入一条状态为 `pending` 的测试记录，或使用飞书客户端直接向你的机器人发送消息：

**指令样例：**
- "兵部，给我写一段 Python 快排代码"
- "去查一下今天最新的科技新闻（调用搜索工具），然后给研发部门留个代码作业，并同时发一条朋友圈文案介绍这个新闻（并行处理）"
- "文案太长了，精简到20字以内"

后台的 `worker.py` 会自动捕获数据库中的待处理消息，进行并发处理后，调用飞书开放网络将精美的互动卡片发回给对应请求者。

---
*👑 陛下，全新的无服务器边缘内阁已备妥当。*
