import uvicorn
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 正确导入app模块
from app import app

if __name__ == "__main__":
    print("启动足球解说语音合成服务...")
    print("服务地址: http://localhost:5001")
    print("API文档: http://localhost:5001/docs")
    # 启动FastAPI服务
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5001,
        reload=False,
        log_level="info"
    )