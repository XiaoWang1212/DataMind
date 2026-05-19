#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5001}"
SCRIPTDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAMPLES_DIR="${SAMPLES_DIR:-$SCRIPTDIR/../samples}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPTDIR/../artifacts/mineru}"

mkdir -p "$OUTPUT_DIR"

SUPPORTED_EXTENSIONS="pdf txt md"

find_samples() {
  find "$SAMPLES_DIR" -type f \( -iname '*.pdf' -o -iname '*.txt' -o -iname '*.md' \) | sort
}

SAMPLE_FILES=$(find_samples)

if [[ -z "$SAMPLE_FILES" ]]; then
  echo "找不到 sample 檔案。請確認資料已放在 $SAMPLES_DIR，支援 pdf / txt / md。"
  exit 1
fi

echo "Base URL: $BASE_URL"
echo "Samples dir: $SAMPLES_DIR"
echo "Output dir: $OUTPUT_DIR"
echo ""

for file_path in $SAMPLE_FILES; do
  filename="$(basename "$file_path")"
  output_file="$OUTPUT_DIR/${filename%.*}.json"

  echo "=== 上傳檔案: $file_path ==="
  response="$(curl -sS -X POST "$BASE_URL/api/mineru/ai-analyze-simple" \
    -F "file=@${file_path}")"

  echo "$response" > "$output_file"
  echo "已儲存回應到: $output_file"

  if command -v jq >/dev/null 2>&1; then
    echo "結果摘要:"
    echo "$response" | jq -r '.result // .error // "(no result)"'
  else
    echo "(提示：若要漂亮顯示回應，請安裝 jq)"
  fi

  echo ""
done

echo "MinerU sample 上傳完成。"
