import time
import requests

# 任务ID，从日志中获取
# task_id = "d522821a-c3f9-4df5-88dd-2a2be8681b52"
# 当前正在处理的任务ID
current_task_id = "a9670977-01d7-40e3-875a-9e2f3f4e4504"

def check_task_status(task_id):
    # 发送请求查询任务状态
    url = f"http://localhost:5000/task_status/{task_id}"
    print(f"正在查询任务状态: {url}")
    try:
        response = requests.get(url)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"解析后的JSON数据: {data}")
                if data.get('success') and data.get('task_status'):
                    task_status = data['task_status']
                    print(f"任务状态: {task_status.get('status')}")
                    print(f"任务消息: {task_status.get('message')}")
                    # 检查是否有进度或其他信息
                    if 'progress' in task_status:
                        print(f"处理进度: {task_status['progress']}%")
                    if 'output_path' in task_status:
                        print(f"输出路径: {task_status['output_path']}")
                else:
                    print(f"无法获取任务状态: {data}")
            except Exception as json_error:
                print(f"JSON解析错误: {str(json_error)}")
                print(f"原始响应内容: {response.text}")
        else:
            print(f"请求失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"请求发生错误: {str(e)}")

# 如果直接运行脚本，则查询当前任务状态
if __name__ == "__main__":
    check_task_status(current_task_id)