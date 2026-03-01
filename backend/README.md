# DataMind Backend (Flask + Local Whisper STT)

## 功能

- `GET /api/health`：健康檢查
- `POST /api/v1/stt/transcribe`：Whisper 語音轉文字

## 安裝與啟動

```bash
cd backend
uv sync
cp .env.example .env
```

本機 Whisper 不需要 API key，但需要系統有 `ffmpeg`：

```bash
brew install ffmpeg
```

可選調整 `.env`：

```dotenv
WHISPER_MODEL=base
```

啟動：

```bash
uv run python app.py
```

## uv 管理

- 依賴來源：`pyproject.toml`
- 鎖版本檔：`uv.lock`
- 新增套件：`uv add <package>`
- 更新鎖檔：`uv lock`

## STT API 用法

`POST /api/v1/stt/transcribe`（`multipart/form-data`）

欄位：

- `audio`：音檔（必要）
- `language`：語言代碼（可選，例如 `zh`）
- `prompt`：提示文字（可選）
- `temperature`：採樣溫度（可選，數字）

範例：

```bash
curl -X POST http://127.0.0.1:5001/api/v1/stt/transcribe \
  -F "audio=@/path/to/audio.m4a" \
  -F "language=zh"
```

支援副檔名：`wav`, `mp3`, `m4a`, `webm`, `ogg`, `mp4`, `mpeg`, `mpga`

## 說明

- 你提到的 `pip install -U openai-whisper` 路線是正確的本機推論方案。
- 第一次推論會下載模型，會花一點時間。
- `requirements.txt` 目前保留相容用途，正式以 `uv` 為主。
