# Football Wisdom Think Tank - AI Football Commentary System

This is an AI-based automatic football video commentary system that integrates computer vision, natural language processing, and speech synthesis technologies. The system automatically analyzes football match videos, identifies player actions and match events, generates professional commentary scripts, synthesizes realistic commentary audio, and finally produces match videos with commentary.

## 📁 File Structure

```
Football Wisdom Think Tank/
├── api/                    # Independent Voice Synthesis API Service (Based on CosyVoice)
│   └── api/                # API Service Source Code
├── football_comment/       # Football Commentary Generation Module
│   └── main.py             # Main Program for Commentary Generation
├── football_main/          # Core Video Analysis Module (Based on YOLO)
│   ├── main.py             # Video Analysis Entry Point
│   ├── trackers/           # Object Tracking Algorithms
│   ├── team_assigner/      # Team Identification
│   ├── player_ball_assigner/ # Ball Possession Determination
│   ├── camera_movement_estimator/ # Camera Movement Estimation
│   ├── speed_and_distance_estimator/ # Speed and Distance Estimation
│   ├── view_transformer/   # View Transformation
│   └── utils/              # Utility Functions
├── football_voice/         # Voice Synthesis Service Module (Integrated with Main Workflow)
│   ├── app.py              # Voice Synthesis API Service (Port 5001)
│   ├── voice_service.py    # Voice Service Logic
│   └── voices.json         # Voice Configuration File
├── Offside detection/      # Independent Offside Detection Module
│   ├── offside_detector.py # Core Offside Detection Logic
│   └── model.py            # Offside Detection Model
├── web_frontend/           # Web Frontend Application
│   ├── server.py           # Flask Backend Server (Port 5000)
│   ├── index.html          # Homepage
│   ├── login.html          # Login Page
│   └── uploads/            # Uploaded File Storage
├── run_AIGC.py             # Core Workflow Orchestration Script (Connects Video Analysis, Commentary Generation, Voice Synthesis)
├── requirements.txt        # Main Project Dependency List
└── 演示视频.mp4            # Project Functionality Demo Video
```

## 🛠️ Tech Stack

- **Core Language**: Python 3.10+
- **Computer Vision**:
  - YOLO (Ultralytics) - Player and Football Detection
  - OpenCV - Video Processing and Image Analysis
  - ByteTrack - Multi-Object Tracking
- **Web Framework**: Flask (Backend), HTML5/CSS3/JS (Frontend)
- **Voice Synthesis**:
  - CosyVoice (Alibaba DashScope) - High-Quality Voice Synthesis
  - FastAPI - Voice Service Interface
- **Multimedia Processing**: FFMPEG - Audio/Video Merging and Transcoding
- **Data Analysis**: Pandas, NumPy - Match Data Processing

## 📺 Demo Video

The project demo video is located in the project root directory:
`Football Wisdom Think Tank\演示视频.mp4`

## 🚀 Environment Deployment

It is recommended to use Conda to manage virtual environments. Since the project contains multiple modules, it is suggested to create two environments to avoid dependency conflicts.

### 1. Main Environment (AI Commentary System)

Used for running the Web application, video analysis, and commentary generation.

```bash
# Create environment
conda create -n football_aigc python=3.10
conda activate football_aigc

# Install PyTorch (Choose according to your CUDA version, here is an example for CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install project dependencies
pip install -r requirements.txt

# Note: If you encounter numpy version conflicts, it is recommended to use numpy==1.26.4
pip install numpy==1.26.4
```

### 2. Offside Detection Environment (Optional)

Since the offside detection module relies on an older numpy version, it is recommended to create a separate environment:

```bash
conda create -n offside_detect python=3.8
conda activate offside_detect
cd "Offside detection"
pip install -r requirements.txt
```

## 💻 Startup & Usage

### Step 1: Configure API Key

Before using, please ensure you have filled in your Dashscope API Key in the code.
Check the following files and replace `YOUR_DASHSCOPE_API_KEY`:
- `api/api/voice_service.py`
- `football_voice/voice_service.py`
- `football_comment/main.py`

### Step 2: Start Voice Synthesis Service

Before running the main program, you need to start the voice service.

```bash
# Activate main environment
conda activate football_aigc

# Enter voice service directory
cd football_voice

# Start service (Default port 5001)
python app.py
```
*Keep this terminal window open.*

### Step 3: Start Web Application

Open a new terminal window:

```bash
# Activate main environment
conda activate football_aigc

# Enter Web frontend directory
cd web_frontend

# Start Flask server
python server.py
```
*The service will start at http://localhost:5000.*

### Step 4: Use the System

1. Open a browser and visit `http://localhost:5000`
2. Click to enter the system (if there is a login interface, please register/login first)
3. Upload a football match video (Supports MP4 format)
4. Select commentary language (e.g., Chinese) and style
5. Click "Generate Commentary"
6. Wait for the system to process, then you can watch online or download the video with commentary

You can also double-click the `start_english.bat` file to start the system with one click (includes voice service, Web application, and offside detection module).

## ⚠️ Common Issues & Compatibility

1. **Dependency Conflicts**: The `Offside detection` module may have `numpy` version conflicts with the main project. Please be sure to use a separate Conda environment to run this module.
2. **FFMPEG**: Please ensure FFMPEG is installed on your system and added to environment variables, or confirm `run_AIGC.py` has `FFMPEG_PATH` pointing to the correct path.
3. **Performance Tip**: Video analysis and rendering require strong GPU power. It is recommended to use NVIDIA RTX 3060 or higher performance graphics cards.

### Contact & Support
If you encounter any issues, feel free to submit feedback in Issues, or contact us via email: [18722164190@163.com](mailto:18722164190@163.com). We welcome guidance and corrections from experts! If you find this project useful, please give us a Star ⭐️!
