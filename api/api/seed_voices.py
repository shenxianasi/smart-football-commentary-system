from typing import List, Dict
from voice_service import VoiceService
from voice_store import VoiceStore


DEFAULT_VOICES: List[Dict[str, str]] = [
    {
        "name": "zhanjun",
        "prefix": "zhanjun",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/zhanjun.MP3",
    },
    {
        "name": "hewei",
        "prefix": "hewei",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/hewei.MP3",
    },
    {
        "name": "zhanglu",
        "prefix": "zhanglu",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/zhanglu.MP3",
    },
    {
        "name": "yangmi",
        "prefix": "yangmi",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/yangmi.MP3",
    },
    {
        "name": "yao",
        "prefix": "yao",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/yao.MP3",
    }
]


def seed_defaults(wait_ready: bool = True) -> None:
    service = VoiceService()
    store = VoiceStore()
    for item in DEFAULT_VOICES:
        print(f"创建音色 {item['name']}，来源: {item['audio_url']}")
        voice_id = service.create_voice(prefix=item["prefix"], audio_url=item["audio_url"])
        if not voice_id:
            print(f"创建失败: {item['name']}")
            continue
        if wait_ready:
            ok = service.wait_for_voice_ok(voice_id)
            if not ok:
                print(f"音色未就绪，跳过保存: {item['name']}")
                continue
        store.add_voice(name=item["name"], voice_id=voice_id, meta={"prefix": item["prefix"], "audio_url": item["audio_url"]})
        print(f"已保存音色: {item['name']} => {voice_id}")


if __name__ == "__main__":
    seed_defaults(wait_ready=True)


