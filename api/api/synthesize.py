import argparse
from voice_store import VoiceStore
from voice_service import VoiceService


def main():
    parser = argparse.ArgumentParser(description="Synthesize speech using voice")
    parser.add_argument("name", help="Voice name (can be stored voice or built-in DashScope voice)")
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("-o", "--output", default="output_synthesized.mp3", help="Output path")
    parser.add_argument("--builtin", action="store_true", help="Use built-in DashScope voice directly")
    args = parser.parse_args()

    service = VoiceService()
    voice_id = args.name
    
    if not args.builtin:
        # Try to get voice from store first
        store = VoiceStore()
        item = store.get_voice(args.name)
        if item:
            voice_id = item["voice_id"]
        else:
            print(f"提示: 音色 '{args.name}' 未在本地存储中找到，将尝试作为内置音色使用")
    
    print(f"使用音色: {voice_id}")
    audio = service.synthesize(voice_id, args.text)
    
    if not audio:
        print("合成失败")
        print("请尝试以下解决方法：")
        print("1. 确认DashScope API Key有效")
        print("2. 检查网络连接")
        print("3. 尝试使用其他内置音色，例如：cosyvoice-tim-zh, cosyvoice-joe-zh, cosyvoice-emma-zh, cosyvoice-ella-zh")
        return

    with open(args.output, "wb") as f:
        f.write(audio)
    print(f"保存到 {args.output}")


if __name__ == "__main__":
    main()


