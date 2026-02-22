import argparse
from voice_store import VoiceStore
from voice_service import VoiceService


def main():
    parser = argparse.ArgumentParser(description="Synthesize speech using stored voice")
    parser.add_argument("name", help="Stored voice name")
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument("-o", "--output", default="output_synthesized.mp3", help="Output path")
    args = parser.parse_args()

    store = VoiceStore()
    item = store.get_voice(args.name)
    if not item:
        print("音色不存在")
        return

    service = VoiceService()
    audio = service.synthesize(item["voice_id"], args.text)
    if not audio:
        print("合成失败")
        return

    with open(args.output, "wb") as f:
        f.write(audio)
    print(f"保存到 {args.output}")


if __name__ == "__main__":
    main()


