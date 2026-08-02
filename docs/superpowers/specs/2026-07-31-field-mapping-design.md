# 欄位對齊（Field Mapping）設計：演算法 + AI 協作的資料對映頁

日期：2026-07-31（2026-08-02 依資料庫遷移現況修訂）
狀態：已與使用者確認方向，實作計畫見 `docs/superpowers/plans/2026-07-31-field-mapping.md`

## 前置現況（2026-08-02）

本設計初稿寫於資料庫遷移之前。其後專案已完成第一階段遷移，以下是撰寫實作時必須知道的現況：

- `create_app()` 強制要求 `DATABASE_URL`，並初始化 `db`（Flask-SQLAlchemy）與 `login_manager`（Flask-Login）。
- `projects` / `frameworks` 已是資料庫資料表，`routes/project.py`、`routes/framework.py` 每支 API 都掛 `@login_required` 並以 `current_user.id` 過濾。
- **`Project.id` 是 `int`**，不是字串。前端 `projectStore` 改為呼叫 API，不再寫 localStorage。
- `datasets` / `workflow_states` 資料表已建立，但**前端尚未接**：資料集檔案仍存在瀏覽器 IndexedDB（`useWorkflowStorage.ts`）。本設計沿用 IndexedDB，等資料集上傳 API 完成後再一起遷移。
- `views/hub/ResultView.vue` 已有一個 AI 聊天面板（結果分析用），聊天記錄走 `saveChatHistoryToStorage()` / `loadChatHistoryFromStorage()`（localStorage）。本設計的聊天面板照這個既有做法，不另立一套。

## 背景

論文分析（`/api/gemini/ai-analyze`）會產出 workflow JSON，其中 `features` 是論文用到的變數清單、`target_col` 是預測目標。使用者接著上傳自己的資料集 CSV。問題是兩邊的欄位名稱幾乎不會一樣：論文說 `age`、`gender`、`braden_score`，使用者的資料表欄位可能叫 `pt_age`、`sex`、`braden_total`。

目前系統沒有任何機制處理這件事。`CreateProjectView.vue` 的四步驟精靈裡，第三步「上傳資料集」的副標題已經寫著「對應您的資料」，但實際上只做了檔案上傳，沒有任何對應動作；建立完專案就直接導向 `/workflow`，資料表欄位與論文變數之間沒有對得起來的環節。

本設計補上這一段：一個獨立頁面，左側是「論文變數 ↔ 使用者欄位」的對映表，右側是 AI 對話。系統先用字串演算法做自動配對，配不到的交給 Gemini 做語意判斷，剩下的由使用者透過下拉選單或自然語言對話修正。

專案定位上，「以自然語言與 AI 互動」是這個功能的核心價值，不是附加選項；但下拉選單必須同時存在，作為 AI 不可用時的保底路徑。

## 決策摘要

- **獨立頁面，不塞進建立專案精靈。** 路由 `/hub/projects/:id/mapping`，左表右聊天。對齊需要專注與操作空間，且之後可隨時回到這一頁重新調整。
- **三層配對，由便宜到貴。** 字串正規化 + 模糊比對（純 Python）→ 樣本值型態加減分（純 Python）→ Gemini 語意判斷（只處理前兩層搞不定的，且一次打包成單一請求）。
- **聊天只管欄位對齊，不做資料前處理指令。** 缺值填補、標準化、移除欄位等已由 workflow 的 Preprocessor 節點負責；聊天若也能改，兩邊會出現不一致且難以除錯。之後若要讓聊天下前處理指令，做法是讓它去改 Preprocessor 節點的設定，不是自己另做一套。
- **對齊結果以「改寫 CSV 表頭」的方式套用，ML 引擎完全不動。** 前端離開頁面時把 CSV 表頭改寫成論文變數名，再交給既有的 `handleDataFile(file)`。`services/workflow/`、`routes/model.py` 一行都不必碰。
- **對映關係存進資料庫，不是用完就丟。** `projects` 表新增 `column_mapping` JSONB 欄位（含 alembic migration），透過既有的 `PATCH /api/projects/<id>` 存取。與 `frameworks.workflow_json` 的既有做法一致。供之後在 DataTablePanel 顯示「此欄對照自 pt_age」使用 —— 本期只負責存，那個 UI 不在範圍內。
- **聊天記錄走 localStorage，不進資料庫。** 對話是過程中的暫存而非成果，且 `ResultView.vue` 的聊天面板已經是這個做法，照抄比自創一套安全。用同一組 `saveChatHistoryToStorage()` / `loadChatHistoryFromStorage()`，以 `mapping-` 前綴的 key 區隔。
- **兩支新 API 掛 `@login_required`。** 與 `routes/project.py`、`routes/framework.py` 一致；同時避免出現一個未登入就能打、會消耗 Gemini 額度的開放端點。
- **後端 API 對「對映狀態」本身無狀態。** `/chat` 每次都由前端帶完整 `current_mapping_state` 與 `chat_history` 上來，伺服器不在記憶體裡保留任何對話。前端重新整理不會對不上，也不需要伺服器端 session 管理。
- **Target 變數強制人工確認。** 即使字串完全相同、信心度 1.0，也標成 `NEEDS_REVIEW`。target 配錯會讓整個實驗結果錯得很安靜，不值得為省一次點擊冒險。
- **用 `response_schema` 從 API 層強制輸出格式，不只靠 prompt 拜託。** 這是對付「JSON 輸出不穩」這個核心風險最有效的手段，既有的 `analyze()` 沒有用（只設了 `response_mime_type`），所以才需要 `_normalize_to_json()` 那套補救。新功能直接跳過這個坑。
- **AI 輸出一律視為不可信。** 白名單過濾後才准影響畫面；Gemini 不可用時頁面照常運作，只是沒有建議。schema 保證「格式合法」，白名單保證「內容合法」，兩者互補而非二選一 —— schema 擋不住模型回一個資料表裡不存在的欄位名。
- **AI 建議的配對永遠不會是 `AUTO_MATCHED`。** `semantic_match()` 的結果最高只到 `NEEDS_REVIEW`，一律需要使用者點頭。綠勾勾只保留給演算法層有把握的配對。
- **`chat_refine()` 的回傳除了 actions 還帶一段 `reply` 文字。** 這一點與原始需求描述不同 —— 原始描述只要求輸出 diff。但聊天介面若沒有 AI 的自然語言回覆，使用者無從得知指令是否被理解、為何某些要求沒被執行，功能會退化成一個難用的表單。`reply` 只是要顯示的文字，不影響「不輸出整包 mapping_status」這個原則。
- **不動既有論文分析邏輯。** `routes/gemini.py` 與 `gemini_service.py` 的 `analyze()` / `analyze_pdf()` / `_build_prompt()` / `_fill_defaults()` 完全不改，只在 `GeminiService` 類別新增兩個方法，並沿用既有的 `_safe_parse_json()` 與 model 設定。

## 使用者流程

```
建立專案：①名稱 ②選框架 ③上傳 CSV
              ↓ （建立完成後導向）
      /hub/projects/:id/mapping     ← 本設計新增
      左：對映表 + 資料預覽　右：AI 對話
              ↓ （按「確認並執行」）
      /workflow?project=:id          ← 既有畫面，收到的是改寫過表頭的 CSV
```

## 1. 後端

### 1.1 新模組：`backend/services/field_mapping_service.py`

不依賴 Gemini、不依賴 Flask，純函式模組，可獨立測試。

```python
def normalize_field(name: str) -> str:
    """欄位名正規化：轉小寫 → 去除空白/底線/破折號 → 去除 tbl_ / col_ 前綴。
    去前綴在去符號之前執行，因為 `tbl_user_name` 要先認出 `tbl_` 才能剝掉。
    例：" Pt_Age " → "ptage"；"tbl_user-name" → "username"
    """

def exact_match(paper_var: str, user_columns: list[str]) -> str | None:
    """正規化後完全相同的第一個欄位，沒有則 None。"""

def fuzzy_match(paper_var: str, user_columns: list[str]) -> list[tuple[str, float]]:
    """用 difflib.SequenceMatcher 對每個 user column 算相似度，
    回傳依分數由高到低排序的 (column_name, ratio) 清單。
    """

def boost_by_sample_values(score: float, required_type: str,
                           sample_values: list[str]) -> float:
    """用樣本值推斷型態（regex 判斷日期 / 數字 / 文字），與 required_type 比對後調整分數。
    型態相符 → +0.1；型態不符 → -0.2；無法判斷（sample_values 為空或全空字串）→ 不調整。
    結果 clamp 在 [0.0, 1.0]。
    """

def run_auto_mapping(paper_variables: list[dict],
                     user_columns: list[dict]) -> dict:
    """組合以上步驟，產出初始對映狀態（格式見 1.3）。"""
```

**型態推斷規則**（`boost_by_sample_values` 內部）

| 推斷結果 | 判斷方式 | 對應的 `required_type` |
|---|---|---|
| date | 樣本值多數符合 `YYYY-MM-DD` / `YYYY/MM/DD` / `YYYYMMDD` | `date`、`datetime` |
| numeric | 樣本值多數可轉為 float | `numerical`、`int`、`integer`、`float` |
| text | 以上皆非 | `categorical`、`string`、`text` |

「多數」定義為非空樣本值中至少 60% 符合。`required_type` 比對不分大小寫；若 `required_type` 不在上表任何一類（含空字串或缺漏），視為無法判斷，不調整分數。

**分數與狀態對應**

| 條件（樣本值加減分後的最終分數） | 狀態 |
|---|---|
| 正規化後完全相同 | 1.0 → `AUTO_MATCHED` |
| ≥ 0.8 | `AUTO_MATCHED` |
| 0.5 ≤ 分數 < 0.8 | `NEEDS_REVIEW` |
| < 0.5 | `UNMATCHED` |

`UNMATCHED` 時 `matched_user_column` 為 `null`，並在 `candidate_columns` 提供分數最高的前 3 個欄位供使用者選擇。

**兩條特別規則**

1. **Target 強制人工確認。** `is_target: true` 的變數，`required` 一律視為 `true`，且不論分數多高，狀態最高只到 `NEEDS_REVIEW`（信心度數值照實回報）。此筆必定出現在 `mapping_status` 中，不會因低信心度被略過。
2. **一對一佔用。** 一個 user column 不可同時被兩個 paper variable 佔用。以分數由高到低貪婪指派；被搶走的一方改用它的次高候選重新計算狀態，若已無可用候選則降為 `UNMATCHED`。target 在貪婪排序中優先，確保它不會被其他變數搶走欄位。

### 1.2 輸入格式

```json
{
  "paper_variables": [
    { "name": "age", "type": "numerical", "required": true, "is_target": false },
    { "name": "pressure_injury", "type": "categorical", "is_target": true }
  ],
  "user_columns": [
    { "name": "pt_age", "sample_values": ["65", "72", "48"] },
    { "name": "adm_date", "sample_values": ["2024-01-03", "2024-02-11"] }
  ]
}
```

`user_columns` 必須是物件陣列並帶 `sample_values`（前 5 筆），否則 `boost_by_sample_values` 無資料可用。路由層對只給字串的情況做寬鬆處理：字串一律轉為 `{ "name": <字串>, "sample_values": [] }`，不報錯。

`required` 為選填，預設 `true`。`is_target: true` 時不論帶什麼值一律視為 `true`。

`paper_variables` 由前端從框架的 `workflowJson` 組出：`features[]` 提供 `name` / `type`，`target_col` 對應的那一筆額外標上 `is_target: true`。若 `target_col` 不在 `features[]` 中，前端自行補一筆 `{ name: target_col, type: "categorical", is_target: true }`。

### 1.3 輸出格式

```json
{
  "total_required": 30,
  "matched_count": 28,
  "mapping_status": [
    {
      "paper_variable": "age",
      "required_type": "numerical",
      "matched_user_column": "pt_age",
      "confidence_score": 0.92,
      "status": "AUTO_MATCHED",
      "sample_values": ["65", "72", "48"],
      "candidate_columns": []
    },
    {
      "paper_variable": "braden_score",
      "required_type": "numerical",
      "matched_user_column": null,
      "confidence_score": 0.0,
      "status": "UNMATCHED",
      "sample_values": [],
      "candidate_columns": ["braden_total", "bs_score"]
    }
  ]
}
```

- `sample_values` 是**已配對到的 user column** 的樣本值；未配對時為空陣列。
- `candidate_columns` 僅在 `UNMATCHED` 時有內容，其餘狀態為空陣列（欄位一律存在，前端不需判斷 key 是否缺漏）。
- `total_required` 為 `paper_variables` 中 `required` 視為 true 的筆數（target 一律計入）；`matched_count` 為狀態是 `AUTO_MATCHED` 的筆數。

### 1.4 `GeminiService` 新增方法（`backend/services/gemini_service.py`）

只新增，不修改任何既有方法。兩個新方法沿用既有的 `self.model`、`_safe_parse_json()`、`_usage_dict()`。

```python
def semantic_match(self, items: list[dict],
                   user_columns: list[dict]) -> list[dict] | None:
    """對非 AUTO_MATCHED 的項目做語意配對建議。

    items 為 mapping_status 中 status != "AUTO_MATCHED" 的子集，
    每筆需含 paper_variable / required_type / candidate_columns。
    user_columns 是完整的使用者欄位清單（含 sample_values），供 Gemini 參考
    並作為白名單來源。

    一次呼叫處理全部項目，不逐筆呼叫。

    回傳（已通過白名單驗證）：
    [{ "paper_variable": str, "matched_user_column": str | None,
       "confidence_score": float, "candidate_columns": list[str] }]

    回傳 [] 代表「AI 可用但沒有給出有效建議」；
    回傳 None 代表「AI 不可用」（呼叫失敗、逾時、回應無法解析）。
    路由層用這個區別來決定 ai_available。任何情況都不拋例外。
    """

def chat_refine(self, current_mapping_state: dict, user_message: str,
                chat_history: list) -> dict:
    """依使用者的自然語言指令，產出這一輪的變更 diff。

    current_mapping_state 的形狀：
      { "mapping_status": [...],                       # 目前的完整對映狀態
        "user_columns": [{"name": str,
                          "sample_values": list[str]}] }  # 白名單來源
    prompt 帶入完整 current_mapping_state 作為 context，
    但只要求輸出變動的部分，不要求輸出整包 mapping_status。

    回傳（已通過白名單驗證）：
    { "actions": [ { "paper_variable": str, "matched_user_column": str | None,
                     "status": str, "confidence_score": float } ],
      "reply": str }
    reply 是要顯示在聊天視窗的自然語言回覆。
    無法解析時回傳 { "actions": [], "reply": "<可讀的錯誤說明>" }。
    """
```

**generation config**：兩者都用 `temperature=0`（配對是判斷題，不需要創造性）、`response_mime_type="application/json"`，並**帶上 `response_schema`**。既有的 `_generation_config()` 是 `temperature=0.2`、`max_output_tokens=8192` 且無 schema，供論文分析使用；本功能另開私有 helper，不改既有那支。

已確認執行環境的 `google-generativeai==0.8.6` 的 `GenerationConfig` 支援 `response_schema`，`GenerativeModel.__init__` 支援 `system_instruction`。

**`response_schema` 定義**（`field_mapping_prompts.py` 內，與 prompt 放在一起）

```python
SEMANTIC_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paper_variable": {"type": "string"},
                    "matched_user_column": {"type": "string", "nullable": True},
                    "confidence_score": {"type": "number"},
                    "candidate_columns": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["paper_variable", "matched_user_column",
                             "confidence_score", "candidate_columns"],
            },
        },
    },
    "required": ["matches"],
}
```

輸出刻意包在物件裡（`{"matches": [...]}`）而非裸陣列，因為既有的 `_safe_parse_json()` 最後一段 fallback 用 `\{[\s\S]*\}` 抓最外層大括號，裸陣列會抓不到。包成物件讓這道防線對兩個方法都有效。

```python

CHAT_REFINE_SCHEMA = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "paper_variable": {"type": "string"},
                    "matched_user_column": {"type": "string", "nullable": True},
                    "status": {"type": "string",
                               "enum": ["AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"]},
                    "confidence_score": {"type": "number"},
                },
                "required": ["paper_variable", "matched_user_column",
                             "status", "confidence_score"],
            },
        },
        "reply": {"type": "string"},
    },
    "required": ["actions", "reply"],
}
```

有了 schema 之後，`_safe_parse_json()` 仍然保留為第二道防線（處理 schema 未生效或 SDK 行為變更的情況），但預期不會被觸發。**白名單驗證不因為有 schema 而省略** —— schema 能保證 `matched_user_column` 是字串，無法保證那個字串真的是使用者資料表裡的欄位。

**`system_instruction`**：兩個方法共用一個獨立的 `GenerativeModel` 實例，在建構時帶入角色與通用規則（見 1.5），避免每次請求重送。此實例與既有的 `self.model` 並存，不取代它 —— 既有論文分析的行為完全不受影響。

**白名單驗證**（兩個方法共用的私有 helper）

Gemini 回傳的每一筆都要通過以下檢查，任一不過即整筆丟棄：

1. `matched_user_column` 必須存在於本次請求的 `user_columns` 中（`null` 視為合法，代表「找不到」）
2. `paper_variable` 必須存在於本次請求的變數清單中
3. `confidence_score` 必須是 0.0 ~ 1.0 的數值，否則丟棄該筆
4. `status` 必須是三個合法值之一，否則丟棄該筆

驗證發生在 service 層，路由層拿到的已是乾淨資料。

### 1.5 Prompt 設計：`backend/services/field_mapping_prompts.py`

Prompt 與 response schema 另開模組存放，不放進 `gemini_service.py`。理由：該檔已 312 行且其中大半是論文分析的 prompt 常數，再加兩段 prompt 與兩份 schema 會逼近 500 行；論文分析與欄位對齊是無關的兩件事，混在同一檔案裡調整 prompt 容易誤傷另一邊。`gemini_service.py` 只 import 常數，維持既有的 `_WORKFLOW_SYSTEM_PROMPT` 風格（模組層級字串常數 + f-string 組裝）。

**分工**：下面兩段 prompt 中，「角色 + 輸出規則 + 判斷依據」屬於不隨請求變動的部分，放進 `system_instruction`；「使用者欄位清單 / 待配對項目 / 對話記錄 / 使用者訊息」等每次都不同的資料，才放進 `generate_content()` 的 prompt。以下以完整內容呈現，實作時依此切分。

輸出格式的保證由 `response_schema` 負責（見 1.4），prompt 裡的格式說明是輔助，不是唯一防線。

#### `SEMANTIC_MATCH_PROMPT`

```
你是資料欄位對映助手。使用者有一份資料表，另有一篇論文要求的變數清單。
請判斷每個「論文變數」對應到使用者資料表的哪一個欄位。

【輸出規則】
1. 只輸出 JSON 陣列本體，不得包含 markdown、程式碼區塊、說明文字。
2. matched_user_column 只能從下方「使用者欄位清單」中挑選，不可自行創造名稱。
3. 不確定時，matched_user_column 填 null，改在 candidate_columns 列出 1~3 個可能的欄位。
4. 完全找不到合理對應時，matched_user_column 填 null，candidate_columns 填空陣列。
5. confidence_score 為 0.0 ~ 1.0 的數值，代表你的把握程度。
6. 每個輸入的論文變數都必須有一筆對應輸出，不可遺漏。

【判斷依據】
- 語意同義：sex 與 gender、dob 與 date_of_birth、bp_sys 與 systolic_bp 是同一件事
- 醫療常見縮寫：pt = patient、adm = admission、dx = diagnosis、hr = heart rate
- 樣本值型態：論文要 numerical 而該欄位樣本值是文字，即使名稱像也要降低信心度
- 論文變數的 required_type 與欄位樣本值明顯不符時，寧可給 null 也不要勉強配對

【使用者欄位清單（含前 5 筆樣本值）】
{user_columns_block}

【待配對的論文變數】
{pending_items_block}

【輸出格式】
[
  {"paper_variable": "systolic_bp", "matched_user_column": "bp_sys",
   "confidence_score": 0.85, "candidate_columns": []},
  {"paper_variable": "braden_score", "matched_user_column": null,
   "confidence_score": 0.0, "candidate_columns": ["braden_total", "bs"]}
]
```

`user_columns_block` 每行一欄：`- pt_age（樣本值：65, 72, 48）`
`pending_items_block` 每行一筆：`- systolic_bp（需要型態：numerical）`

#### `CHAT_REFINE_PROMPT`

```
你是資料欄位對映助手，正在協助使用者修正論文變數與資料表欄位的對應關係。

【輸出規則】
1. 只輸出 JSON 物件本體，不得包含 markdown、程式碼區塊、說明文字。
2. actions 只列出「這一輪要改變的項目」，不要輸出完整的對映清單。
3. 使用者沒有提到的變數，一律不要放進 actions。
4. matched_user_column 只能從下方「使用者欄位清單」中挑選，或填 null 表示解除對應。
5. paper_variable 只能是下方「目前對映狀態」中已存在的變數名稱。
6. status 只能是 AUTO_MATCHED、NEEDS_REVIEW、UNMATCHED 其中之一。
   由你的建議所產生的對應一律填 NEEDS_REVIEW，不可填 AUTO_MATCHED。
7. reply 用繁體中文，簡短說明你做了什麼。若有使用者的要求你無法執行
   （例如他指定的欄位不存在），必須在 reply 中說明原因。
8. 使用者只是提問而不要求修改時，actions 填空陣列，只回答問題。

【目前對映狀態】
{mapping_state_block}

【使用者欄位清單（含前 5 筆樣本值）】
{user_columns_block}

【對話記錄】
{chat_history_block}

【使用者這次的訊息】
{user_message}

【輸出格式】
{
  "actions": [
    {"paper_variable": "braden_score", "matched_user_column": "braden_total",
     "status": "NEEDS_REVIEW", "confidence_score": 0.9}
  ],
  "reply": "已把 braden_score 對應到 braden_total，請確認。"
}
```

`chat_history_block` 只帶最近 10 輪對話，避免 context 無限增長；超出部分由呼叫端截斷。

#### Prompt 相關的驗證重點

上述規則中，第 2、3、4 條（只輸出 diff、不碰未提及的變數、只用既有欄位）是**最容易被模型違反**的三條，也是白名單驗證主要在擋的東西。真實資料驗證時要特別觀察：使用者說「改 A」時，模型是否順手動了 B、C。若違反率偏高，調整方向是在 prompt 中加上反例，而不是放寬驗證。

### 1.6 新路由：`backend/routes/field_mapping.py`

薄路由層，寫法比照 `routes/gemini.py`（同樣的 `GeminiService()` 建構失敗處理、同樣的 try/except + `logger.exception` 風格）。兩支都掛 `@login_required`，與 `routes/project.py` 一致。

這兩支不碰資料庫：對映結果的持久化由前端在使用者按下「確認並執行」時，透過既有的 `PATCH /api/projects/<id>` 完成。

**`POST /api/field-mapping/init`**

```
輸入：{ paper_variables, user_columns }
流程：run_auto_mapping()
      → 若有 status != "AUTO_MATCHED" 的項目，呼叫 semantic_match() 補完
      → 合併結果回傳
輸出：{ success: true, result: <完整 mapping_status 物件>,
        ai_available: bool }
```

**合併規則**：`semantic_match()` 的結果只能影響原本非 `AUTO_MATCHED` 的項目，不得覆蓋演算法層已確定的配對。每筆建議依下列方式併入：

- 有 `matched_user_column`，且該欄位未被其他項目佔用 → 填入，狀態設為 `NEEDS_REVIEW`，`confidence_score` 取 Gemini 給的值但**上限 0.79**（確保它不會被誤讀成自動配對成功）
- 有 `matched_user_column` 但欄位已被佔用 → 不填入，改把該欄位名加進 `candidate_columns`
- 只給 `candidate_columns` → 併入原有的 `candidate_columns`（去重，最多保留 5 個），狀態不變

`semantic_match()` 失敗或 Gemini 不可用時：不回錯誤，回傳純演算法結果並把 `ai_available` 設為 `false`，讓前端顯示提示。`GeminiService()` 建構失敗（缺 `GEMINI_API_KEY`）同樣走這條路徑，不回 400 —— 演算法層不需要 API key 就能運作，沒有理由讓整個功能不可用。

**`POST /api/field-mapping/chat`**

```
輸入：{ current_mapping_state, user_message, chat_history }
流程：chat_refine()
輸出：{ success: true, result: { actions: [...], reply: str } }
```

只回 diff，不回整包狀態。前端自行把 actions 套用到本地狀態上。

### 1.7 掛載（`backend/apps/__init__.py`）

比照既有 blueprint：

```python
from routes.field_mapping import field_mapping_bp
app.register_blueprint(field_mapping_bp, url_prefix="/api/field-mapping")
```

並在根路由 `/` 的回傳中加上 `"field_mapping": "/api/field-mapping"` 一行，與既有各服務一致。

### 1.8 `projects` 表新增 `column_mapping` 欄位

**Model**（`backend/models/project.py`）新增：

```python
column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

**Migration**：新增一支 alembic revision，`down_revision` 指向目前的 head。

**序列化與寫入**（`backend/routes/project.py`）：`_serialize_project()` 加上 `"columnMapping": project.column_mapping`；`update_project()` 加上 `if "columnMapping" in data: project.column_mapping = data["columnMapping"]`。

形狀為 `{ 論文變數名: 使用者欄位名 }`，例如 `{"age": "pt_age", "gender": "sex"}`。這是本設計唯一需要動到既有資料庫結構的地方。

## 2. 前端

### 2.1 共用 CSV 解析工具（先行）

`parseCsvLine` 與 `decodeFileText`（UTF-8 / Big5 自動判斷）目前在 `DataTablePanel.vue` 與 `DistributionPanel.vue` 各有一份完全相同的實作。新頁面會是第三份，因此先抽出：

**檔案**：`frontend/src/utils/csv.ts`

```ts
export function parseCsvLine(line: string): string[]
export async function decodeFileText(file: File): Promise<string>
export async function parseCsvPreview(file: File, sampleRows = 5): Promise<{
  columns: string[]
  rows: string[][]
}>
```

`decodeFileText` 一併抽出，因為它也是兩份相同實作，且新頁面同樣需要（醫療資料表常見 Big5 編碼）。

`DataTablePanel.vue` 與 `DistributionPanel.vue` 改為 import 這份，刪掉各自的本地實作。行為不變，純粹去重複。

### 2.2 新頁面

**路由**：`/hub/projects/:id/mapping`，name `hub-project-mapping`，放在 HubLayout children 內、`projects/:id` 之後。

**檔案**：`frontend/src/views/hub/FieldMappingView.vue`

**版面**

```
┌────────────────────────────────────┬─────────────────────┐
│  欄位對齊    已對照 28 / 30         │  AI 助理             │
│                                    │                     │
│  論文變數      你的欄位      狀態    │  （對話串）          │
│  ─────────────────────────────────  │                     │
│  ★ 壓瘡發生   [pressure ▾]    ⚠    │                     │
│  age          [pt_age ▾]      ✓    │                     │
│  gender       [sex ▾]         ✓    │                     │
│  braden_score [請選擇 ▾]      ✗    │                     │
│                                    │                     │
│  ─── 資料預覽（前 5 筆）──────       │                     │
│  pt_age  sex  braden_total  …       │                     │
│  65      M    18                    │  [輸入訊息…   送出] │
│              [確認並執行 →]         │                     │
└────────────────────────────────────┴─────────────────────┘
```

**行為細節**

- 每一列都有下拉（用既有的 `components/common/CustomSelect.vue`），選項為使用者資料表全部欄位 + 「我的資料沒有這個變數」。已自動配好的也能直接改，不需要先解除。
- 選了「我的資料沒有這個變數」的列進入 `SKIPPED` 狀態（前端專屬狀態，後端不會產生也不會收到）：不阻擋執行，該變數在改寫 CSV 時不做任何事。**target 不可選此項**，因為沒有預測目標就無法執行實驗。
- 已被其他變數佔用的欄位在下拉中標記為已使用但仍可選；選了就從原持有者手上移走，原持有者退回 `UNMATCHED`。
- `★` 標記 target 變數，永遠排在列表最上方。
- 狀態圖示：`✓` AUTO_MATCHED（綠）、`⚠` NEEDS_REVIEW（黃）、`✗` UNMATCHED（紅）。
- **AI 改動的列閃現提示**：被 `chat_refine` 的 action 改到的列，套用淡黃色背景約 2 秒後淡出。沒有這個提示，使用者無法知道剛才那句話改到了哪一列。沿用專案既有的 flash 色票慣例（見 `2026-07-14-node-selected-state-and-flash-color-design`）。
- 「確認並執行」在仍有 `UNMATCHED` 時停用（tooltip 說明還有幾個未對應）；`NEEDS_REVIEW` 不阻擋 —— 待確認代表系統已有猜測，使用者不修改即視為接受。
- 使用者手動選過的列標記為「已鎖定」，後續 AI 建議不覆蓋它。
- `ai_available` 為 `false` 時，聊天區顯示「AI 建議暫時無法使用，可用下拉選單手動對應」，輸入框停用；左側表格功能不受影響。

### 2.3 API 層

**檔案**：`frontend/src/api/fieldMapping.ts`，比照 `api/workflow.ts` 的寫法。

```ts
export async function initFieldMapping(payload: {
  paperVariables: PaperVariable[]
  userColumns: UserColumn[]
}): Promise<MappingState>

export async function refineFieldMapping(payload: {
  currentMappingState: MappingState
  userMessage: string
  chatHistory: ChatMessage[]
}): Promise<{ actions: MappingAction[]; reply: string }>
```

型別定義放 `frontend/src/types/fieldMapping.ts`。

### 2.4 狀態保存

兩種狀態走不同路徑，因為性質不同。

**對映結果 → 資料庫**

`Project` 介面（`store/projectStore.ts`）與 `ProjectDTO`（`api/project.ts`）各新增一個欄位：

```ts
columnMapping?: Record<string, string> | null   // { 論文變數名: 使用者欄位名 }
```

`UpdateProjectPatch` 也加上同名選填欄位。store 新增：

```ts
async function saveColumnMapping (
  projectId: number,
  mapping: Record<string, string>,
): Promise<void>
```

內部呼叫既有的 `updateProject(projectId, { columnMapping: mapping, variables: Object.keys(mapping).length })`，並同步更新本地 `projects` 陣列裡的那一筆。

**聊天記錄 → localStorage**

沿用既有的 `saveChatHistoryToStorage(projectId, history)` / `loadChatHistoryFromStorage(projectId)`（`composables/workflow/useWorkflowStorage.ts`），與 `ResultView.vue` 同一套。為避免和結果分析的聊天撞 key，本頁傳入的 projectId 加 `mapping-` 前綴，例如 `saveChatHistoryToStorage(\`mapping-${projectId}\`, history)`。

對話是過程中的暫存而非成果，沒有理由為它加資料表；而且照既有做法比自創一套不容易出錯。

### 2.5 CSV 檔案的取得與交接

資料集尚未有上傳 API（`datasets` 表已建但前端未接），因此本設計沿用 IndexedDB。`useWorkflowStorage` 的 projectId 參數是字串，而 `Project.id` 是數字，呼叫時一律 `String(projectId)`。

- **進入頁面時**：優先用 `projectStore.activeContext.datasetFile`；若為 null（例如使用者重新整理），改用既有的 `loadWorkflowDataFileFromStorage(String(projectId))` 從 IndexedDB 讀回。若兩者皆無，顯示「找不到資料集，請回上一步重新上傳」並提供返回連結。
- **建立專案時**：`CreateProjectView.executeProject()` 除了設定 `activeContext`，也要呼叫 `saveWorkflowDataFileToStorage(file, projectId)` 存入 IndexedDB，然後導向 `/hub/projects/:id/mapping`（原本是直接導向 `/workflow`）。這同時修掉一個現存問題：目前 `activeContext.datasetFile` 只在記憶體裡，重新整理就遺失。
- **離開頁面時**：依 `columnMapping` 改寫 CSV 表頭（`pt_age` → `age`）。**只改名，不刪任何欄位** —— 未對應到論文變數的欄位保留原名原樣（workflow 端本來就能選要用哪些欄位，在這裡刪掉只會讓使用者失去選擇）。`SKIPPED` 的論文變數不對應到任何欄位，因此不做任何事。產生新的 `File` 物件覆寫存回 IndexedDB，並更新 `activeContext.datasetFile`，再導向 `/workflow?project=:id`。`WorkflowWorkspace.vue` 的 `onMounted` 邏輯完全不需要改。

## 3. 錯誤處理

| 狀況 | 處理方式 |
|---|---|
| Gemini 回傳含 markdown 包裝或前後贅字 | 沿用既有 `_safe_parse_json()` 的三段式解析（直接解析 → 去除 code fence → 正則抓最外層 `{}`） |
| Gemini 掰出不存在的欄位名 | 白名單擋下，整筆丟棄，該變數維持原狀態 |
| `/chat` 回傳超出使用者指令範圍的變更 | 無法在程式層可靠判定「使用者提到了哪些變數」（中文表述、代稱、「把剩下的都清掉」這類批次指令都會誤判），因此不做語意過濾。改為三道並用：prompt 明文禁止、**單輪 actions 上限 10 筆**（超出則整批拒絕並請使用者說得更具體）、前端對每一筆被改動的列都閃現提示讓使用者立刻看見。此項的實際違反率由 4.3 的驗收指標量測，超標時的處置是調整 prompt（加反例），不是放寬驗證 |
| Gemini 逾時 / 額度用盡 / 缺 API key | `/init` 回傳純演算法結果 + `ai_available: false`；`/chat` 回傳空 actions + 可讀錯誤訊息。頁面不崩潰 |
| CSV 只有表頭沒有資料列 | 正常運作，`sample_values` 為空陣列，型態加減分不啟動 |
| CSV 有重複欄位名 | 保留第一個，其餘在頁面上以警告提示（重複欄位無法明確對應） |
| 框架沒有 `features`（空陣列） | 顯示「此框架未擷取到變數清單，請回論文分析重新擷取」，不進入對齊流程 |

核心原則：**AI 的輸出永遠只是建議，白名單過濾後才准影響畫面。使用者的手動選擇優先權最高，不被後續 AI 建議覆蓋。**

## 4. 驗證計畫

程式碼審查無法保證這個功能可用 —— 真正的風險在 Gemini JSON 輸出的穩定性與 0.8 門檻的準確率，兩者都只能用真實資料量測。

### 4.1 單元測試（純函式，不連網）

- `normalize_field`：`" Pt_Age "` → `"ptage"`、`"tbl_user_name"` → `"username"`、`"col_BP-High"` → `"bphigh"`
- `exact_match` / `fuzzy_match`：已知答案的名稱組，確認分數落在預期區間
- `boost_by_sample_values`：型態相符 +0.1、不符 -0.2、無法判斷不變、clamp 邊界
- 狀態切分：0.79 → `NEEDS_REVIEW`、0.80 → `AUTO_MATCHED`、0.49 → `UNMATCHED`
- 一對一佔用：兩個變數搶同一欄時分數高的勝出，落敗者改用次高候選
- Target：一定出現在 `mapping_status`、狀態最高只到 `NEEDS_REVIEW`、貪婪排序中優先

### 4.2 假 Gemini 回應的防呆測試（不連網、不花錢）

以 stub 取代 `GeminiService`，餵入各種壞回應確認不會崩潰：

```
"```json\n{\"actions\":[...]}\n```"      → 解析成功
"好的！以下是結果：{\"actions\":[...]}"   → 解析成功
"抱歉，我無法判斷"                        → 視為無建議，非崩潰
{"matched_user_column": "不存在的欄位"}   → 被白名單丟棄
{"confidence_score": 3.7}                → 該筆被丟棄
""（空字串）                              → 視為無建議
```

### 4.3 真實資料驗證（驗收條件，非加分項）

用**一篇真實論文擷取出的 features + 一份真實資料表**跑完整流程。資料表欄位名須是實務上的縮寫風格（如 `pt_age`、`adm_dt`、`bp_sys`），不可用乾淨的示範檔，否則測不出門檻的準確率。

| 指標 | 通過標準 |
|---|---|
| 自動配對正確率 | 標記為 `AUTO_MATCHED` 的項目中，至少 90% 對應正確 |
| 假陽性 | 標記為 `AUTO_MATCHED` 但對應錯誤的，不超過 1 個 |
| Gemini JSON 解析成功率 | 連續 5 次 `/init` 呼叫全數解析成功（有 `response_schema` 的情況下，任何一次失敗都代表 schema 未如預期生效，須先查明原因再繼續） |
| `/chat` 越權修改率 | 連續 5 次「只改一個變數」的指令中，模型動到其他變數的次數為 0 |
| Target 正確性 | 100% 出現在結果中且狀態標記正確 |

假陽性標準比整體正確率嚴格，因為使用者信任綠勾勾、不會逐筆檢查，錯誤會一路帶進實驗結果。

**未通過的調整方向**：把 `AUTO_MATCHED` 門檻由 0.8 上調（0.85 / 0.9），寧可多幾筆 `NEEDS_REVIEW` 要人確認，也不要出現錯誤的 `AUTO_MATCHED`。此門檻只能靠真實資料校準。

### 4.4 端到端流程驗證

上傳論文 → 建立專案 → 對齊頁面 → 用聊天修改一個欄位 → 按「確認並執行」→ workflow 執行成功並產出結果。重點確認改寫過表頭的 CSV 確實能被既有 ML 引擎接受。

另需驗證：在對齊頁重新整理瀏覽器後，資料集與對映狀態都還在。

## 5. 明確不在本次範圍

- **DataTablePanel 顯示對照來源。** 本期只把 `columnMapping` 存好；在 workflow 的資料表面板顯示「此欄對照自 pt_age」是下一期，屆時不需回頭修改本期的資料結構。
- **聊天下達資料前處理指令。** 見決策摘要。之後的做法是讓聊天去改 Preprocessor 節點設定。
- **資料集上傳到伺服器。** `datasets` 資料表已建立但前端尚未接，本設計沿用 IndexedDB。等資料集上傳 API 完成後，本頁只需把「讀檔」與「寫回改寫後的檔案」兩處換掉，對映邏輯與 API 都不受影響。
- **聊天記錄進資料庫。** 目前走 localStorage，與 `ResultView.vue` 一致。若日後決定把兩處聊天都搬進資料庫，應該一起做，不要只搬這一處。
- **多資料集比對 / 一個論文變數對多欄位合併。** 目前只支援一對一。
- **`google-generativeai` 套件遷移。** Google 已將此套件標為 deprecated，建議改用 `google-genai`。遷移會動到既有的論文分析程式碼，不在本次範圍，但應列為後續待辦。本設計使用的 `response_schema` 與 `system_instruction` 在新舊套件中都有對應，遷移時不會因為本功能而增加額外成本。
