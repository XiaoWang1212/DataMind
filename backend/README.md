# DataMind Backend (Flask + Local Whisper STT)

## 功能

- `GET /api/health`：健康檢查
- `POST /api/stt/transcribe`：Whisper 語音轉文字
- `POST /api/ml/pycaret/train`：執行 PyCaret 分類訓練

## 安裝與啟動

```bash
cd backend
uv python install 3.11
uv sync --python 3.11
cp .env.example .env
```

> PyCaret 目前只支援 Python 3.9/3.10/3.11，建議固定使用 3.11。

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

## Docker / Compose

在專案根目錄執行：

```bash
docker compose up --build
```

背景執行：

```bash
docker compose up --build -d
```

停止：

```bash
docker compose down
```

> Docker 版本已內建 `ffmpeg`，使用者端不需要另外安裝。

測試：

```bash
curl http://127.0.0.1:5001/api/health
curl -X POST http://127.0.0.1:5001/api/stt/transcribe \
  -F "audio=@/path/to/audio.m4a" \
  -F "language=zh"
```

或使用測試腳本：

```bash
cd backend
chmod +x scripts/test_stt.sh
./scripts/test_stt.sh tts_sample/你的音檔.m4a
```

## STT API 用法

`POST /api/stt/transcribe`（`multipart/form-data`）

欄位：

- `audio`：音檔（必要）
- `language`：語言代碼（可選，例如 `zh`）
- `prompt`：提示文字（可選）
- `temperature`：採樣溫度（可選，數字）

範例：

```bash
curl -X POST http://127.0.0.1:5001/api/stt/transcribe \
  -F "audio=@/path/to/audio.m4a" \
  -F "language=zh"
```

支援副檔名：`wav`, `mp3`, `m4a`, `webm`, `ogg`, `mp4`, `mpeg`, `mpga`

## PyCaret API 用法

`POST /api/ml/pycaret/train`（`application/json`）

欄位：

- `data_path`：CSV 檔案路徑（必要）
- `target_col`：目標欄位（可選，預設 `是否跌倒`）
- `output_dir`：輸出目錄（可選，預設 `artifacts/pycaret`）

範例：

```bash
curl -X POST http://127.0.0.1:5001/api/ml/pycaret/train \
  -H "Content-Type: application/json" \
  -d '{
    "data_path": "/Users/你的帳號/path/to/跌倒資料_0611.csv",
    "target_col": "是否跌倒",
    "output_dir": "artifacts/pycaret"
  }'
```

輸出包含：

- `pycaret_compare_results.csv`
- `pycaret_teacher_format.csv`
- `fall_model.pkl`

或使用測試腳本：

```bash
cd backend
chmod +x scripts/test_pycaret.sh
./scripts/test_pycaret.sh /path/to/跌倒資料_0611.csv 是否跌倒 artifacts/pycaret
```

## 說明

- 你提到的 `pip install -U openai-whisper` 路線是正確的本機推論方案。
- 第一次推論會下載模型，會花一點時間。
- `requirements.txt` 目前保留相容用途，正式以 `uv` 為主。
