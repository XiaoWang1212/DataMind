# 論文萃取優先抓完整變數清單 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修正論文萃取 prompt 裡 `features` 的填寫規則，讓 Gemini 優先萃取論文的完整候選變數清單，不要因為論文另外標示了「重要子集」（例如特徵重要性分析挑出的變數）就只列子集。

**Architecture:** 純 prompt 文字改動，只改 `backend/services/gemini_service.py` 裡 `_WORKFLOW_SYSTEM_PROMPT` 字串中「填寫原則」段落的 `features` 那一條規則。這個字串同時被 `analyze()`、`analyze_pdf()`、`analyze_pdf_stream()` 三個方法共用，改一處三者都受益。

**Tech Stack:** Python 3.11、Gemini API（`google-generativeai`/`google-genai`）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-12-extract-complete-variable-list-design.md`
- 只改 `backend/services/gemini_service.py:105` 那一行規則文字，不動其他 key 的規則、不動 `description_zh` 產生邏輯、不動任何 API 介面或前端程式碼
- 這是 prompt 文字調整，沒有程式邏輯可寫單元測試；用真實樣本 PDF（`backend/samples/pycaret_sample/CIN_published (1).pdf`）實際呼叫 Gemini API 驗證效果，需要 `GEMINI_API_KEY` 可用
- 測試用 PDF 目前已知有 54 個候選變數（論文 Table 1），改動前只萃取出約 11 個

---

### Task 1: 修正 features 填寫規則

**Files:**
- Modify: `backend/services/gemini_service.py:105`

**Interfaces:** 無（單一任務，純字串改動，不被其他任務消費）

- [ ] **Step 1: 修改 `_WORKFLOW_SYSTEM_PROMPT` 的 `features` 規則**

找到 `backend/services/gemini_service.py` 的（第 96-105 行）：

```python
填寫原則：
- models：依論文列出的模型，name 必須完全符合可用模型名稱清單
- preprocessing：依論文資料處理方式，若未提及則用 fill_na+standardize
- featureEngineering：依論文特徵選擇方式，若未提及則用 select_relevant_features k=10
- validation：依論文驗證方式，若未提及則用 k_fold n_splits=10
- metrics：依論文評估指標，至少包含 balanced_accuracy 和 auc
- resampling：論文有提類別不平衡處理 → 填對應 method；否則填 none
- tuning：論文有提超參數搜尋 → 填 grid 或 random；否則填 none
- compute_ci：論文有報告信賴區間或 bootstrap → true；否則 false
- features：論文提到的輸入特徵，每個一筆"""
```

改成（只改最後一行 `features` 的規則，前面 8 行完全不動）：

```python
填寫原則：
- models：依論文列出的模型，name 必須完全符合可用模型名稱清單
- preprocessing：依論文資料處理方式，若未提及則用 fill_na+standardize
- featureEngineering：依論文特徵選擇方式，若未提及則用 select_relevant_features k=10
- validation：依論文驗證方式，若未提及則用 k_fold n_splits=10
- metrics：依論文評估指標，至少包含 balanced_accuracy 和 auc
- resampling：論文有提類別不平衡處理 → 填對應 method；否則填 none
- tuning：論文有提超參數搜尋 → 填 grid 或 random；否則填 none
- compute_ci：論文有報告信賴區間或 bootstrap → true；否則 false
- features：優先列出論文中「完整的候選變數清單」（例如變數定義表、資料欄位表），逐一列出每一個變數；即使論文另外用特徵選擇/重要性分析標示出一個「重要子集」，也不要只列子集——完整清單才是這裡要的，子集留給後續 featureEngineering 的 select_relevant_features 處理。論文完全沒有完整清單時，才依文中零星提到的變數盡量列出。"""
```

- [ ] **Step 2: 用真實樣本 PDF 驗證（呼叫 analyze_pdf_stream）**

Run:
```bash
env $(cat backend/.env | grep -v '^#' | xargs) python3 -c "
import sys
sys.path.insert(0, 'backend')
from services.gemini_service import GeminiService

svc = GeminiService()
with open('backend/samples/pycaret_sample/CIN_published (1).pdf', 'rb') as f:
    pdf_bytes = f.read()

result_data = None
for event in svc.analyze_pdf_stream(pdf_bytes, title='CIN_published'):
    if event['type'] == 'result':
        result_data = event['data']
    elif event['type'] == 'error':
        print('ERROR:', event['message'])

features = result_data['workflow_json']['features']
print('feature count:', len(features))
missing_definition = [f['name'] for f in features if not f.get('description_zh')]
print('features missing description_zh:', missing_definition)
print('sample names:', [f['name'] for f in features[:5]])
"
```

（`backend/.env` 裡有 `GEMINI_API_KEY`；這支腳本直接呼叫真實 Gemini API，會花數十秒。如果本機沒有可用的 backend 執行環境，改用 `docker exec datamind-backend` 執行同一段程式碼，路徑相應調整為容器內的 `/app`。）

Expected：
- `feature count` 明顯多於改動前的 11 個（不要求剛好 54，允許 Gemini 對表格理解有誤差，但應該遠多於 11——合理範圍抓 30 個以上都算改動生效）
- `features missing description_zh` 印出空清單 `[]`（每個變數仍然有填定義）
- 沒有印出 `ERROR:` 開頭的訊息（輸出仍是合法 JSON，沒有被截斷）

- [ ] **Step 3: Commit**

```bash
git add backend/services/gemini_service.py
git commit -m "fix: extract complete variable list from papers instead of importance-selected subset"
```
