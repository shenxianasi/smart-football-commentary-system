## CosyVoice 语音合成项目

本项目基于阿里云 DashScope 的 CosyVoice 提供“音色创建/管理/语音合成”的端到端示例，包含：
- 通过参考音频创建音色并等待就绪
- 将音色信息持久化到本地 `voices.json`
- 独立脚本进行语音合成
- FastAPI 服务供前端调用（列出音色、创建音色、批量初始化默认音色、合成音频）

## 目录结构

```
api/
├── app.py                # FastAPI 后端，提供音色与合成接口
├── voice_service.py      # 语音服务封装（创建/查询/等待/合成）
├── voice_store.py        # 本地 JSON 存储（voices.json）
├── seed_voices.py        # 初始化默认音色（贺炜、詹俊）
├── synthesize.py         # 使用已保存音色进行命令行合成
├── voices.json           # 已保存音色列表（运行后生成/更新）
├── requirements.txt      # 依赖清单
├── README.md             # 文档
└── audio/                # 本地样例音频（可选，不依赖本地文件）
```

## 环境准备

### 使用 Conda（推荐）
```bat
conda create -n voice python=3.10 -y
conda activate voice
cd C:\Users\刘浩旸\Desktop\api
pip install -r requirements.txt
```

### API Key 配置
项目已在 `voice_service.py` 中设置默认 Key（`DEFAULT_DASHSCOPE_API_KEY`）。如需更换：
```python
# voice_service.py
DEFAULT_DASHSCOPE_API_KEY = "你的_DashScope_API_KEY"
```
或使用环境变量（可选）：
```bat
setx DASHSCOPE_API_KEY "你的_DashScope_API_KEY"
```

## 快速上手

### 1) 初始化默认音色（贺炜、詹俊）
```bat
python seed_voices.py
```
说明：
- 会使用公网参考音频创建音色并等待状态为 OK
- 成功后写入 `voices.json`，包含：`name`、`voice_id`、`meta`

### 2) 命令行合成
使用已保存的音色名对文本进行合成：
```bat
python synthesize.py hewei "今晚的比赛异常激烈，双方节奏非常快！" -o hewei_demo.mp3
```
将 `hewei` 替换为 `voices.json` 中的 `name`（如 `zhanjun`）。

### 3) 启动后端服务（供前端调用）
```bat
uvicorn app:app --host 0.0.0.0 --port 8000
```

接口说明：
- 列表音色
```http
GET /voices
```

- 创建音色
```http
POST /voices
Content-Type: application/json

{
  "name": "hewei",
  "prefix": "hewei",
  "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/hewei.MP3",
  "wait_ready": true
}
```

- 批量初始化默认音色
```http
POST /voices/seed-defaults
```

- 合成音频（返回 Base64）
```http
POST /synthesize
Content-Type: application/json

{
  "name": "hewei",
  "text": "今晚的比赛异常激烈，双方节奏非常快！"
}
```

前端可直接用返回的 `audio_base64` 播放：
```javascript
const audio = new Audio(`data:audio/mpeg;base64,${res.audio_base64}`);
audio.play();
```

## 代码要点

- 语音服务封装 `voice_service.py`
  - `create_voice(prefix, audio_url)` 创建音色
  - `wait_for_voice_ok(voice_id)` 等待状态为 OK
  - `synthesize(voice_id, text)` 文本转语音，返回二进制音频

- 本地存储 `voice_store.py`
  - JSON 文件 `voices.json` 持久化：`[{ name, voice_id, meta }]`
  - `add_voice(name, voice_id, meta)`、`get_voice(name)`、`list_voices()`

- 脚本
  - `seed_voices.py`：批量创建默认音色（贺炜、詹俊）
  - `synthesize.py`：使用 `name` + 文本进行合成并保存 mp3

## 常见问题（FAQ）

- 创建音色失败：No api key provided
  - 原因：未设置 DashScope API Key
  - 处理：在 `voice_service.py` 写入 `DEFAULT_DASHSCOPE_API_KEY` 或设置环境变量

- 等待超时/状态非 OK
  - 检查：`audio_url` 是否公网可访问；音频是否清晰、时长足够；稍后重试

- 前端无法播放
  - 确认：已将 `audio_base64` 拼接为 `data:audio/mpeg;base64,` 前缀

## 备注

- 本项目默认使用公网参考音频地址，不依赖 `audio/` 本地文件。
- 建议将 Key 存放于环境变量，当前写入代码仅为演示方便。

## 许可证

本项目仅供学习与参考使用。
