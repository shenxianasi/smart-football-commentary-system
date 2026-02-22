import uvicorn
import os
import sys
import uvicorn

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.dirname(current_dir))

if __name__ == "__main__":
    print("==== 启动CosyVoice语音合成服务 ====")
    print("服务将在 http://localhost:8000 上运行")
    print("API接口:")
    print("- GET /voices - 列出所有可用音色")
    print("- POST /synthesize - 合成语音")
    print("- POST /voices/seed-defaults - 初始化默认音色")
    print("按 Ctrl+C 停止服务")
    print("==============================")
    
    # 启动FastAPI服务
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)