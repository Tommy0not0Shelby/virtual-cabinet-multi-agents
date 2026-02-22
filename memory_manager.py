import json
from typing import List, Dict, Any

class MemoryManager:
    """会话长记忆管理器"""
    
    def __init__(self, max_history_per_user: int = 10):
        # 简单内存字典。在生产环境中可替换为 SQLite 或 Redis
        self.store: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history = max_history_per_user

    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取特定用户的上下文历史"""
        if user_id not in self.store:
            self.store[user_id] = []
        return self.store[user_id]

    def add_message(self, user_id: str, role: str, content: str, name: str = None):
        """向特定用户追加一条消息"""
        if user_id not in self.store:
            self.store[user_id] = []
            
        msg = {"role": role, "content": content}
        if name:
            msg["name"] = name
            
        self.store[user_id].append(msg)
        
        # 保持在最大历史限制以内以节省 Token
        if len(self.store[user_id]) > self.max_history:
            self.store[user_id] = self.store[user_id][-self.max_history:]
            
    def clear_history(self, user_id: str):
        """清空用户的上下文历史"""
        if user_id in self.store:
            self.store[user_id] = []
