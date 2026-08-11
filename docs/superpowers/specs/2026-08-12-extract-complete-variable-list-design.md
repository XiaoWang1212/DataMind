# 論文萃取優先抓完整變數清單 Design Spec

## 背景

論文萃取的 `features` 欄位規則目前寫得太模糊（`backend/services/gemini_service.py:105`）：「features：論文提到的輸入特徵，每個一筆」。

當論文同時有「完整候選變數清單」（例如變數定義表）跟「特徵選擇後的重要子集」（例如用 GainRatioAttributeEval 挑出的關鍵變數）時，Gemini 會選擇萃取後者。實測驗證：`backend/samples/pycaret_sample/CIN_published (1).pdf` 這篇論文的 Table 1 列出 54 個候選變數（IVs），Discussion 段落另外用特徵選擇挑出 8 個「key variables」，目前萃取結果只有 11 個變數（對應到重要子集 + 基本人口學欄位），不是完整的 54 個。

目標：改這條規則，讓 Gemini 優先萃取完整候選清單，不要因為論文另外標示了「重要子集」就只列子集。

## 範圍

- 只改 `backend/services/gemini_service.py` 的 `_WORKFLOW_SYSTEM_PROMPT` 字串裡，「填寫原則」段落中 `features` 那一條規則（第 105 行）
- `_WORKFLOW_SYSTEM_PROMPT` 同時被 `analyze()`（純文字）、`analyze_pdf()`（PDF 非串流）、`analyze_pdf_stream()`（PDF 串流思考）三個方法共用，改這一處三者都會受益，不需要分別修改
- **不**動其他 key（`models`/`preprocessing`/`featureEngineering`/`validation`/`metrics`/`resampling`/`tuning`/`compute_ci`）的填寫規則
- **不**動 `description_zh` 的產生邏輯（維持每個變數都要填定義）
- **不**動任何 API 介面、前端程式碼、或 `_fill_defaults()`/`_safe_parse_json()`/`_normalize_to_json()` 等既有解析/修復邏輯

## 規則內容

新規則不限定「表格」這個形式（不是每篇論文的變數清單都用表格呈現），而是用「完整候選清單 vs 重要子集」這個一般性判斷準則：

> features：優先列出論文中「完整的候選變數清單」（例如變數定義表、資料欄位表），逐一列出每一個變數；即使論文另外用特徵選擇/重要性分析標示出一個「重要子集」，也不要只列子集——完整清單才是這裡要的，子集留給後續 featureEngineering 的 select_relevant_features 處理。論文完全沒有完整清單時，才依文中零星提到的變數盡量列出。

設計理由：
- 就算變數數量因此變多（例如 54 個），下游的 `featureEngineering`（預設 `select_relevant_features k=10`）本來就是負責從候選特徵裡篩選出重要子集的步驟，萃取階段不需要越俎代庖先篩過一次，篩兩次反而可能篩掉論文原本用得到的變數
- 保留「論文沒提到就照抄範例預設值」的既有原則：完全沒有完整清單的論文，退回目前的行為（依文中零星提到的變數盡量列出）

## 錯誤處理 / 相容性

- 沒有既有測試或已知呼叫端依賴目前「只萃取重要子集」的行為，這是單純修正萃取品質，不涉及向下相容問題
- 變數數量變多不影響既有的 JSON 輸出格式（`features` 陣列本來就沒有數量上限），`_fill_defaults()`/`_safe_parse_json()` 等既有解析邏輯不需要跟著改
- `max_output_tokens`（非串流路徑 8192、串流路徑因 `thinking_budget=-1` 未設上限）估計足夠容納 50-60 筆 `{name, type, description_zh}` 的 features 陣列，不特別調整；若實測發現輸出被截斷，屬於獨立的後續問題，不在本次範圍

## 測試

- 這是 prompt 文字調整，沒有程式邏輯好寫單元測試。用 `backend/samples/pycaret_sample/CIN_published (1).pdf` 這份已知有 54 個變數、目前只萃取出 11 個的樣本重新跑一次萃取（`analyze_pdf` 或 `analyze_pdf_stream` 皆可，走 `ExtractFrameworkView.vue` 的真實流程），確認：
  - `features` 陣列數量明顯增加、趨近 54 個（不要求剛好 54，Gemini 對表格的理解仍有誤差空間，但應該遠多於現在的 11 個）
  - 每個變數的 `description_zh` 仍然有填（不因為變數變多就開始省略定義）
  - 輸出仍是合法 JSON，沒有被截斷
