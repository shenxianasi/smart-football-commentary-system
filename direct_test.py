import os
import sys
import subprocess
import json
from datetime import datetime

# 设置必要的环境变量
env = os.environ.copy()
env["AIGC_LANGUAGE"] = "zh-CN"
env["AIGC_VOICE"] = "default"
env["VOICE_SERVICE_URL"] = "http://localhost:8000"

# 视频路径
video_path = 'football_main/output_videos/output1.mp4'
abs_video_path = os.path.abspath(video_path)

# 检查文件是否存在
if not os.path.exists(abs_video_path):
    print(f"错误：视频文件不存在: {abs_video_path}")
    exit(1)

print(f"开始测试run_AIGC.py")
print(f"视频路径: {abs_video_path}")
print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 调用run_AIGC.py - 使用二进制模式而不是文本模式，避免自动解码错误
process = subprocess.Popen(
    [sys.executable, "run_AIGC.py", abs_video_path],
    env=env,
    cwd=os.getcwd(),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False  # 使用二进制模式
)

# 智能解码函数，尝试多种编码

def smart_decode(binary_data):
    """智能解码二进制数据，尝试多种编码"""
    if not binary_data:
        return ""
    
    encodings = ['utf-8', 'gbk', 'latin-1']
    for encoding in encodings:
        try:
            return binary_data.decode(encoding)
        except UnicodeDecodeError:
            continue
    # 所有编码都失败时，使用错误替换模式
    return binary_data.decode('utf-8', errors='replace')

# 实时打印输出
print("\n=== 开始处理输出 ===")
try:
    while process.poll() is None:
        # 读取标准输出
        if process.stdout:
            line_bytes = process.stdout.readline()
            if line_bytes:
                line = smart_decode(line_bytes)
                if line.strip():
                    print(f"[STDOUT] {line.strip()}")
                    # 特别关注解说词生成相关的输出
                    if "解说" in line or "commentary" in line.lower():
                        print(f"🔍 检测到解说词相关内容: {line.strip()}")
        
        # 读取标准错误
        if process.stderr:
            line_bytes = process.stderr.readline()
            if line_bytes:
                line = smart_decode(line_bytes)
                if line.strip():
                    print(f"[STDERR] {line.strip()}")
                    # 检测编码错误
                    if "编码" in line or "codec" in line or "decode" in line:
                        print(f"❌ 检测到编码错误: {line.strip()}")
        
        # 避免CPU占用过高
        import time
        time.sleep(0.1)
    
    # 读取剩余输出
    stdout_remaining_bytes = process.stdout.read() if process.stdout else b""
    stderr_remaining_bytes = process.stderr.read() if process.stderr else b""
    
    stdout_remaining = smart_decode(stdout_remaining_bytes)
    stderr_remaining = smart_decode(stderr_remaining_bytes)
    
    if stdout_remaining.strip():
        print(f"[STDOUT REMAINING] {stdout_remaining.strip()}")
    if stderr_remaining.strip():
        print(f"[STDERR REMAINING] {stderr_remaining.strip()}")
    
    print(f"\n=== 处理完成 ===")
    print(f"返回代码: {process.returncode}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 检查输出目录
    output_dirs = [
        os.path.join("output", "commentary"),
        os.path.join("football_comment", "output")
    ]
    
    for output_dir in output_dirs:
        if os.path.exists(output_dir):
            print(f"\n检查输出目录: {output_dir}")
            files = os.listdir(output_dir)
            if files:
                print(f"找到 {len(files)} 个文件:")
                for file in files:
                    file_path = os.path.join(output_dir, file)
                    file_size = os.path.getsize(file_path)
                    print(f"  - {file} ({file_size} 字节)")
                    # 尝试读取解说词文件内容
                    if file.endswith(".txt"):
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                print(f"    内容预览: {content[:100]}..." if len(content) > 100 else f"    内容: {content}")
                        except Exception as e:
                            print(f"    读取失败: {str(e)}")
            else:
                print("  目录为空")
        else:
            print(f"\n输出目录不存在: {output_dir}")
            
except KeyboardInterrupt:
    print("\n测试被用户中断")
    process.kill()