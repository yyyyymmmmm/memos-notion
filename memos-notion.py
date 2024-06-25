import requests
from datetime import datetime
import re
import os

# 配置
MEMOS_API_URL = 'https://memos.fenfa888.xyz/api/v1/memo'
MEMOS_API_TOKEN = os.getenv('MEMOS_API_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = 'a0f22cc5d084455fa4e34b958a9a82d3'

def fetch_memos():
    headers = {
        'Authorization': f'Bearer {MEMOS_API_TOKEN}'
    }
    response = requests.get(MEMOS_API_URL, headers=headers)
    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.content}")
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
    # 使用正则表达式提取以 # 开头的标签
    return re.findall(r'#(\w+)', content)

def create_notion_page(content, tags, timestamp):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16"
    }

    # 转换时间戳为 ISO 8601 日期字符串
    date_str = datetime.utcfromtimestamp(timestamp).isoformat()

    # 使用 Memo 内容的前 10 个字符作为标题
    title = content[:10]

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "icon": {
            "emoji": "😸"
        },
        "properties": {
            "内容": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "标签": {
                "multi_select": [{"name": tag} for tag in tags]
            },
            "时间": {
                "date": {
                    "start": date_str
                }
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Page created successfully.")
    else:
        print(f"Failed to create page: {response.status_code}, {response.text}")

def main():
    memos = fetch_memos()
    for memo in memos:
        content = memo.get('content', 'Untitled')
        tags = extract_tags(content)
        timestamp = memo.get('createdTs', 0)
        create_notion_page(content, tags, timestamp)
    print("运行结束")

if __name__ == "__main__":
    main()
