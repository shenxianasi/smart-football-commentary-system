@echo off

REM 启动CosyVoice语音合成服务
REM 此脚本将在本地8000端口启动FastAPI服务

echo =================================
echo       启动CosyVoice语音服务

echo 请确保已经安装了所有依赖：
echo pip install -r requirements.txt

echo 服务将在 http://localhost:8000 上运行
echo 按 Ctrl+C 可以停止服务

echo 可用API接口：
echo - GET    /voices                 - 列出所有音色

echo - POST   /voices                 - 创建新音色

echo - POST   /synthesize             - 合成语音

echo - POST   /voices/seed-defaults   - 初始化默认音色

echo =================================

python start_voice_service.py

pause