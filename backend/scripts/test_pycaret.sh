#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5001}"
DATA_PATH="${1:-}"
TARGET_COL="${2:-是否跌倒}"
OUTPUT_DIR="${3:-artifacts/pycaret}"

if [[ -z "$DATA_PATH" ]]; then
  echo "請提供 CSV 路徑"
  echo "用法: ./scripts/test_pycaret.sh /path/to/data.csv [target_col] [output_dir]"
  exit 1
fi

if [[ ! -f "$DATA_PATH" ]]; then
  echo "CSV 不存在: $DATA_PATH"
  exit 1
fi

echo "[1/2] 健康檢查: $BASE_URL/api/health"
curl -fsS "$BASE_URL/api/health" >/dev/null
echo "OK"

echo "[2/2] 觸發 PyCaret 訓練"
PAYLOAD=$(cat <<JSON
{
  "data_path": "$DATA_PATH",
  "target_col": "$TARGET_COL",
  "output_dir": "$OUTPUT_DIR"
}
JSON
)

RESPONSE="$(curl -sS -X POST "$BASE_URL/api/ml/pycaret/train" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")"

echo "$RESPONSE"

if command -v jq >/dev/null 2>&1; then
  echo "\n訓練輸出檔案:"
  echo "$RESPONSE" | jq -r '.result.compare_results_path, .result.teacher_format_path, .result.model_path // empty'
fi
