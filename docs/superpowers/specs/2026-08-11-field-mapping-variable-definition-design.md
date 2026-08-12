# 欄位對齊帶入變數定義 Design Spec

## 背景

「建立新專案」流程的最後一步「欄位對齊」（`FieldMappingView.vue`）進頁面就同步呼叫 Gemini 的 `semantic_match`，把演算法比對不出來的論文變數一次送進去做語意配對，使用者要等這支 API 回來畫面才會動。

論文萃取階段（`GeminiService.analyze_pdf`/`analyze_pdf_stream`）其實早就會幫每個變數產生中文定義（`features[].description_zh`，例如 `{"name": "age", "description_zh": "病患年齡"}`），存在 `Framework.workflow_json` 裡。但欄位對齊的 `buildPaperVariables()`（`FieldMappingView.vue:583-605`）目前只取 `name`/`type`，這個定義完全沒被用到。

目標：把這個已經存在、被閒置的定義接進語意配對的 Gemini prompt，讓模型不用自己從變數名稱猜意思，減少配對時的推理量、縮短欄位對齊頁面的等待時間；順便讓使用者在頁面上也看得到這個定義。

## 範圍

- 把 `definition`（來源：`description_zh`）從萃取結果一路帶到 `semantic_match` 的 Gemini prompt，以及欄位對齊頁面的 UI 顯示
- **不**把定義加進純字串比對的演算法層（`run_auto_mapping`/`_score_candidates`）——技術上沒有意義：演算法是字元層級的字串相似度比對，定義是中文自然語言、欄位名稱通常是英文/代號，兩者形式不同，字串相似度演算法沒辦法用中文定義去比對出英文欄位名稱有沒有關聯，這種語意層級的關聯只有 Gemini 才做得到
- **不**動論文萃取端（`description_zh` 早就在產生了，不需要新增或修改萃取邏輯）
- **不**動 `/api/field-mapping/chat`（對話式修正）的邏輯

## 資料串接路徑

```
Framework.workflow_json.features[].description_zh   （既有，萃取時就有）
  ↓ FieldMappingView.vue buildPaperVariables()
paper_variables[].definition                          （新增欄位）
  ↓ POST /api/field-mapping/init
run_auto_mapping(paper_variables, columns)
  ↓ 原樣透傳進每筆輸出（不參與比分）
mapping_status[].definition
  ↓ 篩出 pending（status != AUTO_MATCHED）後
semantic_match(pending, columns) → _format_pending() 把定義寫進 prompt
  ↓ API 回應（definition 隨 mapping_status 一起回傳）
FieldMappingView.vue 變數卡片 → info icon + tooltip 顯示定義
```

## 前端改動

**`frontend/src/types/fieldMapping.ts`**
- `PaperVariable` 新增 `definition?: string`
- `MappingItem` 新增 `definition?: string`（讓 API 回應能把定義帶回來，UI 才讀得到）

**`FieldMappingView.vue`**
- `buildPaperVariables()`：從 `feature.description_zh ?? feature.descriptionZh`（防禦性讀取兩種命名，比照專案內既有 `target_col ?? targetCol` 的寫法）取值，寫進 `definition`；沒有這個欄位（舊框架、或 Gemini 沒填）時就是 `undefined`，不特別處理
- 變數卡片（`v-for="item in sortedItems"` 那段）：`item.definition` 存在時，在變數名稱旁加一個小 info icon，hover/tap 顯示定義文字；不存在就不渲染 icon，卡片維持原樣

## 後端改動

**`backend/services/field_mapping_service.py`**
- `run_auto_mapping()`：組每筆 `variables` 內部物件時多存 `definition = str(raw.get("definition") or "").strip() or None`；輸出 `mapping_status` 的每個 dict 多一個 `"definition": variable["definition"]` 欄位。純傳遞，不參與 `_score_candidates`/`fuzzy_match` 的比分邏輯

**`backend/services/field_mapping_prompts.py`**
- `_format_pending()`：`item.get("definition")` 有值時，該行變數多附加「；定義：{definition}」；沒有就維持現在只顯示型態的格式

## 錯誤處理 / 相容性

- 舊框架（萃取時間早於這次改動、或 Gemini 沒把 `description_zh` 填好）→ `definition` 是 `None`/`undefined`，一路優雅降級：prompt 不多印那段、UI 不顯示 tooltip，行為等同現在
- 不改變 `semantic_match`/`chat_refine` 的回傳格式或 `merge_semantic_suggestions` 的合併規則

## 測試

- 後端無 pytest，前端無 vitest，一律用 `npm run type-check` + 人工瀏覽器驗證：
  - 用一個 `workflow_json.features` 有 `description_zh` 的框架建立新專案，走到欄位對齊頁，確認變數卡片上有 info icon、hover 看得到定義文字
  - 觀察 Network 分頁，確認 `/api/field-mapping/init` 的回應 `mapping_status` 項目有帶 `definition`
  - 用一個沒有 `description_zh`（或用舊資料）的框架測，確認卡片不顯示 icon、流程不出錯
