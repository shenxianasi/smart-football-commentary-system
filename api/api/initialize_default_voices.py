import requests

# 语音服务API地址
VOICE_API_URL = "http://localhost:8000"

print("==== 初始化默认音色 ====")
print(f"连接到服务: {VOICE_API_URL}")

try:
    # 调用初始化默认音色API
    response = requests.post(f"{VOICE_API_URL}/voices/seed-defaults")
    
    if response.status_code == 200:
        result = response.json()
        print(f"初始化成功！已添加 {result['added_voices']} 个默认音色")
        print("可用音色列表：")
        for voice in result['voices']:
            print(f"- {voice['name']} (ID: {voice['voice_id']})")
    else:
        print(f"初始化失败: {response.status_code}, {response.text}")
except Exception as e:
    print(f"请求异常: {str(e)}")
    print("请确保语音服务已经启动！")