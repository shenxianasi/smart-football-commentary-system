# 球智智库 - AI足球解说系统

这是一个基于人工智能的足球视频自动解说系统，集成了计算机视觉、自然语言处理和语音合成技术。系统能够自动分析足球比赛视频，识别球员动作和比赛事件，生成专业的解说词，并合成逼真的解说语音，最终生成带有解说的比赛视频。

## 📁 文件结构

```
球智智库/
├── api/                    # 独立的语音合成API服务（基于CosyVoice）
│   └── api/                # API服务源代码
├── football_comment/       # 足球解说词生成模块
│   └── main.py             # 解说词生成主程序
├── football_main/          # 视频分析核心模块（基于YOLO）
│   ├── main.py             # 视频分析入口
│   ├── trackers/           # 目标跟踪算法
│   ├── team_assigner/      # 球队归属识别
│   ├── player_ball_assigner/ # 控球权判定
│   ├── camera_movement_estimator/ # 摄像机运动估计
│   ├── speed_and_distance_estimator/ # 速度与距离估算
│   └── view_transformer/   # 视角转换
├── football_voice/         # 语音合成服务模块（与主流程集成）
│   ├── app.py              # 语音合成API服务 (端口 5001)
│   ├── voice_service.py    # 语音服务逻辑
│   └── voices.json         # 音色配置文件
├── Offside detection/      # 越位检测独立模块
│   ├── offside_detector.py # 越位检测核心逻辑
│   └── model.py            # 越位检测模型
├── web_frontend/           # Web前端应用
│   ├── server.py           # Flask后端服务器 (端口 5000)
│   ├── index.html          # 主页
│   ├── login.html          # 登录页
│   └── uploads/            # 上传文件存储
├── run_AIGC.py             # 核心工作流编排脚本（串联视频分析、解说生成、语音合成）
├── requirements.txt        # 项目主依赖列表
└── 演示视频.mp4            # 项目功能演示视频
```

## 🛠️ 技术栈

- **核心语言**: Python 3.10+
- **计算机视觉**:
  - YOLO (Ultralytics) - 球员与足球检测
  - OpenCV - 视频处理与图像分析
  - ByteTrack - 多目标跟踪
- **Web框架**: Flask (后端), HTML5/CSS3/JS (前端)
- **语音合成**:
  - CosyVoice (阿里云DashScope) - 高质量语音合成
  - FastAPI - 语音服务接口
- **多媒体处理**: FFMPEG - 音视频合并与转码
- **数据分析**: Pandas, NumPy - 比赛数据处理

## 📺 演示视频

项目演示视频位于项目根目录下：
`球智智库\演示视频.mp4`

## 🚀 环境部署

建议使用 Conda 管理虚拟环境。由于项目包含多个模块，建议创建两个环境以避免依赖冲突。

### 1. 主环境 (AI解说系统)

用于运行Web应用、视频分析和解说生成。

```bash
# 创建环境
conda create -n football_aigc python=3.10
conda activate football_aigc

# 安装PyTorch (根据您的CUDA版本选择，这里以CUDA 12.1为例)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 安装项目依赖
pip install -r requirements.txt

# 注意：如果遇到numpy版本冲突，建议使用 numpy==1.26.4
pip install numpy==1.26.4
```

### 2. 越位检测环境 (可选)

由于越位检测模块依赖较旧的numpy版本，建议单独创建环境：

```bash
conda create -n offside_detect python=3.8
conda activate offside_detect
cd "Offside detection"
pip install -r requirements.txt
```

## 💻 启动与使用

### 步骤 1: 配置 API Key

在使用前，请确保已在代码中填入您的 Dashscope API Key。
检查以下文件并替换 `YOUR_DASHSCOPE_API_KEY`：
- `api/api/voice_service.py`
- `football_voice/voice_service.py`
- `football_comment/main.py`

### 步骤 2: 启动语音合成服务

在运行主程序前，需要先启动语音服务。

```bash
# 激活主环境
conda activate football_aigc

# 进入语音服务目录
cd football_voice

# 启动服务 (默认端口 5001)
python app.py
```
*保持此终端窗口开启。*

### 步骤 3: 启动 Web 应用

打开新的终端窗口：

```bash
# 激活主环境
conda activate football_aigc

# 进入Web前端目录
cd web_frontend

# 启动Flask服务器
python server.py
```
*服务将在 http://localhost:5000 启动。*

### 步骤 4: 使用系统

1. 打开浏览器访问 `http://localhost:5000`
2. 点击进入系统（如有登录界面，请先注册/登录）
3. 上传足球比赛视频（支持 MP4 格式）
4. 选择解说语言（如：汉语）和风格
5. 点击“生成解说”
6. 等待系统处理完成后，即可在线观看或下载带解说的视频

你也可以双击start_english.bat文件直接一键启动系统（包含语音服务、Web应用和越位检测模块）

## ⚠️ 常见问题与兼容性

1. **依赖冲突**: `Offside detection` 模块可能与主项目有 `numpy` 版本冲突。请务必使用独立的 Conda 环境运行该模块。
2. **FFMPEG**: 请确保系统已安装 FFMPEG 并添加到环境变量，或者确认 `run_AIGC.py` 中 `FFMPEG_PATH` 指向正确的路径。
3. **性能提示**: 视频分析和渲染需要较强的 GPU 算力。建议使用 NVIDIA RTX 3060 或更高性能显卡。

### 如果遇到问题可以在Issues中反馈，也可以通过邮箱联系我们：[18722164190@163.com](mailto:18722164190@163.com)，欢迎各位大佬的斧正指导！如果觉得本项目不错，欢迎给个Star⭐️！