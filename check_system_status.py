import os
import subprocess
import requests

# 检查数据库文件位置
print("正在查找数据库文件...")
try:
    # 在当前目录及其子目录中查找数据库文件
    result = subprocess.run(
        ["dir", "/s", "football_translation.db"], 
        shell=True, 
        capture_output=True,
        text=True
    )
    print("查找结果:")
    print(result.stdout)
except Exception as e:
    print(f"查找数据库错误: {e}")

# 检查web服务器状态
print("\n检查web服务器状态...")
try:
    response = requests.get("http://localhost:8000/check_login")
    print(f"服务器响应: {response.status_code} - {response.text}")
except Exception as e:
    print(f"服务器检查错误: {e}")

# 检查output目录状态
print("\n检查output目录...")
output_dir = "output\final_output"
if os.path.exists(output_dir):
    files = os.listdir(output_dir)
    print(f"final_output目录中的文件 ({len(files)}个):")
    for file in sorted(files, key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True):
        file_path = os.path.join(output_dir, file)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        file_time = os.path.getmtime(file_path)
        from datetime import datetime
        time_str = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {file} - 大小: {file_size:.2f}MB - 修改时间: {time_str}")
else:
    print(f"{output_dir} 目录不存在")

# 检查web前端outputs目录
print("\n检查web前端outputs目录...")
web_outputs_dir = "web_frontend\outputs"
if os.path.exists(web_outputs_dir):
    files = os.listdir(web_outputs_dir)
    print(f"web_frontend/outputs目录中的文件 ({len(files)}个):")
    for file in sorted(files, key=lambda x: os.path.getmtime(os.path.join(web_outputs_dir, x)), reverse=True):
        file_path = os.path.join(web_outputs_dir, file)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        file_time = os.path.getmtime(file_path)
        from datetime import datetime
        time_str = datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
        print(f"  {file} - 大小: {file_size:.2f}MB - 修改时间: {time_str}")
else:
    print(f"{web_outputs_dir} 目录不存在")