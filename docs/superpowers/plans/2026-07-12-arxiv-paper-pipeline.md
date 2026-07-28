# arXiv 文獻檢索與論文生成 Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓「資料探勘結果 → AI 分類產生查詢字 → 查 arXiv → 使用者勾選候選論文 → 下載全文入庫 → 生成論文 → 顯示在 /paper」這一整條路徑可以真的跑起來,取代目前 `/paper` 頁面永遠讀假資料 `reportData.ts` 的狀態。

**Architecture:** 後端新增一個不依賴 Gemini 的 `arxiv_source.py`(查 arXiv API + 下載解析 PDF),`PaperRAGService` 疊加三個新方法(分類 → 查候選 → 入庫),兩支新 Flask route 把它們串起來,不改動既有的 `generate_paper()`。前端新增一個候選論文勾選頁 `/paper/sources`,生成完成後透過 Pinia store 把結果轉換成既有 `/paper` 頁面吃的 `PaperReport` 型別,一次性交接給 `/paper` 顯示。

**Tech Stack:** 後端 Flask + Python stdlib(`urllib`、`xml.etree.ElementTree`)+ 既有 `pymupdf`/Gemini;前端 Vue 3 `<script setup lang="ts">` + Pinia + vue-router。

## Global Constraints

- 本專案**沒有測試框架**(前端無 vitest/jest,後端無 pytest)。後端驗證用手動腳本(比照既有 `backend/scripts/test_paper_gen.py` 的模式)+ 對本機 Flask dev server 下 curl;前端驗證用 `npm run type-check` + `npm run lint`,最後一個 task 加上 dev server 目視驗證。不要為此計畫引入任何測試框架。
- **這個 sandbox 的 venv 目前缺少 `flask`、`flask-cors`、`pymupdf`**,即使它們已經寫在 `backend/requirements.txt` 裡。在跑任何後端驗證之前,先確認裝好:`pip install flask flask-cors pymupdf`(用 `which python` 解析到的同一個直譯器)。**不要**額外安裝 `sentence-transformers`、`mineru`、`whisper` —— `Embedder`(`backend/services/rag/embedder.py`)在沒有 `sentence-transformers` 時會自動 fallback 成 TF-IDF(用已安裝的 `scikit-learn`),這個 fallback 對本次功能完全足夠。
- 向量庫維持單一、全域;`ingest_arxiv_selection()` 一律先呼叫 `self.clear()` 再入庫。
- API 回傳的英文/中文文案:後端錯誤訊息沿用既有中文風格(參考 `routes/rag.py` 既有的錯誤訊息用詞);前端介面文案使用繁體中文。
- Python 檔案沿用現有 4 空白縮排、`from typing import ...` 型別註記風格(參考 `paper_rag.py`)。Vue 元件風格:`<template>` 在前、`<script setup lang="ts">` 在後、`<style scoped>` 最後,2 空格縮排。
- Commit message 使用英文、慣例式前綴(`feat:`/`refactor:`),不加 Co-Authored-By 以外的尾註。
- 所有前端指令在 `frontend/` 目錄下執行;所有後端指令在 `backend/` 目錄下執行。

---

### Task 1: arXiv 查詢與 PDF 全文解析模組(`arxiv_source.py`)

**Files:**
- Create: `backend/services/rag/arxiv_source.py`
- Create: `backend/scripts/test_arxiv_source.py`

**Interfaces:**
- Consumes: 無(純 stdlib `urllib`/`xml.etree` + 既有的 `pymupdf`(`fitz`))
- Produces:
  - `search_arxiv(query: str, max_results: int = 8) -> list[dict]`,每筆 `dict` 含 `arxiv_id: str, title: str, authors: str, year: int | None, abstract: str, pdf_url: str`
  - `fetch_pdf_text(pdf_url: str) -> str`,下載失敗或解析失敗時拋出例外(呼叫端負責 try/except)

- [ ] **Step 1: 建立 `backend/services/rag/arxiv_source.py`**

```python
"""arXiv API 查詢與 PDF 全文解析

純函式模組,不依賴 Gemini。供 PaperRAGService 分類/入庫流程使用。
"""

import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_API_URL = "http://export.arxiv.org/api/query"


def search_arxiv(query: str, max_results: int = 8) -> List[dict]:
    """呼叫 arXiv Export API,回傳候選論文清單。

    回傳每筆:{arxiv_id, title, authors, year, abstract, pdf_url}
    """
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
    })
    url = f"{_ARXIV_API_URL}?{params}"

    with urllib.request.urlopen(url, timeout=15) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    candidates: List[dict] = []

    for entry in root.findall(f"{_ATOM_NS}entry"):
        entry_id = entry.findtext(f"{_ATOM_NS}id", default="") or ""
        arxiv_id = entry_id.rsplit("/abs/", 1)[-1] if "/abs/" in entry_id else entry_id

        title = " ".join((entry.findtext(f"{_ATOM_NS}title", default="") or "").split())
        summary = " ".join((entry.findtext(f"{_ATOM_NS}summary", default="") or "").split())
        published = entry.findtext(f"{_ATOM_NS}published", default="") or ""
        year: Optional[int] = int(published[:4]) if published[:4].isdigit() else None

        authors = [
            (author.findtext(f"{_ATOM_NS}name", default="") or "").strip()
            for author in entry.findall(f"{_ATOM_NS}author")
        ]

        pdf_url = ""
        for link in entry.findall(f"{_ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "") or ""
                break

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": ", ".join(a for a in authors if a),
            "year": year,
            "abstract": summary,
            "pdf_url": pdf_url,
        })

    return candidates


def fetch_pdf_text(pdf_url: str) -> str:
    """下載 PDF 到暫存檔,用 pymupdf 解析全文,結束後清除暫存檔。

    下載或解析失敗時讓例外往外拋,由呼叫端(PaperRAGService.ingest_arxiv_selection）
    決定要跳過這一篇還是中止。
    """
    import fitz  # PyMuPDF

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            with urllib.request.urlopen(pdf_url, timeout=30) as resp:
                tmp.write(resp.read())

        doc = fitz.open(str(tmp_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
```

- [ ] **Step 2: 建立驗證腳本 `backend/scripts/test_arxiv_source.py`**

```python
"""arxiv_source.py 手動驗證腳本(用法：在 backend/ 目錄下執行 python scripts/test_arxiv_source.py）"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.rag.arxiv_source import fetch_pdf_text, search_arxiv


def main():
    print("=" * 60)
    print("[Step 1] 查詢 arXiv: 'XGBoost customer churn prediction imbalanced classification'")
    candidates = search_arxiv("XGBoost customer churn prediction imbalanced classification", max_results=3)
    assert len(candidates) > 0, "應該至少查到一篇論文"

    for c in candidates:
        print(f"\n[{c['arxiv_id']}] {c['title']} ({c['year']})")
        print(f"  作者：{c['authors']}")
        print(f"  摘要：{c['abstract'][:120]}...")
        print(f"  PDF：{c['pdf_url']}")
        assert c["pdf_url"], "每篇候選論文都應該有 pdf_url"

    print("\n[Step 2] 下載並解析第一篇的 PDF 全文...")
    text = fetch_pdf_text(candidates[0]["pdf_url"])
    print(f"  解析出全文長度：{len(text)} 字元")
    assert len(text) > 500, "全文長度應該遠超過摘要長度"

    print("\n測試完成！")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 確認相依套件已安裝**

Run(在 `backend/` 目錄下):

```bash
python -c "import fitz; print('pymupdf ok')"
```

Expected: 印出 `pymupdf ok`。若出現 `ModuleNotFoundError`,先執行 `pip install pymupdf`(這是專案 `requirements.txt` 已宣告的既有依賴,只是這個 sandbox 的 venv 沒裝)。

- [ ] **Step 4: 執行驗證腳本**

Run(在 `backend/` 目錄下):

```bash
python scripts/test_arxiv_source.py
```

Expected: 印出至少 3 篇候選論文(含 arxiv_id/title/authors/abstract/pdf_url),接著印出解析出的 PDF 全文長度(遠大於 500 字元),最後印出「測試完成！」,無例外拋出。

- [ ] **Step 5: Commit**

```bash
git add backend/services/rag/arxiv_source.py backend/scripts/test_arxiv_source.py
git commit -m "feat: add arxiv_source module for arXiv search and PDF text extraction"
```

---

### Task 2: `PaperRAGService` 新增分類/查詢/入庫方法

**Files:**
- Modify: `backend/services/rag/paper_rag.py:21`(新增 import)
- Modify: `backend/services/rag/paper_rag.py:246-247`(在 `generate_paper()` 結束後、`get_status()` 之前插入三個新方法)
- Create: `backend/scripts/test_arxiv_pipeline.py`

**Interfaces:**
- Consumes: Task 1 的 `arxiv_source.search_arxiv()`、`arxiv_source.fetch_pdf_text()`；`PaperRAGService` 既有的 `self._model`(Gemini)、`self._call_gemini()`、`self._format_datamind_output()`、`self.add_paper()`、`self.clear()`
- Produces:
  - `PaperRAGService.classify_topic(mining_results: dict) -> dict`,回傳 `{"topic": str, "arxiv_query": str}`
  - `PaperRAGService.search_arxiv_candidates(mining_results: dict) -> dict`,回傳 `{"topic": str, "arxiv_query": str, "candidates": list[dict]}`
  - `PaperRAGService.ingest_arxiv_selection(candidates: list[dict]) -> dict`,回傳 `{"success": bool, "ingested": list[str], "failed": list[str], "error"?: str}`

- [ ] **Step 1: 新增 import**

`backend/services/rag/paper_rag.py` 第 19–21 行,原本:

```python
from .chunker import Chunk, TextChunker
from .embedder import Embedder
from .vector_store import VectorStore
```

改為:

```python
from . import arxiv_source
from .chunker import Chunk, TextChunker
from .embedder import Embedder
from .vector_store import VectorStore
```

- [ ] **Step 2: 在 `generate_paper()` 之後插入三個新方法**

`backend/services/rag/paper_rag.py` 第 245–247 行,原本:

```python
            "usage": usage_total,
        }

    def get_status(self) -> dict:
```

改為:

```python
            "usage": usage_total,
        }

    def classify_topic(self, mining_results: dict) -> dict:
        """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢字串。"""
        results_text = self._format_datamind_output(mining_results)
        prompt = (
            "你是學術論文寫作助手。請根據以下資料探勘實驗結果，"
            "判斷這份研究適合的研究主題與 arXiv 查詢關鍵字。\n\n"
            f"【資料探勘實驗結果】\n{results_text}\n\n"
            "請「只」輸出以下兩行，不要有其他文字：\n"
            "TOPIC: <繁體中文的研究主題，一句話，供論文標題使用>\n"
            "QUERY: <2 到 6 個英文關鍵字，空白分隔，適合直接拿去查 arXiv，"
            "不要加引號或布林運算子>"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)

        topic_match = re.search(r"TOPIC:\s*(.+)", text)
        query_match = re.search(r"QUERY:\s*(.+)", text)

        topic = topic_match.group(1).strip() if topic_match else "資料探勘實驗研究"
        arxiv_query = query_match.group(1).strip() if query_match else topic

        return {"topic": topic, "arxiv_query": arxiv_query}

    def search_arxiv_candidates(self, mining_results: dict) -> dict:
        """分類 mining_results 產生查詢字，查詢 arXiv 取得候選論文清單（不寫入向量庫）。"""
        classification = self.classify_topic(mining_results)
        candidates = arxiv_source.search_arxiv(classification["arxiv_query"])
        return {
            "topic": classification["topic"],
            "arxiv_query": classification["arxiv_query"],
            "candidates": candidates,
        }

    def ingest_arxiv_selection(self, candidates: List[dict]) -> dict:
        """清空向量庫，下載選中的 arXiv 論文全文並加入索引。

        單篇下載/解析失敗時跳過並記錄，不中斷整體流程；若全部失敗則回傳錯誤。
        """
        self.clear()

        ingested: List[str] = []
        failed: List[str] = []

        for candidate in candidates:
            title = candidate.get("title", "")
            pdf_url = candidate.get("pdf_url", "")
            try:
                content = arxiv_source.fetch_pdf_text(pdf_url)
                if not content.strip():
                    raise ValueError("PDF 未解析出任何文字")
            except Exception as e:
                logger.warning("下載/解析 arXiv PDF 失敗：%s (%s)", title, e)
                failed.append(title)
                continue

            result = self.add_paper(
                title=title,
                content=content,
                metadata={
                    "author": candidate.get("authors", ""),
                    "year": candidate.get("year", ""),
                    "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
                },
            )
            if result.get("success"):
                ingested.append(title)
            else:
                failed.append(title)

        if not ingested:
            return {
                "success": False,
                "error": "所有候選論文皆下載/解析失敗，無法建立參考文獻庫",
                "ingested": ingested,
                "failed": failed,
            }

        return {"success": True, "ingested": ingested, "failed": failed}

    def get_status(self) -> dict:
```

- [ ] **Step 3: 建立驗證腳本 `backend/scripts/test_arxiv_pipeline.py`**

```python
"""arXiv 分類/查詢/入庫 pipeline 手動驗證腳本

用法（在 backend/ 目錄下執行）：
    python scripts/test_arxiv_pipeline.py
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# 跟 test_paper_gen.py 相同形狀的假 DataMind 輸出
MOCK_DATAMIND_OUTPUT = {
    "success": True,
    "class_distribution": {
        "counts": {"0": 9820, "1": 2180},
        "imbalance_ratio": 4.5046
    },
    "preprocess_variants": [
        {
            "preprocess_steps": [
                {"type": "fill_na", "strategy": "mean"},
                {"type": "standardize"}
            ],
            "feature_engineering_steps": [
                {"type": "select_relevant_features", "k": 20}
            ]
        }
    ],
    "results": [
        {
            "preprocess_pipeline_index": 0,
            "model_name": "XGBoost",
            "split_name": "split_0",
            "validation_config": {
                "method": "train_test_split",
                "n_splits": 1,
                "stratified": True,
                "train_size": 0.8,
                "test_size": 0.2,
                "shuffle": True,
                "random_state": 42
            },
            "resampling_method": "smote",
            "best_params": {},
            "metrics": [
                {"id": "s0", "metric": "balanced_accuracy", "value": 0.9420, "ci_lower": None, "ci_upper": None},
                {"id": "s1", "metric": "auc", "value": 0.9601, "ci_lower": None, "ci_upper": None},
                {"id": "s2", "metric": "precision", "value": 0.93, "ci_lower": None, "ci_upper": None},
                {"id": "s3", "metric": "recall", "value": 0.89, "ci_lower": None, "ci_upper": None},
                {"id": "s4", "metric": "f1", "value": 0.91, "ci_lower": None, "ci_upper": None},
            ],
        },
    ]
}


def main():
    print("=" * 60)
    print("arXiv Pipeline 測試")
    print("=" * 60)

    from services.rag.paper_rag import PaperRAGService

    test_index_dir = BACKEND_DIR / "artifacts" / "test_arxiv_index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RAG_INDEX_DIR"] = str(test_index_dir)

    service = PaperRAGService()

    print("\n[Step 1] 分類 mining_results 並查詢 arXiv 候選論文...")
    search_result = service.search_arxiv_candidates(MOCK_DATAMIND_OUTPUT)
    print(f"  研究主題：{search_result['topic']}")
    print(f"  arXiv 查詢字串：{search_result['arxiv_query']}")
    print(f"  候選論文數：{len(search_result['candidates'])}")
    assert len(search_result["candidates"]) > 0, "應該至少查到一篇候選論文"

    for c in search_result["candidates"][:3]:
        print(f"    - [{c['arxiv_id']}] {c['title']}")

    print("\n[Step 2] 選前 2 篇候選論文，下載全文入庫...")
    selected = search_result["candidates"][:2]
    ingest_result = service.ingest_arxiv_selection(selected)
    print(f"  入庫成功：{ingest_result['ingested']}")
    print(f"  入庫失敗：{ingest_result['failed']}")
    assert ingest_result["success"], f"入庫應該至少成功一篇：{ingest_result}"

    status = service.get_status()
    print(f"  向量庫狀態：{status['total_papers']} 篇論文，{status['total_chunks']} 個 chunks")

    print("\n測試完成！")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 執行驗證腳本**

Run(在 `backend/` 目錄下):

```bash
python scripts/test_arxiv_pipeline.py
```

Expected: 依序印出研究主題、arXiv 查詢字串、候選論文清單(至少 1 篇)、入庫成功清單(至少 1 篇)、向量庫狀態,最後印出「測試完成！」,無例外拋出。

- [ ] **Step 5: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/scripts/test_arxiv_pipeline.py
git commit -m "feat: add classify_topic, search_arxiv_candidates, ingest_arxiv_selection to PaperRAGService"
```

---

### Task 3: 新增 Flask 路由(`routes/rag.py`)

**Files:**
- Modify: `backend/routes/rag.py`(檔案末尾新增兩個 route function)

**Interfaces:**
- Consumes: Task 2 的 `PaperRAGService.search_arxiv_candidates()`、`.ingest_arxiv_selection()`、既有的 `.generate_paper()`(透過 `get_paper_rag_service()`)
- Produces:
  - `POST /api/rag/arxiv/search`,body `{mining_results: dict}`,回傳 `{success, topic, arxiv_query, candidates}`
  - `POST /api/rag/arxiv/generate`,body `{topic: str, mining_results: dict, selected_candidates: list[dict]}`,回傳 `{success, result: {...同 /generate-paper}, ingested, failed}`

- [ ] **Step 1: 在檔案末尾新增兩個 route**

`backend/routes/rag.py` 檔案末尾(第 348 行之後),新增:

```python


@rag_bp.route("/arxiv/search", methods=["POST"])
def arxiv_search():
    """分類 DataMind 探勘結果並查詢 arXiv 候選論文（不寫入向量庫）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - topic       : AI 產生的研究主題
        - arxiv_query : 用於查詢 arXiv 的關鍵字字串
        - candidates  : 候選論文清單（arxiv_id/title/authors/year/abstract/pdf_url）
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        result = service.search_arxiv_candidates(data["mining_results"])
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.exception("arXiv 查詢失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/arxiv/generate", methods=["POST"])
def arxiv_generate():
    """下載選中的 arXiv 論文、建立索引，並生成論文

    JSON body:
        - topic               : 研究主題（必填）
        - mining_results      : DataMind 探勘結果（必填）
        - selected_candidates : 使用者勾選的候選論文清單（必填，來自 /arxiv/search 的 candidates）

    回傳：與 /generate-paper 相同形狀，外加 ingested/failed 清單
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    topic = data.get("topic", "").strip()
    mining_results = data.get("mining_results")
    selected_candidates = data.get("selected_candidates")

    if not topic:
        return jsonify({"success": False, "error": "topic 為必填欄位"}), 400
    if mining_results is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    if not selected_candidates:
        return jsonify({"success": False, "error": "selected_candidates 為必填欄位，至少需選擇一篇論文"}), 400

    service = get_paper_rag_service()

    try:
        ingest_result = service.ingest_arxiv_selection(selected_candidates)
        if not ingest_result.get("success"):
            return jsonify(ingest_result), 422

        result = service.generate_paper(topic=topic, mining_results=mining_results)
        return jsonify({
            "success": True,
            "result": result,
            "ingested": ingest_result["ingested"],
            "failed": ingest_result["failed"],
        })

    except Exception as e:
        logger.exception("arXiv 論文生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: 啟動本機 Flask dev server**

Run(在 `backend/` 目錄下,背景執行):

```bash
python app.py
```

Expected: 印出 Flask 開發伺服器啟動訊息,監聽 `http://127.0.0.1:5001`。

- [ ] **Step 3: curl 驗證 `/api/rag/arxiv/search`**

Run:

```bash
curl -s -X POST http://127.0.0.1:5001/api/rag/arxiv/search \
  -H "Content-Type: application/json" \
  -d '{"mining_results": {"results": [{"model_name": "XGBoost", "metrics": [{"metric": "auc", "value": 0.96}]}]}}'
```

Expected: 回傳 JSON,`success: true`,含 `topic`(字串)、`arxiv_query`(字串)、`candidates`(陣列,至少 1 筆,每筆有 `arxiv_id/title/authors/year/abstract/pdf_url`)。

- [ ] **Step 4: curl 驗證 `/api/rag/arxiv/generate`**

先把上一步回傳的 `candidates` 陣列取前 1–2 筆,組成請求(可用 Python 腳本組 JSON 避免手動轉義出錯):

```bash
python -c "
import json, urllib.request

search_body = json.dumps({'mining_results': {'results': [{'model_name': 'XGBoost', 'metrics': [{'metric': 'auc', 'value': 0.96}]}]}}).encode()
req = urllib.request.Request('http://127.0.0.1:5001/api/rag/arxiv/search', data=search_body, headers={'Content-Type': 'application/json'})
search_result = json.loads(urllib.request.urlopen(req).read())

gen_body = json.dumps({
    'topic': search_result['topic'],
    'mining_results': {'results': [{'model_name': 'XGBoost', 'metrics': [{'metric': 'auc', 'value': 0.96}]}]},
    'selected_candidates': search_result['candidates'][:1],
}).encode()
req2 = urllib.request.Request('http://127.0.0.1:5001/api/rag/arxiv/generate', data=gen_body, headers={'Content-Type': 'application/json'})
gen_result = json.loads(urllib.request.urlopen(req2).read())
print('success:', gen_result.get('success'))
print('sections_generated:', gen_result.get('result', {}).get('sections_generated'))
print('citation_map entries:', len(gen_result.get('result', {}).get('citation_map', [])))
print('ingested:', gen_result.get('ingested'))
"
```

Expected: `success: True`,`sections_generated` 是非空章節清單,`citation_map entries` 是數字(可能是 0,若 Gemini 生成內容剛好沒引用也算合理,但通常應 > 0),`ingested` 至少含 1 篇標題。

- [ ] **Step 5: 停止 dev server**

Run: 終止 Step 2 啟動的背景程序。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/rag.py
git commit -m "feat: add /api/rag/arxiv/search and /api/rag/arxiv/generate routes"
```

---

### Task 4: `PaperSegment` 支援多重引用(`citationIds`)

**Files:**
- Modify: `frontend/src/constants/reportData.ts:10-13`(型別)、`:56-60`、`:73-76`(mock 資料)
- Modify: `frontend/src/components/paper/PaperSection.vue`(template 與新增 helper function)
- Modify: `frontend/src/views/PaperPage.vue:69`(querySelector 改成屬性包含比對)

**Interfaces:**
- Consumes: 無
- Produces: `PaperSegment { text: string; citationIds?: string[] }`(取代原本的 `citationId?: string`),供 Task 5 的 `paperTransform.ts` 產生資料時使用

- [ ] **Step 1: 修改 `PaperSegment` 型別**

`frontend/src/constants/reportData.ts` 第 10–13 行,原本:

```ts
export interface PaperSegment {
  text: string
  citationId?: string
}
```

改為:

```ts
export interface PaperSegment {
  text: string
  citationIds?: string[]
}
```

- [ ] **Step 2: 更新 mock 資料的第一處引用**

`frontend/src/constants/reportData.ts` 第 56–60 行,原本:

```ts
          {
            // 引用編號 [n] 由 UI 依 citations 順序推導,不要寫進 text
            text: '這項結果與近期文獻一致,指出梯度提升決策樹 (GBDT) 演算法由於具備處理特徵間複雜非線性交互作用的能力,在結構化表格數據 (Tabular Data) 的分類任務中,通常能提供比傳統統計模型更穩健的預測能力',
            citationId: 'cite-1',
          },
```

改為:

```ts
          {
            // 引用編號 [n] 由 UI 依 citations 順序推導,不要寫進 text
            text: '這項結果與近期文獻一致,指出梯度提升決策樹 (GBDT) 演算法由於具備處理特徵間複雜非線性交互作用的能力,在結構化表格數據 (Tabular Data) 的分類任務中,通常能提供比傳統統計模型更穩健的預測能力',
            citationIds: ['cite-1'],
          },
```

- [ ] **Step 3: 更新 mock 資料的第二處引用**

`frontend/src/constants/reportData.ts` 第 73–76 行,原本:

```ts
          {
            text: '數據顯示,採「按月付費 (Month-to-month)」合約的客戶,其基礎流失機率比簽訂「兩年合約」的長期客戶高出 45%,這反映了合約轉換成本 (Switching Cost) 會顯著降低客戶的忠誠度',
            citationId: 'cite-2',
          },
```

改為:

```ts
          {
            text: '數據顯示,採「按月付費 (Month-to-month)」合約的客戶,其基礎流失機率比簽訂「兩年合約」的長期客戶高出 45%,這反映了合約轉換成本 (Switching Cost) 會顯著降低客戶的忠誠度',
            citationIds: ['cite-2'],
          },
```

- [ ] **Step 4: 改寫 `PaperSection.vue` 支援多重引用**

`frontend/src/components/paper/PaperSection.vue` 整份改為:

```vue
<template>
  <section class="paper-section">
    <h3 class="section-heading">{{ section.heading }}</h3>
    <p
      v-for="(paragraph, pIndex) in section.paragraphs"
      :key="pIndex"
      class="section-paragraph"
    >
      <template v-for="(segment, sIndex) in paragraph" :key="sIndex">
        <!-- data-citation-id 是 PaperPage 捲動定位用的 DOM 契約(空白分隔的多個 id),改動需同步 PaperPage -->
        <mark
          v-if="citationIdsOf(segment).length"
          class="cite-highlight"
          :class="{ 'cite-highlight--active': citationIdsOf(segment).includes(activeCitationId ?? '') }"
          :data-citation-id="citationIdsOf(segment).join(' ')"
          role="button"
          tabindex="0"
          @click="$emit('citation-click', firstCitationId(segment))"
          @keydown.enter.prevent="$emit('citation-click', firstCitationId(segment))"
          @keydown.space.prevent="$emit('citation-click', firstCitationId(segment))"
        >{{ segment.text }}<template v-for="cid in citationIdsOf(segment)" :key="cid"> [{{ citationIndex[cid] }}]</template></mark>
        <template v-else>{{ segment.text }}</template>
      </template>
    </p>
  </section>
</template>

<script setup lang="ts">
  import type { PaperSection, PaperSegment } from '@/constants/reportData'

  defineProps<{
    section: PaperSection
    activeCitationId: string | null
    citationIndex: Record<string, number>
  }>()

  defineEmits<{
    (e: 'citation-click', citationId: string): void
  }>()

  function citationIdsOf (segment: PaperSegment): string[] {
    return segment.citationIds ?? []
  }

  function firstCitationId (segment: PaperSegment): string {
    return citationIdsOf(segment)[0] ?? ''
  }
</script>

<style scoped>
  .paper-section {
    margin-bottom: 22px;
  }

  .section-heading {
    margin: 0 0 10px;
    font-size: 15px;
    font-weight: 700;
    color: #1c2130;
  }

  .section-paragraph {
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.9;
    color: #2a2f3a;
    text-align: justify;
    text-indent: 2em;
  }

  .cite-highlight {
    background: #fdf0a8;
    padding: 1px 2px;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .cite-highlight:hover {
    background: #fae57e;
  }

  .cite-highlight:focus-visible {
    outline: 2px solid #c9ad2a;
    outline-offset: 1px;
  }

  .cite-highlight--active {
    background: #f7dc5a;
    box-shadow: 0 0 0 2px rgba(201, 173, 42, 0.35);
  }
</style>
```

- [ ] **Step 5: 修改 `PaperPage.vue` 的 querySelector**

`frontend/src/views/PaperPage.vue` 第 69 行,原本:

```ts
        ?.querySelector(`[data-citation-id="${CSS.escape(citationId)}"]`)
```

改為(`~=` 比對空白分隔清單裡是否包含該 id,才能捲動到含多重引用的段落):

```ts
        ?.querySelector(`[data-citation-id~="${CSS.escape(citationId)}"]`)
```

- [ ] **Step 6: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無新錯誤

- [ ] **Step 7: 目視驗證既有 `/paper` 假資料流程沒壞掉**

Run: `npm run dev`(在 `frontend/` 下),開啟 `/paper`
Expected:
1. 頁面呈現與改動前一致:兩處黃底 highlight,各顯示 `[1]`、`[2]`
2. 點內文 highlight → 右側對應文獻卡片高亮;點右側卡片 → 內文捲動到對應段落

- [ ] **Step 8: Commit**

```bash
git add frontend/src/constants/reportData.ts frontend/src/components/paper/PaperSection.vue frontend/src/views/PaperPage.vue
git commit -m "refactor: support multiple citation ids per paper segment"
```

---

### Task 5: 假 mining_results、arXiv API client、後端結果轉換

**Files:**
- Create: `frontend/src/constants/mockMiningResults.ts`
- Create: `frontend/src/api/arxiv.ts`
- Create: `frontend/src/utils/paperTransform.ts`

**Interfaces:**
- Consumes: `PaperReport`、`PaperSection`、`PaperSegment`、`Citation`(來自 `@/constants/reportData`,Task 4 之後的型別)
- Produces:
  - `mockMiningResults: Record<string, unknown>`(具名匯出)
  - `searchArxivCandidates(miningResults): Promise<ArxivSearchResult>`
  - `generateFromArxiv(params): Promise<ArxivGenerateResult>`
  - `transformArxivResultToPaperReport(result: ArxivGenerateResult, topic: string): PaperReport`

- [ ] **Step 1: 建立 `frontend/src/constants/mockMiningResults.ts`**

```ts
export const mockMiningResults = {
  success: true,
  class_distribution: {
    counts: { '0': 9820, '1': 2180 },
    imbalance_ratio: 4.5046,
  },
  preprocess_variants: [
    {
      preprocess_steps: [
        { type: 'fill_na', strategy: 'mean' },
        { type: 'standardize' },
      ],
      feature_engineering_steps: [
        { type: 'select_relevant_features', k: 20 },
      ],
    },
  ],
  results: [
    {
      preprocess_pipeline_index: 0,
      model_name: 'XGBoost',
      split_name: 'split_0',
      validation_config: {
        method: 'train_test_split',
        n_splits: 1,
        stratified: true,
        train_size: 0.8,
        test_size: 0.2,
        shuffle: true,
        random_state: 42,
      },
      resampling_method: 'smote',
      best_params: {},
      metrics: [
        { id: 's0', metric: 'balanced_accuracy', value: 0.9420, ci_lower: null, ci_upper: null },
        { id: 's1', metric: 'auc', value: 0.9601, ci_lower: null, ci_upper: null },
        { id: 's2', metric: 'precision', value: 0.93, ci_lower: null, ci_upper: null },
        { id: 's3', metric: 'recall', value: 0.89, ci_lower: null, ci_upper: null },
        { id: 's4', metric: 'f1', value: 0.91, ci_lower: null, ci_upper: null },
      ],
    },
  ],
}
```

- [ ] **Step 2: 建立 `frontend/src/api/arxiv.ts`**

```ts
export interface ArxivCandidate {
  arxiv_id: string
  title: string
  authors: string
  year: number | null
  abstract: string
  pdf_url: string
}

export interface ArxivSearchResult {
  topic: string
  arxiv_query: string
  candidates: ArxivCandidate[]
}

export async function searchArxivCandidates (miningResults: Record<string, unknown>): Promise<ArxivSearchResult> {
  const response = await fetch('/api/rag/arxiv/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return {
    topic: String(result.topic ?? ''),
    arxiv_query: String(result.arxiv_query ?? ''),
    candidates: Array.isArray(result.candidates) ? result.candidates as ArxivCandidate[] : [],
  }
}

export interface ArxivCitationSource {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  relevant_chunk?: string
  similarity_score?: number | null
}

export interface ArxivCitationMapEntry {
  section: string
  paragraph_index: number
  text: string
  cited_ref_ids: number[]
  sources: ArxivCitationSource[]
}

export interface ArxivReference {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  journal?: string
}

export interface ArxivGenerateResult {
  paper_markdown: string
  citation_map: ArxivCitationMapEntry[]
  references: ArxivReference[]
  citation_report: string
  sections_generated: string[]
  usage: Record<string, number | null>
}

export async function generateFromArxiv (params: {
  topic: string
  miningResults: Record<string, unknown>
  selectedCandidates: ArxivCandidate[]
}): Promise<ArxivGenerateResult> {
  const response = await fetch('/api/rag/arxiv/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: params.topic,
      mining_results: params.miningResults,
      selected_candidates: params.selectedCandidates,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as ArxivGenerateResult
}
```

- [ ] **Step 3: 建立 `frontend/src/utils/paperTransform.ts`**

```ts
import type { ArxivGenerateResult } from '@/api/arxiv'
import type { Citation, PaperReport, PaperSection, PaperSegment } from '@/constants/reportData'

function parseParagraph (paragraphText: string): PaperSegment[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const segments: PaperSegment[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const ids = Array.from(token.matchAll(/\d+/g)).map(match => `cite-${match[0]}`)
      const prev = segments.at(-1)
      if (prev && !prev.citationIds) {
        prev.citationIds = ids
      } else {
        segments.push({ text: '', citationIds: ids })
      }
    } else {
      segments.push({ text: token })
    }
  }

  return segments
}

function buildCitations (result: ArxivGenerateResult): Citation[] {
  return result.references
    .slice()
    .sort((a, b) => a.ref_id - b.ref_id)
    .map(ref => {
      const snippetEntry = result.citation_map
        .flatMap(entry => entry.sources)
        .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)

      return {
        id: `cite-${ref.ref_id}`,
        title: ref.title,
        authors: String(ref.author ?? ''),
        journal: String(ref.journal ?? 'arXiv'),
        year: Number(ref.year) || 0,
        snippet: snippetEntry?.relevant_chunk ?? '',
      }
    })
}

export function transformArxivResultToPaperReport (result: ArxivGenerateResult, topic: string): PaperReport {
  const blocks = result.paper_markdown.split('\n\n---\n\n')
  const sections: PaperSection[] = []

  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ') || trimmed.startsWith('## 參考文獻')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)
      .map(parseParagraph)

    sections.push({ heading, paragraphs })
  }

  return {
    title: topic,
    sections,
    citations: buildCitations(result),
  }
}
```

- [ ] **Step 4: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過,無新錯誤

- [ ] **Step 5: Commit**

```bash
git add frontend/src/constants/mockMiningResults.ts frontend/src/api/arxiv.ts frontend/src/utils/paperTransform.ts
git commit -m "feat: add mock mining results, arxiv API client, and backend-to-PaperReport transform"
```

---

### Task 6: `paperStore.ts` 與 `/paper` 頁面接收真實生成結果

**Files:**
- Create: `frontend/src/store/paperStore.ts`
- Modify: `frontend/src/views/PaperPage.vue:40-53`

**Interfaces:**
- Consumes: `PaperReport`(來自 `@/constants/reportData`)
- Produces: `usePaperStore()`,回傳 `{ generatedReport: Ref<PaperReport | null>, setGeneratedReport(report: PaperReport): void, clearGeneratedReport(): void }`

- [ ] **Step 1: 建立 `frontend/src/store/paperStore.ts`**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { PaperReport } from '@/constants/reportData'

export const usePaperStore = defineStore('paper', () => {
  const generatedReport = ref<PaperReport | null>(null)

  function setGeneratedReport (report: PaperReport): void {
    generatedReport.value = report
  }

  function clearGeneratedReport (): void {
    generatedReport.value = null
  }

  return { generatedReport, setGeneratedReport, clearGeneratedReport }
})
```

- [ ] **Step 2: 修改 `PaperPage.vue` 讀取真實生成結果,無則 fallback 假資料**

`frontend/src/views/PaperPage.vue` 第 40–53 行,原本:

```ts
<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'

  const router = useRouter()
  const report = mockPaperReport

  const citationIndex = Object.fromEntries(
    report.citations.map((citation, index) => [citation.id, index + 1]),
  )
```

改為:

```ts
<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'

  const router = useRouter()
  const paperStore = usePaperStore()
  const report = paperStore.generatedReport ?? mockPaperReport
  paperStore.clearGeneratedReport()

  const citationIndex = Object.fromEntries(
    report.citations.map((citation, index) => [citation.id, index + 1]),
  )
```

- [ ] **Step 3: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 4: 目視驗證 fallback 行為**

Run: `npm run dev`(在 `frontend/` 下),直接開啟 `/paper`(不經過任何生成流程)
Expected: 跟 Task 4 驗證時一樣,顯示既有假資料 `mockPaperReport`,行為不變(因為 `paperStore.generatedReport` 一開始是 `null`)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/store/paperStore.ts frontend/src/views/PaperPage.vue
git commit -m "feat: add paperStore for handing off generated paper to PaperPage"
```

---

### Task 7: 候選論文選擇頁(`PaperSourcesView.vue`)與觸發入口

**Files:**
- Create: `frontend/src/views/PaperSourcesView.vue`
- Modify: `frontend/src/router/index.ts`(新增 `/paper/sources` 路由)
- Modify: `frontend/src/views/ResultsPage.vue`(新增「生成論文」按鈕)

**Interfaces:**
- Consumes: Task 5 的 `mockMiningResults`、`searchArxivCandidates()`、`generateFromArxiv()`、`transformArxivResultToPaperReport()`;Task 6 的 `usePaperStore()`;`HubSidebar`(`@/components/hub/HubSidebar.vue`,無 props)
- Produces: 路由 `/paper/sources`(name: `paper-sources`)

- [ ] **Step 1: 建立 `frontend/src/views/PaperSourcesView.vue`**

```vue
<template>
  <section class="sources-page">
    <HubSidebar />

    <main class="sources-main">
      <header class="sources-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.push('/results')"
        />
        <h2 class="sources-title">選擇參考文獻</h2>
      </header>

      <p v-if="topic" class="sources-topic">研究主題:{{ topic }}</p>

      <div v-if="loadingSearch" class="sources-status">
        正在分析資料並查詢 arXiv...
      </div>

      <div v-else-if="searchError" class="sources-status sources-status--error">
        {{ searchError }}
        <v-btn size="small" variant="text" @click="loadCandidates">重試</v-btn>
      </div>

      <div v-else-if="candidates.length === 0" class="sources-status">
        找不到相關文獻,請稍後再試。
      </div>

      <template v-else>
        <ul class="candidate-list">
          <li v-for="candidate in candidates" :key="candidate.arxiv_id" class="candidate-card">
            <label class="candidate-select">
              <input
                v-model="selectedIds"
                :value="candidate.arxiv_id"
                type="checkbox"
              >
              <div class="candidate-body">
                <p class="candidate-title">{{ candidate.title }}</p>
                <p class="candidate-meta">
                  {{ candidate.authors }}
                  <span v-if="candidate.year">({{ candidate.year }})</span>
                </p>
                <p class="candidate-abstract">{{ candidate.abstract }}</p>
              </div>
            </label>
          </li>
        </ul>

        <div class="sources-actions">
          <v-btn
            color="primary"
            :disabled="selectedIds.length === 0 || generating"
            @click="handleGenerate"
          >
            {{ generating ? '生成中...' : `確認並生成論文 (${selectedIds.length})` }}
          </v-btn>
          <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
        </div>
      </template>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { generateFromArxiv, searchArxivCandidates, type ArxivCandidate } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import { mockMiningResults } from '@/constants/mockMiningResults'
  import { usePaperStore } from '@/store/paperStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'

  const router = useRouter()
  const paperStore = usePaperStore()

  const topic = ref('')
  const candidates = ref<ArxivCandidate[]>([])
  const selectedIds = ref<string[]>([])

  const loadingSearch = ref(false)
  const searchError = ref<string | null>(null)

  const generating = ref(false)
  const generateError = ref<string | null>(null)

  async function loadCandidates (): Promise<void> {
    loadingSearch.value = true
    searchError.value = null
    try {
      const result = await searchArxivCandidates(mockMiningResults)
      topic.value = result.topic
      candidates.value = result.candidates
      selectedIds.value = []
    } catch (error) {
      searchError.value = error instanceof Error ? error.message : String(error)
    } finally {
      loadingSearch.value = false
    }
  }

  async function handleGenerate (): Promise<void> {
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: mockMiningResults,
        selectedCandidates,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push('/paper')
    } catch (error) {
      generateError.value = error instanceof Error ? error.message : String(error)
    } finally {
      generating.value = false
    }
  }

  onMounted(loadCandidates)
</script>

<style scoped>
  .sources-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    min-height: calc(100vh - 64px);
    display: flex;
    padding: 16px;
    background: linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .sources-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 24px;
    overflow: auto;
  }

  .sources-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .sources-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .sources-topic {
    margin: 14px 2px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status {
    margin: 20px 2px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status--error {
    color: #b91c1c;
  }

  .candidate-list {
    list-style: none;
    margin: 14px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .candidate-card {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--card-bg);
  }

  .candidate-select {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
  }

  .candidate-body {
    flex: 1;
    min-width: 0;
  }

  .candidate-title {
    margin: 0 0 4px;
    font-size: 13.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .candidate-meta {
    margin: 0 0 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .candidate-abstract {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }

  .sources-actions {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
</style>
```

- [ ] **Step 2: 新增路由**

`frontend/src/router/index.ts` 第 26–30 行,原本:

```ts
    {
      path: "/paper",
      name: "paper",
      component: () => import("@/views/PaperPage.vue"),
    },
```

改為:

```ts
    {
      path: "/paper",
      name: "paper",
      component: () => import("@/views/PaperPage.vue"),
    },
    {
      path: "/paper/sources",
      name: "paper-sources",
      component: () => import("@/views/PaperSourcesView.vue"),
    },
```

- [ ] **Step 3: `ResultsPage.vue` 新增「生成論文」按鈕**

`frontend/src/views/ResultsPage.vue` 第 15–28 行,原本:

```vue
        <div class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="toolbar-tab"
            :class="{ 'toolbar-tab--active': tab.active }"
            type="button"
            @click="setActiveTab(tab.key)"
          >
            <v-icon :icon="tab.icon" size="14" />
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </header>
```

改為:

```vue
        <div class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="toolbar-tab"
            :class="{ 'toolbar-tab--active': tab.active }"
            type="button"
            @click="setActiveTab(tab.key)"
          >
            <v-icon :icon="tab.icon" size="14" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <v-btn
          class="generate-paper-btn"
          color="primary"
          size="small"
          @click="router.push('/paper/sources')"
        >
          生成論文
        </v-btn>
      </header>
```

`frontend/src/views/ResultsPage.vue` 第 96–98 行,原本:

```ts
<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
```

改為:

```ts
<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import HubSidebar from '@/components/hub/HubSidebar.vue'

  const router = useRouter()
```

`frontend/src/views/ResultsPage.vue` 第 232–239 行(`<style scoped>` 內的 `.toolbar-tabs` 規則),原本:

```css
  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

```

改為(在後方新增 `.generate-paper-btn` 規則):

```css
  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

  .generate-paper-btn {
    margin-left: 12px;
  }

```

- [ ] **Step 4: 型別檢查與 Lint**

Run(在 `frontend/` 下):`npm run type-check`,接著 `npm run lint`
Expected: 皆通過

- [ ] **Step 5: 全流程目視驗證(需要 Task 1–3 的後端 dev server 同時執行)**

Run: 在 `backend/` 下 `python app.py`(背景),在 `frontend/` 下 `npm run dev`
Expected(依序操作):
1. 開啟 `/results`,點右上「生成論文」→ 導向 `/paper/sources`
2. `/paper/sources` 顯示 loading,幾秒後列出候選論文清單(標題/作者/年份/摘要),含研究主題文字
3. 勾選 1–2 篇,按「確認並生成論文」→ 按鈕顯示「生成中...」
4. 生成完成(可能需要數十秒:下載 PDF + 6 章節 Gemini 生成)後自動導向 `/paper`
5. `/paper` 顯示真實生成的論文標題與章節內容,若章節中有引用會顯示黃底 highlight,點擊後右側對應文獻卡片高亮
6. 重新整理後直接開 `/paper`(不經過 sources 頁)→ 應該 fallback 顯示原本的假資料 `mockPaperReport`(因為 store 已在上次 mount 時被清空)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/PaperSourcesView.vue frontend/src/router/index.ts frontend/src/views/ResultsPage.vue
git commit -m "feat: add PaperSourcesView candidate selection page and results page entry point"
```
