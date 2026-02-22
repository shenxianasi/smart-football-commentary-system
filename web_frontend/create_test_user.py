from server import app
from server import app
from database import db, User

# 创建测试用户
def create_test_user():
    with app.app_context():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username='testuser').first()
        if existing_user:
            print('测试用户已存在!')
            return
        
        # 创建新用户
        new_user = User(
            username='testuser',
            email='test@example.com'
        )
        new_user.set_password('password123')  # 设置密码
        
        # 添加到数据库
        db.session.add(new_user)
        db.session.commit()
        
        print('测试用户创建成功!\n用户名: testuser\n密码: password123')

# 创建或更新特定用户（解决当前遇到的错误）
def create_or_update_user_sunhaoran():
    with app.app_context():
        # 检查用户是否已存在
        existing_user = User.query.filter_by(username='孙浩然').first()
        if existing_user:
            # 如果用户已存在，检查是否需要更新电子邮件字段
            if existing_user.email is None:
                existing_user.email = 'sunhaoran@example.com'
                db.session.commit()
                print('用户 孙浩然 的电子邮件字段已更新!')
            else:
                print('用户 孙浩然 已存在且电子邮件字段已设置!')
            return
        
        # 创建新用户
        new_user = User(
            username='孙浩然',
            email='sunhaoran@example.com'  # 提供有效的电子邮件地址
        )
        new_user.set_password('password123')  # 设置密码
        
        # 添加到数据库
        db.session.add(new_user)
        db.session.commit()
        
        print('用户 孙浩然 创建成功!\n用户名: 孙浩然\n密码: password123')

if __name__ == '__main__':
    # 创建测试用户
    create_test_user()
    # 创建特定用户
    create_or_update_user_sunhaoran()

if __name__ == '__main__':
    create_test_user()
    # 同时创建或更新孙浩然用户以解决当前错误
    create_or_update_user_sunhaoran()