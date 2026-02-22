import json
from pathlib import Path
from typing import Dict, Optional, List


class VoiceStore:
    def __init__(self, store_path: str = "voices.json"):
        self.path = Path(store_path)
        if not self.path.exists():
            self.path.write_text(json.dumps({"voices": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> Dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data: Dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_voice(self, name: str, voice_id: str, meta: Optional[Dict] = None) -> None:
        data = self._load()
        voices: List[Dict] = data.get("voices", [])
        # 覆盖同名音色
        voices = [v for v in voices if v.get("name") != name]
        voices.append({"name": name, "voice_id": voice_id, "meta": meta or {}})
        data["voices"] = voices
        self._save(data)

    def get_voice(self, name: str) -> Optional[Dict]:
        data = self._load()
        for item in data.get("voices", []):
            if item.get("name") == name:
                return item
        return None

    def list_voices(self) -> List[Dict]:
        data = self._load()
        return data.get("voices", [])


