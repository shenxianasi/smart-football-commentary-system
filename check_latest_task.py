import requests
import json
import sqlite3
import os

# 数据库路径
db_path = os.path.join(os.getcwd(), 'football_translation.db')
print(f"数据库路径: {db_path}")
print(f"数据库是否存在: {os.path.exists(db_path)}")

# 先从数据库查询最新的记录
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询video表的最新记录
    print("\n查询video表的最新记录...")
    cursor.execute("SELECT * FROM video ORDER BY id DESC LIMIT 1")
    latest_video = cursor.fetchone()
    
    if latest_video:
        print(f"最新视频记录: {latest_video}")
        # 假设id是第一个字段
        video_id = latest_video[0]
        print(f"最新视频ID: {video_id}")
    else:
        print("video表中没有记录")
        video_id = None
    
    conn.close()
except Exception as e:
    print(f"数据库查询错误: {e}")
    video_id = None

# 使用之前发现的任务ID
task_id = "a9670977-01d7-40e3-875a-9e2f3f4e4504"  # 使用之前发现的任务ID
url = f"http://localhost:8000/task_status/{task_id}"

print(f"正在查询任务状态: {task_id}")
print(f"请求URL: {url}")

try:
    # 发送请求
    response = requests.get(url)
    response.raise_for_status()  # 检查是否有HTTP错误
    
    # 解析响应
    data = response.json()
    print("\n任务状态响应:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    
    # 提取关键信息
    if "status" in data:
        print(f"\n任务状态: {data['status']}")
    if "progress" in data:
        print(f"任务进度: {data['progress']}%")
    if "output_file" in data and data['output_file']:
        print(f"输出文件: {data['output_file']}")
    if "error" in data and data['error']:
        print(f"错误信息: {data['error']}")
    
    # 检查是否生成了视频
    if data.get("status") == "completed" and "output_file" in data:
        print("\n任务已完成，视频文件已生成!")
except requests.exceptions.RequestException as e:
    print(f"请求错误: {e}")
except json.JSONDecodeError:
    print(f"响应解析错误，返回内容: {response.text}")
except Exception as e:
    print(f"发生错误: {e}")

print("\n查询完成。")