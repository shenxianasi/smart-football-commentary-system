import requests
import time
import os
import json

# 检查web前端服务器是否在运行
def check_server_status():
    try:
        response = requests.get('http://localhost:5000/status', timeout=5)
        if response.status_code == 200:
            print("✅ Web前端服务器运行正常")
            return True
        else:
            print(f"❌ Web前端服务器响应状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到Web前端服务器: {str(e)}")
        return False

# 尝试获取最近的任务ID
def get_recent_task_id():
    # 1. 从check_task_status.py获取硬编码的任务ID
    try:
        with open('check_task_status.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # 查找current_task_id的定义
            import re
            match = re.search(r'current_task_id\s*=\s*"(.*?)"', content)
            if match:
                task_id = match.group(1)
                print(f"从check_task_status.py获取到任务ID: {task_id}")
                return task_id
    except Exception as e:
        print(f"无法从check_task_status.py读取任务ID: {str(e)}")
    
    # 2. 尝试从web_frontend的日志中获取
    web_log_path = os.path.join('web_frontend', 'server.log')
    if os.path.exists(web_log_path):
        print(f"提示: 您可以查看 {web_log_path} 获取最新的任务ID")
    
    # 3. 提供手动输入选项
    task_id = input("\n请输入要监控的任务ID (或按Enter退出): ")
    if not task_id:
        return None
    return task_id

# 监控任务状态
def monitor_task_status(task_id):
    print(f"\n开始监控任务进度 (任务ID: {task_id})...")
    print("按Ctrl+C可以停止监控")
    
    try:
        while True:
            url = f"http://localhost:5000/task_status/{task_id}"
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get('success') and data.get('task_status'):
                            task_status = data['task_status']
                            status = task_status.get('status')
                            message = task_status.get('message')
                            
                            # 清空当前行并打印新状态
                            print("\r" + " " * 80, end="")
                            status_line = f"\r任务状态: {status} - {message}"
                            
                            # 显示进度条(如果有)
                            if 'progress_step' in task_status and 'progress_max' in task_status:
                                step = task_status['progress_step']
                                max_step = task_status['progress_max']
                                progress_percent = int((step / max_step) * 100)
                                bar_length = 30
                                filled_length = int(bar_length * step / max_step)
                                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                                status_line += f" [进度: {progress_percent}%] [{bar}]"
                            
                            print(status_line, end="", flush=True)
                            
                            # 如果任务完成或出错，结束监控
                            if status == 'completed' or status == 'error':
                                print("\n\n任务监控结束")
                                if status == 'completed' and 'output_path' in task_status:
                                    print(f"✅ 视频已生成完成! 输出路径: {task_status['output_path']}")
                                break
                        else:
                            print(f"\r无法获取任务状态: {data}", end="", flush=True)
                    except Exception as json_error:
                        print(f"\rJSON解析错误: {str(json_error)}", end="", flush=True)
                else:
                    print(f"\r请求失败，状态码: {response.status_code}", end="", flush=True)
            except Exception as e:
                print(f"\r请求发生错误: {str(e)}", end="", flush=True)
            
            time.sleep(2)  # 每2秒检查一次
    except KeyboardInterrupt:
        print("\n\n监控已停止")

# 主函数
def main():
    print("=== 视频合成进度监控工具 ===")
    
    # 检查服务器状态
    if not check_server_status():
        print("请先启动web_frontend服务器")
        print("启动命令: python web_frontend/server.py")
        return
    
    # 获取任务ID
    task_id = get_recent_task_id()
    if not task_id:
        return
    
    # 开始监控
    monitor_task_status(task_id)

if __name__ == "__main__":
    main()