import json
import urllib.request
from typing import Dict, Any, List
from datetime import datetime

# ---------------------------------------------------------------------------
# 1. 定义可被调用的本地 Python 函数
# ---------------------------------------------------------------------------

def get_current_time(timezone_offset: int = 8) -> str:
    """获取当前时间 (支持时区偏移)"""
    return f"当地时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def search_web_mock(query: str) -> str:
    """模拟网页搜索功能"""
    print(f"[{__name__}] 正在执行网页搜索: {query}")
    # 在此由于环境限制，返回 Dummy 数据
    return f"【搜索结果：{query}】2026年最新科技新闻显示，AI 智能体正加速接管各类开发及运营工作，各公司架构全面倒向 Supervisor-Worker 模式。"

# ---------------------------------------------------------------------------
# 2. 将此映射为大模型可理解的 JSON Schema 格式
# ---------------------------------------------------------------------------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前服务器系统的时间，对需要确定现在是何时很有用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone_offset": {
                        "type": "integer",
                        "description": "时区偏移小时数，默认为8（北京时间）。"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web_mock",
            "description": "在互联网上搜索最新资讯、新闻或百科知识。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要搜索的关键字或短语。"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# 3. 供 Agent 实际调用的派发字典
# ---------------------------------------------------------------------------

AVAILABLE_TOOLS_MAP = {
    "get_current_time": get_current_time,
    "search_web_mock": search_web_mock
}

def execute_tool_call(tool_call) -> str:
    """统一执行 Tool Call 并返回序列化字符串结果"""
    function_name = tool_call.function.name
    function_to_call = AVAILABLE_TOOLS_MAP.get(function_name)
    if not function_to_call:
        return json.dumps({"error": f"Tool {function_name} not found."})
        
    function_args = json.loads(tool_call.function.arguments)
    print(f"[Tool Execution] 调用 {function_name}，参数: {function_args}")
    try:
        function_response = function_to_call(**function_args)
        return str(function_response)
    except Exception as e:
        return json.dumps({"error": str(e)})
