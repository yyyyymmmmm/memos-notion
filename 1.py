import requests
from datetime import datetime
import re
import os

# 配置
MEMOS_API_URL = 'https://memos.fenfa888.xyz/api/v1/memo'
MEMOS_API_TOKEN = os.getenv('MEMOS_API_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = 'a0f22cc5d084455fa4e34b958a9a82d3'
WECHAT_WEBHOOK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d1dac968-5e65-47e9-bab0-568041e0d4bb'

# 获取Memos中的备忘录
def fetch_memos():
    headers = {
        'Authorization': f'Bearer {MEMOS_API_TOKEN}'
    }
    response = requests.get(MEMOS_API_URL, headers=headers)
    if response.status_code == 200:
        try:
            return response.json()
        except ValueError as e:
            print(f"JSON decode error: {e}")
            return []
    else:
        print(f"Failed to fetch memos: {response.status_code}, {response.text}")
        return []

# 提取标签
def extract_tags(content):
    return re.findall(r'#(\w+)', content)

# 获取现有的Notion条目（支持分页）
def get_existing_notion_entries():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }
    entries = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            try:
                data = response.json()
                results = data.get('results', [])
                entries.extend([
                    {
                        'id': result['properties']['MemosID']['rich_text'][0]['text']['content'],
                        'content': result['children'][0]['paragraph']['text'][0]['text']['content'] if result.get('children') else ''
                    }
                    for result in results if '内容' in result['properties'] and 'MemosID' in result['properties']
                ])
                has_more = data.get('has_more', False)
                next_cursor = data.get('next_cursor', None)
            except ValueError as e:
                print(f"JSON decode error: {e}")
                break
        else:
            print(f"Failed to fetch existing Notion entries: {response.status_code}, {response.text}")
            break
    return entries

# 创建新的Notion页面
def create_notion_page(memos_id, content, tags, timestamp):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }
    date_str = datetime.utcfromtimestamp(timestamp).isoformat()
    title = content[:10]
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "icon": {"emoji": "😸"},
        "properties": {
            "MemosID": {
                "rich_text": [{"text": {"content": memos_id}}]
            },
            "内容": {
                "title": [{"text": {"content": title}}]
            },
            "标签": {
                "multi_select": [{"name": tag} for tag in tags]
            },
            "时间": {
                "date": {"start": date_str}
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [{"type": "text", "text": {"content": content}}]
                }
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Page created successfully.")
        return True
    else:
        print(f"Failed to create page: {response.status_code}, {response.text}")
        return False

# 发送运行结果通知
def send_wechat_notification(start_time, end_time, original_count
