import os
import sys
import time
import requests
import json
from datetime import datetime

def print_section(title):
    print(f"\n{'='*20} {title} {'='*20}")

print("=== 开始足球智能解说系统完整流程测试 ===")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))

# 1. 检查服务状态
print_section("检查各服务状态")

# 检查Web服务
web_server_url = "http://localhost:5000"
print(f"检查Web服务器: {web_server_url}")
try:
    web_response = requests.get(web_server_url, timeout=5)
    print(f"✓ Web服务器状态正常，响应码: {web_response.status_code}")
except Exception as e:
    print(f"✗ Web服务器未运行: {str(e)}")
    sys.exit(1)

# 检查语音服务
voice_server_url = "http://localhost:5001"
print(f"检查语音服务: {voice_server_url}")
try:
    voice_response = requests.get(f"{voice_server_url}/tts", timeout=5)
    print(f"✓ 语音服务状态正常，响应码: {voice_response.status_code}")
    print(f"  响应: {voice_response.json()}")
except Exception as e:
    print(f"✗ 语音服务未运行: {str(e)}")
    sys.exit(1)

# 2. 检查测试视频
print_section("检查测试视频")
test_video_path = os.path.join("football_main", "output_videos", "output1.mp4")
if os.path.exists(test_video_path):
    print(f"✓ 测试视频存在: {test_video_path}")
    print(f"  视频大小: {os.path.getsize(test_video_path) / 1024 / 1024:.2f} MB")
else:
    # 尝试使用其他路径
    alternative_paths = [
        os.path.join("input_videos", "a1.mp4"),
        os.path.join("uploads", "3ee3d458_a1.mp4")
    ]
    found = False
    for alt_path in alternative_paths:
        if os.path.exists(alt_path):
            test_video_path = alt_path
            print(f"✓ 找到替代测试视频: {test_video_path}")
            print(f"  视频大小: {os.path.getsize(test_video_path) / 1024 / 1024:.2f} MB")
            found = True
            break
    if not found:
        print(f"✗ 未找到测试视频，请检查视频路径")
        sys.exit(1)

# 3. 启动直接测试脚本
print_section("启动直接测试脚本")
print("执行run_AIGC.py进行端到端测试...")

import subprocess
process = subprocess.Popen(
    [sys.executable, "run_AIGC.py", test_video_path],
    cwd=project_root,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# 智能解码函数
def smart_decode(binary_data):
    encodings = ['utf-8', 'gbk', 'latin-1']
    for encoding in encodings:
        try:
            return binary_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return binary_data.decode('utf-8', errors='replace')

# 实时输出监控
print("\n=== 测试输出开始 ===")
while True:
    # 读取stdout
    stdout_line = process.stdout.readline()
    if stdout_line:
        decoded_line = smart_decode(stdout_line).strip()
        if decoded_line and not decoded_line.isspace():
            print(f"[STDOUT] {decoded_line}")
    
    # 读取stderr
    stderr_line = process.stderr.readline()
    if stderr_line:
        decoded_line = smart_decode(stderr_line).strip()
        if decoded_line and not decoded_line.isspace():
            print(f"[STDERR] {decoded_line}")
    
    # 检查进程是否结束
    if process.poll() is not None:
        break
    
    # 短暂等待
    time.sleep(0.1)

# 获取剩余输出
for stdout_line in process.stdout.readlines():
    decoded_line = smart_decode(stdout_line).strip()
    if decoded_line:
        print(f"[STDOUT] {decoded_line}")

for stderr_line in process.stderr.readlines():
    decoded_line = smart_decode(stderr_line).strip()
    if decoded_line:
        print(f"[STDERR] {decoded_line}")

print(f"\n测试脚本退出码: {process.returncode}")

# 4. 检查输出结果
print_section("检查输出结果")
output_dirs = [
    os.path.join("output", "final_output"),
    os.path.join("output", "commentary"),
    os.path.join("output", "audio")
]

all_files_found = False
for output_dir in output_dirs:
    if os.path.exists(output_dir):
        files = sorted(os.listdir(output_dir), key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True)
        if files:
            print(f"\n在 {output_dir} 中找到最新文件:")
            for i, file in enumerate(files[:3]):  # 显示最新的3个文件
                file_path = os.path.join(output_dir, file)
                file_size = os.path.getsize(file_path) / 1024
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {i+1}. {file} ({file_size:.2f} KB) - {file_time}")
                
                # 对于文本文件，显示部分内容
                if file.endswith('.txt') and i == 0:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read(200)  # 只读取前200个字符
                            print(f"    内容预览: {content}...")
                    except Exception as e:
                        print(f"    无法读取文件内容: {str(e)}")
            
            all_files_found = True

if not all_files_found:
    print("\n✗ 未找到输出文件，请检查测试是否成功完成")

# 5. 总结
print_section("测试总结")
print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Web服务状态: {'✓ 正常运行' if 'web_response' in locals() else '✗ 未运行'}")
print(f"语音服务状态: {'✓ 正常运行' if 'voice_response' in locals() else '✗ 未运行'}")
print(f"测试脚本结果: {'✓ 成功' if process.returncode == 0 else '✗ 失败'}")
print(f"输出文件: {'✓ 已生成' if all_files_found else '✗ 未找到'}")
print(f"\n提示: 您可以通过浏览器访问 {web_server_url} 使用Web界面进行操作")
print("=== 测试完成 ===")