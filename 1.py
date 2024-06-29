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
                    result['properties']['MemosID']['rich_text'][0]['text']['content']
                    for result in results if 'MemosID' in result['properties']
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
def send_wechat_notification(start_time, end_time, original_count, new_count, total_count, tags_count):
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
- 共有数据: {total_count} 条

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

# 主函数
def main():
    start_time = datetime.now()
    
    # 获取现有的Notion条目
    existing_notion_ids = get_existing_notion_entries()
    original_count = len(existing_notion_ids)
    
    # 获取Memos数据
    memos = fetch_memos()
    new_count = 0
    tags_count = {}

    for memo in memos:
        memos_id = str(memo.get('id', ''))
        content = memo.get('content', 'Untitled')
        if memos_id not in existing_notion_ids:
            tags = extract_tags(content)
            timestamp = memo.get('createdTs', 0)
            if create_notion_page(memos_id, content, tags, timestamp):
                new_count += 1
                existing_notion_ids.append(memos_id)
                for tag in tags:
                    if tag in tags_count:
                        tags_count[tag] += 1
                    else:
                        tags_count[tag] = 1

    end_time = datetime.now()
    total_count = original_count + new_count
    send_wechat_notification(start_time, end_time, original_count, new_count, total_count, tags_count)
    print("运行结束")

if __name__ == "__main__":
    main()
