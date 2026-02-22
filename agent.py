#!/usr/bin/env python3
"""
一人公司全能数字合伙人 & 深度效能教练
核心 Agent 模块
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

# 数据库配置
DB_CONFIG = {
    'projects': {
        'id': '30fafaa8-7c16-810b-bc66-e770d3e666d7',
        'url': 'https://www.notion.so/30dafaa87c16810bbc66e770d3e666d7'
    },
    'tasks': {
        'id': '30fafaa8-7c16-81c5-8e80-c5f67c011d4c',
        'url': 'https://www.notion.so/30dafaa87c1681c58e80c5f67c011d4c'
    },
    'daily_logs': {
        'id': '30fafaa8-7c16-81ca-9554-cdbdbc80c5e9',
        'url': 'https://www.notion.so/30dafaa87c1681ca9554cdbdbc80c5e9'
    }
}

# API 配置
NOTION_API_KEY = os.environ.get('NOTION_API_KEY', 'your-notion-api-key')
NOTION_VERSION = '2022-06-28'
BASE_URL = 'https://api.notion.com/v1'

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json'
}


class NotionClient:
    """Notion API 客户端"""
    
    @staticmethod
    def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送 HTTP 请求"""
        url = f'{BASE_URL}/{endpoint}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=HEADERS, params=data)
            elif method == 'POST':
                response = requests.post(url, headers=HEADERS, json=data)
            elif method == 'PATCH':
                response = requests.patch(url, headers=HEADERS, json=data)
            else:
                raise ValueError(f'不支持的 HTTP 方法: {method}')
            
            # 处理速率限制
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                import time
                time.sleep(retry_after)
                return NotionClient.make_request(method, endpoint, data)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    @staticmethod
    def query_database(database_id: str, filter: Optional[Dict] = None) -> Dict:
        """查询数据库"""
        data = {}
        if filter:
            data['filter'] = filter
        return NotionClient.make_request('POST', f'databases/{database_id}/query', data)
    
    @staticmethod
    def create_page(database_id: str, properties: Dict) -> Dict:
        """创建页面"""
        data = {
            'parent': {'database_id': database_id, 'type': 'database_id'},
            'properties': properties
        }
        return NotionClient.make_request('POST', 'pages', data)
    
    @staticmethod
    def update_page(page_id: str, properties: Dict) -> Dict:
        """更新页面"""
        data = {'properties': properties}
        return NotionClient.make_request('PATCH', f'pages/{page_id}', data)


class TimeParser:
    """时间解析器"""
    
    @staticmethod
    def extract_duration(text: str) -> float:
        """从文本中提取时间时长（小时）"""
        text = text.lower()
        
        # 常见表达方式
        patterns = [
            (r'(\d+(?:\.\d+)?)\s*小时?', lambda m: float(m.group(1))),
            (r'(\d+)\s*个多小时?', lambda m: float(m.group(1))),
            (r'(\d+)\s*小时左右?', lambda m: float(m.group(1))),
            (r'(\d+)\s*半小时?', lambda m: 0.5),
            (r'搞了一下午?', lambda m: 4.0),
            (r'搞了一上午?', lambda m: 4.0),
            (r'忙了一天?', lambda m: 8.0),
            (r'半天?', lambda m: 4.0),
        ]
        
        for pattern, extractor in patterns:
            match = re.search(pattern, text)
            if match:
                return extractor(match)
        
        return 0.0
    
    @staticmethod
    def estimate_task_time(task_name: str) -> float:
        """根据任务名称预估耗时（基于经验）"""
        task_name = task_name.lower()
        
        # 简单的规则匹配
        if '接口' in task_name or 'api' in task_name:
            return 2.0
        elif '文档' in task_name or '写' in task_name:
            return 1.5
        elif '会议' in task_name:
            return 1.0
        elif '测试' in task_name:
            return 1.0
        elif '部署' in task_name:
            return 0.5
        elif '修复' in task_name or 'bug' in task_name:
            return 1.5
        else:
            return 1.0  # 默认 1 小时


class EmotionAnalyzer:
    """情绪分析器"""
    
    @staticmethod
    def detect_energy_level(text: str) -> str:
        """检测精力水平"""
        text = text.lower()
        
        # 耗尽信号
        exhausted_signals = ['累死了', '没劲', '疲惫', '透支', '太累了']
        if any(signal in text for signal in exhausted_signals):
            return '🪫 耗尽'
        
        # 充沛信号
        energetic_signals = ['终于', '搞定', '完成', '搞定', '顺畅', '不错']
        if any(signal in text for signal in energetic_signals):
            return '🔋 充沛'
        
        # 平稳（默认）
        return '⚖️ 平稳'


class TaskClassifier:
    """任务分类器"""
    
    @staticmethod
    def classify_task_type(text: str) -> str:
        """判断任务类型"""
        text = text.lower()
        
        if '会议' in text or '沟通' in text or '讨论' in text:
            return '📅 会议'
        elif '想到' in text or '想法' in text or '灵感' in text or '点子' in text:
            return '💡 闪念灵感'
        else:
            return '🛠️ 任务'
    
    @staticmethod
    def detect_urgency(text: str) -> str:
        """检测紧急程度"""
        text = text.lower()
        
        urgent_signals = ['急', '问题', '故障', '出事', '客户', '紧急']
        if any(signal in text for signal in urgent_signals):
            return 'P0'
        
        # 默认 P1
        return 'P1'


class OneCompanyAgent:
    """一人公司全能数字合伙人"""
    
    def __init__(self):
        self.notion = NotionClient()
        self.time_parser = TimeParser()
        self.emotion_analyzer = EmotionAnalyzer()
        self.task_classifier = TaskClassifier()
    
    def process_message(self, message: str) -> Dict:
        """处理用户消息"""
        result = {
            'actions': [],
            'front_end': {
                'coach_message': '',
                'buttons': []
            }
        }
        
        # 检测消息类型
        task_type = self.task_classifier.classify_task_type(message)
        
        if task_type == '💡 闪念灵感':
            return self._handle_idea(message)
        elif '累' in message or '忙' in message:
            return self._handle_review(message)
        elif '今天' in message or '要做' in message:
            return self._handle_task_creation(message)
        else:
            return self._handle_general(message)
    
    def _handle_idea(self, message: str) -> Dict:
        """处理闪念灵感"""
        # 提取灵感内容
        content = message.replace('突然想到', '').replace('突然想到', '').strip()
        
        return {
            'actions': [{
                'type': 'create_task',
                'database': 'tasks',
                'data': {
                    'Task Name': content[:50],  # 限制长度
                    'Type': '💡 闪念灵感',
                    'Status': 'Not started',
                    'Date': datetime.now().strftime('%Y-%m-%d'),
                    'Est. Time': 1.0
                },
                'next': '等待确认'
            }],
            'front_end': {
                'coach_message': f'收到老板！"{content[:30]}..." 我已经记到灵感库里了。要不要我明天帮你评估一下可行性，安排个时间？',
                'buttons': [
                    {'text': '📝 立即转为明日待办', 'recommended': True},
                    {'text': '📌 保持为灵感', 'recommended': False},
                    {'text': '🗨️ 补充更多细节', 'recommended': False}
                ]
            }
        }
    
    def _handle_review(self, message: str) -> Dict:
        """处理复盘"""
        # 提取时间
        actual_time = self.time_parser.extract_duration(message)
        
        # 检测情绪
        energy_level = self.emotion_analyzer.detect_energy_level(message)
        
        return {
            'actions': [{
                'type': 'update_daily_log',
                'database': 'daily_logs',
                'data': {
                    'Total Work Hours': actual_time,
                    'Energy Level': energy_level,
                    'Time Audit': f'今日工作了 {actual_time} 小时，状态为 {energy_level}',
                    'Coach Advice': '今晚好好休息，明天保持这个节奏！'
                }
            }],
            'front_end': {
                'coach_message': f'辛苦了老板！今天工作了 {actual_time} 小时，{energy_level}。我已经帮你把今天的任务都闭环了。💪 今晚好好休息！',
                'buttons': [
                    {'text': '🌙 查看今日完整日报', 'recommended': True},
                    {'text': '💤 安排明天核心任务', 'recommended': False},
                    {'text': '😴 休息，明天再说', 'recommended': False}
                ]
            }
        }
    
    def _handle_task_creation(self, message: str) -> Dict:
        """处理任务创建"""
        # 提取任务内容
        task_name = message.replace('今天', '').replace('我要', '').replace('要做', '').strip()
        
        # 预估时间
        est_time = self.time_parser.estimate_task_time(task_name)
        
        # 检测紧急程度
        priority = self.task_classifier.detect_urgency(message)
        
        return {
            'actions': [{
                'type': 'create_task',
                'database': 'tasks',
                'data': {
                    'Task Name': task_name[:50],
                    'Type': '🛠️ 任务',
                    'Status': 'Not started',
                    'Date': datetime.now().strftime('%Y-%m-%d'),
                    'Est. Time': est_time
                },
                'next': '等待确认'
            }],
            'front_end': {
                'coach_message': f'好的老板！我理解你要"{task_name[:30]}"，预估需要 {est_time} 小时。今天目前排了 4 小时，加上这个是 {4 + est_time} 小时，还在可控范围内。关联到 A 项目可以吗？',
                'buttons': [
                    {'text': '🔴 确认创建，关联 A项目', 'recommended': True},
                    {'text': '⚪ 关联到其他项目', 'recommended': False},
                    {'text': '⚪ 不关联', 'recommended': False}
                ]
            }
        }
    
    def _handle_general(self, message: str) -> Dict:
        """处理一般消息"""
        return {
            'actions': [],
            'front_end': {
                'coach_message': f'收到老板！我能帮你做什么？\n\n• 记录任务（说"今天我要..."）\n• 捕获灵感（说"突然想到..."）\n• 晚间复盘（说"今天忙了多久..."）',
                'buttons': [
                    {'text': '📝 创建任务', 'recommended': True},
                    {'text': '💡 记录灵感', 'recommended': False},
                    {'text': '📊 查看今日任务', 'recommended': False}
                ]
            }
        }
    
    def check_daily_capacity(self) -> Dict:
        """检查每日容量（早晨定时任务）"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 查询今天的任务
        result = self.notion.query_database(
            DB_CONFIG['tasks']['id'],
            filter={
                'and': [
                    {
                        'property': 'Date',
                        'date': {
                            'equals': today
                        }
                    },
                    {
                        'property': 'Status',
                        'status': {
                            'equals': 'Not started'
                        }
                    }
                ]
            }
        )
        
        if 'error' in result:
            return result
        
        tasks = result.get('results', [])
        total_hours = 0.0
        
        for task in tasks:
            # 提取预估时间
            est_time_property = task.get('properties', {}).get('Est. Time', {})
            if est_time_property.get('type') == 'number':
                total_hours += est_time_property.get('number', 0)
        
        # 判断是否超载
        is_overloaded = total_hours > 8.0
        
        return {
            'total_hours': total_hours,
            'is_overloaded': is_overloaded,
            'task_count': len(tasks),
            'tasks': tasks
        }


# CLI 接口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='一人公司全能数字合伙人')
    parser.add_argument('message', nargs='?', help='用户消息')
    parser.add_argument('--check-capacity', action='store_true', help='检查每日容量')
    
    args = parser.parse_args()
    
    agent = OneCompanyAgent()
    
    if args.check_capacity:
        # 检查每日容量
        result = agent.check_daily_capacity()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.message:
        # 处理消息
        result = agent.process_message(args.message)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 交互模式
        print('一人公司全能数字合伙人 & 深度效能教练')
        print('输入你的消息（或 q 退出）')
        
        while True:
            message = input('\n老板: ')
            
            if message.lower() == 'q':
                break
            
            result = agent.process_message(message)
            print('\n--- 系统响应 ---')
            print(json.dumps(result, indent=2, ensure_ascii=False))
