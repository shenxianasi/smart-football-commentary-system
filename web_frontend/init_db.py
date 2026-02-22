from server import app
from database import db

with app.app_context():
    db.create_all()
    print('数据库初始化成功!')