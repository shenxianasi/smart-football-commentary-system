from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from voice_service import VoiceService
from voice_store import VoiceStore
from seed_voices import seed_defaults


app = FastAPI(title="Voice API", version="1.0.0")
voice_service = VoiceService()
# 使用当前目录下的voices.json文件
store = VoiceStore(store_path="voices.json")

# 添加健康检查端点
@app.get("/")
def health_check():
    return {
        "status": "ok", 
        "message": "Voice service is running",
        "available_endpoints": [
            "/voices",
            "/synthesize",
            "/voices/seed-defaults"
        ]
    }


class CreateVoiceRequest(BaseModel):
    name: str
    prefix: str
    audio_url: str
    wait_ready: Optional[bool] = True


class SynthesizeRequest(BaseModel):
    name: str
    text: str


@app.get("/voices")
def list_voices():
    return {"voices": store.list_voices()}


@app.post("/voices")
def create_voice(req: CreateVoiceRequest):
    voice_id = voice_service.create_voice(prefix=req.prefix, audio_url=req.audio_url)
    if not voice_id:
        raise HTTPException(status_code=500, detail="创建音色失败")
    if req.wait_ready:
        ok = voice_service.wait_for_voice_ok(voice_id)
        if not ok:
            raise HTTPException(status_code=500, detail="音色未准备好")
    store.add_voice(name=req.name, voice_id=voice_id, meta={"prefix": req.prefix, "audio_url": req.audio_url})
    return {"name": req.name, "voice_id": voice_id}


@app.post("/synthesize")
def synthesize(req: SynthesizeRequest):
    # 先尝试从存储中查找音色
    item = store.get_voice(req.name)
    if item:
        # 使用存储中的音色ID
        voice_id = item["voice_id"]
    else:
        # 如果存储中不存在，直接将name作为voice_id尝试使用（可能是DashScope内置音色）
        voice_id = req.name
    
    # 尝试合成语音
    audio = voice_service.synthesize(voice_id, req.text)
    
    if not audio:
        # 合成失败时提供更详细的错误信息
        if not item:
            raise HTTPException(
                status_code=500, 
                detail=f"合成失败：无法使用音色 '{req.name}'\n"+
                       "可能的原因：\n"+
                       "1. DashScope API Key无效\n"+
                       "2. 音色ID不正确\n"+
                       "3. 网络连接问题\n"+
                       "请尝试使用内置音色，例如：cosyvoice-tim-zh, cosyvoice-joe-zh, cosyvoice-emma-zh, cosyvoice-ella-zh"
            )
        raise HTTPException(status_code=500, detail="合成失败")
    
    # 返回Base64以便前端播放，也可改为StreamingResponse
    import base64
    return {"name": req.name, "voice_id": voice_id, "audio_base64": base64.b64encode(audio).decode("utf-8")}


@app.post("/voices/seed-defaults")
def seed_default_voices(wait_ready: bool = True):
    try:
        seed_defaults(wait_ready=wait_ready)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


