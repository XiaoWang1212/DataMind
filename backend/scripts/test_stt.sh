#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5001}"
STT_LANG="${STT_LANG:-zh}"
AUDIO_PATH="${1:-}"

if [[ -z "$AUDIO_PATH" ]]; then
  AUDIO_PATH="$(find tts_sample -type f \( -iname '*.wav' -o -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.webm' -o -iname '*.ogg' -o -iname '*.mp4' -o -iname '*.mpeg' -o -iname '*.mpga' \) | head -n 1 || true)"
fi

if [[ -z "$AUDIO_PATH" ]]; then
  echo "找不到可測試音檔。請放一個音檔到 backend/tts_sample，或手動指定檔案："
  echo "  ./scripts/test_stt.sh /path/to/audio.m4a"
  exit 1
fi

if [[ ! -f "$AUDIO_PATH" ]]; then
  echo "音檔不存在: $AUDIO_PATH"
  exit 1
fi

echo "[1/2] 健康檢查: $BASE_URL/api/health"
curl -fsS "$BASE_URL/api/health" > /dev/null
echo "OK"

echo "[2/2] 上傳轉文字: $AUDIO_PATH"
RESPONSE="$(curl -sS -X POST "$BASE_URL/api/stt/transcribe" \
  -F "audio=@${AUDIO_PATH}" \
  -F "language=${STT_LANG}")"

echo "$RESPONSE"

if command -v jq >/dev/null 2>&1; then
  echo "\n辨識文字:"
  echo "$RESPONSE" | jq -r '.result.text // .error // "(無回應)"'
fi
