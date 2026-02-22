import os
import uuid
import time
import secrets
import shutil
import glob
import threading
import subprocess
import requests
import sys
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from database import db, User, Video

# 获取项目根目录（只定义一次）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 语音服务配置
VOICE_SERVICE_URL = "http://localhost:5001"
VOICE_SERVICE_PATH = os.path.join(PROJECT_ROOT, "football_voice")
voice_service_process = None

# 配置上传文件夹和允许的文件类型
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')

# 统一的输出目录
UNIFIED_OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv'}

# 创建Flask应用
app = Flask(__name__, static_folder='.', template_folder='.')

# 配置Flask应用
app.config['SECRET_KEY'] = secrets.token_hex(16)  # 使用安全随机生成的密钥
app.config['PERMANENT_SESSION_LIFETIME'] = 60 * 60 * 24 * 7  # 会话有效期为7天
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///football_translation.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库和登录管理器
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 创建上传和输出文件夹
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 检查和启动语音服务
def check_and_start_voice_service():
    """检查语音服务是否运行，如未运行则启动"""
    global voice_service_process
    
    # 尝试连接语音服务
    try:
        response = requests.get(f"{VOICE_SERVICE_URL}/tts", timeout=2)
        if response.status_code == 200:
            print("语音服务已在运行")
            return True
    except (requests.ConnectionError, requests.Timeout):
        print("语音服务未运行，正在启动...")
    
    # 启动语音服务
    try:
        # 检查是否已经有语音服务进程在运行
        if voice_service_process is not None and voice_service_process.poll() is None:
            print("语音服务进程已存在但可能未响应，尝试重启")
            voice_service_process.terminate()
            voice_service_process.wait(timeout=5)
        
        # 启动新的语音服务进程
        python_exe = sys.executable
        voice_service_process = subprocess.Popen(
            [python_exe, "-m", "football_voice"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待服务启动
        print("正在等待语音服务启动...")
        for _ in range(10):  # 最多等待10秒
            time.sleep(1)
            try:
                response = requests.get(f"{VOICE_SERVICE_URL}/tts", timeout=1)
                if response.status_code == 200:
                    print("语音服务已成功启动")
                    return True
            except (requests.ConnectionError, requests.Timeout):
                continue
        
        print("警告：语音服务可能未成功启动，请手动检查")
        return False
    except Exception as e:
        print(f"启动语音服务失败: {str(e)}")
        return False

# 支持的语言列表
LANGUAGES = [
    {'code': 'zh-CN', 'name': '中文'},
    {'code': 'en-US', 'name': 'English'},
    {'code': 'ja-JP', 'name': '日本語'},
    {'code': 'ko-KR', 'name': '한국어'},
    {'code': 'es-ES', 'name': 'Español'},
    {'code': 'fr-FR', 'name': 'Français'},
    {'code': 'de-DE', 'name': 'Deutsch'},
    {'code': 'ru-RU', 'name': 'Русский'},
    {'code': 'pt-BR', 'name': 'Português'},
    {'code': 'ar-SA', 'name': 'العربية'}
]

# 登录管理器的用户加载函数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 检查文件类型是否允许
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 辅助函数：查找最新的文件
def find_latest_file(folder, pattern):
    files = glob.glob(os.path.join(folder, pattern))
    if not files:
        return None
    files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return files[0]

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 静态文件路由
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': '用户名已存在'})
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': '邮箱已被注册'})
        
        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            return jsonify({'success': True, 'message': '注册成功'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    return send_from_directory('.', 'register.html')

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            # 设置session为永久有效
            session.permanent = True
            return jsonify({'success': True, 'message': '登录成功'})
        
        return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    return send_from_directory('.', 'login.html')

# 登出路由
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# 个人主页路由
@app.route('/profile')
@login_required
def profile():
    # 获取当前用户的视频列表
    videos = Video.query.filter_by(user_id=current_user.id).order_by(Video.created_at.desc()).all()
    
    # 转换为JSON可序列化的格式
    video_list = []
    for video in videos:
        video_list.append({
            'id': video.id,
            'filename': video.filename,
            'created_at': video.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'has_processed': video.processed_path is not None
        })
    
    return jsonify({
        'success': True,
        'user': {
            'username': current_user.username,
            'email': current_user.email,
            'created_at': current_user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        },
        'videos': video_list
    })

# 上传视频文件路由
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件上传'})
    
    file = request.files['file']
    
    # 检查文件名是否为空
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'})
    
    # 检查文件类型是否允许
    if file and allowed_file(file.filename):
        # 生成唯一的文件名
        original_filename = file.filename
        filename = secure_filename(original_filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        
        # 将视频信息保存到数据库
        video = Video(
            filename=original_filename,
            filepath=filepath,
            user_id=current_user.id
        )
        
        try:
            db.session.add(video)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '文件上传成功',
                'filename': unique_filename,
                'filepath': filepath
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})
    
    return jsonify({'success': False, 'message': '不支持的文件类型'})

# 导入必要的模块
import threading
import uuid
import datetime
import shutil

# 添加调试信息打印函数
def print_debug_info(message):
    """打印调试信息，带时间戳"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[DEBUG {timestamp}] {message}")

# 安全地复制文件
def safe_copy(src, dst):
    """安全地复制文件，处理可能的异常"""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print_debug_info(f"复制文件失败 {src} -> {dst}: {str(e)}")
        return False

# 用于存储任务状态的字典
task_status = {}

# 后台处理函数
def process_video_background(filename, language, voice, input_filepath, output_filepath, task_id):
    try:
        # 更新任务状态为处理中
        task_status[task_id] = {'status': 'processing', 'message': '正在处理视频...'}
        
        # 1. 将上传的视频复制到项目根目录的input_videos文件夹
        project_input_dir = os.path.join(PROJECT_ROOT, "input_videos")
        os.makedirs(project_input_dir, exist_ok=True)
        project_input_path = os.path.join(project_input_dir, filename)
        shutil.copy2(input_filepath, project_input_path)
        print(f"已将视频复制到项目输入目录: {project_input_path}")
        task_status[task_id] = {'status': 'processing', 'message': '正在准备AI解说...'}
        
        # 3. 设置环境变量并调用run_AIGC.py
        env = os.environ.copy()
        env["AIGC_LANGUAGE"] = language
        env["AIGC_VOICE"] = voice
        env["VOICE_SERVICE_URL"] = VOICE_SERVICE_URL  # 传递语音服务URL
        
        print(f"开始调用run_AIGC.py，语言: {language}")
        task_status[task_id] = {'status': 'processing', 'message': '正在生成AI解说...'}
        
        # 确保语音服务正在运行
        if not check_and_start_voice_service():
            raise Exception("语音服务启动失败，无法继续处理")
        
        # 使用Popen而不是run，以便可以捕获实时输出并更新进度
        import subprocess
        import time
            
        # 传递视频路径参数给run_AIGC.py
        process = subprocess.Popen(
            ["python", os.path.join(PROJECT_ROOT, "run_AIGC.py"), "--video_path", project_input_path], 
            env=env,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 实时捕获输出并更新任务状态
        stdout_output = []
        stderr_output = []
        
        # 设置超时时间（30分钟）
        timeout = 30 * 60  # 30分钟
        start_time = time.time()
        
        # 创建一个字典来跟踪进度状态
        progress_phrases = {
            "tracking_ball": "正在跟踪足球...",
            "commentary": "正在生成解说文本...",
            "voice": "正在合成语音...",
            "merge": "正在合成音视频...",
            "complete": "处理完成"
        }
        
        while process.poll() is None:
            # 检查超时
            if time.time() - start_time > timeout:
                process.kill()
                raise Exception("视频处理超时")
                
            # 读取输出
            line = process.stdout.readline()
            if line:
                stdout_output.append(line)
                print(line.strip())
                
                # 根据输出内容更新进度
                if "tracking_ball" in line.lower():
                    task_status[task_id] = {'status': 'processing', 'message': progress_phrases["tracking_ball"]}
                elif "commentary" in line.lower() or "解说" in line:
                    task_status[task_id] = {'status': 'processing', 'message': progress_phrases["commentary"]}
                elif "voice" in line.lower() or "语音" in line:
                    task_status[task_id] = {'status': 'processing', 'message': progress_phrases["voice"]}
                elif "merge" in line.lower() or "合成" in line:
                    task_status[task_id] = {'status': 'processing', 'message': progress_phrases["merge"]}
            
            time.sleep(0.1)  # 避免CPU占用过高
        
        # 读取剩余输出
        stdout_output.extend(process.stdout.readlines())
        stderr_output.extend(process.stderr.readlines())
        
        # 检查进程是否成功完成
        if process.returncode != 0:
            error_message = f"处理失败，错误码: {process.returncode}\n标准错误输出: {''.join(stderr_output)}"
            print_debug_info(error_message)
            task_status[task_id] = {'status': 'error', 'message': '视频处理失败'}
            return
        
        # 查找生成的视频文件
        # 1. 定义所有可能的输出目录
        possible_dirs = [
            os.path.join(PROJECT_ROOT, 'output', 'final_output'),  # 主要输出目录
            os.path.join(UNIFIED_OUTPUT_DIR, 'final_output'),      # 统一输出目录
            os.path.join(PROJECT_ROOT, 'output_videos')            # 旧版输出目录
        ]
        
        # 2. 定义所有可能的文件模式
        file_patterns = [
            'football_commentary_*.mp4',  # 标准解说视频
            'test_commentary_*.mp4',      # 测试解说视频
            '*.mp4'                       # 所有MP4文件
        ]
        
        final_video = None
        latest_time = 0
        
        # 3. 遍历所有目录和模式进行查找，找出最新的文件
        for output_dir in possible_dirs:
            if os.path.exists(output_dir):
                print_debug_info(f"正在检查目录: {output_dir}")
                
                # 列出目录中的所有文件，用于调试
                try:
                    all_files = os.listdir(output_dir)
                    print_debug_info(f"目录中的文件数量: {len(all_files)}")
                    if len(all_files) > 0:
                        print_debug_info(f"最近的5个文件: {', '.join(sorted(all_files)[-5:])}")
                except Exception as e:
                    print_debug_info(f"无法读取目录内容: {str(e)}")
                
                # 尝试所有文件模式
                for pattern in file_patterns:
                    files = glob.glob(os.path.join(output_dir, pattern))
                    print_debug_info(f"在 {output_dir} 中查找 {pattern}: 找到 {len(files)} 个文件")
                    
                    # 遍历找到的文件，找出最新的
                    for file in files:
                        try:
                            file_time = os.path.getmtime(file)
                            file_size = os.path.getsize(file)
                            print_debug_info(f"  - 找到文件: {os.path.basename(file)}, 修改时间: {datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')}, 大小: {file_size / (1024*1024):.2f} MB")
                            
                            # 如果是最新的文件，更新final_video
                            if file_time > latest_time:
                                latest_time = file_time
                                final_video = file
                        except Exception as e:
                            print_debug_info(f"  - 无法获取文件信息: {str(e)}")
        
        # 打印找到的视频路径（如果有）
        if final_video:
            print_debug_info(f"找到视频文件: {final_video}, 大小: {os.path.getsize(final_video) / (1024*1024):.2f} MB")
        else:
            print_debug_info("未找到生成的视频文件")
            # 打印所有可能的目录路径，便于调试
            print_debug_info(f"UNIFIED_OUTPUT_DIR: {UNIFIED_OUTPUT_DIR}")
            print_debug_info(f"aigc_output_dir: {aigc_output_dir}")
            task_status[task_id] = {'status': 'error', 'message': '未找到生成的视频文件'}
            return
        
        # 复制视频到web前端的outputs目录
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        output_filename = f"processed_{unique_id}_{timestamp}_{filename}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        
        if safe_copy(final_video, output_path):
            print_debug_info(f"已将视频复制到前端输出目录: {output_path}")
            
            # 更新数据库中的视频信息
            video = Video.query.filter_by(filepath=input_filepath).first()
            if video:
                video.processed_path = output_path
                video.status = 'processed'
                db.session.commit()
                print_debug_info(f"已更新视频状态为已处理: {video.id}")
        else:
            print_debug_info("复制视频到前端输出目录失败")
            task_status[task_id] = {'status': 'error', 'message': '复制视频失败'}
            return
        
        # 查找相关的解说词和音频文件
        # 解说词文件
        commentary_dir = os.path.join(UNIFIED_OUTPUT_DIR, 'commentary')
        latest_commentary = find_latest_file(commentary_dir, 'commentary_*.txt')
        
        # 音频文件
        audio_dir = os.path.join(UNIFIED_OUTPUT_DIR, 'audio')
        latest_audio = find_latest_file(audio_dir, 'commentary_*.wav')
        
        # 比赛分析数据
        analysis_dir = os.path.join(UNIFIED_OUTPUT_DIR, 'analysis')
        latest_analysis = find_latest_file(analysis_dir, '*_analysis.json')
        
        # 准备返回给前端的数据
        result_data = {
            'video_path': output_filename,
            'has_commentary': latest_commentary is not None,
            'has_audio': latest_audio is not None,
            'has_analysis': latest_analysis is not None
        }
        
        # 更新任务状态为完成
        task_status[task_id] = {
            'status': 'completed',
            'message': '视频处理完成',
            'result': result_data
        }
        
        print_debug_info(f"视频处理完成，输出文件: {output_path}")
        
        # 合并输出
        stdout_str = ''.join(stdout_output)
        stderr_str = ''.join(stderr_output)
        
        print(f"run_AIGC.py输出:\n{stdout_str}")
        
        if process.returncode != 0:
            print(f"run_AIGC.py执行失败:\n{stderr_str}")
            task_status[task_id] = {'status': 'error', 'message': f'AI解说生成失败: {stderr_str[:100]}...'}
            return
        
        # 任务状态已在前面的逻辑中更新为完成
        print("视频处理任务已完成并设置状态")
        
    except Exception as e:
        print(f"处理异常: {str(e)}")
        task_status[task_id] = {'status': 'error', 'message': f'处理失败: {str(e)}'}

# 生成解说视频路由
@app.route('/generate', methods=['POST'])
# @login_required  # 临时注释掉登录检查
def generate_commentary():
    # 创建一个模拟的current_user对象用于测试
    class MockUser:
        def __init__(self):
            self.id = 1
            self.username = 'testuser'
    
    # 临时设置current_user
    from flask_login import current_user
    if not hasattr(current_user, 'id') or current_user.is_anonymous:
        current_user = MockUser()
    try:
        data = request.json
        filename = data.get('filename')
        language_code = data.get('language', 'zh-CN')
        # 语言代码映射，将前端传递的语言代码映射到run_AIGC.py支持的语言名称
        language_mapping = {
            'zh-CN': '汉语',
            'en-US': 'English',
            'ja-JP': 'English',  # 当前run_AIGC.py只支持汉语和英语，其他语言默认使用英语
            'ko-KR': 'English',
            'es-ES': 'English',
            'fr-FR': 'English',
            'de-DE': 'English',
            'ru-RU': 'Русский',
            'pt-BR': 'English',
            'ar-SA': 'English'
        }
        language = language_mapping.get(language_code, '汉语')
        voice = data.get('voice', 'auto')
        frame_interval = data.get('frame_interval', 15)  # 添加帧间隔参数，默认15
        max_commentary_words = data.get('max_commentary_words', 500)  # 添加解说词最大字数限制，默认500

        if not filename:
            return jsonify({'success': False, 'message': '文件名不能为空'})

        input_filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(input_filepath):
            return jsonify({'success': False, 'message': '文件不存在'})

        # 创建任务ID
        task_id = str(uuid.uuid4())

        # 初始化任务状态
        task_status[task_id] = {
            'status': 'processing', 
            'message': '正在准备处理视频...',
            'progress_step': 0,
            'progress_max': 5
        }

        # 将视频复制到项目根目录的input_videos目录
        project_input_dir = os.path.join(PROJECT_ROOT, "input_videos")
        os.makedirs(project_input_dir, exist_ok=True)
        project_input_path = os.path.join(project_input_dir, filename)
        shutil.copy2(input_filepath, project_input_path)
        print(f"已将视频复制到项目输入目录: {project_input_path}")

        # 设置输出文件路径
        output_filepath = os.path.join(OUTPUT_FOLDER, f"processed_{filename}")

        # 启动异步进程处理视频
        def process_video():
            stdout_output = []
            stderr_output = []
            start_time = time.time()
            timeout = 30 * 60  # 30分钟超时

            try:
                # 确保语音服务正在运行
                if not check_and_start_voice_service():
                    task_status[task_id] = {
                        'status': 'error', 
                        'message': '语音服务启动失败，无法生成解说',
                        'progress_step': 0,
                        'progress_max': 5
                    }
                    return
                
                # 创建一个字典来跟踪进度状态
                progress_phrases = {
                    "tracking_ball": "正在跟踪足球...",
                    "commentary": "正在生成解说文本...",
                    "voice": "正在合成语音...",
                    "merge": "正在合成音视频...",
                    "complete": "处理完成"
                }

                # 设置环境变量
                env = os.environ.copy()
                env['VOICE_SERVICE_URL'] = VOICE_SERVICE_URL  # 确保run_AIGC.py能找到语音服务
                
                # 执行run_AIGC.py并传递参数
                cmd = [
                    'python', os.path.join(PROJECT_ROOT, 'run_AIGC.py'),
                    '--language', language,
                    '--voice', voice,
                    '--frame_interval', str(frame_interval),
                    '--max_words', str(max_commentary_words)
                ]
                
                print(f"启动视频处理进程: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=PROJECT_ROOT,
                    env=env
                )

                while process.poll() is None:
                    # 检查超时
                    if time.time() - start_time > timeout:
                        process.kill()
                        raise Exception("视频处理超时")
                        
                    # 读取输出
                    line = process.stdout.readline()
                    if line:
                        stdout_output.append(line)
                        print(line.strip())
                        
                        # 根据输出内容更新进度
                        if "tracking_ball" in line.lower():
                            task_status[task_id] = {
                                'status': 'processing', 
                                'message': progress_phrases["tracking_ball"],
                                'progress_step': 1,
                                'progress_max': 5
                            }
                        elif "commentary" in line.lower() or "解说" in line:
                            task_status[task_id] = {
                                'status': 'processing', 
                                'message': progress_phrases["commentary"],
                                'progress_step': 2,
                                'progress_max': 5
                            }
                        elif "voice" in line.lower() or "语音" in line:
                            task_status[task_id] = {
                                'status': 'processing', 
                                'message': progress_phrases["voice"],
                                'progress_step': 3,
                                'progress_max': 5
                            }
                        elif "merge" in line.lower() or "合成" in line:
                            task_status[task_id] = {
                                'status': 'processing', 
                                'message': progress_phrases["merge"],
                                'progress_step': 4,
                                'progress_max': 5
                            }
                    
                    time.sleep(0.1)  # 避免CPU占用过高

                # 读取剩余输出
                stdout_output.extend(process.stdout.readlines())
                stderr_output.extend(process.stderr.readlines())
                
                # 合并输出
                stdout_str = ''.join(stdout_output)
                stderr_str = ''.join(stderr_output)
                
                print(f"run_AIGC.py输出:\n{stdout_str}")
                
                if process.returncode != 0:
                    print(f"run_AIGC.py执行失败:\n{stderr_str}")
                    task_status[task_id] = {
                        'status': 'error', 
                        'message': f'AI解说生成失败: {stderr_str[:100]}...',
                        'progress_step': 0,
                        'progress_max': 5
                    }
                    return

                # 4. 查找生成的视频文件 - 使用更全面的查找策略
                task_status[task_id] = {
                    'status': 'processing', 
                    'message': '正在准备最终视频...',
                    'progress_step': 4,
                    'progress_max': 5
                }
                
                # 定义可能的输出目录
                possible_dirs = [
                    os.path.join(UNIFIED_OUTPUT_DIR, 'final_output'),  # 主要输出目录
                    UNIFIED_OUTPUT_DIR,  # 统一输出目录
                    os.path.join(PROJECT_ROOT, 'output_videos'),  # 旧版输出目录
                    os.path.join(PROJECT_ROOT, 'output')  # 其他可能的输出目录
                ]
                
                # 定义可能的文件模式
                file_patterns = [
                    'football_commentary_*.mp4',  # 标准解说视频
                    'test_commentary_*.mp4',  # 测试解说视频
                    '*.mp4'  # 所有MP4文件作为后备
                ]
                
                # 查找最新生成的视频文件
                generated_video = None
                latest_time = 0
                found_files = []
                
                print("开始查找生成的视频文件...")
                # 遍历所有可能的目录和模式
                for output_dir in possible_dirs:
                    if os.path.exists(output_dir):
                        print(f"检查输出目录: {output_dir}")
                        
                        for pattern in file_patterns:
                            search_path = os.path.join(output_dir, pattern)
                            matching_files = glob.glob(search_path)
                            
                            for file in matching_files:
                                file_time = os.path.getmtime(file)
                                file_size = os.path.getsize(file)
                                found_files.append((file, file_time, file_size))
                                
                                if file_time > latest_time:
                                    latest_time = file_time
                                    generated_video = file
                
                # 打印找到的文件信息，便于调试
                print(f"在所有目录中找到 {len(found_files)} 个视频文件")
                if found_files:
                    print("最近的5个视频文件:")
                    found_files.sort(key=lambda x: x[1], reverse=True)
                    for i, (file, file_time, file_size) in enumerate(found_files[:5]):
                        file_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                        file_size_mb = file_size / (1024 * 1024)
                        print(f"  {i+1}. {os.path.basename(file)} - 修改时间: {file_time_str}, 大小: {file_size_mb:.2f}MB")
                
                if not generated_video:
                    print("错误: 未能找到生成的视频文件")
                    task_status[task_id] = {
                        'status': 'error', 
                        'message': '未能找到生成的视频文件',
                        'progress_step': 0,
                        'progress_max': 5
                    }
                    return
                
                print(f"找到生成的视频文件: {generated_video}")

                # 5. 将生成的视频复制到web_frontend的outputs文件夹
                try:
                    # 确保输出目录存在
                    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                    # 先检查生成的视频文件是否完整（大小是否合理）
                    video_size = os.path.getsize(generated_video)
                    print(f"生成的视频文件大小: {video_size / (1024 * 1024):.2f}MB")
                    
                    if video_size < 1024 * 1024:  # 如果文件太小（小于1MB），可能不完整
                        print(f"警告: 生成的视频文件可能不完整，大小仅为{video_size / 1024:.2f}KB")
                    
                    # 复制文件时添加异常处理和重试机制
                    max_retries = 3
                    retry_count = 0
                    copied_successfully = False
                    
                    while retry_count < max_retries and not copied_successfully:
                        try:
                            shutil.copy2(generated_video, output_filepath)
                            print(f"已将生成的视频复制到前端输出目录: {output_filepath}")
                            copied_successfully = True
                        except Exception as copy_e:
                            retry_count += 1
                            print(f"复制视频文件时出错 (尝试 {retry_count}/{max_retries}): {str(copy_e)}")
                            if retry_count < max_retries:
                                time.sleep(1)  # 等待1秒后重试
                    
                    if not copied_successfully:
                        print("所有复制尝试均失败，将使用原始路径访问视频")
                        # 使用原始路径作为备选方案
                        output_filepath = generated_video
                except Exception as copy_e:
                    print(f"复制视频文件时出错: {str(copy_e)}")
                    # 即使复制失败，仍然继续处理，但使用原始路径
                    output_filepath = generated_video
                
                # 更新数据库中的视频记录
                try:
                    # 在后台线程中访问数据库需要应用上下文
                    with app.app_context():
                        # 使用完整文件路径查找视频记录，更准确
                        video = Video.query.filter_by(filepath=input_filepath).first()
                        if video:
                            video.processed_path = output_filepath
                            db.session.commit()
                            print(f"已更新数据库记录，视频ID: {video.id}")
                        else:
                            print(f"未找到对应视频记录: {input_filepath}")
                except Exception as e:
                    print(f"更新数据库失败: {str(e)}")
                    db.session.rollback()

                # 更新任务状态为完成
                output_filename = os.path.basename(output_filepath)
                output_path = f'/output/{output_filename}'
                
                # 添加更多调试信息到任务状态中
                video_size_value = f"{os.path.getsize(output_filepath) / (1024 * 1024):.2f}MB" if os.path.exists(output_filepath) else 'unknown'
                task_status[task_id] = {
                    'status': 'completed', 
                    'message': '解说生成完成',
                    'output_filename': output_filename,
                    'output_path': output_path,
                    'original_video_path': generated_video,
                    'video_size': video_size_value,
                    'progress_step': 5,
                    'progress_max': 5
                }
                print(f"任务 {task_id} 已完成，输出路径: {output_path}")

            except Exception as e:
                print(f"处理异常: {str(e)}")
                task_status[task_id] = {
                    'status': 'error', 
                    'message': f'处理失败: {str(e)}',
                    'progress_step': 0,
                    'progress_max': 5
                }

        # 启动后台处理
        threading.Thread(target=process_video).start()

        # 返回任务ID
        return jsonify({
            'success': True, 
            'message': '解说生成任务已启动',
            'task_id': task_id
        })

    except Exception as e:
        print(f"生成解说时出错: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'生成解说失败: {str(e)}'
        })

# 提供任务状态查询的路由
@app.route('/task_status/<task_id>')
def get_task_status(task_id):
    print(f"收到任务状态查询请求: task_id={task_id}")
    try:
        # 检查task_status字典是否包含该任务ID
        if task_id not in task_status:
            print(f"任务ID {task_id} 不存在于task_status字典中")
            # 打印当前所有可用的任务ID，方便调试
            print(f"当前可用的任务ID列表: {list(task_status.keys())}")
            return jsonify({
                'success': False, 
                'message': '任务ID不存在'
            })
        
        # 获取任务状态
        status = task_status[task_id].copy()  # 使用copy避免并发修改问题
        print(f"任务 {task_id} 当前状态: {status.get('status')}, 进度: {status.get('progress_step', 0)}/{status.get('progress_max', 0)}")
        
        # 当任务完成时，自动查找并准备最新的视频文件
        if status.get('status') == 'completed':
            print(f"任务 {task_id} 已完成，正在查找最新的视频文件...")
            
            # 使用之前优化过的视频查找逻辑
            try:
                # 定义可能的输出目录
                possible_dirs = [
                    os.path.join(UNIFIED_OUTPUT_DIR, 'final_output'),  # 主要输出目录
                    UNIFIED_OUTPUT_DIR,  # 统一输出目录
                    os.path.join(PROJECT_ROOT, 'output_videos'),  # 旧版输出目录
                    os.path.join(PROJECT_ROOT, 'output')  # 其他可能的输出目录
                ]
                
                # 定义可能的文件模式
                file_patterns = [
                    'football_commentary_*.mp4',  # 标准解说视频
                    'test_commentary_*.mp4',  # 测试解说视频
                    '*.mp4'  # 所有MP4文件作为后备
                ]
                
                # 查找最新生成的视频文件
                latest_video = None
                latest_time = 0
                found_files = []
                
                # 遍历所有可能的目录和模式
                for output_dir in possible_dirs:
                    if os.path.exists(output_dir):
                        print(f"检查输出目录: {output_dir}")
                        
                        for pattern in file_patterns:
                            search_path = os.path.join(output_dir, pattern)
                            matching_files = glob.glob(search_path)
                            
                            for file in matching_files:
                                file_time = os.path.getmtime(file)
                                file_size = os.path.getsize(file)
                                found_files.append((file, file_time, file_size))
                                
                                if file_time > latest_time:
                                    latest_time = file_time
                                    latest_video = file
                
                # 打印找到的文件信息，便于调试
                print(f"在所有目录中找到 {len(found_files)} 个视频文件")
                if found_files:
                    print("最近的5个视频文件:")
                    found_files.sort(key=lambda x: x[1], reverse=True)
                    for i, (file, file_time, file_size) in enumerate(found_files[:5]):
                        file_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                        file_size_mb = file_size / (1024 * 1024)
                        print(f"  {i+1}. {os.path.basename(file)} - 修改时间: {file_time_str}, 大小: {file_size_mb:.2f}MB")
                
                if latest_video:
                    video_filename = os.path.basename(latest_video)
                    print(f"找到最新视频文件: {video_filename}, 路径: {latest_video}")
                    
                    # 检查文件是否已在前端输出目录中
                    output_file_path = os.path.join(OUTPUT_FOLDER, video_filename)
                    
                    if not os.path.exists(output_file_path):
                        try:
                            # 确保输出目录存在
                            os.makedirs(OUTPUT_FOLDER, exist_ok=True)
                            # 复制最新视频到前端输出目录
                            shutil.copy2(latest_video, output_file_path)
                            print(f"已自动复制最新视频: {video_filename} -> {output_file_path}")
                        except Exception as copy_e:
                            print(f"复制最新视频时出错: {str(copy_e)}")
                            # 即使复制失败，仍然返回任务完成状态，只是没有视频文件路径
                            return jsonify({
                                'success': True, 
                                'task_status': status,
                                'warning': f'任务已完成但无法访问视频文件: {str(copy_e)}'
                            })
                    
                    # 更新任务状态，添加视频文件名和完整路径
                    status['output_file'] = video_filename
                    status['output_path'] = f"/output/{video_filename}"  # 确保前端能正确访问
                    task_status[task_id] = status
                    print(f"已更新任务 {task_id} 的输出信息")
                else:
                    print(f"警告: 未找到任何视频文件")
            except Exception as search_e:
                print(f"查找视频文件时出错: {str(search_e)}")
                # 即使查找失败，仍然返回任务完成状态
                return jsonify({
                    'success': True, 
                    'task_status': status,
                    'warning': f'任务已完成但查找视频文件失败: {str(search_e)}'
                })
        
        # 确保返回完整的状态信息，包括进度
        print(f"返回任务 {task_id} 状态信息")
        return jsonify({
            'success': True, 
            'task_status': status
        })
    except Exception as e:
        error_message = f"获取任务状态时出错: {str(e)}"
        print(error_message)
        # 打印详细的错误堆栈信息，便于调试
        import traceback
        print(traceback.format_exc())
        return jsonify({
              'success': False, 
              'message': error_message
          })

# 提供输出视频文件路由
@app.route('/output/<filename>')
def serve_output(filename):
    print(f"接收到视频访问请求: {filename}")
    
    # 定义可能的视频文件位置
    possible_paths = []
    
    # 1. 首先检查前端输出目录
    output_file_path = os.path.join(OUTPUT_FOLDER, filename)
    possible_paths.append(output_file_path)
    
    # 2. 检查统一输出目录的final_output子目录
    final_output_dir = os.path.join(UNIFIED_OUTPUT_DIR, 'final_output')
    if os.path.exists(final_output_dir):
        final_output_path = os.path.join(final_output_dir, filename)
        possible_paths.append(final_output_path)
        
        # 查找可能包含filename的其他文件
        for file in os.listdir(final_output_dir):
            if filename in file:
                possible_paths.append(os.path.join(final_output_dir, file))
    
    # 3. 检查其他可能的输出目录
    other_dirs = [
        os.path.join(PROJECT_ROOT, 'output_videos'),
        PROJECT_ROOT,
        os.path.join(PROJECT_ROOT, 'output')
    ]
    
    for dir_path in other_dirs:
        if os.path.exists(dir_path):
            possible_paths.append(os.path.join(dir_path, filename))
            # 查找可能包含filename的其他文件
            for file in os.listdir(dir_path):
                if filename in file and file.endswith('.mp4'):
                    possible_paths.append(os.path.join(dir_path, file))
    
    # 去重并检查文件是否存在
    found_path = None
    for path in possible_paths:
        if os.path.exists(path):
            # 验证文件是否为有效的视频文件（检查文件大小）
            file_size = os.path.getsize(path)
            if file_size > 0:
                found_path = path
                print(f"找到视频文件: {found_path} (大小: {file_size / (1024 * 1024):.2f}MB)")
                break
    
    # 如果找到文件但不在前端输出目录，复制一份
    if found_path and found_path != output_file_path:
        try:
            # 确保输出目录存在
            os.makedirs(OUTPUT_FOLDER, exist_ok=True)
            # 复制文件到前端输出目录
            print(f"复制视频文件到前端目录: {found_path} -> {output_file_path}")
            shutil.copy2(found_path, output_file_path)
            # 更新文件路径为前端目录中的路径
            found_path = output_file_path
        except Exception as copy_e:
            print(f"复制文件时出错，但仍使用原始路径: {str(copy_e)}")
    
    # 如果找不到文件，返回404错误
    if not found_path:
        print(f"错误: 无法在以下路径中找到视频文件 {filename}: {possible_paths}")
        return jsonify({
            'success': False,
            'message': '视频文件不存在或无法访问'
        }), 404
    
    # 提供文件 - 直接使用找到的路径
    try:
        # 获取文件目录和文件名
        file_dir = os.path.dirname(found_path)
        file_name = os.path.basename(found_path)
        print(f"提供视频文件: 目录={file_dir}, 文件名={file_name}")
        
        # 检查文件扩展名，确保正确设置MIME类型
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # 为MP4文件设置正确的MIME类型
        if file_ext == '.mp4':
            # 使用send_file而不是send_from_directory，以便更好地控制响应头
            from flask import send_file
            return send_file(
                found_path,
                mimetype='video/mp4',
                as_attachment=False,
                download_name=file_name
            )
        else:
            # 对于其他文件类型，使用send_from_directory
            return send_from_directory(file_dir, file_name)
    except Exception as e:
        print(f"提供文件时出错: {str(e)}")
        # 打印详细的错误堆栈信息
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'提供视频文件失败: {str(e)}'
        }), 500

# 获取服务器状态路由
@app.route('/status')
def get_status():
    # 检查上传和输出文件夹的状态
    upload_files = len(os.listdir(UPLOAD_FOLDER))
    output_files = len(os.listdir(OUTPUT_FOLDER))
    
    return jsonify({
        'success': True,
        'upload_files_count': upload_files,
        'output_files_count': output_files,
        'supported_languages': LANGUAGES
    })

# 获取语言列表的路由
@app.route('/languages')
def get_languages():
    return jsonify(LANGUAGES)



# 检查登录状态的路由
@app.route('/check_login')
def check_login():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'email': current_user.email
        })
    else:
        return jsonify({'authenticated': False})

# 删除视频路由
@app.route('/delete_video', methods=['POST'])
@login_required
def delete_video():
    data = request.json
    if 'id' not in data:
        return jsonify({'success': False, 'message': '缺少视频ID'})
    
    video_id = data['id']
    try:
        # 查找视频记录
        video = Video.query.get_or_404(video_id)
        
        # 检查视频是否属于当前用户
        if video.user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权删除此视频'})
        
        # 删除文件
        if video.filepath and os.path.exists(video.filepath):
            os.remove(video.filepath)
        if video.processed_path and os.path.exists(video.processed_path):
            os.remove(video.processed_path)
        
        # 删除数据库记录
        db.session.delete(video)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '视频已成功删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

# 创建数据库表并启动应用
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # 启动语音服务
    check_and_start_voice_service()
    
    # 启动Flask服务器
    # 在生产环境中，应该使用WSGI服务器如Gunicorn或uWSGI
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # 确保在Flask服务关闭时也关闭语音服务
        if voice_service_process is not None:
            print("正在关闭语音服务...")
            try:
                voice_service_process.terminate()
                voice_service_process.wait(timeout=5)
                print("语音服务已关闭")
            except:
                print("关闭语音服务时发生错误")
                pass