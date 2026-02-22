import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from openai import AsyncOpenAI

from notion_client import NotionClient
from memory_manager import MemoryManager
from tools import TOOLS_SCHEMA, AVAILABLE_TOOLS_MAP, execute_tool_call

# ---------------------------------------------------------------------------
# 1. 定义 Pydantic 数据模型，约束 LLM 输出格式
# ---------------------------------------------------------------------------

class Button(BaseModel):
    text: str = Field(description="按钮文案，支持带 emoji")
    action_payload: Optional[str] = Field(None, description="按钮点击后触发的值或动作，可为空")
    recommended: Optional[bool] = Field(False, description="是否为推荐操作（红色按钮）")

class FrontEnd(BaseModel):
    coach_message: str = Field(description="给老板的教练留言，支持 markdown 格式，包含情绪价值和数据总结，需展示各部门处理人信息")
    buttons: List[Button] = Field(default_factory=list, description="飞书卡片底部的交互按钮")

class Action(BaseModel):
    type: str = Field(description="操作类型，如 create_task, update_daily_log, update_project 等")
    database: str = Field(description="要操作的数据库标识，可选: projects, tasks, daily_logs")
    data: Dict[str, Any] = Field(description="具体的属性键值对")
    next: Optional[str] = Field(None, description="后续的动作说明，例如 '等待确认'")

class AgentResponse(BaseModel):
    actions: List[Action] = Field(default_factory=list, description="需要在 Notion 中执行的动作列表")
    front_end: FrontEnd = Field(description="需要发送给老板的飞书卡片内容")

# ---------------------------------------------------------------------------
# MAS (Multi-Agent System) 路由与响应模型
# ---------------------------------------------------------------------------

class Delegation(BaseModel):
    agent_name: str = Field(description="接收任务的部门或Agent名称，必须在 [coder, marketer, analyst] 中选择")
    task_description: str = Field(description="给该部门的具体任务描述")

class RouterPlan(BaseModel):
    direct_actions: List[Action] = Field(default_factory=list, description="大总管直接处理的外部动作，如更新Notion日程等")
    delegations: List[Delegation] = Field(default_factory=list, description="需要分发给各个尚书的业务需求")
    direct_reply: Optional[str] = Field(None, description="如果无需分发业务，直接向老板的汇报或问候的话术")

# ---------------------------------------------------------------------------
# 2. 从配置文件加载 Agents
# ---------------------------------------------------------------------------

def load_agents_config() -> Dict[str, Any]:
    config_path = os.path.join(os.path.dirname(__file__), "config", "agents_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    print("警告：未找到 agents_config.json")
    return {}

# ---------------------------------------------------------------------------
# 3. CabinetManager 核心调度实现 (异步版)
# ---------------------------------------------------------------------------

class CabinetManager:
    """虚拟内阁大总管 (Multi-Agent Supervisor Routing, 支持 Async、Memory、Tools)"""
    
    def __init__(self):
        self.notion = NotionClient()
        self.agents_config = load_agents_config()
        self.memory = MemoryManager(max_history_per_user=10)
        
        # 改用 AsyncOpenAI 支持并发
        self.client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", "your-openai-api-key"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        )
        self.router_model = self.agents_config.get("router", {}).get("model", "gpt-4o-2024-08-06")

    def _get_prompt(self, agent_name: str) -> str:
        prompt_file = self.agents_config.get(agent_name, {}).get("prompt_file")
        if not prompt_file:
            return ""
        prompt_path = os.path.join(os.path.dirname(__file__), prompt_file)
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    async def _call_sub_agent(self, agent_name: str, task_desc: str, user_id: str) -> str:
        """异步调用单个部门，支持 Function Calling 循环"""
        agent_model = self.agents_config.get(agent_name, {}).get("model", "gpt-4o-2024-08-06")
        agent_prompt = self._get_prompt(agent_name)
        
        print(f"[{agent_name}] 接收任务开始处理...")
        
        # 1. 组装历史上下文 (这里只让 Worker 知道当前的 Task，不混入整个聊天的历史，以此保持专注)
        # 如果需要共享记忆，可将 self.memory.get_history(user_id) 传入。
        messages = [
            {"role": "system", "content": agent_prompt},
            {"role": "user", "content": task_desc}
        ]

        # 2. 调用 LLM 并提供 Tools
        response = await self.client.chat.completions.create(
            model=agent_model,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto"
        )
        
        first_choice = response.choices[0]
        message = first_choice.message
        
        # 3. 判断是否需要使用工具
        if message.tool_calls:
            print(f"[{agent_name}] 触发 Tool Call")
            messages.append(message)  # 必须将返回的 tool_calls 对象追加进对话
            
            for tool_call in message.tool_calls:
                # 本地执行工具并捕获结果
                tool_result = execute_tool_call(tool_call)
                # 追加 tool 角色结果
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_result
                })
                
            # 将工具结果交给大模型最终分析
            second_response = await self.client.chat.completions.create(
                model=agent_model,
                messages=messages
            )
            final_reply = second_response.choices[0].message.content
        else:
            final_reply = message.content

        print(f"[{agent_name}] 任务处理完成！")
        return f"【处理人：{agent_name} 部门】\n{final_reply}"


    async def process_message(self, message: str, user_id: str = "default_boss") -> Optional[AgentResponse]:
        """主入口：处理意图，并行分发，并调用工具。"""
        
        from datetime import datetime
        current_context = f"\n[System Context] 当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        router_prompt = self._get_prompt("router") + current_context
        
        # 将用户新消息加入 Router 长记忆
        self.memory.add_message(user_id, "user", message)
        history_messages = self.memory.get_history(user_id)
        
        # 组装完整的消息体发送给大总管
        messages = [{"role": "system", "content": router_prompt}] + history_messages
        
        print("[Router] 正在获取记忆，解析陛下意图...")
        router_response = await self.client.beta.chat.completions.parse(
            model=self.router_model,
            messages=messages,
            response_format=RouterPlan,
        )
        
        plan: RouterPlan = router_response.choices[0].message.parsed
        print(f"[Router 计划] 需分发任务数: {len(plan.delegations)}, 直接Notion动作数: {len(plan.direct_actions)}")

        # ---------------------------------------------------------
        # 大幅优化：使用 Asyncio 并发调用子部门 (Workers)
        # ---------------------------------------------------------
        tasks = []
        for delegation in plan.delegations:
            # 将分发的任务推入 async 任务列表，准备并发执行
            task = self._call_sub_agent(delegation.agent_name, delegation.task_description, user_id)
            tasks.append(task)
            
        # 并发执行并等待所有结果返回 (时间将取决于最慢的那个响应)
        sub_results = await asyncio.gather(*tasks) if tasks else []

        # ---------------------------------------------------------
        # 大总管汇总与组装飞书卡片返回格式
        # ---------------------------------------------------------
        print("[Router] 正在组装前端卡片...")
        coach_msg = ""
        
        # 1. 附加 Router 自身想交代给老板的直言
        if plan.direct_reply:
            coach_msg += f"{plan.direct_reply}\n\n"
        
        # 2. 附加各个子模块的执行回执
        for reply in sub_results:
            coach_msg += f"{reply}\n\n"
            
        if not coach_msg.strip():
            coach_msg = "陛下，查无相关指令回执。"
            
        # 将大总管的最终合并答复存入历史记录，供下一次对话追溯
        self.memory.add_message(user_id, "assistant", coach_msg.strip())
            
        front_end = FrontEnd(
            coach_message=coach_msg.strip(),
            buttons=[Button(text="朕已阅", action_payload="ack_done")]
        )
        
        return AgentResponse(actions=plan.direct_actions, front_end=front_end)

    async def execute_actions(self, actions: List[Action]):
        """执行大总管在 Notion 的动作 (保持同步，也可使用线程池，但动作一般较快)"""
        for action in actions:
            print(f"[Notion Action] 类型: {action.type}, 数据库: {action.database}")
            print(f"[Notion Data] {json.dumps(action.data, ensure_ascii=False, indent=2)}")
            # ... 实际通过 self.notion 操作
