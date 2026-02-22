import os
import time
from pathlib import Path
from typing import Optional
import dashscope
from dashscope.audio.tts_v2 import VoiceEnrollmentService, SpeechSynthesizer


# 请在这里填写您的Dashscope API Key
DEFAULT_DASHSCOPE_API_KEY = "YOUR_DASHSCOPE_API_KEY"


class VoiceService:
    def __init__(self, api_key: Optional[str] = None, target_model: str = "cosyvoice-v2"):
        # 优先使用传入的 api_key；否则使用硬编码默认值
        dashscope.api_key = api_key or DEFAULT_DASHSCOPE_API_KEY
        self.target_model = target_model
        self.service = VoiceEnrollmentService()

    def upload_audio_to_oss(self, local_audio_path: str) -> Optional[str]:
        # 使用用户提供的公网URL作为参考音频
        print("已使用提供的公网URL作为参考音频来源")
        return "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/hewei.MP3"

    def create_voice(self, prefix: str, audio_url: str) -> Optional[str]:
        try:
            voice_id = self.service.create_voice(target_model=self.target_model, prefix=prefix, url=audio_url)
            return voice_id
        except Exception as exc:
            print(f"创建音色失败: {exc}")
            return None

    def query_voice(self, voice_id: str):
        try:
            return self.service.query_voice(voice_id=voice_id)
        except Exception as exc:
            print(f"查询音色失败: {exc}")
            return None

    def wait_for_voice_ok(self, voice_id: str, max_wait_time: int = 300, interval: int = 20) -> bool:
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            info = self.query_voice(voice_id)
            if info and info.get("status") == "OK":
                return True
            if info and info.get("status") == "UNDEPLOYED":
                return False
            time.sleep(interval)
        return False

    def synthesize(self, voice_id: str, text: str) -> Optional[bytes]:
        try:
            synthesizer = SpeechSynthesizer(model=self.target_model, voice=voice_id)
            return synthesizer.call(text)
        except Exception as exc:
            print(f"合成失败: {exc}")
            return None


