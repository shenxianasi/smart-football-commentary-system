from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from voice_service import VoiceService
from voice_store import VoiceStore
from seed_voices import seed_defaults


app = FastAPI(title="Voice API", version="1.0.0")
voice_service = VoiceService()
store = VoiceStore()


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
    item = store.get_voice(req.name)
    if not item:
        raise HTTPException(status_code=404, detail="音色不存在")
    audio = voice_service.synthesize(item["voice_id"], req.text)
    if not audio:
        raise HTTPException(status_code=500, detail="合成失败")
    # 返回Base64以便前端播放，也可改为StreamingResponse
    import base64
    return {"name": req.name, "voice_id": item["voice_id"], "audio_base64": base64.b64encode(audio).decode("utf-8")}


@app.post("/voices/seed-defaults")
def seed_default_voices(wait_ready: bool = True):
    try:
        seed_defaults(wait_ready=wait_ready)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/tts")
def tts_test():
    return {"status": "ok", "message": "语音合成服务正常运行"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5001, reload=False)


