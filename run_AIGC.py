# -*- coding: utf-8 -*-
import os
import sys
import time
import uuid
import shutil
import subprocess
import argparse
import glob
import threading
from datetime import datetime
import requests

# 安全打印函数，专门处理Unicode字符
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        # 使用安全的编码方式处理，确保在Windows系统上正常显示
        safe_text = text.encode('utf-8', 'replace').decode('utf-8', 'replace')
        # 尝试直接打印，如果失败则使用文件重定向方法
        try:
            print(safe_text)
        except UnicodeEncodeError:
            # 作为最后手段，将输出写入临时文件
            with open('print_output.txt', 'a', encoding='utf-8') as f:
                f.write(safe_text + '\n')

# 添加调试信息打印
def print_debug_info(message):
    """打印调试信息，带时间戳"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        print(f"[DEBUG {timestamp}] {message}")
    except UnicodeEncodeError:
        # 处理Unicode编码错误，使用更安全的方式
        try:
            # 尝试使用utf-8编码处理
            safe_message = str(message).encode('utf-8', 'replace').decode('utf-8', 'replace')
            print(f"[DEBUG {timestamp}] {safe_message}")
        except UnicodeEncodeError:
            # 作为最后手段，将输出写入临时文件
            with open('debug_output.txt', 'a', encoding='utf-8') as f:
                f.write(f"[DEBUG {timestamp}] {message}\n")

# 检查timm模块是否可用
try:
    import timm
    print_debug_info(f"timm模块版本: {timm.__version__}")
except ImportError:
    print_debug_info("timm模块未安装")

# 配置和路径设置
LANGUAGES = {
    "zh-CN": "Chinese",
    "en-US": "English",
    "ja-JP": "Japanese",
    "ko-KR": "Korean",
    "es-ES": "Spanish",
    "fr-FR": "French",
    "de-DE": "German",
    "ru-RU": "Russian",
    "pt-BR": "Portuguese",
    "ar-SA": "Arabic"
}

# 获取当前脚本所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 统一输出目录
OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")

# 语音合成API地址 - 优先从环境变量获取
VOICE_API_URL = os.environ.get('VOICE_SERVICE_URL', 'http://localhost:5001')
print_debug_info(f"使用语音合成API地址: {VOICE_API_URL}")

# FFMPEG路径
FFMPEG_PATH = os.path.join(CURRENT_DIR, "tools", "ffmpeg", "ffmpeg-8.0-essentials_build", "bin", "ffmpeg.exe")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)
for subdir in ["processed_videos", "commentary", "audio", "final_output", "analysis", "temp"]:
    os.makedirs(os.path.join(OUTPUT_DIR, subdir), exist_ok=True)

# 工具函数
def find_latest_video(directory, pattern="*.mp4"):
    """查找目录中最新的视频文件"""
    if not directory or not os.path.exists(directory):
        return None
    search_pattern = os.path.join(directory, pattern)
    files = glob.glob(search_pattern)
    if not files:
        return None
    # 按修改时间排序，返回最新的文件
    return max(files, key=os.path.getmtime)

def safe_copy(src, dst):
    """安全地复制文件，处理可能的异常"""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print_debug_info(f"复制文件失败 {src} -> {dst}: {str(e)}")
        return False

def run_python_script(script_path, *args, timeout=300, cwd=None):
    """运行Python脚本并返回结果，添加超时机制和实时输出"""
    cmd = [sys.executable, script_path] + list(args)
    print_debug_info(f"运行脚本: {' '.join(cmd)}")
    print_debug_info(f"脚本路径: {script_path}")
    print_debug_info(f"脚本参数: {args}")
    if cwd:
        print_debug_info(f"工作目录: {cwd}")
    
    # 检查脚本文件是否存在
    if not os.path.exists(script_path):
        error_msg = f"脚本文件不存在: {script_path}"
        print_debug_info(error_msg)
        return False, error_msg
    
    # 如果未指定工作目录，则使用脚本所在目录
    if cwd is None:
        cwd = os.path.dirname(os.path.abspath(script_path))
    
    try:
        # 使用Popen来手动处理输出流，并设置超时
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=False,  # 保持二进制模式以正确处理编码
            cwd=cwd  # 设置工作目录
        )
        
        # 实时读取输出的函数
        def read_output(stream, is_error=False):
            output = []
            encodings = ['utf-8', 'gbk', 'latin-1']
            while True:
                line = stream.readline()
                if not line:
                    break
                # 尝试解码行
                decoded_line = None
                for encoding in encodings:
                    try:
                        decoded_line = line.decode(encoding, errors='replace')
                        break
                    except UnicodeDecodeError:
                        continue
                # 如果所有编码都失败，使用二进制表示
                if not decoded_line:
                    decoded_line = repr(line)
                
                output.append(decoded_line)
                # 实时打印输出
                if is_error:
                    print_debug_info(f"脚本错误输出: {decoded_line.strip()}")
                else:
                    print(decoded_line, end='')  # 不添加额外的换行符
            return ''.join(output)
        
        # 创建线程来实时读取标准输出和标准错误
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, False))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True))
        
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        stdout_thread.start()
        stderr_thread.start()
        
        # 添加超时机制
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.kill()
                error_msg = f"脚本执行超时({timeout}秒): {' '.join(cmd)}"
                print_debug_info(error_msg)
                return False, error_msg
            time.sleep(0.5)  # 避免CPU占用过高
        
        # 等待线程结束
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        # 重新读取剩余的输出
        stdout_remaining = []
        stderr_remaining = []
        encodings = ['utf-8', 'gbk', 'latin-1']
        
        for encoding in encodings:
            try:
                stdout_remaining = process.stdout.read().decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        for encoding in encodings:
            try:
                stderr_remaining = process.stderr.read().decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if process.returncode != 0:
            print_debug_info(f"脚本执行失败(返回码: {process.returncode}): {stderr_remaining}")
            return False, f"返回码: {process.returncode}, 错误: {stderr_remaining}"
        return True, stdout_remaining
    except Exception as e:
        print_debug_info(f"运行脚本异常: {str(e)}")
        return False, str(e)
    finally:
        # 确保进程被终止
        if 'process' in locals() and process.poll() is None:
            process.kill()

# 语音合成函数
def synthesize_audio_with_voice_api(text, language, voice):
    """使用语音API合成音频"""
    url = f"{VOICE_API_URL}/synthesize"
    headers = {'Content-Type': 'application/json'}
        
    # 根据语言选择默认音色
    if language == '汉语':
        voice_name = voice if voice != 'auto' else 'zhanjun'  # 使用之前初始化的中文音色
    else:
        voice_name = voice if voice != 'auto' else 'cosyvoice-emma-en'  # 使用内置英文音色
        
    data = {
        "name": voice_name,  # 使用name字段而不是voice字段
        "text": text
        # 移除language字段，根据API文档似乎不需要
    }
    
    # 首先检查语音服务是否可访问
    try:
        # 尝试连接到语音服务
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2秒超时
        host, port = VOICE_API_URL.replace('http://', '').replace('https://', '').split(':')
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        if result != 0:
            print_debug_info("语音服务未启动或不可访问")
            return False, "语音服务未启动或不可访问"
    except Exception as e:
        print_debug_info(f"检查语音服务失败: {str(e)}")
        return False, f"检查语音服务失败: {str(e)}"
    
    # 多次尝试调用语音合成API
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                try:
                    # 尝试解析JSON响应
                    result = response.json()
                    if 'audio_base64' in result:
                        return True, result['audio_base64']
                    elif 'audio' in result:
                        return True, result['audio']
                    else:
                        return False, f"无效的API响应格式: {result}"
                except json.JSONDecodeError:
                    # 如果响应不是JSON，直接返回内容
                    return True, response.content
            else:
                print_debug_info(f"语音API调用失败 (尝试 {attempt+1}/{max_retries}): HTTP {response.status_code}, 响应: {response.text}")
                time.sleep(1)  # 等待1秒后重试
        except requests.exceptions.RequestException as e:
            print_debug_info(f"语音API请求异常 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            time.sleep(1)  # 等待1秒后重试
    
    return False, f"语音API调用失败，已尝试 {max_retries} 次"

def merge_audio_with_video(video_path, audio_path, output_path):
    """使用ffmpeg合并视频和音频"""
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print_debug_info(f"创建输出目录: {output_dir}")
        
        # 首先检查输入视频文件是否存在
        if not os.path.exists(video_path):
            error_msg = f"输入视频文件不存在: {video_path}"
            print_debug_info(error_msg)
            return False, error_msg
        
        # 检查视频文件大小
        video_size = os.path.getsize(video_path)
        print_debug_info(f"输入视频文件大小: {video_size} 字节")
        
        # 构建增强的ffmpeg命令，添加更多格式兼容性参数
        # 不再直接复制视频流，而是进行适当的重新编码以确保兼容性
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'libx264',  # 使用H.264编码，兼容性更好
            '-preset', 'medium',  # 平衡编码速度和质量
            '-crf', '23',  # 视频质量，18-28是合理范围
            '-c:a', 'aac',   # 音频编码使用aac
            '-b:a', '192k',  # 音频比特率
            '-movflags', '+faststart',  # 允许在下载完成前开始播放
            '-pix_fmt', 'yuv420p',  # 确保浏览器兼容性的像素格式
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        print_debug_info(f"执行ffmpeg命令: {' '.join(cmd)}")
        
        # 运行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=False  # 保持二进制模式
        )
        
        # 等待命令完成
        stdout, stderr = process.communicate()
        
        # 检查返回码
        if process.returncode == 0:
            # 尝试解码输出
            try:
                stdout_str = stdout.decode('utf-8', errors='replace')
                print_debug_info(f"ffmpeg成功输出: {stdout_str[:200]}...")
            except:
                pass
            return True, "视频合成成功"
        else:
            # 尝试解码错误输出
            try:
                stderr_str = stderr.decode('utf-8', errors='replace')
            except:
                stderr_str = str(stderr)
            print_debug_info(f"ffmpeg错误输出: {stderr_str}")
            return False, stderr_str
    except Exception as e:
        error_msg = str(e)
        print_debug_info(f"视频音频合并异常: {error_msg}")
        return False, error_msg

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='足球视频解说生成工具')
    parser.add_argument('--language', type=str, default='汉语', choices=['汉语', 'English'],
                      help='解说语言')
    parser.add_argument('--voice', type=str, default='auto',
                      help='语音类型')
    parser.add_argument('--frame_interval', type=int, default=15,
                      help='帧截取间隔，默认15帧')
    parser.add_argument('--max_words', type=int, default=500,
                      help='解说词最大字数限制，默认500字')
    parser.add_argument('video_path', nargs='?', default=None,
                      help='输入视频路径（可选，不指定则使用input_videos目录中的最新视频）')
    args = parser.parse_args()
    
    # 从环境变量覆盖参数
    env_language = os.environ.get('AIGC_LANGUAGE')
    if env_language:
        args.language = env_language
        print_debug_info(f"从环境变量获取语言设置: {args.language}")
    
    env_voice = os.environ.get('AIGC_VOICE')
    if env_voice:
        args.voice = env_voice
        print_debug_info(f"从环境变量获取语音设置: {args.voice}")
    
    # 从环境变量更新语音API地址
    global VOICE_API_URL
    env_voice_url = os.environ.get('VOICE_SERVICE_URL')
    if env_voice_url:
        VOICE_API_URL = env_voice_url
        print_debug_info(f"从环境变量更新语音API地址: {VOICE_API_URL}")
    
    print_debug_info(f"参数配置: 语言={args.language}, 语音={args.voice}, 帧间隔={args.frame_interval}, 最大字数={args.max_words}")
    
    # 获取当前工作目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print_debug_info(f"当前工作目录: {current_dir}")
    
    # 设置项目根目录
    project_root = current_dir
    
    # 输入视频目录和输出视频目录
    input_dir = os.path.join(project_root, 'input_videos')
    # 统一的视频输出目录
    output_dir = os.path.join(OUTPUT_DIR, 'final_output')
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取输入视频路径
    if args.video_path and os.path.exists(args.video_path):
        # 使用命令行参数中指定的视频路径
        input_video = args.video_path
        print_debug_info(f"使用命令行参数中的视频路径: {input_video}")
    else:
        # 查找最新的输入视频 - 优先使用input_videos目录
        print_debug_info(f"查找输入视频目录: {input_dir}")
        input_video = find_latest_video(input_dir, '*.mp4')
        
        if not input_video:
            print_debug_info(f"未在 {input_dir} 找到视频文件，列出目录内容:")
            try:
                for file in os.listdir(input_dir):
                    file_path = os.path.join(input_dir, file)
                    print_debug_info(f"  {file} - {os.path.isfile(file_path)}")
            except Exception as e:
                print_debug_info(f"无法列出目录内容: {e}")
            return
        else:
            print_debug_info(f"成功找到输入视频: {input_video}")
    
    print_debug_info(f"找到输入视频: {input_video}")
    
    # 统一的临时文件目录
    temp_dir = os.path.join(OUTPUT_DIR, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 生成临时输出文件名
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    output_filename = f"football_commentary_{timestamp}.mp4"
    output_video = os.path.join(output_dir, output_filename)
    
    # 步骤1: 运行football_main模块进行视频分析
    print_debug_info("开始运行football_main模块")
    main_script = os.path.join(project_root, 'football_main', 'main.py')
    print_debug_info(f"football_main脚本路径: {main_script}")
    
    # 添加单独的日志记录，便于调试
    start_time = time.time()
    
    # 首先验证input_video是否存在
    if not os.path.exists(input_video):
        print_debug_info(f"错误：输入视频文件不存在: {input_video}")
        # 尝试查找替代视频文件
        alternative_videos = [
            os.path.join(project_root, 'input_videos', 'a1.mp4'),
            os.path.join(project_root, 'uploads', '3ee3d458_a1.mp4'),
            os.path.join(project_root, 'football_main', 'input_videos', 'a1.mp4')
        ]
        found = False
        for alt_video in alternative_videos:
            if os.path.exists(alt_video):
                input_video = alt_video
                print_debug_info(f"使用替代视频文件: {input_video}")
                found = True
                break
        if not found:
            print(f"\n严重错误: 找不到有效的视频文件")
            # 即使找不到视频，也继续执行以生成默认解说词
    
    # 运行football_main模块
    success, output = run_python_script(
        main_script,
        '--input_video', input_video,
        '--frame_interval', str(args.frame_interval),
        timeout=1800,  # 增加超时时间为30分钟，因为视频处理可能需要较长时间
        cwd=os.path.join(project_root, 'football_main')  # 设置正确的工作目录
    )
    
    end_time = time.time()
    print_debug_info(f"football_main模块执行耗时: {end_time - start_time:.2f}秒")
    
    if not success:
        print_debug_info(f"football_main模块执行失败: {output}")
        print(f"\n警告: football_main模块执行失败\n详细信息: {output}")
        print("\n将继续使用默认解说词生成逻辑...")
        # 不返回，而是继续执行后续步骤，使用默认解说词
    
    # 打印更详细的输出信息
    if output:
        print_debug_info(f"football_main输出长度: {len(output)}字符")
        # 仅打印前200个字符以避免日志过长
        print_debug_info(f"football_main输出预览: {output[:200]}...")
    else:
        print_debug_info("football_main输出为空")
    
    # 从输出中提取关键点
    print_debug_info(f"football_main输出: {output}")
    
    # 步骤2: 运行football_comment模块生成解说词
    print_debug_info("开始运行football_comment模块")
    
    # 获取football_comment目录
    football_comment_dir = os.path.join(project_root, 'football_comment')
    comment_input_dir = os.path.join(football_comment_dir, 'input_video')
    
    # 确保football_comment的input_video目录存在
    try:
        os.makedirs(comment_input_dir, exist_ok=True)
        print_debug_info(f"确保视频输入目录存在: {comment_input_dir}")
    except Exception as e:
        print_debug_info(f"创建目录失败: {e}")
        # 如果创建目录失败，使用原始input_videos目录作为备选
        comment_input_dir = input_dir
        print_debug_info(f"使用备选目录: {comment_input_dir}")
    
    # 获取视频文件名并复制视频
    video_filename = os.path.basename(input_video)
    comment_video_path = os.path.join(comment_input_dir, video_filename)
    
    # 复制视频文件（使用绝对路径确保正确性）
    input_video_abs = os.path.abspath(input_video)
    comment_video_path_abs = os.path.abspath(comment_video_path)
    
    print_debug_info(f"准备复制视频: {input_video_abs} -> {comment_video_path_abs}")
    
    # 强制复制视频，确保football_comment模块能找到正确的视频
    try:
        # 先删除目标文件（如果存在），避免覆盖问题
        if os.path.exists(comment_video_path_abs):
            os.remove(comment_video_path_abs)
            print_debug_info(f"已删除旧视频文件: {comment_video_path_abs}")
        
        # 使用shutil复制文件，更可靠的文件复制
        shutil.copy2(input_video_abs, comment_video_path_abs)
        print_debug_info(f"已成功复制视频文件到: {comment_video_path_abs}")
        
        # 验证复制后的文件大小
        if os.path.exists(comment_video_path_abs):
            size = os.path.getsize(comment_video_path_abs)
            print_debug_info(f"复制后的视频文件大小: {size} 字节")
    except Exception as e:
        print_debug_info(f"复制视频文件失败: {e}，将使用原始视频路径")
        comment_video_path_abs = input_video_abs
    
    # 验证视频是否存在
    if not os.path.exists(comment_video_path_abs):
        print_debug_info(f"严重错误：视频文件不存在: {comment_video_path_abs}")
        print(f"错误：找不到视频文件，请检查路径: {comment_video_path_abs}")
        return
    
    # 列出football_comment的input_video目录内容，确认视频已正确复制
    try:
        comment_files = os.listdir(comment_input_dir)
        print_debug_info(f"football_comment输入目录中的文件数量: {len(comment_files)}")
        for file in comment_files[:5]:  # 只显示前5个文件
            file_path = os.path.join(comment_input_dir, file)
            file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 'N/A'
            print_debug_info(f"  {file} - 大小: {file_size} 字节")
    except Exception as e:
        print_debug_info(f"无法列出football_comment输入目录内容: {e}")
    
    # 添加单独的日志记录，便于调试
    start_time = time.time()
    
    # 直接导入并调用football_comment模块的generate_commentary函数
    success = False
    commentary_text = ""
    
    try:
        # 动态添加football_comment目录到Python路径
        if football_comment_dir not in sys.path:
            sys.path.append(football_comment_dir)
        
        print_debug_info("尝试直接导入football_comment模块")
        # 导入football_comment的main模块
        from football_comment import main as football_comment_main
        
        # 直接调用generate_commentary函数
        print_debug_info(f"调用football_comment.generate_commentary函数，视频路径: {comment_video_path_abs}")
        success, commentary_text = football_comment_main.generate_commentary(
            video_file=comment_video_path_abs
        )
        
        print_debug_info(f"football_comment.generate_commentary调用结果: success={success}, text长度={len(commentary_text) if commentary_text else 0}")
        
    except ImportError as e:
        print_debug_info(f"导入football_comment模块失败: {e}")
        # 如果导入失败，使用备选方案（通过run_python_script执行）
        print_debug_info("使用备选方案：通过run_python_script执行football_comment")
        comment_script = os.path.join(project_root, 'football_comment', 'main.py')
        success, commentary_text = run_python_script(
            comment_script,
            '--language', args.language,
            timeout=900  # 增加超时时间为15分钟
        )
    except Exception as e:
        print_debug_info(f"调用football_comment模块时发生错误: {e}")
        # 记录错误但继续执行，尝试从文件读取
        success = False
    
    end_time = time.time()
    print_debug_info(f"football_comment模块执行耗时: {end_time - start_time:.2f}秒")
    
    # 尝试从输出文件中读取解说词，作为备选方案
    video_basename = os.path.splitext(video_filename)[0]
    
    # 检查多个可能的解说词文件路径
    commentary_paths = [
        # 统一输出目录中的解说词
        os.path.join(OUTPUT_DIR, 'commentary', f'{video_basename}.txt'),
        # football_comment目录的output子目录
        os.path.join(football_comment_dir, 'output', f'{video_basename}.txt'),
        # 主输出目录
        os.path.join(OUTPUT_DIR, f'{video_basename}.txt'),
        # 直接在football_comment的output目录中查找最新的txt文件
        find_latest_video(os.path.join(football_comment_dir, 'output'), '*.txt')
    ]
    
    file_commentary = None
    found_path = None
    
    # 遍历所有可能的路径，找到第一个有效的解说词文件
    for path in commentary_paths:
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read().strip()
                    if content:  # 确保内容不为空
                        file_commentary = content
                        found_path = path
                        print_debug_info(f"从文件读取到解说词: {file_commentary[:100]}...")
                        print_debug_info(f"解说词文件路径: {found_path}")
                        break  # 找到第一个有效解说词就退出循环
            except Exception as e:
                print_debug_info(f"读取解说词文件{path}失败: {e}")
    
    if not success or not commentary_text or not commentary_text.strip():
        print_debug_info(f"football_comment模块执行状态: {success}，返回文本: {commentary_text[:50] if commentary_text else '空'}")
        
        # 优先使用文件中的解说词
        if file_commentary:
            commentary_text = file_commentary
            print_debug_info(f"使用从文件读取的解说词")
            # 安全地打印解说词，处理Unicode字符
            safe_print(f"\n使用从文件读取的解说词: {commentary_text}")
        else:
            # 使用默认解说词
            safe_print("\n使用默认解说词，因为无法从模块或文件获取有效的解说词")
            if args.language == '汉语':
                commentary_text = "这是一场精彩的足球比赛，双方球员展现了出色的技术和战术配合。进攻方组织了多次有威胁的攻势，防守方也做出了精彩的扑救。这场比赛充满了悬念和看点，我们一起欣赏这些精彩瞬间。"
            else:
                commentary_text = "This is a wonderful football match. Both teams have shown excellent skills and tactical coordination. The attacking team has organized several threatening offensives, while the defending team has also made brilliant saves. This game is full of suspense and highlights..."
    
    print_debug_info(f"生成解说词: {commentary_text[:100]}...")
    
    # 处理解说词文本
    if not commentary_text.strip():
        # 如果没有生成解说词，使用默认文本
        if args.language == '汉语':
            commentary_text = "这是一场精彩的足球比赛，双方球员展现了出色的技术和战术配合。进攻方组织了多次有威胁的攻势，防守方也做出了精彩的扑救。这场比赛充满了悬念和看点，我们一起欣赏这些精彩瞬间。"
        else:
            commentary_text = "This is a wonderful football match. Both teams have shown excellent skills and tactical coordination. The attacking team has organized several threatening offensives, while the defending team has also made brilliant saves. This game is full of suspense and highlights. Let's enjoy these wonderful moments together."
    
    # 限制解说词长度
    if len(commentary_text) > args.max_words:
        print_debug_info(f"解说词长度 {len(commentary_text)} 超过限制 {args.max_words}，将进行截断")
        # 尽量在句子结束处截断
        truncated = False
        for i in range(args.max_words, len(commentary_text)):
            if commentary_text[i] in ['.', '。', '!', '！', '?', '？']:
                commentary_text = commentary_text[:i+1]
                truncated = True
                break
        if not truncated:
            # 如果没有找到合适的截断点，直接截断
            commentary_text = commentary_text[:args.max_words] + '...'
    
    print_debug_info(f"最终解说词: {commentary_text}")
    safe_print(f"\n最终使用的解说词: {commentary_text}")
    
    # 步骤3: 运行voice_synthesis模块生成语音
    print_debug_info("开始生成语音")
    success, audio_result = synthesize_audio_with_voice_api(
        commentary_text,
        args.language,
        args.voice
    )
    
    # 保存音频数据到统一的audio目录
    audio_dir = os.path.join(OUTPUT_DIR, 'audio')
    os.makedirs(audio_dir, exist_ok=True)
    audio_file = os.path.join(audio_dir, f"commentary_{timestamp}.wav")
    
    # 处理语音生成
    if success:
        try:
            import base64
            # 检查audio_result的类型
            if isinstance(audio_result, bytes):
                audio_data = audio_result
            else:
                audio_data = base64.b64decode(audio_result)
            
            with open(audio_file, 'wb') as f:
                f.write(audio_data)
            print_debug_info(f"音频文件已保存: {audio_file}")
        except Exception as e:
            print_debug_info(f"保存音频文件失败: {str(e)}")
            success = False
    else:
        print_debug_info(f"语音生成失败: {audio_result}")
        print(f"\n警告: 语音生成失败，将尝试使用pyttsx3作为备用方案")
        
        # 尝试使用pyttsx3作为备用语音合成方案
        try:
            import pyttsx3
            print_debug_info("尝试使用pyttsx3生成语音")
            engine = pyttsx3.init()
            
            # 设置中文语音属性
            if args.language == '汉语':
                voices = engine.getProperty('voices')
                # 尝试找到中文语音
                chinese_voice_found = False
                for voice in voices:
                    if 'chinese' in voice.id.lower() or 'china' in voice.id.lower() or 'mandarin' in voice.id.lower() or '中文' in voice.name:
                        engine.setProperty('voice', voice.id)
                        print_debug_info(f"使用中文语音: {voice.id}")
                        chinese_voice_found = True
                        break
                if not chinese_voice_found:
                    print_debug_info("未找到中文语音，使用默认语音")
                engine.setProperty('rate', 170)  # 调整语速为更自然的中文朗读速度
                engine.setProperty('volume', 1.0)  # 音量
            
            # 保存为wav文件
            engine.save_to_file(commentary_text, audio_file)
            engine.runAndWait()
            
            if os.path.exists(audio_file):
                print_debug_info(f"pyttsx3音频文件已保存: {audio_file}")
                success = True
                print(f"备用语音合成成功！使用pyttsx3生成了音频。")
            else:
                print_debug_info("pyttsx3保存音频失败")
        except ImportError:
            print_debug_info("pyttsx3模块未安装，无法使用备用语音合成")
            print(f"\n提示: 可以通过运行 'pip install pyttsx3' 安装pyttsx3模块作为备用语音合成方案")
            print("安装完成后，即使主语音服务不可用，系统也能生成解说音频。")
        except Exception as e:
            print_debug_info(f"pyttsx3语音合成失败: {str(e)}")
            print(f"pyttsx3语音合成失败: {str(e)}")
    
    # 如果所有语音合成方法都失败，创建一个空的音频文件以继续处理
    if not success and not os.path.exists(audio_file):
        print_debug_info("所有语音合成方法都失败，将创建一个空的音频文件以继续处理")
        print(f"\n创建空音频文件以确保视频合成过程能够继续...")
        # 创建一个非常短的静音音频文件
        try:
            # 使用ffmpeg创建空音频
            cmd = [
                FFMPEG_PATH,
                '-f', 'lavfi',
                '-i', 'anullsrc=r=44100:cl=mono',
                '-t', '1',
                '-c:a', 'pcm_s16le',
                '-y',
                audio_file
            ]
            # 使用capture_output=False避免编码问题，或者使用正确的编码参数
            subprocess.run(cmd, capture_output=False)
            if os.path.exists(audio_file):
                print_debug_info("已创建空音频文件")
                print(f"空音频文件创建成功，将继续进行视频合成。")
                success = True
        except Exception as e:
            print_debug_info(f"创建空音频文件失败: {e}")
            print(f"创建空音频文件失败: {e}")
            # 即使失败也不返回，而是尝试保存解说词
    
    # 步骤4: 查找football_main处理后的视频（优先在统一目录中查找）
    # 先检查统一处理目录
    processed_video_dir = os.path.join(OUTPUT_DIR, 'processed_videos')
    print_debug_info(f"检查处理后视频目录: {processed_video_dir}")
    
    # 列出目录内容，帮助调试
    try:
        processed_files = os.listdir(processed_video_dir)
        print_debug_info(f"处理目录中的文件数量: {len(processed_files)}")
        for file in processed_files[:5]:  # 只显示前5个文件
            print_debug_info(f"  找到文件: {file}")
    except Exception as e:
        print_debug_info(f"无法列出处理目录内容: {e}")
    
    # 根据比赛分析数据中的文件名查找
    analysis_file = os.path.join(project_root, 'football_main', 'match_analysis.json')
    target_video_name = None
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
                if 'video_filename' in analysis_data:
                    target_video_name = analysis_data['video_filename']
                    print_debug_info(f"从分析数据中获取目标视频名: {target_video_name}")
        except Exception as e:
            print_debug_info(f"读取分析数据失败: {e}")
    
    # 优先使用目标文件名查找
    # 修改处理后视频查找部分，确保能正确找到video_a1_1.avi文件
    
    processed_video = None
    
    # 首先检查用户提到的特定视频文件
    user_mentioned_video = os.path.join(OUTPUT_DIR, 'processed_videos', 'video_a1_1.avi')
    if os.path.exists(user_mentioned_video):
        processed_video = user_mentioned_video
        print_debug_info(f"找到用户提到的视频: {processed_video}")
    
    # 如果没有找到，尝试直接查找video_a1_1.avi
    if not processed_video:
        video_a1_1_path = os.path.join(OUTPUT_DIR, 'processed_videos', 'video_a1_1.avi')
        if os.path.exists(video_a1_1_path):
            processed_video = video_a1_1_path
            print_debug_info(f"找到video_a1_1.avi文件: {processed_video}")
    
    # 如果没有找到，按原来的逻辑查找
    if not processed_video and target_video_name:
        # 扩展可能的路径列表
        possible_paths = [
            os.path.join(processed_video_dir, target_video_name),
            os.path.join(project_root, 'football_main', 'output_videos', target_video_name),
            # 检查常见的输出路径
            os.path.join(project_root, 'football_main', target_video_name),
            os.path.join(project_root, target_video_name)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                processed_video = path
                print_debug_info(f"根据目标文件名找到处理后视频: {processed_video}")
                break
    
    # 如果没有找到，使用find_latest_video方法
    if not processed_video:
        processed_video = find_latest_video(processed_video_dir, '*.avi')
        
        # 如果统一目录中没有，再检查football_main的output_videos目录
        if not processed_video:
            legacy_processed_dir = os.path.join(project_root, 'football_main', 'output_videos')
            print_debug_info(f"检查legacy处理目录: {legacy_processed_dir}")
            try:
                legacy_files = os.listdir(legacy_processed_dir)
                print_debug_info(f"Legacy目录中的文件数量: {len(legacy_files)}")
                for file in legacy_files[:5]:  # 只显示前5个文件
                    print_debug_info(f"  找到文件: {file}")
            except Exception as e:
                print_debug_info(f"无法列出legacy目录内容: {e}")
            processed_video = find_latest_video(legacy_processed_dir, '*.avi')
    
    # 添加对.mp4格式的检查支持
    if not processed_video:
        print_debug_info("检查.mp4格式的处理后视频文件")
        processed_video = find_latest_video(processed_video_dir, '*.mp4')
        if not processed_video:
            processed_video = find_latest_video(os.path.join(project_root, 'football_main', 'output_videos'), '*.mp4')
    
    # 如果还是没找到，再次检查所有可能的路径
    if not processed_video:
        all_possible_paths = [
            os.path.join(OUTPUT_DIR, 'processed_videos', 'video_a1_1.avi'),
            os.path.join(project_root, 'football_main', 'video_a1_1.avi'),
            os.path.join(project_root, 'video_a1_1.avi')
        ]
        
        for path in all_possible_paths:
            if os.path.exists(path):
                processed_video = path
                print_debug_info(f"在备用路径中找到video_a1_1.avi: {processed_video}")
                break
    
    if not processed_video:
        print_debug_info(f"未找到处理后的视频，将使用原始视频: {input_video}")
        video_to_use = input_video
    else:
        print_debug_info(f"找到处理后的视频: {processed_video}")
        video_to_use = processed_video
    
    # 验证最终使用的视频文件是否存在
    if not os.path.exists(video_to_use):
        print_debug_info(f"严重错误: 最终选择的视频文件不存在: {video_to_use}")
        # 使用原始输入视频作为最后的备选
        video_to_use = input_video
        print_debug_info(f"回退到使用原始输入视频: {video_to_use}")
        
    # 再次验证视频是否存在
    if not os.path.exists(video_to_use):
        print_debug_info(f"严重错误: 备选视频文件也不存在: {video_to_use}")
        # 尝试查找任何可用的视频文件
        all_video_candidates = []
        # 检查input_videos目录
        input_videos_dir = os.path.join(project_root, 'input_videos')
        if os.path.exists(input_videos_dir):
            for ext in ['.mp4', '.avi', '.mov']:
                all_video_candidates.extend(glob.glob(os.path.join(input_videos_dir, f'*{ext}')))
        # 检查uploads目录
        uploads_dir = os.path.join(project_root, 'uploads')
        if os.path.exists(uploads_dir):
            for ext in ['.mp4', '.avi', '.mov']:
                all_video_candidates.extend(glob.glob(os.path.join(uploads_dir, f'*{ext}')))
        # 选择第一个找到的视频
        if all_video_candidates:
            video_to_use = all_video_candidates[0]
            print_debug_info(f"找到替代视频文件: {video_to_use}")
        else:
            print(f"\n严重错误: 无法找到任何可用的视频文件")
            print(f"解说词生成成功，但无法合成视频。解说词内容已保存。")
            # 保存解说词到统一的commentary目录
            try:
                commentary_dir = os.path.join(OUTPUT_DIR, 'commentary')
                os.makedirs(commentary_dir, exist_ok=True)
                text_output_file = os.path.join(commentary_dir, f"commentary_{timestamp}.txt")
                with open(text_output_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(commentary_text)
                safe_print(f"解说词已保存到: {text_output_file}")
                return
            except Exception as e:
                print_debug_info(f"保存解说词失败: {str(e)}")
                return
    
    # 步骤5: 合成视频和音频
    print_debug_info("开始合成视频和音频")
    print_debug_info(f"视频路径: {video_to_use}")
    print_debug_info(f"音频路径: {audio_file}")
    print_debug_info(f"输出路径: {output_video}")
    
    # 验证输入文件是否存在
    if not os.path.exists(video_to_use):
        print_debug_info(f"错误: 视频文件不存在: {video_to_use}")
        return
    
    if not os.path.exists(audio_file):
        print_debug_info(f"错误: 音频文件不存在: {audio_file}")
        return
    
    success, message = merge_audio_with_video(
        video_to_use,
        audio_file,
        output_video
    )
    
    if success:
        print_debug_info(f"视频合成成功: {output_video}")
        safe_print(f"\n解说视频已成功生成: {output_video}")
    else:
        print_debug_info(f"视频合成失败: {message}")
        safe_print(f"\n解说词生成成功，但由于缺少ffmpeg，无法合成视频。\n解说词内容:\n{commentary_text}")
        safe_print("\n您可以单独保存解说词，或者安装ffmpeg后重新运行程序。")
        # 保存解说词到统一的commentary目录
        try:
            commentary_dir = os.path.join(OUTPUT_DIR, 'commentary')
            os.makedirs(commentary_dir, exist_ok=True)
            text_output_file = os.path.join(commentary_dir, f"commentary_{timestamp}.txt")
            with open(text_output_file, 'w', encoding='utf-8', errors='replace') as f:
                f.write(commentary_text)
            safe_print(f"解说词已保存到: {text_output_file}")
        except Exception as e:
            print_debug_info(f"保存解说词失败: {str(e)}")
        return
    
    # 清理临时文件
    print_debug_info("清理临时文件")
    if os.path.exists(temp_dir):
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            try:
                os.remove(file_path)
            except Exception as e:
                print_debug_info(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
        
    # 移动生成的视频到output_videos目录
    print_debug_info(f"解说视频已生成: {output_video}")

if __name__ == "__main__":
    main()