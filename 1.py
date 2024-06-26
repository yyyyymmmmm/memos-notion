import requests
from datetime import datetime
import re
import os

# 配置
MEMOS_API_URL = 'https://memos.fenfa888.xyz/api/v1/memo'
MEMOS_API_TOKEN = 'your_memos_api_token'  # 请替换为实际的 MEMOS API 令牌
NOTION_TOKEN = 'your_notion_token'  # 请替换为实际的 Notion API 令牌
NOTION_DATABASE_ID = 'a0f22cc5d084455fa4e34b958a9a82d3'
WECHAT_WEBHOOK_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=d1dac968-5e65-47e9-bab0-568041e0d4bb'

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

def extract_tags(content):
    return re.findall(r'#(\w+)', content)

def get_existing_notion_entries():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }
    response = requests.post(url, headers=headers, json={})
    if response.status_code == 200:
        try:
            results = response.json().get('results', [])
            entries = [
                {
                    'title': result['properties']['内容']['title'][0]['text']['content'],
                    'content': result['children'][0]['paragraph']['text'][0]['text']['content'] if result.get('children') else ''
                }
                for result in results if '内容' in result['properties']
            ]
            return entries
        except ValueError as e:
            print(f"JSON decode error: {e}")
            return []
    else:
        print(f"Failed to fetch existing Notion entries: {response.status_code}, {response.text}")
        return []

def create_notion_page(content, tags, timestamp):
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

def send_wechat_notification(start_time, end_time, original_count, new_count, tags_count):
    duration = end_time - start_time
    duration_minutes = duration.total_seconds() / 60
    tags_summary = "\n".join([f"- {tag}: {count} 条" for tag, count in tags_count.items()])

    message = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""
**运行结果通知**
- 运行时间: {duration_minutes:.2f} 分钟
- Notion 原有数据: {original_count} 条
- 今日新增数据: {new_count} 条

**标签统计**
{tags_summary if tags_summary else '无标签'}
"""
        }
    }
    response = requests.post(WECHAT_WEBHOOK_URL, json=message)
    if response.status_code == 200:
        print("通知发送成功")
    else:
        print(f"通知发送失败: {response.status_code}, {response.text}")

def main():
    start_time = datetime.now()
    
    existing_notion_entries = get_existing_notion_entries()
    original_count = len(existing_notion_entries)
    
    memos = fetch_memos()
    new_count = 0
    tags_count = {}

    for memo in memos:
        content = memo.get('content', 'Untitled')
        title_snippet = content[:10]
        if not any(entry['title'] == title_snippet and entry['content'] == content for entry in existing_notion_entries):
            tags = extract_tags(content)
            timestamp = memo.get('createdTs', 0)
            if create_notion_page(content, tags, timestamp):
                new_count += 1
                for tag in tags:
                    if tag in tags_count:
                        tags_count[tag] += 1
                    else:
                        tags_count[tag] = 1

    end_time = datetime.now()
    send_wechat_notification(start_time, end_time, original_count, new_count, tags_count)
    print("运行结束")

if __name__ == "__main__":
    main()
