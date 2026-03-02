# 使用步驟

## 先啟後端（擇一）

- **本機**：`cd backend && uv run python app.py`
- **Docker**：`cd /Users/xiaowang/Documents/Github/DataMind && docker compose up --build`

## 準備音檔

放到 `tts_sample`（例如 `sample.m4a`）

## 執行腳本

- **自動抓第一個音檔**：`cd backend && ./scripts/test_stt.sh`
- **指定音檔**：`cd backend && ./scripts/test_stt.sh tts_sample/sample.m4a`

## 可選參數

- **指定語言**：`cd backend && STT_LANG=zh ./scripts/test_stt.sh tts_sample/sample.m4a`
- **指定 API 位址**：`cd backend && BASE_URL=http://127.0.0.1:5001 ./scripts/test_stt.sh tts_sample/sample.m4a`
