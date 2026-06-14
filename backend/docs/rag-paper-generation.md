# RAG 論文生成系統設計文件

## 目標

使用者提供**資料探勘實驗結果**，系統從已上傳的**參考論文庫**中檢索相關知識，
透過 Gemini 2.5 Flash 自動撰寫一篇符合學術格式的中文論文。

---

## 系統架構

```
┌──────────────────────── Phase 1：建立參考論文庫 ─────────────────────────┐
│                                                                          │
│  POST /api/rag/upload  (一次上傳一篇，可重複呼叫)                        │
│        │                                                                 │
│        ▼                                                                 │
│  extract_text_from_file()     ← PyMuPDF / pdfplumber 解析 PDF           │
│        │                                                                 │
│        ▼                                                                 │
│  TextChunker.chunk()          ← 500字一塊，50字重疊，中文句號為切點      │
│        │  每塊帶：chunk_id / paper_id / title / content / chunk_index   │
│        ▼                                                                 │
│  Embedder.encode()            ← BAAI/bge-small-zh-v1.5 (384維)          │
│        │                                                                 │
│        ▼                                                                 │
│  VectorStore.add()            ← 持久化到 artifacts/rag_index/            │
│                                    embeddings.npy   (所有向量)           │
│                                    chunks.json      (文字塊 + metadata)  │
│                                    papers.json      (論文清單)           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────── Phase 2：論文生成 ───────────────────────────────┐
│                                                                          │
│  POST /api/rag/generate-paper                                            │
│  {                                                                       │
│    "topic":    "研究主題（必填）",                                        │
│    "mining_results": { ... },   ← 資料探勘結果（見下方格式）              │
│    "structure": [...],          ← 論文章節（選填，有預設值）              │
│    "language": "zh-TW"                                                   │
│  }                                                                       │
│        │                                                                 │
│        ▼                                                                 │
│  [章節迴圈] 針對每個章節生成搜尋 query                                    │
│        │  摘要  → "研究目的 主要方法 核心發現"                            │
│        │  前言  → "研究背景 問題定義 現有方法限制"                        │
│        │  方法  → "資料集 預處理 特徵工程 模型選擇 驗證策略"              │
│        │  結果  → "模型效能 指標比較 統計顯著性"                          │
│        │  討論  → "結果解讀 與文獻比較 研究限制"                          │
│        │  結論  → "主要貢獻 實務建議 未來研究方向"                        │
│        ▼                                                                 │
│  VectorStore.search(query, top_k=5)                                      │
│        │  cosine similarity → 最相關 5 個 chunk                          │
│        ▼                                                                 │
│  建立章節 Prompt：                                                        │
│    [系統角色] 你是醫學 / 資料科學學術論文撰寫助手                          │
│    [參考文獻] [1] (Title A) chunk內容...                                  │
│               [2] (Title B) chunk內容...                                  │
│    [資料探勘結果] (格式化後的實驗數據)                                    │
│    [任務] 撰寫「前言」章節，800-1200字，引用標記用 [1][2]                 │
│        ▼                                                                 │
│  Gemini 2.5 Flash 生成每個章節                                           │
│        │                                                                 │
│        ▼                                                                 │
│  合併章節 + 自動生成參考文獻列表（APA 格式）                              │
│        ▼                                                                 │
│  回傳：                                                                  │
│    paper_markdown: 完整論文（Markdown 格式）                             │
│    references:     引用論文清單                                           │
│    usage:          token 用量統計                                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 資料探勘結果輸入格式（`mining_results`）

使用者提供的資料探勘結果以 JSON 格式傳入，欄位皆為**選填**，系統會根據有填的欄位生成對應內容。

```json
{
  "dataset": {
    "name": "MIMIC-III 重症照護資料庫",
    "size": 12000,
    "features": 48,
    "target": "院內死亡率",
    "class_distribution": "正類 18%，負類 82%"
  },

  "preprocessing": {
    "missing_handling": "KNN 插補法（k=5）",
    "scaling": "標準化（Z-score）",
    "encoding": "One-Hot 編碼類別變數",
    "outlier": "IQR 方法移除異常值",
    "resampling": "SMOTE 過採樣（最終樣本數 1:1）"
  },

  "feature_engineering": {
    "method": "Random Forest 特徵重要性選擇",
    "selected_features": 20,
    "top_features": [
      {"name": "SOFA_score", "importance": 0.142},
      {"name": "age",         "importance": 0.098},
      {"name": "lactate",     "importance": 0.087}
    ]
  },

  "models": [
    {
      "name": "Logistic Regression",
      "auc":      0.812,
      "auprc":    0.634,
      "f1":       0.701,
      "accuracy": 0.788,
      "recall":   0.723,
      "specificity": 0.791,
      "mcc":      0.489,
      "ci_95":    "AUC [0.798, 0.826]"
    },
    {
      "name": "Random Forest",
      "auc":      0.891,
      "auprc":    0.754,
      "f1":       0.803,
      "accuracy": 0.856,
      "recall":   0.812,
      "specificity": 0.871,
      "mcc":      0.623,
      "ci_95":    "AUC [0.881, 0.901]"
    },
    {
      "name": "XGBoost",
      "auc":      0.912,
      "auprc":    0.781,
      "f1":       0.834,
      "accuracy": 0.878,
      "recall":   0.841,
      "specificity": 0.889,
      "mcc":      0.668,
      "ci_95":    "AUC [0.903, 0.921]"
    }
  ],

  "best_model": "XGBoost",
  "best_model_reason": "AUC 最高，且在高召回率下維持最佳 MCC",

  "validation": {
    "method": "10-fold 分層交叉驗證",
    "train_ratio": 0.8,
    "test_ratio": 0.2
  },

  "statistical_tests": {
    "delong_test": "XGBoost vs Logistic Regression: p < 0.001",
    "calibration": "Hosmer-Lemeshow 檢定 p = 0.423（良好校準）"
  },

  "additional_notes": "任何補充說明，如資料來源限制、特殊處理等"
}
```

---

## 論文章節結構（預設值）

| 章節 | 預設字數 | RAG 搜尋重點 |
|------|---------|------------|
| 摘要 | 300字 | 研究目的、方法摘要、主要發現 |
| 前言 | 1000字 | 研究背景、臨床問題、現有方法的不足 |
| 研究方法 | 1200字 | 資料集、預處理步驟、模型選擇依據、驗證策略 |
| 實驗結果 | 800字 | 各模型指標、特徵重要性、統計檢定 |
| 討論 | 1000字 | 與文獻比較、臨床意義、研究限制 |
| 結論 | 300字 | 主要貢獻、實務建議、未來研究 |

---

## 要新增的檔案

```
backend/
├── services/
│   └── rag/
│       ├── __init__.py
│       ├── chunker.py          ← 文字切塊邏輯
│       ├── embedder.py         ← BAAI/bge-small-zh-v1.5 封裝
│       ├── vector_store.py     ← numpy cosine similarity + 持久化
│       └── paper_rag.py        ← 主服務（routes/rag.py import 的那個）
│
├── routes/
│   └── rag.py                 ← 新增 POST /api/rag/generate-paper 端點
│
└── requirements.txt           ← 新增 sentence-transformers, pymupdf
```

---

## 要新增的 API 端點

### `POST /api/rag/generate-paper`

**Request Body:**
```json
{
  "topic": "以機器學習預測 ICU 病患院內死亡率",
  "mining_results": { "...": "（上方格式）" },
  "structure": ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"],
  "language": "zh-TW"
}
```

**Response:**
```json
{
  "success": true,
  "result": {
    "paper_markdown": "# 以機器學習預測 ICU 病患院內死亡率\n\n## 摘要\n...",
    "references": [
      { "paper_id": "abc123", "title": "...", "author": "...", "year": "2023" }
    ],
    "sections_generated": ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"],
    "usage": {
      "total_tokens": 15420,
      "sections_detail": [...]
    }
  }
}
```

---

## 現有 API 端點（已有，不動）

| 端點 | 說明 |
|------|------|
| `POST /api/rag/upload` | 上傳參考論文 PDF |
| `POST /api/rag/search` | 語意搜尋論文庫 |
| `POST /api/rag/cite` | 生成 APA/MLA 引用 |
| `GET  /api/rag/status` | 查看論文庫狀態 |
| `POST /api/rag/clear` | 清空論文庫 |
| `DELETE /api/rag/paper/<id>` | 刪除指定論文 |

---

## 技術選型

| 元件 | 選擇 | 理由 |
|------|------|------|
| Embedding 模型 | `BAAI/bge-small-zh-v1.5` | 中文優化、輕量（約100MB）、支援學術文本 |
| 向量搜尋 | numpy cosine similarity | 無需 FAISS、Windows 相容、幾十篇論文夠用 |
| 持久化 | `.npy` + `.json` | 簡單、不需額外資料庫 |
| LLM | Gemini 2.5 Flash | 已整合、支援長 context、中文品質佳 |
| 引用格式 | APA | 醫學/資料科學常用 |

---

## 使用流程

```bash
# Step 1：上傳參考論文（可多次）
curl -X POST http://localhost:5001/api/rag/upload \
  -F "file=@paper1.pdf" -F "title=XXX Study" -F "year=2023"

curl -X POST http://localhost:5001/api/rag/upload \
  -F "file=@paper2.pdf" -F "title=YYY Research" -F "year=2024"

# Step 2：確認論文庫狀態
curl http://localhost:5001/api/rag/status

# Step 3：提供資料探勘結果，生成論文
curl -X POST http://localhost:5001/api/rag/generate-paper \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "以機器學習預測 ICU 病患院內死亡率",
    "mining_results": {
      "dataset": { "name": "MIMIC-III", "size": 12000 },
      "best_model": "XGBoost",
      "models": [{ "name": "XGBoost", "auc": 0.912, "f1": 0.834 }]
    }
  }'
```

---

## 注意事項

- **`.env` 不得 commit 到 git**，已加入 `.gitignore`
- Embedding 模型第一次使用時會自動下載到 `~/.cache/huggingface`
- 論文庫 index 儲存在 `backend/artifacts/rag_index/`，重啟 Flask 後仍然存在
- 每篇論文大約消耗 Gemini token：前言約 2000 tokens，全篇約 12000–18000 tokens
