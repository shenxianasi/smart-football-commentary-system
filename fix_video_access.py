import os
import shutil
import datetime
import sqlite3
from pathlib import Path

def ensure_directory_exists(directory):
    """确保目录存在"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")

def copy_latest_videos():
    """复制最新生成的视频到前端outputs目录"""
    # 定义路径
    source_dir = os.path.join(os.getcwd(), 'output', 'final_output')
    destination_dir = os.path.join(os.getcwd(), 'web_frontend', 'outputs')
    
    ensure_directory_exists(source_dir)
    ensure_directory_exists(destination_dir)
    
    # 获取source_dir中的所有视频文件
    video_files = [f for f in os.listdir(source_dir) if f.endswith('.mp4')]
    if not video_files:
        print(f"错误: 在 {source_dir} 中未找到视频文件")
        return []
    
    # 按修改时间排序，获取最新的视频
    video_files.sort(key=lambda x: os.path.getmtime(os.path.join(source_dir, x)), reverse=True)
    
    # 复制最新的3个视频到目标目录
    copied_files = []
    for video_file in video_files[:3]:  # 复制最新的3个视频
        source_path = os.path.join(source_dir, video_file)
        dest_path = os.path.join(destination_dir, video_file)
        
        # 复制文件
        shutil.copy2(source_path, dest_path)
        print(f"已复制视频: {video_file} 到 {destination_dir}")
        copied_files.append(video_file)
    
    return copied_files

def init_database():
    """初始化数据库并创建必要的表"""
    db_path = os.path.join(os.getcwd(), 'football_translation.db')
    
    # 创建数据库目录
    db_dir = os.path.dirname(db_path)
    ensure_directory_exists(db_dir)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建users表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建videos表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            processed_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            has_processed BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 检查是否有默认用户，如果没有则创建
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            # 创建默认测试用户
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ('test_user', 'test@example.com', 'test_password_hash')  # 实际应用中应该使用哈希密码
            )
            print("已创建默认测试用户: test_user")
        
        conn.commit()
        return conn, cursor
    except Exception as e:
        print(f"初始化数据库时出错: {e}")
        return None, None

def update_video_records(cursor, video_files):
    """更新数据库中的视频记录"""
    if not video_files:
        return
    
    # 获取第一个用户ID（假设是默认用户）
    cursor.execute("SELECT id FROM users LIMIT 1")
    user_row = cursor.fetchone()
    if not user_row:
        print("错误: 未找到用户记录")
        return
    
    user_id = user_row[0]
    
    # 为每个视频文件更新数据库记录
    for video_file in video_files:
        video_path = os.path.join('web_frontend', 'outputs', video_file)
        
        # 检查是否已存在该视频记录
        cursor.execute("SELECT id FROM videos WHERE filename = ?", (video_file,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute(
                "UPDATE videos SET processed_path = ?, has_processed = TRUE WHERE id = ?",
                (video_path, existing[0])
            )
            print(f"已更新视频记录: {video_file}")
        else:
            # 创建新记录
            cursor.execute(
                "INSERT INTO videos (user_id, filename, filepath, processed_path, has_processed) VALUES (?, ?, ?, ?, TRUE)",
                (user_id, video_file, video_path, video_path)
            )
            print(f"已创建视频记录: {video_file}")

def test_video_access(video_files):
    """测试视频文件的访问路径"""
    print("\n视频访问路径测试:")
    print("----------------------------------------")
    print("在前端可以通过以下URL访问视频:")
    
    for video_file in video_files:
        # 假设服务器运行在localhost:5000
        video_url = f"http://localhost:5000/output/{video_file}"
        print(f"  - {video_url}")
    
    print("\n在前端JavaScript中，视频应该通过以下方式加载:")
    print("----------------------------------------")
    print("videoPlayer.src = '" + f"/output/{video_files[0]}" + "?t=' + Date.now();")
    print("videoPlayer.load();")

def main():
    print("开始修复视频访问问题...\n")
    
    # 步骤1: 复制最新视频到前端目录
    print("步骤1: 复制最新视频到前端可访问目录")
    print("----------------------------------------")
    copied_files = copy_latest_videos()
    
    if not copied_files:
        print("无法继续，没有找到可复制的视频文件")
        return
    
    # 步骤2: 初始化数据库并更新视频记录
    print("\n步骤2: 初始化数据库并更新视频记录")
    print("----------------------------------------")
    conn, cursor = init_database()
    if conn and cursor:
        update_video_records(cursor, copied_files)
        conn.commit()
        conn.close()
        print("数据库更新完成")
    
    # 步骤3: 显示测试信息
    test_video_access(copied_files)
    
    print("\n修复完成! 请刷新前端页面查看更新后的视频")

if __name__ == "__main__":
    main()