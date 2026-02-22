import requests
import base64
import os
import requests

# 语音服务API地址
VOICE_API_URL = "http://localhost:8000"


# 获取音色列表并展示

def test_list_voices():
    """测试列出所有可用音色"""
    print("\n=== 测试列出所有音色 ===")
    try:
        response = requests.get(f"{VOICE_API_URL}/voices")
        if response.status_code == 200:
            voices = response.json().get('voices', [])
            print(f"本地存储的音色数量: {len(voices)}")
            for voice in voices:
                print(f"- 音色名称: {voice['name']}, 音色ID: {voice['voice_id']}")
            return voices
        else:
            print(f"获取音色列表失败: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        print(f"请求异常: {str(e)}")
        print("请确保语音服务已经启动！")
        return None


# 测试语音合成功能
def test_synthesize_voice(voice_name, text):
    """测试语音合成功能"""
    print(f"\n=== 测试语音合成 (音色: {voice_name}) ===")
    print(f"合成文本: {text}")
    
    try:
        # 调用合成API
        response = requests.post(
            f"{VOICE_API_URL}/synthesize",
            json={
                "name": voice_name,
                "text": text
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if "audio_base64" in result:
                # 解码Base64音频数据
                audio_data = base64.b64decode(result["audio_base64"])
                
                # 保存音频文件
                output_dir = "audio_test_output"
                os.makedirs(output_dir, exist_ok=True)
                audio_output_path = os.path.join(output_dir, f"test_{voice_name}.wav")
                
                with open(audio_output_path, "wb") as f:
                    f.write(audio_data)
                
                print(f"语音合成成功！音频已保存至: {audio_output_path}")
                return True
            else:
                print(f"语音合成失败：响应中没有audio_base64字段")
                return False
        else:
            print(f"语音合成API调用失败: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"请求异常: {str(e)}")
        print("请确保语音服务已经启动！")
        return False


# 主测试函数
def main():
    print("==== CosyVoice语音服务测试工具 ====")
    print(f"测试服务地址: {VOICE_API_URL}")
    
    # 测试文本
    test_text = "这是一段测试文本，用于验证CosyVoice语音合成服务是否正常工作。"
    
    # 初始化测试结果
    test_success = False
    
    # 1. 先测试本地存储的音色
    print("\n=== 测试本地存储的音色 ====")
    voices = test_list_voices()
    
    if voices and len(voices) > 0:
        # 测试所有唯一的音色名称
        unique_voice_names = list({voice['name'] for voice in voices})
        print(f"\n开始测试所有唯一音色: {', '.join(unique_voice_names)}")
        
        # 测试每个音色
        all_success = True
        for voice_name in unique_voice_names:
            success = test_synthesize_voice(voice_name, test_text)
            if success:
                print(f"音色 {voice_name} 测试成功！")
            else:
                print(f"音色 {voice_name} 测试失败！")
                all_success = False
                
        test_success = all_success
        if all_success:
            print("\n所有音色测试成功！")
        else:
            print("\n部分音色测试失败，请检查配置！")
    
    # 不测试预置音色，严格按照要求只使用本地存储的音色
    print("\n==== 测试完成 ====")
    
    if not test_success:
        print("\n测试失败，请检查以下事项：")
        print("1. 语音服务是否已启动 (python start_voice_service.py)")
        print("2. DashScope API Key是否有效 (在voice_service.py中设置)")
        print("3. 网络连接是否正常")
        print("4. 本地音色配置是否正确 (voices.json)")
        print("\n根据您的要求，测试仅使用voices.json中配置的音色，不尝试其他预置音色。")
        print("\n当前voices.json中存储的音色：")
        # 读取并显示voices.json中的音色配置
        try:
            import json
            with open("voices.json", "r", encoding="utf-8") as f:
                voices_data = json.load(f)
                for voice in voices_data.get("voices", []):
                    print(f"   - {voice['name']} ({voice['voice_id']})")
        except Exception as e:
            print(f"   读取voices.json失败: {str(e)}")
    

# 主程序入口
if __name__ == "__main__":
    main()