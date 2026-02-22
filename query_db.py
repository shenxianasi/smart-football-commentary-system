import sqlite3
import os

# 数据库路径
db_path = os.path.join('web_frontend', 'instance', 'football_translation.db')

print(f"数据库路径: {db_path}")
print(f"文件是否存在: {os.path.exists(db_path)}")

# 连接到数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 获取所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("\n数据库中的表:")
for table in tables:
    print(table[0])

# 查看video表的结构
cursor.execute("PRAGMA table_info(video);")
columns = cursor.fetchall()
print("\nvideo表结构:")
for col in columns:
    print(col)

# 查询video表中的所有记录
print("\nvideo表中的所有记录:")
cursor.execute("SELECT * FROM video ORDER BY id DESC LIMIT 10;")
records = cursor.fetchall()

if records:
    for record in records:
        print("\n--- 记录 ---")
        for i, col in enumerate(columns):
            print(f"{col[1]}: {record[i]}")
else:
    print("video表中没有记录")

# 关闭连接
conn.close()