# CosyVoice 语音合成服务使用指南

## 概述

本服务基于阿里云 DashScope 的 CosyVoice 提供专业的足球解说语音合成功能，可以为您的足球视频生成高质量的解说音频。

## 快速开始

### 1. 安装依赖

在使用前，请确保已安装所有必要的依赖：

```bash
cd api/api
pip install -r requirements.txt
```

### 2. 初始化默认音色

首次使用前，需要初始化默认音色（贺炜、詹俊等著名解说员音色）：

```bash
python seed_voices.py
```

这个过程可能需要几分钟时间，因为系统需要创建音色并等待其就绪。

### 3. 启动语音服务

有两种方式启动语音服务：

#### 方式一：使用Python脚本

```bash
python start_voice_service.py
```

#### 方式二：双击批处理文件

直接双击 `start_voice_service.bat` 文件即可启动服务。

服务启动后，将在 `http://localhost:8000` 上运行。

## API 接口说明

服务提供以下API接口：

### 1. 列出所有可用音色

```http
GET /voices
```

**响应示例：**
```json
{
  "voices": [
    {
      "name": "zhanjun",
      "voice_id": "cosyvoice-v2-zhanjun-6ef009e8d50441a5a7c1482c4b72aad8",
      "meta": {
        "prefix": "zhanjun",
        "audio_url": "https://zhanjun-voice.oss-cn-beijing.aliyuncs.com/zhanjun.MP3"
      }
    },
    ...
  ]
}
```

### 2. 创建新音色

```http
POST /voices
Content-Type: application/json

{
  "name": "custom_voice",
  "prefix": "custom",
  "audio_url": "https://example.com/voice.mp3",
  "wait_ready": true
}
```

### 3. 初始化默认音色

```http
POST /voices/seed-defaults
```

### 4. 合成语音

```http
POST /synthesize
Content-Type: application/json

{
  "name": "hewei",
  "text": "今晚的比赛异常激烈，双方节奏非常快！"
}
```

**响应示例：**
```json
{
  "name": "hewei",
  "voice_id": "cosyvoice-v2-hewei-5945747bb52f449bac64038b49b26d12",
  "audio_base64": "SUQzAwAAAAAAJlRQRTEAAAAcAAAA..."
}
```

## 集成到主系统

主系统（run_AIGC.py）已经配置为自动调用此语音服务。只需确保：

1. 语音服务正在运行（`http://localhost:8000`）
2. run_AIGC.py 中的 `VOICE_API_URL` 设置为 `http://localhost:8000`

当主系统执行到语音合成步骤时，会自动发送请求到本服务进行语音合成。

## 语言与风格映射

系统支持以下语言和风格组合：

| 语言 | 风格 | 对应音色 |
|------|------|----------|
| 汉语 | 幽默 | yangmi   |
| 汉语 | 激情 | zhanjun  |
| 汉语 | 专业 | hewei    |
| 汉语 | 默认 | hewei    |
| 英语 | 幽默 | yao      |
| 英语 | 激情 | zhanglu  |
| 英语 | 专业 | hewei    |
| 英语 | 默认 | hewei    |

## 常见问题排查

### 1. 服务启动失败

- 检查端口 8000 是否已被占用
- 确认所有依赖已正确安装
- 查看错误日志以获取详细信息

### 2. 语音合成失败

- 确认 DashScope API Key 是否有效（在 voice_service.py 中设置）
- 检查网络连接是否正常
- 确认请求参数是否正确

### 3. 音色未准备好

- 首次创建音色可能需要一些时间，请耐心等待
- 检查音频URL是否可访问
- 确保音频质量良好且时长足够

## 注意事项

1. 本服务使用阿里云 DashScope API，可能产生相关费用
2. 建议在稳定的网络环境下使用
3. 服务默认使用开发模式运行，生产环境请进行相应配置
4. 如需修改端口或其他配置，请编辑 start_voice_service.py 文件