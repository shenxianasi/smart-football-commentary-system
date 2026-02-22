@echo off
cls
echo Football Commentary System - One-click Startup
echo ========================
cd /d %~dp0

rem Create necessary directories
echo Creating directories...
mkdir input_videos 2>nul
mkdir output_videos 2>nul
mkdir web_frontend\uploads 2>nul
mkdir web_frontend\outputs 2>nul

rem Start voice synthesis service
echo Starting Voice Service...
start "Voice Synthesis Service" cmd /k "cd api\api && python start_voice_service.py"

rem Wait for voice service initialization
echo Initializing services...
ping -n 8 127.0.0.1 >nul

rem Start web frontend service
echo Starting Web Service...
start "Web Frontend Service" cmd /k "cd web_frontend && python server.py"

rem Wait for web service and open browser
echo Preparing browser...
ping -n 12 127.0.0.1 >nul

rem Open browser automatically
start http://localhost:5000

echo System started! Browser opening automatically.
echo Press any key to continue...
pause >nul