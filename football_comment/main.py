import os
import time
import cv2
import base64
import json
from pathlib import Path
from openai import OpenAI

# 安全打印函数，处理Unicode字符
def safe_print(text):
    try:
        print(text)
    except UnicodeEncodeError:
        # 使用安全方式打印，替换无法编码的字符
        safe_text = text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        print(safe_text)

# 配置API客户端
def get_api_client():
    try:
        # 请在这里填写您的Dashscope API Key
        return OpenAI(
            api_key="YOUR_DASHSCOPE_API_KEY",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
    except Exception as e:
        safe_print(f"API客户端初始化错误: {e}")
        return None

client = get_api_client()

# 使用正确的模型名称
MODEL_NAME = "qwen-vl-plus"
# 获取当前脚本所在目录的绝对路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
VIDEO_DIR = Path(os.path.join(CURRENT_DIR, "input_video"))  # 使用绝对路径
# 统一输出目录
OUTPUT_DIR = Path(os.path.join(os.path.dirname(CURRENT_DIR), "output"))

# 确保输出目录存在
OUTPUT_DIR.mkdir(exist_ok=True)

# 改进的提示词模板 - 基于比赛进程
PROMPT_TEMPLATE = (
    "作为足球解说员，请根据以下足球比赛场景信息生成一段生动的中文解说：\n"
    "场景描述：{scene_description}\n"
    "关键事件：{key_events}\n"
    "要求：纯中文，20-50字，结合比赛实际情况，语气激昂，专业且富有感染力，适合短视频平台播放"
)

# 从football_main结果中提取比赛分析数据
def extract_match_analysis():
    try:
        # 假设football_main会生成一个包含比赛分析的JSON文件
        analysis_path = os.path.join(os.path.dirname(CURRENT_DIR), "football_main", "match_analysis.json")
        if os.path.exists(analysis_path):
            with open(analysis_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        safe_print(f"提取比赛分析数据时出错: {e}")
        return {}

def extract_video_keyframes(video_path, num_frames=3):
    """从视频中提取关键帧并转换为base64编码"""
    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"无法打开视频文件: {video_path}")
            return []
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            print(f"视频文件没有帧: {video_path}")
            cap.release()
            return []
        
        frame_indices = [int(i * total_frames / (num_frames + 1)) for i in range(1, num_frames + 1)]
        
        frames_base64 = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if ret:
                frame = cv2.resize(frame, (320, 240))
                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frames_base64.append(frame_base64)
        
        cap.release()
        return frames_base64
        
    except Exception as e:
        print(f"视频处理错误: {e}")
        return []

def call_wen_model(prompt: str, images_base64: list = None):
    """调用千问模型"""
    global client
    
    # 如果client为None，尝试重新初始化
    if client is None:
        client = get_api_client()
        if client is None:
            return ""  # 初始化失败，返回空字符串
    
    try:
        content = [{"type": "text", "text": prompt}]
        
        if images_base64:
            for img_base64 in images_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_base64}"
                    }
                })
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": content}],
            max_tokens=100,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"模型调用错误: {e}")
        # 备选方案：使用纯文本模型
        try:
            response = client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            print(f"纯文本模型调用也失败: {e2}")
            return ""

def process_one_video(video_file=None):
    """处理视频并返回生成的解说词
    
    Args:
        video_file: 可选，指定要处理的视频文件路径
        
    Returns:
        str: 生成的解说词文本，如果处理失败则返回备用解说词
    """
    safe_print(f"检查视频目录: {VIDEO_DIR}")
    
    # 确保目录存在
    VIDEO_DIR.mkdir(exist_ok=True)
    safe_print(f"目录是否存在: {VIDEO_DIR.exists()}")
    
    # 如果没有指定视频文件，查找目录中的最新视频
    if video_file is None:
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv']
        video_files = []
        for ext in video_extensions:
            video_files.extend(VIDEO_DIR.glob(ext))
        
        if not video_files:
            safe_print(f"未找到 {VIDEO_DIR} 目录中的视频文件")
            # 列出目录内容以便调试
            try:
                safe_print(f"目录内容: {os.listdir(VIDEO_DIR)}")
            except Exception as e:
                safe_print(f"无法列出目录内容: {e}")
            return get_default_commentary()
        
        # 按修改时间排序，取最新的一个
        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        video_path = video_files[0]
    else:
        video_path = Path(video_file)
        if not video_path.exists():
            safe_print(f"指定的视频文件不存在: {video_file}")
            return get_default_commentary()
    
    safe_print(f"处理视频: {video_path.name}")
    
    frames_base64 = extract_video_keyframes(video_path)
    
    if not frames_base64:
        print(f"无法从 {video_path.name} 提取帧，跳过")
        return get_default_commentary()
        
    # 获取比赛分析数据
    match_analysis = extract_match_analysis()
    print(f"获取到的比赛分析数据: {match_analysis}")
    
    # 构建场景描述和关键事件
    scene_description = f"足球比赛视频: {video_path.stem}"
    
    # 从比赛分析中提取关键事件，如果没有则提供默认
    key_events = []
    
    # 检查是否有比赛分析数据
    if match_analysis:
        # 检查是否有队伍控球信息
        if "team_ball_control" in match_analysis:
            team_ball_control = match_analysis["team_ball_control"]
            # 简单统计哪支队伍控球时间更多
            team1_count = team_ball_control.count(1)
            team2_count = team_ball_control.count(2)
            if team1_count > team2_count:
                key_events.append("红队控球占据优势，积极组织进攻")
            else:
                key_events.append("蓝队控球占据优势，积极组织进攻")
        
        # 检查是否有球员信息
        if "players" in match_analysis and match_analysis["players"]:
            players = match_analysis["players"]
            # 计算场上球员数量
            player_count = sum(1 for p in players.values() if p)
            key_events.append(f"场上共有{player_count}名球员正在激烈角逐")
        
        # 检查是否有球的信息
        if "ball" in match_analysis and match_analysis["ball"]:
            key_events.append("足球正在场上快速传递")
        
        # 检查是否有射门信息
        if "shots" in match_analysis and match_analysis["shots"]:
            shots_count = len(match_analysis["shots"])
            key_events.append(f"比赛中出现{shots_count}次射门机会")
    
    # 如果没有关键事件数据，使用更详细的默认描述
    if not key_events:
        key_events = ["球员们正在激烈比赛", "双方争夺球权", "场面十分精彩", "进攻防守转换快速"]
    
    # 构建提示词
    key_events_text = "，".join(key_events) + "。"
    prompt = PROMPT_TEMPLATE.format(scene_description=scene_description, key_events=key_events_text)
    
    print(f"使用提示词生成解说: {prompt}")
    
    res_text = call_wen_model(prompt, frames_base64)
    
    # 如果AI生成失败或结果太短，使用备用解说词
    if not res_text or len(res_text) < 10:
        res_text = get_default_commentary()
        safe_print(f"AI生成失败或结果太短，使用备用解说词: '{res_text}'")
        
    # 使用安全的文件写入方式
    try:
        out_path = OUTPUT_DIR / (video_path.stem + ".txt")
        out_path.write_text(res_text, encoding="utf-8", errors="replace")
        safe_print(f"已生成解说: {out_path} - '{res_text[:100]}...'")
    except Exception as e:
        safe_print(f"写入解说词文件时出错: {e}")
    
    # 同时保存解说词到统一的commentary目录
    try:
        commentary_dir = os.path.join(OUTPUT_DIR, "commentary")
        os.makedirs(commentary_dir, exist_ok=True)
        commentary_path = os.path.join(commentary_dir, f"{video_path.stem}.txt")
        with open(commentary_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(res_text)
        safe_print(f"解说词已保存到统一目录: {commentary_path}")
    except Exception as e:
        safe_print(f"保存解说词到统一目录时出错: {e}")
    
    # 返回生成的解说词
    return res_text

def get_default_commentary():
    """获取默认解说词"""
    return "比赛进行到关键时刻！红队和蓝队的球员们在场上展开激烈争夺，双方都展现出了极高的竞技水平。看这个进攻配合多么流畅，防守也毫不示弱！真是一场精彩绝伦的比赛！"

# 添加主函数接口，供其他模块调用
def generate_commentary(video_file=None):
    """生成足球比赛解说词的主函数接口
    
    Args:
        video_file: 可选，指定要处理的视频文件路径
        
    Returns:
        tuple: (success, commentary_text)
    """
    try:
        safe_print(f"===== 开始生成足球视频解说 =====")
        start_time = time.time()
        
        # 确保目录存在
        VIDEO_DIR.mkdir(exist_ok=True)
        safe_print(f"视频目录路径: {VIDEO_DIR}")
        safe_print(f"目录是否存在: {VIDEO_DIR.exists()}")
        
        # 列出目录内容以便调试
        try:
            safe_print(f"目录内容: {os.listdir(VIDEO_DIR)}")
        except Exception as e:
            safe_print(f"无法列出目录内容: {e}")
        
        commentary_text = process_one_video(video_file)
        end_time = time.time()
        safe_print(f"处理完成，耗时: {end_time - start_time:.2f}秒")
        
        # 返回成功状态和生成的解说词
        return True, commentary_text
    except Exception as e:
        safe_print(f"生成解说词时发生异常: {e}")
        # 返回失败状态和默认解说词
        return False, get_default_commentary()

if __name__ == "__main__":
    success, commentary = generate_commentary()
    safe_print(f"\n处理完成! 生成状态: {'成功' if success else '失败'}")
    safe_print(f"生成的解说词: {commentary}")