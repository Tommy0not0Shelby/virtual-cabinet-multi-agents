# 虚拟内阁 (Virtual Cabinet) - Multi-Agent System 🏛️

这是一个轻量级、高度可扩展的基于大模型 (LLM) 的**多智能体 (Multi-Agent System) 架构**项目。
它的设计灵感来源于古代朝廷的“内阁制度”，其中由“大内总管”(Router) 负责意图识别与任务分发，由“六部尚书”(Workers) 并发处理各类专业任务（如写代码、写文案、分析数据等）。

整个系统最终挂载于一个 FastAPI 服务上，可以通过飞书的 Webhook 回调接收指令，并返回具有【处理人】标识的综合卡片。

## 🌟 核心特性
1. **Supervisor-Worker 模式**：任务按需被划分为多个子任务，交给不同的专用 Prompt 生成器处理。
2. **异步并发处理 (Async Execution)**：集成 `AsyncOpenAI` 与 `asyncio.gather`，即使触发多个部门协作，也只需等待最慢的那一个，响应速度极快。
3. **隔离长记忆 (Session Memory)**：拥有 `memory_manager.py`，根据用户的 `user_id`（飞书 OpenID）隔离聊天上下文，支持多轮“带有代词”的自然对话与追问。
4. **功能挂载体系 (Tools/Function Calling)**：所有的 Agent 都可以调用本地的 Python 函数（如联网搜索、获取时间、读取文件），通过 JSON Schema 实现技能无缝扩充。
5. **高度解耦设计**：
    - `agents/`：纯粹的 Markdown 提示词集，热更新无需重启服务。
    - `config/agents_config.json`：定义处理者所用的模型型号及能力介绍。
    - `notion_client.py`：所有与外部 Notion 交互的逻辑收拢于此。

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
├── agent_manager.py       # 👑 核心调度控制层（含 Pydantic 数据结构与 Async 并发分发）
├── memory_manager.py      # 🧠 会话长记忆管理器
├── tools.py               # 🛠️ 供 Agent 驱动的外部扩展能力集 (Function Calling)
├── notion_client.py       # 📝 Notion 操作封装层
└── main.py                # 🚀 FastAPI 服务入口，供飞书等调用
```

## 🚀 极速启动

**1. 准备环境**
推荐使用 Python 3.10+，并安装所需依赖包：
```bash
pip install fastapi uvicorn openai requests pydantic
```

**2. 环境变量配置**
在使用之前，请确保你已经向系统环境变量中注入了以下配置（系统兼容 OpenAI 接口标准的任何模型）：
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

**3. 启动 FastAPI 服务**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🧪 测试与验证

你可以直接使用 `curl` 模拟飞书发送的 Webhook 消息来进行本地测试。

**场景一：直达单一部门的常规诉求**
```bash
curl -X POST http://127.0.0.1:8000/webhook/feishu \
    -H "Content-Type: application/json" \
    -d '{"message": {"text": "兵部，给我写一段 Python 快排代码"}, "user_id": "boss_01"}'
```

**场景二：触发并行分发与工具能力 (Async + Tools)**
```bash
curl -X POST http://127.0.0.1:8000/webhook/feishu \
    -H "Content-Type: application/json" \
    -d '{"message": {"text": "去查一下今天最新的科技新闻（调用搜索工具），然后给研发部门留个代码作业，并同时发一条朋友圈文案介绍这个新闻（并行处理）"}, "user_id": "boss_01"}'
```

**场景三：追问（ Memory 验证）**
```bash
curl -X POST http://127.0.0.1:8000/webhook/feishu \
    -H "Content-Type: application/json" \
    -d '{"message": {"text": "文案太长了，精简到20字以内"}, "user_id": "boss_01"}'
```

---
*👑 陛下，一切已准备就绪。*
