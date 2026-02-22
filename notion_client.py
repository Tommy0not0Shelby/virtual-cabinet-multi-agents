import requests
from typing import Dict, Optional
import time
import os

DB_CONFIG = {
    'projects': {
        'id': 'your-notion-projects-database-id',
        'url': 'https://www.notion.so/your-notion-projects-database-id'
    },
    'tasks': {
        'id': 'your-notion-tasks-database-id',
        'url': 'https://www.notion.so/your-notion-tasks-database-id'
    },
    'daily_logs': {
        'id': 'your-notion-daily-logs-database-id',
        'url': 'https://www.notion.so/your-notion-daily-logs-database-id'
    }
}

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', 'your-notion-api-key')
NOTION_VERSION = '2022-06-28'
BASE_URL = 'https://api.notion.com/v1'

HEADERS = {
    'Authorization': f'Bearer {NOTION_API_KEY}',
    'Notion-Version': NOTION_VERSION,
    'Content-Type': 'application/json'
}

class NotionClient:
    """Notion API 客户端 (独立封装)"""
    
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
                time.sleep(retry_after)
                return NotionClient.make_request(method, endpoint, data)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    @staticmethod
    def query_database(database_id: str, filter: Optional[Dict] = None) -> Dict:
        data = {}
        if filter:
            data['filter'] = filter
        return NotionClient.make_request('POST', f'databases/{database_id}/query', data)
    
    @staticmethod
    def create_page(database_id: str, properties: Dict) -> Dict:
        data = {
            'parent': {'database_id': database_id, 'type': 'database_id'},
            'properties': properties
        }
        return NotionClient.make_request('POST', 'pages', data)
    
    @staticmethod
    def update_page(page_id: str, properties: Dict) -> Dict:
        data = {'properties': properties}
        return NotionClient.make_request('PATCH', f'pages/{page_id}', data)
