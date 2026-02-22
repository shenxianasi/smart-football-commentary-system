import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from web_frontend.database import db
from web_frontend.server import app

print("开始初始化数据库...")
with app.app_context():
    try:
        # 创建所有数据库表
        db.create_all()
        print("数据库表已成功创建!")
        print("数据库初始化完成!")
    except Exception as e:
        print(f"数据库初始化出错: {e}")