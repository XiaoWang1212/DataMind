#!/bin/bash
# RAG API 測試腳本

BASE_URL="${BASE_URL:-http://localhost:5001}"
API_URL="$BASE_URL/api/rag"

echo "=== RAG API 測試 ==="
echo "Base URL: $BASE_URL"
echo ""

# 1. 檢查狀態
echo "1. 檢查服務狀態..."
curl -s "$API_URL/status" | jq .
echo ""

# 2. 上傳論文 (JSON)
echo "2. 上傳論文 (JSON)..."
curl -s -X POST "$API_URL/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Machine Learning in Healthcare",
    "content": "Machine learning has revolutionized healthcare diagnostics. Deep learning models can now detect diseases from medical images with high accuracy. Recent studies show that convolutional neural networks outperform traditional methods in radiology. The integration of AI in clinical workflows has improved patient outcomes significantly. Natural language processing enables efficient analysis of electronic health records.",
    "author": "Smith et al.",
    "year": "2024"
  }' | jq .
echo ""

# 3. 上傳第二篇論文
echo "3. 上傳第二篇論文..."
curl -s -X POST "$API_URL/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Transformer Models for NLP",
    "content": "Transformer architecture has transformed natural language processing. Attention mechanisms allow models to capture long-range dependencies effectively. BERT and GPT models have achieved state-of-the-art results on various benchmarks. Fine-tuning pre-trained models has become the standard approach for many NLP tasks. Large language models demonstrate emergent capabilities that scale with model size.",
    "author": "Johnson et al.",
    "year": "2023"
  }' | jq .
echo ""

# 4. 檢查狀態 (應該有 2 篇論文)
echo "4. 再次檢查狀態..."
curl -s "$API_URL/status" | jq .
echo ""

# 5. 搜尋論文
echo "5. 搜尋 'deep learning diagnostics'..."
curl -s -X POST "$API_URL/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deep learning diagnostics",
    "top_k": 3
  }' | jq .
echo ""

# 6. 生成引用
echo "6. 生成引用 (APA 格式)..."
curl -s -X POST "$API_URL/cite" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "neural networks in medical imaging",
    "top_k": 2,
    "style": "apa"
  }' | jq .
echo ""

# 7. 清空索引 (可選)
# echo "7. 清空索引..."
# curl -s -X POST "$API_URL/clear" | jq .

echo "=== 測試完成 ==="
