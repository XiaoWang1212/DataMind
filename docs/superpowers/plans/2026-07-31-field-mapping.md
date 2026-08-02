# 欄位對齊（Field Mapping）實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一個「資料前處理 Agent」頁面，把論文擷取出的變數自動對映到使用者上傳的資料表欄位，配不到的交給 Gemini 語意判斷，剩下的由使用者用下拉選單或自然語言對話修正。

**Architecture:** 後端新增一個純函式配對模組（字串正規化 + `difflib` 模糊比對 + 樣本值型態加減分），與一個薄路由層；Gemini 的兩個新方法只新增在 `GeminiService` 上、用 `response_schema` 從 API 層強制輸出格式、再過一層白名單驗證。前端新增獨立頁面（左對映表 + 右聊天），離開頁面時直接改寫 CSV 表頭交給既有 workflow，ML 引擎零修改。

**Tech Stack:** Python 3.10/3.11 + Flask + Flask-SQLAlchemy + Flask-Login + alembic + `google-generativeai` 0.8.6（`response_schema` / `system_instruction`）；Vue 3 `<script setup>` + TypeScript + Pinia + Vite。新增 `pytest` 作為 dev 依賴。

**Spec:** `docs/superpowers/specs/2026-07-31-field-mapping-design.md`

**修訂（2026-08-02）：** 本計畫初稿寫於資料庫遷移之前。已依現況修訂：`create_app()` 需要 `DATABASE_URL`、API 掛 `@login_required`、`Project.id` 是 `int`、`projectStore` 改為 API-backed、對映結果改存資料庫（Task 11 整個重寫）、聊天記錄沿用 `ResultView.vue` 的 localStorage 做法。

## Global Constraints

- **後端測試指令**：`uv run --group dev pytest tests/ -v`（從 `backend/` 執行，跑在 host 的 `.venv`，**不是**容器裡 —— 執行中的 backend 容器映像是舊的，沒有 pytest 也沒有 alembic）。本專案原本沒有測試框架，Task 1 會建立。
- **資料庫只在 Docker 裡**：`backend/.env` 的 `DATABASE_URL` 主機名是 `postgres`，從 host 解析不到。需要連資料庫的指令（只有 Task 11）要把主機名換成 `localhost`（容器有映射 5432），作法見該 task。**不要修改 `.env`** —— 容器裡的後端需要 `postgres` 這個名字。
- **`create_app()` 需要 `DATABASE_URL`**（沒設會在啟動時 raise）。Task 1~7 是純函式與純邏輯測試，不碰 app factory；只有 Task 8 的路由測試需要，作法見該 task。
- **`Project.id` 是 `int`**，不是字串。但 `useWorkflowStorage` 的各個函式參數是字串，呼叫時一律 `String(projectId)`。
- **新的 API 掛 `@login_required`**，與 `routes/project.py`、`routes/framework.py` 一致。
- **對映結果存資料庫**（`projects.column_mapping` JSONB），**聊天記錄存 localStorage**（沿用 `saveChatHistoryToStorage`，key 加 `mapping-` 前綴，與 `ResultView.vue` 的聊天區隔）。
- **`projectStore` 是 API-backed 的**：改 store 裡的 ref 不等於存檔，必須呼叫 API。
- **前端驗證指令**：`npm run build`（`vue-tsc` 型別檢查 + vite build），從 `frontend/` 執行。前端沒有自動測試，另需 `npm run dev` 手動操作驗證。
- **`npm run lint` 是既有壞基線**，不作為 gate；照現有檔案風格撰寫。
- **使用者可見文字、註解、文件一律繁體中文**。
- **不得修改既有論文分析邏輯**：`routes/gemini.py` 全檔、`gemini_service.py` 的 `analyze()` / `analyze_pdf()` / `_build_prompt()` / `_normalize_to_json()` / `_generation_config()` / `_fill_defaults()` / `_parse_response()` / `__init__()` 一行都不能動。`_safe_parse_json()` / `_usage_dict()` 可讀取沿用但不可改。
- **不得修改 ML 引擎**：`backend/services/workflow/`、`backend/services/model/`、`backend/routes/model.py` 不在本計畫範圍。
- **Commit**：使用者已於 2026-08-02 對**本計畫全部 task** 一次性授權，執行時不需再逐一詢問。commit 訊息一行、英文、不加 `Co-Authored-By` trailer，一個 task 一個 commit。**不可 `git push`** —— 授權範圍只到本機 commit。
- **狀態常數只有三個**：`AUTO_MATCHED`、`NEEDS_REVIEW`、`UNMATCHED`。前端另有一個 `SKIPPED`，後端永遠不產生也不接受。
- **信心度門檻**：`AUTO_THRESHOLD = 0.8`、`REVIEW_THRESHOLD = 0.5`、`SEMANTIC_SCORE_CAP = 0.79`。這三個數字在 Task 15 的真實資料驗證後可能上調，實作時務必定義成模組層級常數，不要散落在程式碼裡。

---

### Task 1: 測試基礎建設 + 欄位名正規化與字串比對

**Files:**
- Modify: `backend/pyproject.toml`（新增 dev dependency group）
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/services/field_mapping_service.py`
- Test: `backend/tests/test_field_mapping_service.py`

**Interfaces:**
- Produces: `normalize_field(name: str) -> str`、`exact_match(paper_var: str, user_columns: list[str]) -> str | None`、`fuzzy_match(paper_var: str, user_columns: list[str]) -> list[tuple[str, float]]`。Task 2、3 直接呼叫這三個函式。

- [ ] **Step 1: 新增 pytest dev 依賴**

Modify `backend/pyproject.toml`，在 `[build-system]` 區塊**之前**插入：

```toml
[dependency-groups]
dev = [
  "pytest",
]
```

- [ ] **Step 2: 建立測試目錄與 conftest**

Create `backend/tests/__init__.py` as an empty file.

Create `backend/tests/conftest.py` with exactly:

```python
"""讓測試可以直接 import backend 底下的模組（services.xxx、routes.xxx）。

backend/ 不是安裝成套件（pyproject 設了 package = false），所以
測試執行時要自己把 backend/ 加進 sys.path。
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
```

- [ ] **Step 3: 寫失敗的測試**

Create `backend/tests/test_field_mapping_service.py` with exactly:

```python
from services.field_mapping_service import exact_match, fuzzy_match, normalize_field


class TestNormalizeField:
    def test_lowercases_and_strips_whitespace(self):
        assert normalize_field(" Pt_Age ") == "ptage"

    def test_removes_tbl_prefix(self):
        assert normalize_field("tbl_user_name") == "username"

    def test_removes_col_prefix_and_dashes(self):
        assert normalize_field("col_BP-High") == "bphigh"

    def test_keeps_prefix_like_text_without_separator(self):
        # "tblname" 沒有分隔符號，tbl 是名字的一部分而非前綴，不可剝掉
        assert normalize_field("tblname") == "tblname"

    def test_empty_input(self):
        assert normalize_field("") == ""


class TestExactMatch:
    def test_finds_match_ignoring_formatting(self):
        assert exact_match("patient_age", ["PatientAge", "gender"]) == "PatientAge"

    def test_returns_none_when_no_match(self):
        assert exact_match("braden_score", ["age", "gender"]) is None

    def test_returns_original_column_name_not_normalized(self):
        assert exact_match("age", ["  Age  "]) == "  Age  "


class TestFuzzyMatch:
    def test_sorts_by_score_descending(self):
        scored = fuzzy_match("age", ["gender", "pt_age"])
        assert scored[0][0] == "pt_age"
        assert round(scored[0][1], 2) == 0.75

    def test_returns_every_column(self):
        scored = fuzzy_match("age", ["gender", "pt_age", "bp_sys"])
        assert len(scored) == 3

    def test_identical_name_scores_one(self):
        scored = fuzzy_match("age", ["age"])
        assert scored[0][1] == 1.0
```

- [ ] **Step 4: 執行測試確認失敗**

Run: `cd backend && uv sync --group dev && uv run --group dev pytest tests/test_field_mapping_service.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.field_mapping_service'`

- [ ] **Step 5: 實作最小程式碼**

Create `backend/services/field_mapping_service.py` with exactly:

```python
"""欄位對齊：把論文擷取出的變數對映到使用者資料表的欄位。

純函式模組，不依賴 Flask 也不依賴 Gemini，可以獨立測試。
Gemini 的語意補強在 services/gemini_service.py，合併規則在本檔的
merge_semantic_suggestions()。
"""

import re
from difflib import SequenceMatcher

AUTO_MATCHED = "AUTO_MATCHED"
NEEDS_REVIEW = "NEEDS_REVIEW"
UNMATCHED = "UNMATCHED"

# 門檻集中在這裡：真實資料驗證後若假陽性偏高，只調這幾個數字
AUTO_THRESHOLD = 0.8
REVIEW_THRESHOLD = 0.5

# 前綴要有分隔符號才算前綴，避免把 "tblname" 這種名字誤剝成 "name"
_PREFIX_RE = re.compile(r"^(?:tbl|col)[\s_-]+", re.IGNORECASE)
_SEPARATOR_RE = re.compile(r"[\s_-]+")


def normalize_field(name: str) -> str:
    """欄位名正規化：轉小寫 → 去 tbl_/col_ 前綴 → 去空白/底線/破折號。

    去前綴必須在去分隔符號之前，否則 "tbl_user_name" 會先被壓成
    "tblusername"，前綴就認不出來了。
    """
    if not name:
        return ""
    result = _PREFIX_RE.sub("", name.strip().lower())
    return _SEPARATOR_RE.sub("", result)


def exact_match(paper_var: str, user_columns: list[str]) -> str | None:
    """正規化後完全相同的第一個欄位，回傳原始欄位名；沒有則 None。"""
    target = normalize_field(paper_var)
    if not target:
        return None
    for column in user_columns:
        if normalize_field(column) == target:
            return column
    return None


def fuzzy_match(paper_var: str, user_columns: list[str]) -> list[tuple[str, float]]:
    """對每個欄位算字串相似度，依分數由高到低排序回傳。

    分數相同時維持輸入順序（Python 的 sort 是穩定排序），確保結果可重現。
    """
    target = normalize_field(paper_var)
    scored = [
        (column, SequenceMatcher(None, target, normalize_field(column)).ratio())
        for column in user_columns
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored
```

- [ ] **Step 6: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/test_field_mapping_service.py -v`

Expected: PASS，11 passed

- [ ] **Step 7: Commit（需先取得使用者確認）**

```bash
git add backend/pyproject.toml backend/uv.lock backend/tests/ backend/services/field_mapping_service.py
git commit -m "feat: add field name normalization and string matching for field mapping"
```

---

### Task 2: 樣本值型態推斷與信心度加減分

**Files:**
- Modify: `backend/services/field_mapping_service.py`
- Test: `backend/tests/test_field_mapping_service.py`

**Interfaces:**
- Consumes: 無（純新增函式）
- Produces: `infer_value_type(sample_values: list[str]) -> str | None`（回傳 `"date"` / `"numeric"` / `"text"` / `None`）、`boost_by_sample_values(score: float, required_type: str, sample_values: list[str]) -> float`。Task 3 呼叫 `boost_by_sample_values`。

- [ ] **Step 1: 寫失敗的測試**

Append to `backend/tests/test_field_mapping_service.py`:

```python
import pytest

from services.field_mapping_service import boost_by_sample_values, infer_value_type


class TestInferValueType:
    def test_detects_iso_date(self):
        assert infer_value_type(["2024-01-03", "2024-02-11", "2024-3-5"]) == "date"

    def test_detects_slash_date(self):
        assert infer_value_type(["2024/01/03", "2024/02/11"]) == "date"

    def test_detects_compact_date(self):
        assert infer_value_type(["20240103", "20240211"]) == "date"

    def test_detects_numeric(self):
        assert infer_value_type(["65", "72", "48.5"]) == "numeric"

    def test_detects_text(self):
        assert infer_value_type(["男", "女", "男"]) == "text"

    def test_ignores_empty_values(self):
        assert infer_value_type(["65", "", "  ", "72"]) == "numeric"

    def test_returns_none_when_no_usable_values(self):
        assert infer_value_type([]) is None
        assert infer_value_type(["", "  "]) is None

    def test_minority_mismatch_still_counts_as_numeric(self):
        # 4 筆數字 + 1 筆文字 = 80% >= 60%
        assert infer_value_type(["1", "2", "3", "4", "n/a"]) == "numeric"

    def test_below_threshold_falls_back_to_text(self):
        # 只有 40% 是數字，達不到 60% 門檻
        assert infer_value_type(["1", "2", "甲", "乙", "丙"]) == "text"


class TestBoostBySampleValues:
    def test_matching_type_adds_bonus(self):
        assert boost_by_sample_values(0.75, "numerical", ["65", "72"]) == pytest.approx(0.85)

    def test_mismatched_type_applies_penalty(self):
        assert boost_by_sample_values(0.75, "numerical", ["男", "女"]) == pytest.approx(0.55)

    def test_date_type_matches(self):
        assert boost_by_sample_values(0.6, "date", ["2024-01-03", "2024-02-11"]) == pytest.approx(0.7)

    def test_categorical_matches_text(self):
        assert boost_by_sample_values(0.6, "categorical", ["男", "女"]) == pytest.approx(0.7)

    def test_no_samples_leaves_score_unchanged(self):
        assert boost_by_sample_values(0.75, "numerical", []) == 0.75

    def test_unknown_required_type_leaves_score_unchanged(self):
        assert boost_by_sample_values(0.75, "mystery", ["65"]) == 0.75
        assert boost_by_sample_values(0.75, "", ["65"]) == 0.75

    def test_type_comparison_is_case_insensitive(self):
        assert boost_by_sample_values(0.75, "Numerical", ["65"]) == pytest.approx(0.85)

    def test_clamps_to_upper_bound(self):
        assert boost_by_sample_values(0.95, "numerical", ["65"]) == 1.0

    def test_clamps_to_lower_bound(self):
        assert boost_by_sample_values(0.1, "numerical", ["男"]) == 0.0
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_field_mapping_service.py -v`

Expected: FAIL with `ImportError: cannot import name 'infer_value_type'`

- [ ] **Step 3: 實作最小程式碼**

Append to `backend/services/field_mapping_service.py`:

```python
_TYPE_BONUS = 0.1
_TYPE_PENALTY = 0.2

# 非空樣本值中至少要有這個比例符合，才算是該型態
_TYPE_MAJORITY = 0.6

_DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),
    re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"),
    re.compile(r"^\d{8}$"),
)

# 論文變數的 type 字串 → 推斷型態。不在表內的一律視為無法判斷。
_TYPE_ALIASES = {
    "date": "date",
    "datetime": "date",
    "numerical": "numeric",
    "numeric": "numeric",
    "int": "numeric",
    "integer": "numeric",
    "float": "numeric",
    "continuous": "numeric",
    "categorical": "text",
    "category": "text",
    "string": "text",
    "text": "text",
    "nominal": "text",
}


def _is_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def infer_value_type(sample_values: list[str]) -> str | None:
    """從樣本值推斷欄位型態，無法判斷時回傳 None。

    日期先於數字判斷：YYYYMMDD 這種寫法同時符合兩者，但它是日期。
    """
    values = [str(value).strip() for value in sample_values or [] if str(value).strip()]
    if not values:
        return None

    threshold = len(values) * _TYPE_MAJORITY
    date_hits = sum(1 for value in values if any(p.match(value) for p in _DATE_PATTERNS))
    if date_hits >= threshold:
        return "date"

    numeric_hits = sum(1 for value in values if _is_numeric(value))
    if numeric_hits >= threshold:
        return "numeric"

    return "text"


def boost_by_sample_values(
    score: float,
    required_type: str,
    sample_values: list[str],
) -> float:
    """用樣本值的型態調整信心度。

    型態相符 +0.1、不符 -0.2、無法判斷不調整，結果 clamp 在 [0, 1]。
    不對稱是刻意的：型態不符是「這大概配錯了」的強訊號，
    型態相符只是「沒有反證」的弱訊號。
    """
    inferred = infer_value_type(sample_values)
    if inferred is None:
        return score

    expected = _TYPE_ALIASES.get((required_type or "").strip().lower())
    if expected is None:
        return score

    adjusted = score + _TYPE_BONUS if expected == inferred else score - _TYPE_PENALTY
    return max(0.0, min(1.0, adjusted))
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/test_field_mapping_service.py -v`

Expected: PASS，29 passed

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add backend/services/field_mapping_service.py backend/tests/test_field_mapping_service.py
git commit -m "feat: infer column type from sample values to adjust match confidence"
```

---

### Task 3: 組合自動對映 `run_auto_mapping()`

**Files:**
- Modify: `backend/services/field_mapping_service.py`
- Test: `backend/tests/test_run_auto_mapping.py`

**Interfaces:**
- Consumes: Task 1 的 `exact_match` / `fuzzy_match`、Task 2 的 `boost_by_sample_values`
- Produces:
  - `normalize_user_columns(user_columns: list) -> list[dict]` — 把字串或物件統一成 `{"name": str, "sample_values": list[str]}`，路由層與 Task 4 都會用
  - `run_auto_mapping(paper_variables: list[dict], user_columns: list[dict]) -> dict` — 回傳 `{"total_required": int, "matched_count": int, "mapping_status": [...]}`

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_run_auto_mapping.py` with exactly:

```python
from services.field_mapping_service import normalize_user_columns, run_auto_mapping


def find(result: dict, variable: str) -> dict:
    """從 mapping_status 取出指定變數那一筆。"""
    for item in result["mapping_status"]:
        if item["paper_variable"] == variable:
            return item
    raise AssertionError(f"{variable} 不在 mapping_status 裡")


class TestNormalizeUserColumns:
    def test_accepts_plain_strings(self):
        assert normalize_user_columns(["age"]) == [{"name": "age", "sample_values": []}]

    def test_accepts_objects(self):
        assert normalize_user_columns([{"name": "age", "sample_values": ["65"]}]) == [
            {"name": "age", "sample_values": ["65"]},
        ]

    def test_coerces_sample_values_to_strings(self):
        result = normalize_user_columns([{"name": "age", "sample_values": [65, None]}])
        assert result[0]["sample_values"] == ["65", "None"]

    def test_drops_nameless_columns(self):
        assert normalize_user_columns([{"name": "  "}, "age"]) == [
            {"name": "age", "sample_values": []},
        ]


class TestRunAutoMapping:
    def test_exact_match_is_auto_matched_with_full_confidence(self):
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "Age", "sample_values": ["65", "72"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "AUTO_MATCHED"
        assert item["matched_user_column"] == "Age"
        assert item["confidence_score"] == 1.0
        assert item["sample_values"] == ["65", "72"]
        assert item["candidate_columns"] == []

    def test_fuzzy_plus_type_bonus_reaches_auto_matched(self):
        # "age" vs "pt_age" = 0.75，型態相符 +0.1 → 0.85 >= 0.8
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "pt_age", "sample_values": ["65", "72"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "AUTO_MATCHED"
        assert item["matched_user_column"] == "pt_age"

    def test_type_mismatch_downgrades_to_needs_review(self):
        # 同樣是 0.75，但樣本值是文字、論文要數字 → 0.55，落在待確認區間
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "pt_age", "sample_values": ["甲", "乙"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "NEEDS_REVIEW"
        assert item["matched_user_column"] == "pt_age"

    def test_unrelated_name_is_unmatched_with_candidates(self):
        result = run_auto_mapping(
            [{"name": "braden_score", "type": "numerical"}],
            normalize_user_columns(["gender", "hospital_id"]),
        )
        item = find(result, "braden_score")
        assert item["status"] == "UNMATCHED"
        assert item["matched_user_column"] is None
        assert item["confidence_score"] == 0.0
        assert item["sample_values"] == []
        assert len(item["candidate_columns"]) <= 3
        assert set(item["candidate_columns"]) <= {"gender", "hospital_id"}

    def test_target_never_reaches_auto_matched(self):
        result = run_auto_mapping(
            [{"name": "outcome", "type": "categorical", "is_target": True}],
            normalize_user_columns(["outcome"]),
        )
        item = find(result, "outcome")
        assert item["status"] == "NEEDS_REVIEW"
        assert item["confidence_score"] == 1.0  # 分數照實回報，只有狀態被降級
        assert item["matched_user_column"] == "outcome"

    def test_one_column_cannot_serve_two_variables(self):
        result = run_auto_mapping(
            [{"name": "age", "type": ""}, {"name": "ageyears", "type": ""}],
            normalize_user_columns(["age"]),
        )
        assert find(result, "age")["matched_user_column"] == "age"
        loser = find(result, "ageyears")
        assert loser["matched_user_column"] is None
        assert loser["status"] == "UNMATCHED"
        assert loser["candidate_columns"] == ["age"]

    def test_target_wins_the_column_even_with_lower_score(self):
        # target "ageyears"(0.545) 比 "age"(1.0) 分數低，但 target 優先分配
        result = run_auto_mapping(
            [
                {"name": "age", "type": ""},
                {"name": "ageyears", "type": "", "is_target": True},
            ],
            normalize_user_columns(["age"]),
        )
        assert find(result, "ageyears")["matched_user_column"] == "age"
        assert find(result, "age")["matched_user_column"] is None

    def test_target_is_always_present_even_with_zero_confidence(self):
        result = run_auto_mapping(
            [{"name": "zzzz_nothing_alike", "type": "", "is_target": True}],
            normalize_user_columns(["age", "gender"]),
        )
        item = find(result, "zzzz_nothing_alike")
        assert item["status"] == "UNMATCHED"

    def test_counts(self):
        result = run_auto_mapping(
            [
                {"name": "age", "type": "numerical"},
                {"name": "note", "type": "", "required": False},
                {"name": "outcome", "type": "categorical", "is_target": True},
            ],
            normalize_user_columns([
                {"name": "age", "sample_values": ["65"]},
                {"name": "outcome", "sample_values": ["1", "0"]},
            ]),
        )
        assert result["total_required"] == 2   # note 不算，target 一律算
        assert result["matched_count"] == 1    # 只有 age；target 被降為待確認

    def test_output_keeps_input_order(self):
        result = run_auto_mapping(
            [{"name": "zzz", "type": ""}, {"name": "aaa", "type": ""}],
            normalize_user_columns(["aaa", "zzz"]),
        )
        assert [item["paper_variable"] for item in result["mapping_status"]] == ["zzz", "aaa"]

    def test_variables_without_name_are_dropped(self):
        result = run_auto_mapping(
            [{"name": "  ", "type": ""}, {"name": "age", "type": ""}],
            normalize_user_columns(["age"]),
        )
        assert len(result["mapping_status"]) == 1

    def test_empty_user_columns_marks_everything_unmatched(self):
        result = run_auto_mapping([{"name": "age", "type": "numerical"}], [])
        item = find(result, "age")
        assert item["status"] == "UNMATCHED"
        assert item["candidate_columns"] == []
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_run_auto_mapping.py -v`

Expected: FAIL with `ImportError: cannot import name 'normalize_user_columns'`

- [ ] **Step 3: 實作最小程式碼**

Append to `backend/services/field_mapping_service.py`:

```python
def normalize_user_columns(user_columns: list) -> list[dict]:
    """把使用者欄位統一成 {"name": str, "sample_values": list[str]}。

    只給字串的呼叫端（沒帶樣本值）也接受，不報錯 —— 樣本值只是輔助訊號，
    沒有它配對照樣能跑，只是準確率會差一點。
    """
    normalized: list[dict] = []
    for column in user_columns or []:
        if isinstance(column, str):
            name, samples = column.strip(), []
        elif isinstance(column, dict):
            name = str(column.get("name", "")).strip()
            samples = [str(value) for value in (column.get("sample_values") or [])]
        else:
            continue
        if not name:
            continue
        normalized.append({"name": name, "sample_values": samples})
    return normalized


def _status_for(score: float) -> str:
    if score >= AUTO_THRESHOLD:
        return AUTO_MATCHED
    if score >= REVIEW_THRESHOLD:
        return NEEDS_REVIEW
    return UNMATCHED


def _score_candidates(name: str, required_type: str, columns: list[dict]) -> list[tuple[str, float]]:
    """算出這個論文變數對每個欄位的分數，由高到低排序。

    正規化後完全相同的欄位直接給 1.0 且不做型態加減分：名稱完全一致已經是
    夠強的證據，不該被樣本值推翻（例如欄位真的叫 age、但裡面資料很髒）。
    """
    column_names = [column["name"] for column in columns]
    samples = {column["name"]: column["sample_values"] for column in columns}
    exact = exact_match(name, column_names)

    scored = []
    for column_name, ratio in fuzzy_match(name, column_names):
        if column_name == exact:
            scored.append((column_name, 1.0))
        else:
            scored.append((
                column_name,
                boost_by_sample_values(ratio, required_type, samples[column_name]),
            ))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def run_auto_mapping(paper_variables: list[dict], user_columns: list[dict]) -> dict:
    """字串比對 + 樣本值輔助的自動對映，產出初始對映狀態。"""
    columns = normalize_user_columns(user_columns)
    samples_by_name = {column["name"]: column["sample_values"] for column in columns}

    variables: list[dict] = []
    for raw in paper_variables or []:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        is_target = bool(raw.get("is_target", False))
        required_type = str(raw.get("type", "") or "")
        variables.append({
            "name": name,
            "type": required_type,
            "is_target": is_target,
            # target 一律視為必要，不管呼叫端傳什麼
            "required": True if is_target else bool(raw.get("required", True)),
            "candidates": _score_candidates(name, required_type, columns),
        })

    # target 先分配，確保它不會被其他變數搶走欄位；其餘依最佳分數由高到低
    order = sorted(
        variables,
        key=lambda item: (
            0 if item["is_target"] else 1,
            -(item["candidates"][0][1] if item["candidates"] else 0.0),
        ),
    )

    taken: set[str] = set()
    assignment: dict[str, tuple[str | None, float]] = {}
    for variable in order:
        chosen_name: str | None = None
        chosen_score = 0.0
        for column_name, score in variable["candidates"]:
            if score < REVIEW_THRESHOLD:
                break  # 已排序，後面只會更低
            if column_name in taken:
                continue
            chosen_name, chosen_score = column_name, score
            break
        if chosen_name is not None:
            taken.add(chosen_name)
        assignment[variable["name"]] = (chosen_name, chosen_score)

    mapping_status = []
    for variable in variables:  # 依輸入順序輸出，前端不需要再排
        matched, score = assignment[variable["name"]]
        if matched is None:
            status = UNMATCHED
            score = 0.0
        else:
            status = _status_for(score)
            if variable["is_target"] and status == AUTO_MATCHED:
                status = NEEDS_REVIEW  # target 一律人工確認
        mapping_status.append({
            "paper_variable": variable["name"],
            "required_type": variable["type"],
            "matched_user_column": matched,
            "confidence_score": round(score, 4),
            "status": status,
            "sample_values": samples_by_name.get(matched, []) if matched else [],
            "candidate_columns": (
                [name for name, _ in variable["candidates"][:3]]
                if status == UNMATCHED
                else []
            ),
        })

    return {
        "total_required": sum(1 for variable in variables if variable["required"]),
        "matched_count": sum(1 for item in mapping_status if item["status"] == AUTO_MATCHED),
        "mapping_status": mapping_status,
    }
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，全部通過（29 + 16 = 45 passed）

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add backend/services/field_mapping_service.py backend/tests/test_run_auto_mapping.py
git commit -m "feat: assemble auto field mapping with greedy one-to-one assignment"
```

---

### Task 4: 合併 Gemini 語意建議 `merge_semantic_suggestions()`

**Files:**
- Modify: `backend/services/field_mapping_service.py`
- Test: `backend/tests/test_merge_semantic_suggestions.py`

**Interfaces:**
- Consumes: Task 3 的 `run_auto_mapping` 輸出格式
- Produces: `merge_semantic_suggestions(result: dict, suggestions: list[dict], user_columns: list[dict]) -> dict`（原地修改並回傳 `result`）；常數 `SEMANTIC_SCORE_CAP = 0.79`

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_merge_semantic_suggestions.py` with exactly:

```python
from services.field_mapping_service import merge_semantic_suggestions


def build_result(items: list[dict]) -> dict:
    return {
        "total_required": len(items),
        "matched_count": sum(1 for item in items if item["status"] == "AUTO_MATCHED"),
        "mapping_status": items,
    }


def unmatched(variable: str, candidates: list[str] | None = None) -> dict:
    return {
        "paper_variable": variable,
        "required_type": "numerical",
        "matched_user_column": None,
        "confidence_score": 0.0,
        "status": "UNMATCHED",
        "sample_values": [],
        "candidate_columns": candidates or [],
    }


COLUMNS = [
    {"name": "braden_total", "sample_values": ["18", "14"]},
    {"name": "bp_sys", "sample_values": ["120", "134"]},
]


class TestMergeSemanticSuggestions:
    def test_suggestion_fills_column_as_needs_review(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 0.95, "candidate_columns": []}],
            COLUMNS,
        )
        item = result["mapping_status"][0]
        assert item["matched_user_column"] == "braden_total"
        assert item["status"] == "NEEDS_REVIEW"
        assert item["sample_values"] == ["18", "14"]
        assert item["candidate_columns"] == []

    def test_confidence_is_capped_below_auto_threshold(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 1.0, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["confidence_score"] == 0.79

    def test_never_overwrites_an_auto_matched_item(self):
        locked = {
            "paper_variable": "age", "required_type": "numerical",
            "matched_user_column": "pt_age", "confidence_score": 0.9,
            "status": "AUTO_MATCHED", "sample_values": ["65"], "candidate_columns": [],
        }
        result = build_result([locked])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "age", "matched_user_column": "bp_sys",
              "confidence_score": 0.99, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["matched_user_column"] == "pt_age"
        assert result["mapping_status"][0]["status"] == "AUTO_MATCHED"

    def test_taken_column_becomes_a_candidate_instead(self):
        taken = {
            "paper_variable": "systolic", "required_type": "numerical",
            "matched_user_column": "bp_sys", "confidence_score": 0.85,
            "status": "AUTO_MATCHED", "sample_values": [], "candidate_columns": [],
        }
        result = build_result([taken, unmatched("blood_pressure")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "blood_pressure", "matched_user_column": "bp_sys",
              "confidence_score": 0.9, "candidate_columns": []}],
            COLUMNS,
        )
        item = result["mapping_status"][1]
        assert item["matched_user_column"] is None
        assert item["candidate_columns"] == ["bp_sys"]

    def test_candidate_only_suggestion_merges_without_duplicates(self):
        result = build_result([unmatched("braden_score", ["bp_sys"])])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": None,
              "confidence_score": 0.0, "candidate_columns": ["bp_sys", "braden_total"]}],
            COLUMNS,
        )
        item = result["mapping_status"][0]
        assert item["candidate_columns"] == ["bp_sys", "braden_total"]
        assert item["status"] == "UNMATCHED"

    def test_candidate_list_is_capped_at_five(self):
        result = build_result([unmatched("x", ["a", "b", "c", "d"])])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "x", "matched_user_column": None,
              "confidence_score": 0.0, "candidate_columns": ["e", "f", "g"]}],
            [{"name": name, "sample_values": []} for name in "abcdefg"],
        )
        assert len(result["mapping_status"][0]["candidate_columns"]) == 5

    def test_unknown_variable_is_ignored(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "does_not_exist", "matched_user_column": "bp_sys",
              "confidence_score": 0.9, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["matched_user_column"] is None

    def test_matched_count_is_recomputed(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 0.95, "candidate_columns": []}],
            COLUMNS,
        )
        # AI 建議一律是待確認，不會讓 matched_count 增加
        assert result["matched_count"] == 0

    def test_empty_suggestions_is_a_noop(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(result, [], COLUMNS)
        assert result["mapping_status"][0]["status"] == "UNMATCHED"
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_merge_semantic_suggestions.py -v`

Expected: FAIL with `ImportError: cannot import name 'merge_semantic_suggestions'`

- [ ] **Step 3: 實作最小程式碼**

在 `backend/services/field_mapping_service.py` 的常數區塊（`REVIEW_THRESHOLD = 0.5` 那一行後面）加上：

```python
# AI 語意建議的信心度上限：刻意壓在 AUTO_THRESHOLD 之下，
# 讓綠勾勾只保留給演算法層有把握的配對
SEMANTIC_SCORE_CAP = 0.79
_MAX_CANDIDATES = 5
```

Append to `backend/services/field_mapping_service.py`:

```python
def merge_semantic_suggestions(
    result: dict,
    suggestions: list[dict],
    user_columns: list[dict],
) -> dict:
    """把 Gemini 的語意建議併回 run_auto_mapping() 的結果（原地修改並回傳）。

    只影響非 AUTO_MATCHED 的項目：演算法層已經有把握的配對不容 AI 推翻。
    AI 建議產生的配對一律標成 NEEDS_REVIEW、信心度上限 SEMANTIC_SCORE_CAP，
    確保使用者一定會親眼確認過。
    """
    samples_by_name = {column["name"]: column["sample_values"] for column in user_columns}
    by_variable = {item["paper_variable"]: item for item in result["mapping_status"]}
    taken = {
        item["matched_user_column"]
        for item in result["mapping_status"]
        if item["matched_user_column"]
    }

    for suggestion in suggestions or []:
        item = by_variable.get(suggestion.get("paper_variable"))
        if item is None or item["status"] == AUTO_MATCHED:
            continue

        column = suggestion.get("matched_user_column")
        extra = list(suggestion.get("candidate_columns") or [])

        if column and column not in taken:
            item["matched_user_column"] = column
            item["confidence_score"] = min(
                float(suggestion.get("confidence_score") or 0.0),
                SEMANTIC_SCORE_CAP,
            )
            item["status"] = NEEDS_REVIEW
            item["sample_values"] = samples_by_name.get(column, [])
            item["candidate_columns"] = []
            taken.add(column)
            continue

        if column:
            extra.append(column)  # 欄位已被佔用 → 降格為候選，讓使用者自己決定要不要搶
        merged = list(item["candidate_columns"])
        for name in extra:
            if name not in merged:
                merged.append(name)
        item["candidate_columns"] = merged[:_MAX_CANDIDATES]

    result["matched_count"] = sum(
        1 for item in result["mapping_status"] if item["status"] == AUTO_MATCHED
    )
    return result
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，54 passed

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add backend/services/field_mapping_service.py backend/tests/test_merge_semantic_suggestions.py
git commit -m "feat: merge Gemini semantic suggestions into auto mapping result"
```

---

### Task 5: Prompt 與 response schema 模組

**Files:**
- Create: `backend/services/field_mapping_prompts.py`
- Test: `backend/tests/test_field_mapping_prompts.py`

**Interfaces:**
- Produces:
  - `FIELD_MAPPING_SYSTEM_INSTRUCTION: str`
  - `SEMANTIC_MATCH_SCHEMA: dict`、`CHAT_REFINE_SCHEMA: dict`
  - `build_semantic_match_prompt(items: list[dict], user_columns: list[dict]) -> str`
  - `build_chat_refine_prompt(mapping_status: list[dict], user_columns: list[dict], chat_history: list, user_message: str) -> str`
  - `MAX_CHAT_HISTORY = 10`、`MAX_CHAT_ACTIONS = 10`

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_field_mapping_prompts.py` with exactly:

```python
from services.field_mapping_prompts import (
    CHAT_REFINE_SCHEMA,
    MAX_CHAT_HISTORY,
    SEMANTIC_MATCH_SCHEMA,
    build_chat_refine_prompt,
    build_semantic_match_prompt,
)

COLUMNS = [
    {"name": "pt_age", "sample_values": ["65", "72"]},
    {"name": "braden_total", "sample_values": ["18"]},
]


class TestSchemas:
    def test_semantic_schema_wraps_array_in_object(self):
        # 包成物件而非裸陣列，_safe_parse_json 的大括號 fallback 才抓得到
        assert SEMANTIC_MATCH_SCHEMA["type"] == "object"
        assert SEMANTIC_MATCH_SCHEMA["properties"]["matches"]["type"] == "array"

    def test_chat_schema_restricts_status_values(self):
        status = CHAT_REFINE_SCHEMA["properties"]["actions"]["items"]["properties"]["status"]
        assert status["enum"] == ["AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"]

    def test_chat_schema_requires_reply(self):
        assert "reply" in CHAT_REFINE_SCHEMA["required"]


class TestBuildSemanticMatchPrompt:
    def test_includes_every_column_and_its_samples(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "braden_score", "required_type": "numerical"}],
            COLUMNS,
        )
        assert "pt_age" in prompt
        assert "65, 72" in prompt
        assert "braden_total" in prompt

    def test_includes_pending_variable_and_its_type(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "braden_score", "required_type": "numerical"}],
            COLUMNS,
        )
        assert "braden_score" in prompt
        assert "numerical" in prompt

    def test_handles_column_without_samples(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "x", "required_type": ""}],
            [{"name": "lonely", "sample_values": []}],
        )
        assert "lonely" in prompt
        assert "（無樣本值）" in prompt


class TestBuildChatRefinePrompt:
    def test_includes_current_state_and_user_message(self):
        prompt = build_chat_refine_prompt(
            [{"paper_variable": "braden_score", "matched_user_column": None,
              "status": "UNMATCHED", "required_type": "numerical"}],
            COLUMNS,
            [],
            "braden 分數是 braden_total",
        )
        assert "braden_score" in prompt
        assert "braden 分數是 braden_total" in prompt

    def test_truncates_chat_history(self):
        history = [{"role": "user", "content": f"訊息{i}"} for i in range(20)]
        prompt = build_chat_refine_prompt([], COLUMNS, history, "最後一句")
        assert "訊息19" in prompt
        assert "訊息0" not in prompt
        assert prompt.count("使用者：") <= MAX_CHAT_HISTORY + 1

    def test_empty_history_does_not_break(self):
        prompt = build_chat_refine_prompt([], COLUMNS, [], "你好")
        assert "（尚無對話）" in prompt
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_field_mapping_prompts.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.field_mapping_prompts'`

- [ ] **Step 3: 實作最小程式碼**

Create `backend/services/field_mapping_prompts.py` with exactly:

```python
"""欄位對齊功能給 Gemini 的 prompt 與 response schema。

跟論文分析的 prompt 分開放：兩者互不相干，混在同一個檔案裡調整
其中一邊的措辭很容易誤傷另一邊。
"""

MAX_CHAT_HISTORY = 10
MAX_CHAT_ACTIONS = 10

FIELD_MAPPING_SYSTEM_INSTRUCTION = """你是資料欄位對映助手。
使用者有一份資料表，另有一篇論文要求的變數清單，你的工作是判斷
每個「論文變數」對應到使用者資料表的哪一個欄位。

【絕對規則】
1. 只輸出 JSON 本體，不得包含 markdown、程式碼區塊或任何說明文字。
2. 欄位名稱只能從使用者提供的欄位清單中挑選，絕不可自行創造或改寫名稱。
3. 不確定時寧可回報 null 與候選清單，也不要勉強配對。
4. 只回報你被要求處理的項目，不要擅自更動其他項目。

【判斷依據】
- 語意同義：sex 與 gender、dob 與 date_of_birth、bp_sys 與 systolic_bp 是同一件事
- 醫療常見縮寫：pt = patient、adm = admission、dx = diagnosis、hr = heart rate、
  bp = blood pressure、wbc = white blood cell、los = length of stay
- 樣本值型態：論文變數需要數值，而該欄位的樣本值是文字時，
  即使名稱相似也要降低信心度
- 論文變數的型態與欄位樣本值明顯不符時，寧可回報 null"""


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
                "required": [
                    "paper_variable",
                    "matched_user_column",
                    "confidence_score",
                    "candidate_columns",
                ],
            },
        },
    },
    "required": ["matches"],
}


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
                    "status": {
                        "type": "string",
                        "enum": ["AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"],
                    },
                    "confidence_score": {"type": "number"},
                },
                "required": [
                    "paper_variable",
                    "matched_user_column",
                    "status",
                    "confidence_score",
                ],
            },
        },
        "reply": {"type": "string"},
    },
    "required": ["actions", "reply"],
}


def _format_columns(user_columns: list[dict]) -> str:
    if not user_columns:
        return "（無欄位）"
    lines = []
    for column in user_columns:
        samples = column.get("sample_values") or []
        preview = ", ".join(str(value) for value in samples[:5]) if samples else "（無樣本值）"
        lines.append(f"- {column['name']}（樣本值：{preview}）")
    return "\n".join(lines)


def _format_pending(items: list[dict]) -> str:
    if not items:
        return "（無待配對項目）"
    lines = []
    for item in items:
        required_type = item.get("required_type") or "未指定"
        lines.append(f"- {item['paper_variable']}（需要型態：{required_type}）")
    return "\n".join(lines)


def _format_mapping_status(mapping_status: list[dict]) -> str:
    if not mapping_status:
        return "（無對映項目）"
    lines = []
    for item in mapping_status:
        matched = item.get("matched_user_column") or "（未對應）"
        lines.append(
            f"- {item['paper_variable']}"
            f"（型態：{item.get('required_type') or '未指定'}）"
            f" → {matched}　狀態：{item.get('status')}"
        )
    return "\n".join(lines)


def _format_history(chat_history: list) -> str:
    recent = (chat_history or [])[-MAX_CHAT_HISTORY:]
    if not recent:
        return "（尚無對話）"
    lines = []
    for message in recent:
        role = "使用者" if message.get("role") == "user" else "助理"
        lines.append(f"{role}：{message.get('content', '')}")
    return "\n".join(lines)


def build_semantic_match_prompt(items: list[dict], user_columns: list[dict]) -> str:
    """語意配對的請求 prompt（角色與規則已在 system_instruction 中）。"""
    return (
        "請為下列每一個論文變數，從使用者欄位清單中找出對應的欄位。\n\n"
        "【輸出規則】\n"
        "1. matched_user_column 只能是下方欄位清單中出現過的名稱，或 null。\n"
        "2. 不確定時 matched_user_column 填 null，並在 candidate_columns 列出 1~3 個可能欄位。\n"
        "3. 完全找不到合理對應時，matched_user_column 填 null、candidate_columns 填空陣列。\n"
        "4. confidence_score 是 0.0 到 1.0 的數值，代表你的把握程度。\n"
        "5. 每一個待配對的論文變數都必須有一筆輸出，不可遺漏。\n\n"
        "【使用者欄位清單】\n"
        f"{_format_columns(user_columns)}\n\n"
        "【待配對的論文變數】\n"
        f"{_format_pending(items)}\n\n"
        "【輸出格式】\n"
        '{"matches": [\n'
        '  {"paper_variable": "systolic_bp", "matched_user_column": "bp_sys",\n'
        '   "confidence_score": 0.85, "candidate_columns": []},\n'
        '  {"paper_variable": "braden_score", "matched_user_column": null,\n'
        '   "confidence_score": 0.0, "candidate_columns": ["braden_total"]}\n'
        "]}"
    )


def build_chat_refine_prompt(
    mapping_status: list[dict],
    user_columns: list[dict],
    chat_history: list,
    user_message: str,
) -> str:
    """對話式修正的請求 prompt。只要求輸出這一輪的變動，不要整包狀態。"""
    return (
        "使用者正在檢視論文變數與資料表欄位的對應關係，並用自然語言要求修改。\n"
        "請依使用者這次的訊息，輸出「這一輪要改變的項目」。\n\n"
        "【輸出規則】\n"
        "1. actions 只列出這一輪要改變的項目，不要輸出完整的對映清單。\n"
        "2. 使用者沒有提到的變數，一律不要放進 actions。\n"
        "3. matched_user_column 只能是下方欄位清單中出現過的名稱，"
        "或 null 表示解除對應。\n"
        "4. paper_variable 只能是下方「目前對映狀態」中已存在的變數名稱。\n"
        "5. 由你的建議所產生的對應，status 一律填 NEEDS_REVIEW，"
        "不可填 AUTO_MATCHED。\n"
        f"6. actions 最多 {MAX_CHAT_ACTIONS} 筆。若使用者的要求會影響更多項目，"
        "請不要輸出 actions，改在 reply 中請他說得更具體。\n"
        "7. reply 用繁體中文簡短說明你做了什麼。若有無法執行的要求"
        "（例如他指定的欄位不存在），必須在 reply 中說明原因。\n"
        "8. 使用者只是提問而沒有要求修改時，actions 填空陣列，只在 reply 中回答。\n\n"
        "【目前對映狀態】\n"
        f"{_format_mapping_status(mapping_status)}\n\n"
        "【使用者欄位清單】\n"
        f"{_format_columns(user_columns)}\n\n"
        "【對話記錄】\n"
        f"{_format_history(chat_history)}\n\n"
        "【使用者這次的訊息】\n"
        f"{user_message}\n\n"
        "【輸出格式】\n"
        "{\n"
        '  "actions": [\n'
        '    {"paper_variable": "braden_score", "matched_user_column": "braden_total",\n'
        '     "status": "NEEDS_REVIEW", "confidence_score": 0.9}\n'
        "  ],\n"
        '  "reply": "已把 braden_score 對應到 braden_total，請確認。"\n'
        "}"
    )
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，65 passed

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add backend/services/field_mapping_prompts.py backend/tests/test_field_mapping_prompts.py
git commit -m "feat: add field mapping prompts and Gemini response schemas"
```

---

### Task 6: `GeminiService.semantic_match()`

**Files:**
- Modify: `backend/services/gemini_service.py`（只在檔尾的 `GeminiService` 類別內新增，既有方法一行不動）
- Test: `backend/tests/test_gemini_field_mapping.py`

**Interfaces:**
- Consumes: Task 5 的 `FIELD_MAPPING_SYSTEM_INSTRUCTION` / `SEMANTIC_MATCH_SCHEMA` / `build_semantic_match_prompt`
- Produces: `GeminiService.semantic_match(items: list[dict], user_columns: list[dict]) -> list[dict] | None`。回傳 `[]` = AI 可用但無建議；`None` = AI 不可用。Task 8 的路由用這個區別決定 `ai_available`。
  另產生兩個共用的 static helper：`GeminiService._valid_score(value) -> float | None`、`GeminiService._sanitize_columns(values, allowed, limit) -> list[str]`，Task 7 會用到。

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_gemini_field_mapping.py` with exactly:

```python
"""semantic_match 的白名單驗證測試。

不連網：用假的 response 物件直接餵給已建構好的 GeminiService 實例，
所以不需要 GEMINI_API_KEY，也不會產生任何 API 費用。
"""

import pytest

from services.gemini_service import GeminiService

COLUMNS = [
    {"name": "braden_total", "sample_values": ["18"]},
    {"name": "bp_sys", "sample_values": ["120"]},
]

ITEMS = [{"paper_variable": "braden_score", "required_type": "numerical"}]


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeModel:
    """假的 GenerativeModel：回傳預設好的字串，或拋出指定的例外。"""

    def __init__(self, text: str = "", error: Exception | None = None):
        self._text = text
        self._error = error
        self.calls = 0

    def generate_content(self, *args, **kwargs):
        self.calls += 1
        if self._error:
            raise self._error
        return FakeResponse(self._text)


@pytest.fixture
def service(monkeypatch):
    """繞過 __init__ 的 API key 檢查，直接生出一個可用的實例。"""
    instance = GeminiService.__new__(GeminiService)
    instance.model_name = "gemini-2.5-flash"
    return instance


def patch_model(service, monkeypatch, fake: FakeModel):
    monkeypatch.setattr(service, "_field_mapping_model", lambda: fake, raising=False)


class TestValidScore:
    def test_accepts_values_in_range(self):
        assert GeminiService._valid_score(0.0) == 0.0
        assert GeminiService._valid_score(1) == 1.0
        assert GeminiService._valid_score(0.85) == 0.85

    def test_rejects_out_of_range(self):
        assert GeminiService._valid_score(1.5) is None
        assert GeminiService._valid_score(-0.1) is None

    def test_rejects_non_numbers(self):
        assert GeminiService._valid_score("0.9") is None
        assert GeminiService._valid_score(None) is None
        assert GeminiService._valid_score(True) is None


class TestSanitizeColumns:
    def test_keeps_only_known_columns(self):
        assert GeminiService._sanitize_columns(
            ["bp_sys", "ghost"], {"bp_sys"}, 3
        ) == ["bp_sys"]

    def test_deduplicates_and_respects_limit(self):
        assert GeminiService._sanitize_columns(
            ["a", "a", "b", "c"], {"a", "b", "c"}, 2
        ) == ["a", "b"]

    def test_handles_none(self):
        assert GeminiService._sanitize_columns(None, {"a"}, 3) == []


class TestSemanticMatch:
    def test_empty_items_skips_the_api_call(self, service, monkeypatch):
        fake = FakeModel('{"matches": []}')
        patch_model(service, monkeypatch, fake)
        assert service.semantic_match([], COLUMNS) == []
        assert fake.calls == 0

    def test_parses_clean_json(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": "braden_total",'
            ' "confidence_score": 0.9, "candidate_columns": []}]}'
        ))
        result = service.semantic_match(ITEMS, COLUMNS)
        assert result == [{
            "paper_variable": "braden_score",
            "matched_user_column": "braden_total",
            "confidence_score": 0.9,
            "candidate_columns": [],
        }]

    def test_parses_markdown_wrapped_json(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '```json\n{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": "braden_total",'
            ' "confidence_score": 0.9, "candidate_columns": []}]}\n```'
        ))
        assert len(service.semantic_match(ITEMS, COLUMNS)) == 1

    def test_parses_json_with_leading_chatter(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '好的！以下是結果：{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": "braden_total",'
            ' "confidence_score": 0.9, "candidate_columns": []}]}'
        ))
        assert len(service.semantic_match(ITEMS, COLUMNS)) == 1

    def test_drops_hallucinated_column(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": "查無此欄",'
            ' "confidence_score": 0.9, "candidate_columns": []}]}'
        ))
        result = service.semantic_match(ITEMS, COLUMNS)
        assert result[0]["matched_user_column"] is None

    def test_drops_unknown_variable(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"matches": [{"paper_variable": "從未要求的變數",'
            ' "matched_user_column": "bp_sys",'
            ' "confidence_score": 0.9, "candidate_columns": []}]}'
        ))
        assert service.semantic_match(ITEMS, COLUMNS) == []

    def test_drops_out_of_range_score(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": "braden_total",'
            ' "confidence_score": 3.7, "candidate_columns": []}]}'
        ))
        assert service.semantic_match(ITEMS, COLUMNS) == []

    def test_filters_candidate_columns(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"matches": [{"paper_variable": "braden_score",'
            ' "matched_user_column": null, "confidence_score": 0.0,'
            ' "candidate_columns": ["braden_total", "幽靈欄位"]}]}'
        ))
        result = service.semantic_match(ITEMS, COLUMNS)
        assert result[0]["candidate_columns"] == ["braden_total"]

    def test_unparseable_response_returns_none(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel("抱歉，我無法判斷"))
        assert service.semantic_match(ITEMS, COLUMNS) is None

    def test_empty_response_returns_none(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(""))
        assert service.semantic_match(ITEMS, COLUMNS) is None

    def test_api_error_returns_none(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(error=RuntimeError("timeout")))
        assert service.semantic_match(ITEMS, COLUMNS) is None
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_gemini_field_mapping.py -v`

Expected: FAIL with `AttributeError: type object 'GeminiService' has no attribute '_valid_score'`

- [ ] **Step 3: 實作最小程式碼**

在 `backend/services/gemini_service.py` 頂端的 import 區塊（`import google.generativeai as genai` 之後）加上：

```python
from services.field_mapping_prompts import (
    FIELD_MAPPING_SYSTEM_INSTRUCTION,
    SEMANTIC_MATCH_SCHEMA,
    build_semantic_match_prompt,
)
```

在 `GeminiService` 類別的**最後**（`analyze_pdf()` 方法之後、模組層級的 `def truncate_content` 之前）加上：

```python
    # ── Field mapping（欄位對齊）─────────────────────────────────────────────
    #
    # 以下方法與上面的論文分析完全獨立：另建 model 實例、另一組 generation
    # config，不共用 self.model 也不共用 _generation_config()。

    _VALID_STATUSES = {"AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"}

    def _field_mapping_model(self) -> genai.GenerativeModel:
        """欄位對齊專用的 model 實例。

        每次呼叫都重新建構：GenerativeModel 只是本地物件，不會發出網路請求，
        這樣就不必動到 __init__（既有論文分析邏輯必須零修改）。
        """
        return genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=FIELD_MAPPING_SYSTEM_INSTRUCTION,
        )

    @staticmethod
    def _field_mapping_config(schema: dict, max_output_tokens: int) -> genai.GenerationConfig:
        """配對是判斷題，temperature 設 0；格式交給 response_schema 強制。"""
        return genai.GenerationConfig(
            temperature=0,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )

    @staticmethod
    def _valid_score(value) -> Optional[float]:
        """信心度必須是 0~1 的數值，否則視為無效。

        bool 是 int 的子類別，得先擋掉，不然 True 會被當成 1.0。
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        score = float(value)
        if score < 0.0 or score > 1.0:
            return None
        return score

    @staticmethod
    def _sanitize_columns(values, allowed: set, limit: int) -> list:
        """只保留白名單內、且不重複的欄位名，最多 limit 個。"""
        result: list = []
        for value in values or []:
            if isinstance(value, str) and value in allowed and value not in result:
                result.append(value)
            if len(result) >= limit:
                break
        return result

    def semantic_match(self, items: list, user_columns: list) -> Optional[list]:
        """對演算法配不出來的項目做語意配對建議。

        回傳 [] 代表「AI 可用但沒有有效建議」，回傳 None 代表「AI 不可用」——
        路由層靠這個區別決定要不要在前端顯示「AI 建議暫時無法使用」。
        """
        if not items:
            return []

        prompt = build_semantic_match_prompt(items, user_columns)
        try:
            response = self._field_mapping_model().generate_content(
                prompt,
                generation_config=self._field_mapping_config(SEMANTIC_MATCH_SCHEMA, 4096),
            )
        except Exception:
            logger.exception("semantic_match 呼叫 Gemini 失敗")
            return None

        parsed = self._safe_parse_json(getattr(response, "text", "") or "")
        if not isinstance(parsed, dict):
            logger.warning("semantic_match 回應無法解析為 JSON 物件")
            return None

        allowed_columns = {column["name"] for column in user_columns}
        allowed_variables = {item["paper_variable"] for item in items}

        results = []
        for entry in parsed.get("matches") or []:
            if not isinstance(entry, dict):
                continue
            variable = entry.get("paper_variable")
            if variable not in allowed_variables:
                continue
            score = self._valid_score(entry.get("confidence_score"))
            if score is None:
                continue
            column = entry.get("matched_user_column")
            if column not in allowed_columns:
                column = None  # 掰出來的欄位名 → 當作沒配到，其餘欄位照收
            results.append({
                "paper_variable": variable,
                "matched_user_column": column,
                "confidence_score": score,
                "candidate_columns": self._sanitize_columns(
                    entry.get("candidate_columns"), allowed_columns, 3
                ),
            })
        return results
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，86 passed

- [ ] **Step 5: 確認既有論文分析邏輯沒被動到**

Run: `cd backend && git diff --stat services/gemini_service.py && git diff services/gemini_service.py | grep '^-' | grep -v '^---'`

Expected: 只有新增行（`+`），沒有任何刪除行（`-`）輸出

- [ ] **Step 6: Commit（需先取得使用者確認）**

```bash
git add backend/services/gemini_service.py backend/tests/test_gemini_field_mapping.py
git commit -m "feat: add semantic_match to GeminiService with whitelist validation"
```

---

### Task 7: `GeminiService.chat_refine()`

**Files:**
- Modify: `backend/services/gemini_service.py`
- Test: `backend/tests/test_gemini_chat_refine.py`

**Interfaces:**
- Consumes: Task 5 的 `CHAT_REFINE_SCHEMA` / `build_chat_refine_prompt` / `MAX_CHAT_ACTIONS`、Task 6 的 `_field_mapping_model` / `_field_mapping_config` / `_valid_score` / `_VALID_STATUSES`
- Produces: `GeminiService.chat_refine(current_mapping_state: dict, user_message: str, chat_history: list) -> dict`，回傳 `{"actions": [...], "reply": str}`。`current_mapping_state` 形狀為 `{"mapping_status": [...], "user_columns": [{"name", "sample_values"}]}`。

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_gemini_chat_refine.py` with exactly:

```python
"""chat_refine 的白名單驗證測試（不連網、不需要 API key）。"""

import pytest

from services.gemini_service import GeminiService

STATE = {
    "mapping_status": [
        {"paper_variable": "braden_score", "required_type": "numerical",
         "matched_user_column": None, "status": "UNMATCHED"},
        {"paper_variable": "age", "required_type": "numerical",
         "matched_user_column": "pt_age", "status": "AUTO_MATCHED"},
    ],
    "user_columns": [
        {"name": "braden_total", "sample_values": ["18"]},
        {"name": "pt_age", "sample_values": ["65"]},
    ],
}


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeModel:
    def __init__(self, text: str = "", error: Exception | None = None):
        self._text = text
        self._error = error

    def generate_content(self, *args, **kwargs):
        if self._error:
            raise self._error
        return FakeResponse(self._text)


@pytest.fixture
def service():
    instance = GeminiService.__new__(GeminiService)
    instance.model_name = "gemini-2.5-flash"
    return instance


def patch_model(service, monkeypatch, fake: FakeModel):
    monkeypatch.setattr(service, "_field_mapping_model", lambda: fake, raising=False)


def action(**overrides) -> str:
    import json
    base = {
        "paper_variable": "braden_score",
        "matched_user_column": "braden_total",
        "status": "NEEDS_REVIEW",
        "confidence_score": 0.9,
    }
    base.update(overrides)
    return json.dumps({"actions": [base], "reply": "已更新"}, ensure_ascii=False)


class TestChatRefine:
    def test_accepts_a_valid_action(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(action()))
        result = service.chat_refine(STATE, "braden 分數是 braden_total", [])
        assert result["actions"] == [{
            "paper_variable": "braden_score",
            "matched_user_column": "braden_total",
            "status": "NEEDS_REVIEW",
            "confidence_score": 0.9,
        }]
        assert result["reply"] == "已更新"

    def test_accepts_null_column_as_unmapping(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            action(matched_user_column=None, status="UNMATCHED", confidence_score=0.0)
        ))
        result = service.chat_refine(STATE, "把 braden_score 的對應拿掉", [])
        assert result["actions"][0]["matched_user_column"] is None

    def test_drops_action_with_unknown_column(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(action(matched_user_column="幽靈欄位")))
        assert service.chat_refine(STATE, "隨便", [])["actions"] == []

    def test_drops_action_with_unknown_variable(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(action(paper_variable="不存在的變數")))
        assert service.chat_refine(STATE, "隨便", [])["actions"] == []

    def test_drops_action_with_invalid_status(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(action(status="MAYBE")))
        assert service.chat_refine(STATE, "隨便", [])["actions"] == []

    def test_drops_action_with_invalid_score(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(action(confidence_score=9)))
        assert service.chat_refine(STATE, "隨便", [])["actions"] == []

    def test_rejects_the_whole_batch_when_too_many_actions(self, service, monkeypatch):
        import json
        actions = [
            {"paper_variable": "braden_score", "matched_user_column": "braden_total",
             "status": "NEEDS_REVIEW", "confidence_score": 0.9}
            for _ in range(11)
        ]
        patch_model(service, monkeypatch, FakeModel(
            json.dumps({"actions": actions, "reply": "全改了"}, ensure_ascii=False)
        ))
        result = service.chat_refine(STATE, "隨便改", [])
        assert result["actions"] == []
        assert "具體" in result["reply"]

    def test_question_without_changes_returns_reply_only(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"actions": [], "reply": "因為 sex 和 gender 是同義詞。"}'
        ))
        result = service.chat_refine(STATE, "為什麼這樣配？", [])
        assert result["actions"] == []
        assert result["reply"] == "因為 sex 和 gender 是同義詞。"

    def test_unparseable_response_degrades_gracefully(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel("我不知道"))
        result = service.chat_refine(STATE, "隨便", [])
        assert result["actions"] == []
        assert result["reply"]

    def test_api_error_degrades_gracefully(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(error=RuntimeError("timeout")))
        result = service.chat_refine(STATE, "隨便", [])
        assert result["actions"] == []
        assert result["reply"]

    def test_blank_reply_falls_back_to_default_text(self, service, monkeypatch):
        patch_model(service, monkeypatch, FakeModel(
            '{"actions": [], "reply": "   "}'
        ))
        assert service.chat_refine(STATE, "隨便", [])["reply"].strip()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_gemini_chat_refine.py -v`

Expected: FAIL with `AttributeError: 'GeminiService' object has no attribute 'chat_refine'`

- [ ] **Step 3: 實作最小程式碼**

把 `backend/services/gemini_service.py` 頂端的 field mapping import 改成（新增三個名稱）：

```python
from services.field_mapping_prompts import (
    CHAT_REFINE_SCHEMA,
    FIELD_MAPPING_SYSTEM_INSTRUCTION,
    MAX_CHAT_ACTIONS,
    SEMANTIC_MATCH_SCHEMA,
    build_chat_refine_prompt,
    build_semantic_match_prompt,
)
```

在 `GeminiService.semantic_match()` 之後加上：

```python
    def chat_refine(
        self,
        current_mapping_state: dict,
        user_message: str,
        chat_history: list,
    ) -> dict:
        """依使用者的自然語言指令，產出這一輪的對映變更 diff。

        current_mapping_state 形狀：
          {"mapping_status": [...], "user_columns": [{"name", "sample_values"}]}

        永遠回傳可用的結果，不拋例外 —— 聊天壞掉時使用者還有下拉選單可用，
        不該讓整頁跟著掛掉。
        """
        mapping_status = current_mapping_state.get("mapping_status") or []
        user_columns = current_mapping_state.get("user_columns") or []

        prompt = build_chat_refine_prompt(
            mapping_status, user_columns, chat_history, user_message
        )
        try:
            response = self._field_mapping_model().generate_content(
                prompt,
                generation_config=self._field_mapping_config(CHAT_REFINE_SCHEMA, 2048),
            )
        except Exception:
            logger.exception("chat_refine 呼叫 Gemini 失敗")
            return {
                "actions": [],
                "reply": "AI 目前無法回應，請改用下拉選單手動對應。",
            }

        parsed = self._safe_parse_json(getattr(response, "text", "") or "")
        if not isinstance(parsed, dict):
            logger.warning("chat_refine 回應無法解析為 JSON 物件")
            return {
                "actions": [],
                "reply": "AI 的回覆格式無法解析，請換個說法再試一次，或改用下拉選單。",
            }

        raw_actions = parsed.get("actions") or []
        if len(raw_actions) > MAX_CHAT_ACTIONS:
            # 一次要改這麼多筆，多半是模型誤解了指令範圍。整批拒絕比部分套用安全。
            return {
                "actions": [],
                "reply": (
                    f"這個要求會一次更動 {len(raw_actions)} 個欄位，超出單次修改上限，"
                    "已暫停套用。請說得更具體一點，例如指名要改哪一個變數。"
                ),
            }

        allowed_columns = {
            column.get("name") for column in user_columns if isinstance(column, dict)
        }
        allowed_variables = {
            item.get("paper_variable") for item in mapping_status if isinstance(item, dict)
        }

        actions = []
        for entry in raw_actions:
            if not isinstance(entry, dict):
                continue
            variable = entry.get("paper_variable")
            if variable not in allowed_variables:
                continue
            column = entry.get("matched_user_column")
            if column is not None and column not in allowed_columns:
                continue  # 欄位不存在 → 整筆丟棄，不猜使用者想要哪一欄
            status = entry.get("status")
            if status not in self._VALID_STATUSES:
                continue
            score = self._valid_score(entry.get("confidence_score"))
            if score is None:
                continue
            actions.append({
                "paper_variable": variable,
                "matched_user_column": column,
                "status": status,
                "confidence_score": score,
            })

        reply = parsed.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = "已更新對映，請確認左側表格。"
        return {"actions": actions, "reply": reply}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，97 passed

- [ ] **Step 5: 再次確認既有論文分析邏輯沒被動到**

Run: `cd backend && git diff services/gemini_service.py | grep '^-' | grep -v '^---'`

Expected: 無輸出（沒有任何刪除行）

- [ ] **Step 6: Commit（需先取得使用者確認）**

```bash
git add backend/services/gemini_service.py backend/tests/test_gemini_chat_refine.py
git commit -m "feat: add chat_refine to GeminiService for conversational mapping edits"
```

---

### Task 8: 路由與 blueprint 掛載

**Files:**
- Create: `backend/routes/field_mapping.py`
- Modify: `backend/apps/__init__.py`
- Test: `backend/tests/test_field_mapping_routes.py`

**Interfaces:**
- Consumes: Task 3 的 `run_auto_mapping` / `normalize_user_columns`、Task 4 的 `merge_semantic_suggestions`、Task 6 的 `semantic_match`、Task 7 的 `chat_refine`
- Produces: `POST /api/field-mapping/init`、`POST /api/field-mapping/chat`。前端 Task 10 依這兩個端點實作。

- [ ] **Step 1: 寫失敗的測試**

Create `backend/tests/test_field_mapping_routes.py` with exactly:

```python
"""路由層測試：用 Flask test client，Gemini 全部以 monkeypatch 取代，不連網。

這兩支 API 不碰資料庫，所以 DATABASE_URL 只要是合法的連線字串就好，
SQLAlchemy 是延遲連線的，不會真的去連。
LOGIN_DISABLED 讓 @login_required 變成 no-op，測試不必真的登入。
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.field_mapping as field_mapping_route  # noqa: E402
from apps import create_app  # noqa: E402

PAYLOAD = {
    "paper_variables": [
        {"name": "age", "type": "numerical"},
        {"name": "braden_score", "type": "numerical"},
    ],
    "user_columns": [
        {"name": "pt_age", "sample_values": ["65", "72"]},
        {"name": "braden_total", "sample_values": ["18", "14"]},
    ],
}


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    return app.test_client()


class FakeService:
    """假的 GeminiService：semantic_match / chat_refine 回傳預設好的東西。"""

    def __init__(self, semantic=None, chat=None):
        self._semantic = semantic
        self._chat = chat or {"actions": [], "reply": "ok"}

    def semantic_match(self, items, user_columns):
        return self._semantic

    def chat_refine(self, state, message, history):
        return self._chat


class TestInitRoute:
    def test_returns_mapping_status(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[]),
        )
        response = client.post("/api/field-mapping/init", json=PAYLOAD)
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        variables = [i["paper_variable"] for i in body["result"]["mapping_status"]]
        assert variables == ["age", "braden_score"]

    def test_applies_semantic_suggestions(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[{
                "paper_variable": "braden_score",
                "matched_user_column": "braden_total",
                "confidence_score": 0.95,
                "candidate_columns": [],
            }]),
        )
        body = client.post("/api/field-mapping/init", json=PAYLOAD).get_json()
        braden = [
            i for i in body["result"]["mapping_status"]
            if i["paper_variable"] == "braden_score"
        ][0]
        assert braden["matched_user_column"] == "braden_total"
        assert braden["status"] == "NEEDS_REVIEW"
        assert body["ai_available"] is True

    def test_survives_gemini_being_unavailable(self, client, monkeypatch):
        def boom():
            raise ValueError("GEMINI_API_KEY is required.")

        monkeypatch.setattr(field_mapping_route, "GeminiService", boom)
        response = client.post("/api/field-mapping/init", json=PAYLOAD)
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["ai_available"] is False
        assert len(body["result"]["mapping_status"]) == 2

    def test_semantic_match_returning_none_marks_ai_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=None),
        )
        body = client.post("/api/field-mapping/init", json=PAYLOAD).get_json()
        assert body["ai_available"] is False

    def test_accepts_plain_string_columns(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[]),
        )
        response = client.post("/api/field-mapping/init", json={
            "paper_variables": [{"name": "age", "type": "numerical"}],
            "user_columns": ["pt_age", "gender"],
        })
        assert response.status_code == 200

    def test_rejects_missing_paper_variables(self, client):
        response = client.post("/api/field-mapping/init", json={"user_columns": ["a"]})
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_rejects_missing_user_columns(self, client):
        response = client.post("/api/field-mapping/init", json={
            "paper_variables": [{"name": "age"}],
        })
        assert response.status_code == 400

    def test_rejects_empty_body(self, client):
        assert client.post("/api/field-mapping/init", json={}).status_code == 400


class TestChatRoute:
    def test_returns_diff(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(chat={
                "actions": [{
                    "paper_variable": "braden_score",
                    "matched_user_column": "braden_total",
                    "status": "NEEDS_REVIEW",
                    "confidence_score": 0.9,
                }],
                "reply": "已更新",
            }),
        )
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "braden 分數是 braden_total",
            "chat_history": [],
        })
        assert response.status_code == 200
        body = response.get_json()
        assert body["result"]["reply"] == "已更新"
        assert len(body["result"]["actions"]) == 1

    def test_rejects_empty_message(self, client):
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "   ",
            "chat_history": [],
        })
        assert response.status_code == 400

    def test_returns_503_when_gemini_unavailable(self, client, monkeypatch):
        def boom():
            raise ValueError("GEMINI_API_KEY is required.")

        monkeypatch.setattr(field_mapping_route, "GeminiService", boom)
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "隨便",
            "chat_history": [],
        })
        assert response.status_code == 503
        assert response.get_json()["success"] is False
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `cd backend && uv run --group dev pytest tests/test_field_mapping_routes.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'routes.field_mapping'`

- [ ] **Step 3: 實作路由**

Create `backend/routes/field_mapping.py` with exactly:

```python
"""欄位對齊 API：把論文變數對映到使用者資料表欄位。

薄路由層，寫法比照 routes/gemini.py。所有配對邏輯在
services/field_mapping_service.py，Gemini 相關在 services/gemini_service.py。

這兩支不碰資料庫：對映結果的持久化由前端在使用者確認時，
透過既有的 PATCH /api/projects/<id> 完成。

無狀態設計：/chat 每次都由前端帶完整 current_mapping_state 上來，
伺服器不保留任何對話。這樣前端重新整理不會對不上。
"""

import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

from services.field_mapping_service import (
    AUTO_MATCHED,
    merge_semantic_suggestions,
    normalize_user_columns,
    run_auto_mapping,
)
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

field_mapping_bp = Blueprint("field_mapping", __name__)


@field_mapping_bp.post("/init")
@login_required
def init_field_mapping():
    """初始化對映狀態。

    輸入：{ paper_variables: [...], user_columns: [...] }
    流程：演算法自動配對 → 配不到的交給 Gemini 語意判斷 → 合併
    回傳：{ success, result: {...}, ai_available }

    Gemini 不可用不會讓這支 API 失敗 —— 演算法層不需要 API key 就能運作，
    沒有理由讓整個功能不可用。改用 ai_available 告訴前端要不要顯示提示。
    """
    data = request.get_json(silent=True) or {}
    paper_variables = data.get("paper_variables") or []
    user_columns = data.get("user_columns") or []

    if not paper_variables:
        return jsonify({"success": False, "error": "paper_variables is required"}), 400
    if not user_columns:
        return jsonify({"success": False, "error": "user_columns is required"}), 400

    columns = normalize_user_columns(user_columns)
    if not columns:
        return jsonify({"success": False, "error": "user_columns has no valid column"}), 400

    result = run_auto_mapping(paper_variables, columns)
    pending = [
        item for item in result["mapping_status"] if item["status"] != AUTO_MATCHED
    ]

    if not pending:
        return jsonify({"success": True, "result": result, "ai_available": True})

    try:
        suggestions = GeminiService().semantic_match(pending, columns)
    except Exception:
        logger.exception("semantic_match 階段失敗，改用純演算法結果")
        suggestions = None

    if suggestions is None:
        return jsonify({"success": True, "result": result, "ai_available": False})

    merge_semantic_suggestions(result, suggestions, columns)
    return jsonify({"success": True, "result": result, "ai_available": True})


@field_mapping_bp.post("/chat")
@login_required
def chat_field_mapping():
    """對話式修正對映。

    輸入：{ current_mapping_state, user_message, chat_history }
    回傳：{ success, result: { actions: [...], reply: str } }

    只回這一輪的 diff，不回整包 mapping_status —— 由前端自行套用到本地狀態。
    """
    data = request.get_json(silent=True) or {}
    state = data.get("current_mapping_state") or {}
    message = (data.get("user_message") or "").strip()
    history = data.get("chat_history") or []

    if not message:
        return jsonify({"success": False, "error": "user_message is required"}), 400

    try:
        service = GeminiService()
    except Exception as exc:
        logger.exception("GeminiService 初始化失敗")
        return jsonify({"success": False, "error": str(exc)}), 503

    try:
        result = service.chat_refine(state, message, history)
    except Exception as exc:
        logger.exception("chat_refine 失敗")
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "result": result})
```

- [ ] **Step 4: 掛載 blueprint**

在 `backend/apps/__init__.py` 的 `# Load blueprints` 區塊中，`from routes.model import model_bp` 之後加上：

```python
    from routes.field_mapping import field_mapping_bp
```

在 `app.register_blueprint(model_bp, url_prefix="/api/models")` 之後加上：

```python
    app.register_blueprint(field_mapping_bp, url_prefix="/api/field-mapping")
```

在根路由 `/` 回傳的字典中，`"mineru": "/api/mineru",` 之後加上：

```python
                "field_mapping": "/api/field-mapping",
```

- [ ] **Step 5: 執行測試確認通過**

Run: `cd backend && uv run --group dev pytest tests/ -v`

Expected: PASS，109 passed

- [ ] **Step 6: 手動 smoke test**

Run（開兩個終端機，第一個跑 server；需要 `DATABASE_URL` 與可登入的帳號）：

```bash
cd backend && uv run python app.py
```

端點掛了 `@login_required`，所以要先登入拿 cookie：

```bash
curl -s -c /tmp/dm.cookie -X POST http://127.0.0.1:5001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"<你的帳號>","password":"<你的密碼>"}'

curl -s -b /tmp/dm.cookie -X POST http://127.0.0.1:5001/api/field-mapping/init \
  -H 'Content-Type: application/json' \
  -d '{"paper_variables":[{"name":"age","type":"numerical"},{"name":"gender","type":"categorical"}],
       "user_columns":[{"name":"pt_age","sample_values":["65","72"]},
                       {"name":"sex","sample_values":["M","F"]}]}' | python -m json.tool
```

Expected: `success: true`，`age` 對到 `pt_age` 且 `status` 為 `AUTO_MATCHED`。
未登入直接打應該回 401（Flask-Login 的預設行為）。

- [ ] **Step 7: Commit（需先取得使用者確認）**

```bash
git add backend/routes/field_mapping.py backend/apps/__init__.py backend/tests/test_field_mapping_routes.py
git commit -m "feat: add field mapping API endpoints and mount blueprint"
```

---

### Task 9: 前端 CSV 工具抽出與去重

**Files:**
- Create: `frontend/src/utils/csv.ts`
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue`

**Interfaces:**
- Produces: `parseCsvLine(line: string): string[]`、`decodeFileText(file: File): Promise<string>`、`parseCsvPreview(file: File, sampleRows?: number): Promise<{ columns: string[]; rows: string[][] }>`。Task 12、14 都會用到。

- [ ] **Step 1: 建立共用工具檔**

Create `frontend/src/utils/csv.ts` with exactly:

```ts
/**
 * CSV 解析共用工具。
 *
 * parseCsvLine 與 decodeFileText 原本在 DataTablePanel 和 DistributionPanel
 * 各有一份完全相同的實作，欄位對齊頁需要第三份，因此抽出來共用。
 */

/** 解析一行 CSV，處理雙引號包住的欄位與跳脫的雙引號。 */
export function parseCsvLine (line: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    const next = line[i + 1]

    if (ch === '"' && inQuotes && next === '"') {
      cur += '"'
      i += 1
      continue
    }

    if (ch === '"') {
      inQuotes = !inQuotes
      continue
    }

    if (ch === ',' && !inQuotes) {
      out.push(cur.trim())
      cur = ''
      continue
    }

    cur += ch
  }

  out.push(cur.trim())
  return out
}

/**
 * 讀檔並自動判斷編碼。
 *
 * 醫院匯出的資料表常見 Big5，UTF-8 解不出來或解出一堆替換字元時改用 Big5。
 */
export async function decodeFileText (file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const decoderUtf8 = new TextDecoder('utf-8', { fatal: true })
  let utf8Text: string | null = null
  try {
    utf8Text = decoderUtf8.decode(buffer)
  } catch {
    utf8Text = null
  }

  const decoderBig5 = new TextDecoder('big5')
  const big5Text = decoderBig5.decode(buffer)

  if (!utf8Text) {
    return big5Text
  }

  const scoreText = (text: string) => {
    const headerLine = text.split(/\r?\n/, 1)[0] ?? ''
    const cjkCount = (headerLine.match(/[一-鿿]/g) || []).length
    const replacementCount = (text.match(/�/g) || []).length
    return cjkCount * 10 - replacementCount * 20
  }

  const utf8Score = scoreText(utf8Text)
  const big5Score = scoreText(big5Text)

  return big5Score > utf8Score ? big5Text : utf8Text
}

/** 讀出表頭與前 sampleRows 筆資料列。 */
export async function parseCsvPreview (
  file: File,
  sampleRows = 5,
): Promise<{ columns: string[]; rows: string[][] }> {
  const text = await decodeFileText(file)
  const lines = text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .filter(line => line.trim().length > 0)

  if (lines.length === 0) return { columns: [], rows: [] }

  return {
    columns: parseCsvLine(lines[0]!),
    rows: lines.slice(1, sampleRows + 1).map(line => parseCsvLine(line)),
  }
}
```

- [ ] **Step 2: 讓 DataTablePanel 改用共用工具**

在 `frontend/src/components/workflow/nodePanel/DataTablePanel.vue` 的 `<script setup>` import 區塊加上：

```ts
  import { decodeFileText, parseCsvLine } from '@/utils/csv'
```

然後刪除該檔中本地定義的 `async function decodeFileText (file: File) { ... }` 與 `function parseCsvLine (line: string): string[] { ... }` 兩個函式（連同它們的函式主體整段刪掉）。其他程式碼不動 —— 呼叫端的名稱與行為完全一致。

- [ ] **Step 3: 讓 DistributionPanel 改用共用工具**

在 `frontend/src/components/workflow/nodePanel/DistributionPanel.vue` 的 `<script setup>` import 區塊加上：

```ts
  import { decodeFileText, parseCsvLine } from '@/utils/csv'
```

同樣刪除該檔本地定義的 `decodeFileText` 與 `parseCsvLine`。

- [ ] **Step 4: 型別檢查與建置**

Run: `cd frontend && npm run build`

Expected: build 成功，無 `vue-tsc` 錯誤。若出現「已宣告但未使用」的錯誤，代表還有殘留的本地函式沒刪乾淨。

- [ ] **Step 5: 手動驗證兩個面板沒壞**

Run: `cd frontend && npm run dev`，開 `/workflow`，上傳一個 CSV，確認 Data Table 面板的欄位與預覽資料照常顯示、Distribution 面板的圖表照常產生。

- [ ] **Step 6: Commit（需先取得使用者確認）**

```bash
git add frontend/src/utils/csv.ts frontend/src/components/workflow/nodePanel/DataTablePanel.vue frontend/src/components/workflow/nodePanel/DistributionPanel.vue
git commit -m "refactor: extract shared CSV parsing helpers into utils/csv.ts"
```

---

### Task 10: 前端型別與 API 層

**Files:**
- Create: `frontend/src/types/fieldMapping.ts`
- Create: `frontend/src/api/fieldMapping.ts`

**Interfaces:**
- Consumes: Task 8 的 `/api/field-mapping/init` 與 `/api/field-mapping/chat`
- Produces: 型別 `PaperVariable` / `UserColumn` / `MappingItem` / `MappingState` / `MappingAction` / `ChatMessage` / `MappingStatus`；函式 `initFieldMapping()` / `refineFieldMapping()`。Task 11~14 都會 import。

- [ ] **Step 1: 建立型別檔**

Create `frontend/src/types/fieldMapping.ts` with exactly:

```ts
/** 後端產生的三種狀態；SKIPPED 是前端專屬，後端永遠不會回傳也不會收到。 */
export type MappingStatus = 'AUTO_MATCHED' | 'NEEDS_REVIEW' | 'UNMATCHED' | 'SKIPPED'

/** 論文擷取出來的變數。is_target 的那一筆一律視為必要。 */
export interface PaperVariable {
  name: string
  type: string
  required?: boolean
  is_target?: boolean
}

/** 使用者資料表的欄位，樣本值取前 5 筆。 */
export interface UserColumn {
  name: string
  sample_values: string[]
}

export interface MappingItem {
  paper_variable: string
  required_type: string
  matched_user_column: string | null
  confidence_score: number
  status: MappingStatus
  sample_values: string[]
  candidate_columns: string[]
}

export interface MappingState {
  total_required: number
  matched_count: number
  mapping_status: MappingItem[]
}

/** chat_refine 回傳的單筆變更。 */
export interface MappingAction {
  paper_variable: string
  matched_user_column: string | null
  status: MappingStatus
  confidence_score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}
```

- [ ] **Step 2: 建立 API 層**

Create `frontend/src/api/fieldMapping.ts` with exactly:

```ts
import type {
  ChatMessage,
  MappingAction,
  MappingState,
  PaperVariable,
  UserColumn,
} from '@/types/fieldMapping'

const BASE = '/api/field-mapping'

interface InitResponse {
  success: boolean
  result: MappingState
  ai_available: boolean
  error?: string
}

interface ChatResponse {
  success: boolean
  result: { actions: MappingAction[]; reply: string }
  error?: string
}

/** 初始化對映：演算法自動配對 + Gemini 語意補完。 */
export async function initFieldMapping (payload: {
  paperVariables: PaperVariable[]
  userColumns: UserColumn[]
}): Promise<{ state: MappingState; aiAvailable: boolean }> {
  const response = await fetch(`${BASE}/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      paper_variables: payload.paperVariables,
      user_columns: payload.userColumns,
    }),
  })

  const body = await response.json() as InitResponse
  if (!response.ok || !body.success) {
    throw new Error(body.error || '欄位對齊初始化失敗')
  }
  return { state: body.result, aiAvailable: body.ai_available }
}

/** 對話式修正：只回這一輪的變更，套用由呼叫端負責。 */
export async function refineFieldMapping (payload: {
  mappingState: MappingState
  userColumns: UserColumn[]
  userMessage: string
  chatHistory: ChatMessage[]
}): Promise<{ actions: MappingAction[]; reply: string }> {
  const response = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_mapping_state: {
        mapping_status: payload.mappingState.mapping_status,
        user_columns: payload.userColumns,
      },
      user_message: payload.userMessage,
      chat_history: payload.chatHistory,
    }),
  })

  const body = await response.json() as ChatResponse
  if (!response.ok || !body.success) {
    throw new Error(body.error || 'AI 目前無法回應')
  }
  return body.result
}
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run build`

Expected: build 成功

- [ ] **Step 4: Commit（需先取得使用者確認）**

```bash
git add frontend/src/types/fieldMapping.ts frontend/src/api/fieldMapping.ts
git commit -m "feat: add field mapping types and API client"
```

---

### Task 11: 把對映結果存進資料庫

對映結果是真正的專案資料（之後 DataTablePanel 要讀它來顯示對照來源），所以進資料庫。
聊天記錄不在這個 task —— 它走 localStorage，沿用 `ResultView.vue` 的既有做法，在 Task 13 一併處理。

**Files:**
- Modify: `backend/models/project.py`
- Create: `backend/migrations/versions/<新的 revision>_add_column_mapping_to_projects.py`
- Modify: `backend/routes/project.py`
- Modify: `frontend/src/api/project.ts`
- Modify: `frontend/src/store/projectStore.ts`

**Interfaces:**
- Consumes: 既有的 `PATCH /api/projects/<id>`
- Produces: `Project.column_mapping` DB 欄位；`ProjectDTO.columnMapping` / `UpdateProjectPatch.columnMapping`；store 方法 `saveColumnMapping(projectId: number, mapping: Record<string, string>): Promise<void>`。Task 14 會呼叫。

- [ ] **Step 1: Model 加欄位**

在 `backend/models/project.py` 的 import 區塊加上：

```python
from sqlalchemy.dialects.postgresql import JSONB
```

在 `Project` 類別中，`variables` 欄位之後加上：

```python
    # { 論文變數名: 使用者欄位名 }，由欄位對齊頁寫入
    column_mapping: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
```

- [ ] **Step 2: 產生 migration**

**注意連線設定**：`backend/.env` 的 `DATABASE_URL` 主機名是 `postgres`（Docker 內部網路名），從 host 執行會解析不到。Postgres 容器有把 5432 對外映射，所以在 host 執行 alembic 時要把主機名換成 `localhost`。以下所有 alembic 指令都用這個包裝（不會把密碼印出來）：

```bash
cd backend
export DM_DB="$(grep '^DATABASE_URL=' .env | cut -d= -f2- | sed 's/@postgres:/@localhost:/')"
```

（不要改 `.env` —— 容器裡跑的後端需要 `postgres` 這個主機名。）

Run: `DATABASE_URL="$DM_DB" uv run alembic revision --autogenerate -m "add column_mapping to projects"`

Expected: `migrations/versions/` 底下產生一支新檔案，`upgrade()` 內容應該是：

```python
    op.add_column('projects', sa.Column('column_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
```

**檢查產生出來的檔案**：`down_revision` 應該指向 `97e81ea64538`（2026-08-02 當下的 head，可用 `DATABASE_URL="$DM_DB" uv run alembic heads` 再確認一次），且 `upgrade()` 裡**不應該**出現任何其他資料表的變更。若 autogenerate 順手產生了無關的變更（model 與資料庫不同步時會發生），把那些行刪掉，只留 `column_mapping` 這一個。

- [ ] **Step 3: 套用 migration**

Run: `DATABASE_URL="$DM_DB" uv run alembic upgrade head`

Expected: 無錯誤。用 `DATABASE_URL="$DM_DB" uv run alembic current` 確認 head 是新的 revision。

**容器要重啟才吃得到新程式碼**：`docker compose restart backend`（Task 11 改了 model 與路由）。另注意目前執行中的 backend 容器映像是舊的（裡面沒有 alembic），若之後需要在容器內跑 alembic，要先 `docker compose build backend`。

- [ ] **Step 4: 路由讀寫這個欄位**

在 `backend/routes/project.py` 的 `_serialize_project()` 中，`"date": ...` 那一行**之前**加上：

```python
        "columnMapping": project.column_mapping,
```

在 `update_project()` 中，`if "keyFinding" in data:` 那一段之後加上：

```python
    if "columnMapping" in data:
        project.column_mapping = data["columnMapping"]
    if "variables" in data:
        project.variables = data["variables"]
```

- [ ] **Step 5: 前端 API 型別**

在 `frontend/src/api/project.ts` 中：

`ProjectDTO` 的 `date: string` 之前加上：

```ts
  columnMapping?: Record<string, string> | null
```

`UpdateProjectPatch` 加上兩個欄位：

```ts
  columnMapping?: Record<string, string>
  variables?: number
```

- [ ] **Step 6: store 介面與方法**

在 `frontend/src/store/projectStore.ts` 的 `export interface Project { ... }` 中，`variables: number` 之後加上：

```ts
  /** 對映關係：{ 論文變數名: 使用者欄位名 }。供資料表面板顯示對照來源用。 */
  columnMapping?: Record<string, string> | null
```

在 `return { ... }` 之前加上：

```ts
  /**
   * 把欄位對映存回資料庫。
   *
   * store 是 API-backed 的：只改本地 ref 不等於存檔，一定要打 API，
   * 否則使用者重新整理就會發現對映不見了。
   */
  async function saveColumnMapping (
    projectId: number,
    mapping: Record<string, string>,
  ): Promise<void> {
    const variables = Object.keys(mapping).length
    const target = projects.value.find(p => p.id === projectId)
    if (target) {
      target.columnMapping = mapping
      target.variables = variables
    }
    try {
      await updateProject(projectId, { columnMapping: mapping, variables })
    } catch (error) {
      console.error('儲存欄位對映失敗', error)
      throw error
    }
  }
```

把 `return { ... }` 的清單加上 `saveColumnMapping`（維持既有其他項目不動）。

- [ ] **Step 7: 型別檢查**

Run: `cd frontend && npm run build`

Expected: build 成功。`columnMapping` 是選填，既有的 `addProject` 呼叫端不需要改。

- [ ] **Step 8: 驗證 round-trip**

後端跑起來、前端登入後，在瀏覽器 console 執行：

```js
await fetch('/api/projects/<某個專案 id>', {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ columnMapping: { age: 'pt_age' } }),
}).then(r => r.json())
```

Expected: 回傳的 `result.columnMapping` 是 `{ age: 'pt_age' }`。重新整理後再 `GET /api/projects` 應該還在。

- [ ] **Step 9: Commit（需先取得使用者確認）**

```bash
git add backend/models/project.py backend/migrations/versions/ backend/routes/project.py frontend/src/api/project.ts frontend/src/store/projectStore.ts
git commit -m "feat: store column mapping on project record"
```

---

### Task 12: 欄位對齊頁 — 左側對映表

**Files:**
- Create: `frontend/src/views/hub/FieldMappingView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: Task 9 的 `parseCsvPreview`、Task 10 的 `initFieldMapping` 與型別、Task 11 的 store 方法、既有的 `CustomSelect.vue` 與 `loadWorkflowDataFileFromStorage`
- Produces: 路由 `hub-project-mapping`（路徑 `/hub/projects/:id/mapping`）。Task 13 在同一個檔案加聊天區，Task 14 導向這個路由。

- [ ] **Step 1: 新增路由**

在 `frontend/src/router/index.ts` 的 hub children 中，`projects/:id` 那一筆之後加上：

```ts
        {
          path: "projects/:id/mapping",
          name: "hub-project-mapping",
          component: () => import("@/views/hub/FieldMappingView.vue"),
        },
```

- [ ] **Step 2: 建立頁面骨架與左側對映表**

Create `frontend/src/views/hub/FieldMappingView.vue` with exactly:

```vue
<template>
  <div class="mapping-page">
    <RouterLink :to="`/hub/projects/${projectId}`" class="back-link">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <div class="page-header">
      <h1 class="page-title">欄位對齊</h1>
      <p class="page-sub">確認論文需要的變數對應到資料表的哪一個欄位</p>
    </div>

    <div v-if="loadError" class="load-error">
      <v-icon icon="mdi-alert-circle-outline" size="20" />
      <span>{{ loadError }}</span>
      <RouterLink to="/hub/projects/new" class="load-error-link">重新上傳資料集</RouterLink>
    </div>

    <div v-else class="mapping-layout">
      <!-- 左：對映表 + 資料預覽 -->
      <section class="mapping-main">
        <div class="mapping-head">
          <span class="mapping-title">論文變數對應</span>
          <span class="mapping-count">
            已對照 {{ matchedCount }} / {{ items.length }}
          </span>
        </div>

        <div v-if="loading" class="mapping-loading">
          <v-progress-circular indeterminate size="28" color="#2347c5" />
          <span>正在自動配對…</span>
        </div>

        <table v-else class="mapping-table">
          <thead>
            <tr>
              <th class="col-var">論文變數</th>
              <th class="col-col">你的欄位</th>
              <th class="col-status">狀態</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in sortedItems"
              :key="item.paper_variable"
              :class="{ 'row-flash': flashed.has(item.paper_variable) }"
            >
              <td class="col-var">
                <span v-if="isTarget(item)" class="target-badge" title="預測目標">★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
              <td class="col-col">
                <CustomSelect
                  :model-value="item.matched_user_column ?? selectionKey(item)"
                  :options="optionsFor(item)"
                  placeholder="請選擇"
                  :highlight="item.status === 'UNMATCHED'"
                  @update:model-value="value => applySelection(item, value)"
                />
                <div v-if="item.sample_values.length" class="col-samples">
                  {{ item.sample_values.slice(0, 3).join('、') }}
                </div>
              </td>
              <td class="col-status">
                <span class="status-chip" :class="`status-chip--${item.status.toLowerCase()}`">
                  {{ STATUS_LABEL[item.status] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="!loading && previewColumns.length" class="preview-block">
          <div class="preview-title">資料預覽（前 {{ previewRows.length }} 筆）</div>
          <div class="preview-scroll">
            <table class="preview-table">
              <thead>
                <tr><th v-for="col in previewColumns" :key="col">{{ col }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in previewRows" :key="i">
                  <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="mapping-footer">
          <span v-if="unmatchedCount > 0" class="footer-hint">
            還有 {{ unmatchedCount }} 個變數未對應
          </span>
          <button class="confirm-btn" :disabled="!canConfirm" @click="confirmAndRun">
            確認並執行
            <v-icon icon="mdi-arrow-right" size="17" />
          </button>
        </div>
      </section>

      <!-- 右：AI 對話（Task 13 填入） -->
      <aside class="mapping-chat" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { MappingItem, PaperVariable, UserColumn } from '@/types/fieldMapping'
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { initFieldMapping } from '@/api/fieldMapping'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import { loadWorkflowDataFileFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { parseCsvPreview } from '@/utils/csv'

  const SKIP_VALUE = '__skip__'

  const STATUS_LABEL: Record<string, string> = {
    AUTO_MATCHED: '已對應',
    NEEDS_REVIEW: '待確認',
    UNMATCHED: '未對應',
    SKIPPED: '不使用',
  }

  const route = useRoute()
  const router = useRouter()
  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  // Project.id 在資料庫裡是 int；useWorkflowStorage 的參數是字串，呼叫時要轉
  const projectId = computed(() => Number(route.params.id ?? 0))

  const loading = ref(true)
  const loadError = ref('')
  const items = ref<MappingItem[]>([])
  const userColumns = ref<UserColumn[]>([])
  const previewColumns = ref<string[]>([])
  const previewRows = ref<string[][]>([])
  const targetName = ref('')
  const datasetFile = ref<File | null>(null)
  const flashed = ref(new Set<string>())
  // 使用者手動選過的變數：後續 AI 建議不覆蓋
  const locked = ref(new Set<string>())

  const aiAvailable = ref(false)

  function isTarget (item: MappingItem): boolean {
    return item.paper_variable === targetName.value
  }

  // target 永遠排最前面：它配錯的話整個實驗都白做，不能混在幾十列裡被滑過去
  const sortedItems = computed(() => {
    const list = [...items.value]
    list.sort((a, b) => Number(isTarget(b)) - Number(isTarget(a)))
    return list
  })

  // SKIPPED 不算「已對照」：使用者是主動表示資料裡沒有這個變數
  const matchedCount = computed(
    () => items.value.filter(
      i => i.status !== 'UNMATCHED' && i.status !== 'SKIPPED',
    ).length,
  )
  const unmatchedCount = computed(
    () => items.value.filter(i => i.status === 'UNMATCHED').length,
  )
  const canConfirm = computed(() => !loading.value && unmatchedCount.value === 0)

  function selectionKey (item: MappingItem): string {
    return item.status === 'SKIPPED' ? SKIP_VALUE : ''
  }

  function optionsFor (item: MappingItem) {
    const taken = new Map<string, string>()
    for (const other of items.value) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column) {
        taken.set(other.matched_user_column, other.paper_variable)
      }
    }
    const options = userColumns.value.map(column => ({
      value: column.name,
      label: taken.has(column.name)
        ? `${column.name}（目前給 ${taken.get(column.name)}）`
        : column.name,
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '我的資料沒有這個變數' })
    }
    return options
  }

  function applySelection (item: MappingItem, value: string): void {
    locked.value.add(item.paper_variable)

    if (value === SKIP_VALUE) {
      item.matched_user_column = null
      item.sample_values = []
      item.candidate_columns = []
      item.confidence_score = 0
      item.status = 'SKIPPED'
      return
    }

    // 同一個欄位不能同時服務兩個變數：搶過來，原持有者退回未對應
    for (const other of items.value) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column === value) {
        other.matched_user_column = null
        other.sample_values = []
        other.confidence_score = 0
        other.status = 'UNMATCHED'
        flash(other.paper_variable)
      }
    }

    const column = userColumns.value.find(c => c.name === value)
    item.matched_user_column = value
    item.sample_values = column?.sample_values ?? []
    item.candidate_columns = []
    item.confidence_score = 1
    item.status = 'NEEDS_REVIEW'
  }

  /** 被改動的列閃一下：沒有這個提示，使用者不知道剛才那一步改到了哪裡。 */
  function flash (variable: string): void {
    flashed.value.add(variable)
    setTimeout(() => {
      flashed.value.delete(variable)
      flashed.value = new Set(flashed.value)
    }, 2000)
    flashed.value = new Set(flashed.value)
  }

  /**
   * 確保 store 已經載好。
   *
   * main.ts 的 loadProjects() / loadFrameworks() 是 fire-and-forget 的，
   * 使用者直接開這個網址或按重新整理時，onMounted 可能比它們先跑完，
   * 拿到空陣列就會誤判成「框架沒有變數清單」。
   */
  async function ensureStoresLoaded (): Promise<void> {
    const waiting: Promise<void>[] = []
    if (projectStore.projects.length === 0) waiting.push(projectStore.loadProjects())
    if (frameworkStore.frameworks.length === 0) waiting.push(frameworkStore.loadFrameworks())
    if (waiting.length > 0) await Promise.all(waiting)
  }

  function buildPaperVariables (): PaperVariable[] {
    const project = projectStore.projects.find(p => p.id === projectId.value)
    const framework = frameworkStore.frameworks.find(f => f.id === project?.frameworkId)
    const workflowJson = framework?.workflowJson as
      | { features?: { name: string, type?: string }[], target_col?: string }
      | undefined

    const features = workflowJson?.features ?? []
    const targetCol = workflowJson?.target_col ?? ''
    targetName.value = targetCol

    const variables: PaperVariable[] = features.map(feature => ({
      name: feature.name,
      type: feature.type ?? '',
      is_target: feature.name === targetCol,
    }))

    // target 不在 features 裡時自己補一筆，否則使用者無從指定預測目標
    if (targetCol && !features.some(f => f.name === targetCol)) {
      variables.unshift({ name: targetCol, type: 'categorical', is_target: true })
    }
    return variables
  }

  async function loadDataset (): Promise<File | null> {
    const ctx = projectStore.activeContext
    if (ctx?.datasetFile) return ctx.datasetFile
    return await loadWorkflowDataFileFromStorage(String(projectId.value))
  }

  async function confirmAndRun (): Promise<void> {
    const mapping: Record<string, string> = {}
    for (const item of items.value) {
      if (item.matched_user_column && item.status !== 'SKIPPED') {
        mapping[item.paper_variable] = item.matched_user_column
      }
    }
    await projectStore.saveColumnMapping(projectId.value, mapping)
    router.push(`/workflow?project=${projectId.value}`)
  }

  onMounted(async () => {
    try {
      await ensureStoresLoaded()

      const file = await loadDataset()
      if (!file) {
        loadError.value = '找不到資料集，請回上一步重新上傳。'
        loading.value = false
        return
      }
      datasetFile.value = file

      const preview = await parseCsvPreview(file, 5)
      if (preview.columns.length === 0) {
        loadError.value = '資料集沒有欄位，請確認檔案內容。'
        loading.value = false
        return
      }
      previewColumns.value = preview.columns
      previewRows.value = preview.rows

      const seen = new Set<string>()
      userColumns.value = preview.columns
        .filter(name => {
          if (seen.has(name)) return false  // 重複欄位名只留第一個
          seen.add(name)
          return true
        })
        .map((name, index) => ({
          name,
          sample_values: preview.rows.map(row => row[index] ?? '').filter(Boolean),
        }))

      const paperVariables = buildPaperVariables()
      if (paperVariables.length === 0) {
        loadError.value = '此框架未擷取到變數清單，請回論文分析重新擷取。'
        loading.value = false
        return
      }

      const { state, aiAvailable: available } = await initFieldMapping({
        paperVariables,
        userColumns: userColumns.value,
      })
      items.value = state.mapping_status
      aiAvailable.value = available
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : '欄位對齊初始化失敗'
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .mapping-page {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: #64748b;
    font-size: 13px;
    text-decoration: none;
  }

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
  }

  .page-sub {
    margin-top: 4px;
    font-size: 13px;
    color: #64748b;
  }

  .load-error {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px;
    border: 1px solid #fecaca;
    border-radius: 10px;
    background: #fef2f2;
    color: #b91c1c;
    font-size: 14px;
  }

  .load-error-link {
    color: #b91c1c;
    font-weight: 600;
  }

  .mapping-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 340px;
    gap: 18px;
    align-items: start;
  }

  .mapping-main {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 18px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
  }

  .mapping-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
  }

  .mapping-title {
    font-size: 15px;
    font-weight: 600;
    color: #0f172a;
  }

  .mapping-count {
    font-size: 13px;
    color: #64748b;
  }

  .mapping-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 0;
    justify-content: center;
    color: #64748b;
    font-size: 14px;
  }

  .mapping-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  .mapping-table th {
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    color: #64748b;
    border-bottom: 1px solid #e2e8f0;
  }

  .mapping-table td {
    padding: 10px;
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
  }

  .col-status {
    width: 92px;
  }

  .col-col {
    width: 260px;
  }

  .target-badge {
    color: #d97706;
    margin-right: 4px;
  }

  .var-name {
    font-weight: 600;
    color: #0f172a;
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }

  .col-samples {
    margin-top: 4px;
    font-size: 11px;
    color: #94a3b8;
  }

  .status-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .status-chip--auto_matched {
    background: #dcfce7;
    color: #15803d;
  }

  .status-chip--needs_review {
    background: #fef3c7;
    color: #b45309;
  }

  .status-chip--unmatched {
    background: #fee2e2;
    color: #b91c1c;
  }

  .status-chip--skipped {
    background: #f1f5f9;
    color: #64748b;
  }

  /* AI 或搶欄位造成的變動閃一下，讓使用者看見改到哪一列 */
  .row-flash {
    animation: row-flash 2s ease-out;
  }

  @keyframes row-flash {
    0%, 40% { background: #fef9c3; }
    100% { background: transparent; }
  }

  .preview-block {
    border-top: 1px solid #e2e8f0;
    padding-top: 12px;
  }

  .preview-title {
    font-size: 13px;
    font-weight: 600;
    color: #475569;
    margin-bottom: 8px;
  }

  .preview-scroll {
    overflow-x: auto;
  }

  .preview-table {
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-table th,
  .preview-table td {
    padding: 6px 10px;
    border: 1px solid #f1f5f9;
    color: #475569;
  }

  .preview-table th {
    background: #f8fafc;
    font-weight: 600;
  }

  .mapping-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 8px;
  }

  .footer-hint {
    font-size: 12px;
    color: #b91c1c;
  }

  .confirm-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 18px;
    border-radius: 8px;
    background: #2347c5;
    color: #fff;
    font-size: 14px;
    font-weight: 600;
  }

  .confirm-btn:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }

  .mapping-chat {
    min-height: 420px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
  }
</style>
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run build`

Expected: build 成功

- [ ] **Step 4: 手動驗證**

Run: `cd frontend && npm run dev`，手動走一次：`/hub/projects/new` 建專案（選一個有 `workflowJson` 的框架、上傳 CSV）→ 網址列改成 `/hub/projects/<id>/mapping`。

Expected: 看到對映表、target 排在最上面且有 `★`、下拉可以改、資料預覽顯示前 5 筆。（此時還是從 `/workflow` 導過來的舊路徑，Task 14 才會改成自動導向這一頁。）

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add frontend/src/views/hub/FieldMappingView.vue frontend/src/router/index.ts
git commit -m "feat: add field mapping page with mapping table and data preview"
```

---

### Task 13: 欄位對齊頁 — 右側 AI 對話

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: Task 10 的 `refineFieldMapping`、Task 12 的 `items` / `userColumns` / `locked` / `flash` / `aiAvailable`、既有的 `saveChatHistoryToStorage` / `loadChatHistoryFromStorage`
- Produces: 完整可用的欄位對齊頁

**聊天記錄的存法**：沿用 `ResultView.vue` 用的那一組 localStorage 函式，key 前綴 `mapping-` 以免和結果分析的聊天撞在一起。對話是過程中的暫存，不進資料庫。

- [ ] **Step 1: 換掉聊天區的佔位元素**

把 `FieldMappingView.vue` template 中的 `<aside class="mapping-chat" />` 整行換成：

```vue
      <aside class="mapping-chat">
        <div class="chat-head">
          <v-icon icon="mdi-robot-outline" size="18" color="#2347c5" />
          <span>AI 助理</span>
        </div>

        <div v-if="!aiAvailable" class="chat-offline">
          AI 建議暫時無法使用，可用左側下拉選單手動對應。
        </div>

        <div ref="chatScroll" class="chat-body">
          <div
            v-for="(message, i) in chatHistory"
            :key="i"
            class="chat-bubble"
            :class="`chat-bubble--${message.role}`"
          >
            {{ message.content }}
          </div>
          <div v-if="chatPending" class="chat-bubble chat-bubble--assistant chat-bubble--pending">
            思考中…
          </div>
        </div>

        <form class="chat-input" @submit.prevent="sendMessage">
          <input
            v-model="chatDraft"
            class="chat-field"
            :disabled="!aiAvailable || chatPending"
            placeholder="例如：Braden 分數是 braden_total"
          />
          <button
            class="chat-send"
            type="submit"
            :disabled="!aiAvailable || chatPending || !chatDraft.trim()"
          >
            送出
          </button>
        </form>
      </aside>
```

- [ ] **Step 2: 新增聊天邏輯**

在 `<script setup>` 的 import 區塊，把 `initFieldMapping` 那一行改成：

```ts
  import { initFieldMapping, refineFieldMapping } from '@/api/fieldMapping'
```

在 import 型別那一行補上 `ChatMessage` 與 `MappingAction`：

```ts
  import type {
    ChatMessage,
    MappingAction,
    MappingItem,
    PaperVariable,
    UserColumn,
  } from '@/types/fieldMapping'
```

在 `const aiAvailable = ref(false)` 之後加上：

```ts
  const chatHistory = ref<ChatMessage[]>([])
  const chatDraft = ref('')
  const chatPending = ref(false)
  const chatScroll = ref<HTMLElement | null>(null)
```

在 `confirmAndRun()` 之前加上：

```ts
  /** 把 AI 回傳的 diff 套用到本地狀態；使用者手動選過的列不覆蓋。 */
  function applyActions (actions: MappingAction[]): string[] {
    const changed: string[] = []
    for (const action of actions) {
      const item = items.value.find(i => i.paper_variable === action.paper_variable)
      if (!item || locked.value.has(item.paper_variable)) continue

      if (action.matched_user_column) {
        // 搶欄位：原持有者退回未對應，同樣要閃給使用者看
        for (const other of items.value) {
          if (
            other.paper_variable !== item.paper_variable
            && other.matched_user_column === action.matched_user_column
          ) {
            other.matched_user_column = null
            other.sample_values = []
            other.confidence_score = 0
            other.status = 'UNMATCHED'
            changed.push(other.paper_variable)
          }
        }
        const column = userColumns.value.find(c => c.name === action.matched_user_column)
        item.matched_user_column = action.matched_user_column
        item.sample_values = column?.sample_values ?? []
        item.candidate_columns = []
      } else {
        item.matched_user_column = null
        item.sample_values = []
      }

      item.confidence_score = action.confidence_score
      item.status = action.status
      changed.push(item.paper_variable)
    }
    return changed
  }

  async function sendMessage (): Promise<void> {
    const message = chatDraft.value.trim()
    if (!message || chatPending.value) return

    chatDraft.value = ''
    chatHistory.value.push({ role: 'user', content: message })
    chatPending.value = true
    await scrollChatToBottom()

    try {
      const { actions, reply } = await refineFieldMapping({
        mappingState: {
          total_required: items.value.length,
          matched_count: matchedCount.value,
          mapping_status: items.value,
        },
        userColumns: userColumns.value,
        userMessage: message,
        chatHistory: chatHistory.value.slice(0, -1),
      })
      for (const variable of applyActions(actions)) flash(variable)
      chatHistory.value.push({ role: 'assistant', content: reply })
    } catch (error) {
      chatHistory.value.push({
        role: 'assistant',
        content: error instanceof Error ? error.message : 'AI 目前無法回應，請改用下拉選單。',
      })
    } finally {
      chatPending.value = false
      // key 加 mapping- 前綴，避免和 ResultView 的結果分析聊天撞在一起
      saveChatHistoryToStorage(`mapping-${projectId.value}`, chatHistory.value)
      await scrollChatToBottom()
    }
  }

  async function scrollChatToBottom (): Promise<void> {
    await nextTick()
    if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight
  }
```

把 `import { computed, onMounted, ref } from 'vue'` 改成：

```ts
  import { computed, nextTick, onMounted, ref } from 'vue'
```

- [ ] **Step 3: 進頁時還原聊天記錄**

在 `<script setup>` 的 import 區塊，把 `loadWorkflowDataFileFromStorage` 那一行改成：

```ts
  import {
    loadChatHistoryFromStorage,
    loadWorkflowDataFileFromStorage,
    saveChatHistoryToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
```

在 `onMounted` 的 `await ensureStoresLoaded()` 之後、`const file = await loadDataset()` 之前加上：

```ts
      chatHistory.value = loadChatHistoryFromStorage(
        `mapping-${projectId.value}`,
      ) as ChatMessage[]
```

- [ ] **Step 4: 加上聊天區樣式**

在 `<style scoped>` 中，把 `.mapping-chat { ... }` 那個區塊整段換成：

```css
  .mapping-chat {
    display: flex;
    flex-direction: column;
    height: 620px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
    overflow: hidden;
  }

  .chat-head {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 14px 16px;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
    font-weight: 600;
    color: #0f172a;
  }

  .chat-offline {
    padding: 10px 16px;
    background: #fffbeb;
    border-bottom: 1px solid #fde68a;
    font-size: 12px;
    color: #b45309;
  }

  .chat-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .chat-bubble {
    max-width: 88%;
    padding: 9px 12px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.55;
    white-space: pre-wrap;
  }

  .chat-bubble--user {
    align-self: flex-end;
    background: #2347c5;
    color: #fff;
  }

  .chat-bubble--assistant {
    align-self: flex-start;
    background: #f1f5f9;
    color: #0f172a;
  }

  .chat-bubble--pending {
    color: #94a3b8;
  }

  .chat-input {
    display: flex;
    gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid #e2e8f0;
  }

  .chat-field {
    flex: 1;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 13px;
  }

  .chat-field:disabled {
    background: #f8fafc;
  }

  .chat-send {
    padding: 8px 14px;
    border-radius: 8px;
    background: #2347c5;
    color: #fff;
    font-size: 13px;
    font-weight: 600;
  }

  .chat-send:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
  }
```

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run build`

Expected: build 成功

- [ ] **Step 6: 手動驗證（需要 GEMINI_API_KEY）**

後端要跑起來且 `backend/.env` 有設 `GEMINI_API_KEY`。在對齊頁輸入「Braden 分數是 braden_total」之類的指令。

Expected: 左側對應的列被改到、閃一下黃底、右側出現 AI 的回覆文字。

- [ ] **Step 7: Commit（需先取得使用者確認）**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: add AI chat panel to field mapping page"
```

---

### Task 14: 接進建立專案流程並改寫 CSV 表頭

**Files:**
- Modify: `frontend/src/views/hub/CreateProjectView.vue`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: Task 9 的 `decodeFileText`、Task 12 的頁面、既有的 `saveWorkflowDataFileToStorage`
- Produces: 完整的端到端流程：建立專案 → 對齊頁 → workflow

- [ ] **Step 1: 建立專案後導向對齊頁**

在 `frontend/src/views/hub/CreateProjectView.vue` 的 import 區塊加上：

```ts
  import { saveWorkflowDataFileToStorage } from '@/composables/workflow/useWorkflowStorage'
```

`executeProject()` 已經是 async（它要 await `addProject`）。把它最後兩段換掉，原本的：

```ts
    projectStore.setActiveContext({
      projectId: project.id,
      datasetFile: form.value.datasetFile,
      frameworkId: form.value.frameworkId,
    })

    router.push(`/workflow?project=${project.id}`)
  }
```

換成：

```ts
    projectStore.setActiveContext({
      projectId: project.id,
      datasetFile: form.value.datasetFile,
      frameworkId: form.value.frameworkId,
    })

    // 先寫進 IndexedDB：activeContext 只活在記憶體裡，
    // 使用者在對齊頁按重新整理就會遺失。
    // useWorkflowStorage 的 projectId 參數是字串，而 Project.id 是數字。
    if (form.value.datasetFile) {
      await saveWorkflowDataFileToStorage(form.value.datasetFile, String(project.id))
    }

    router.push(`/hub/projects/${project.id}/mapping`)
  }
```

- [ ] **Step 2: 對齊頁離開時改寫 CSV 表頭**

在 `FieldMappingView.vue` 的 import 區塊，把 Task 13 建立的那個 `useWorkflowStorage` import 補上 `saveWorkflowDataFileToStorage`，變成：

```ts
  import {
    loadChatHistoryFromStorage,
    loadWorkflowDataFileFromStorage,
    saveChatHistoryToStorage,
    saveWorkflowDataFileToStorage,
  } from '@/composables/workflow/useWorkflowStorage'
```

並把 `parseCsvPreview` 那一行改成：

```ts
  import { decodeFileText, parseCsvLine, parseCsvPreview } from '@/utils/csv'
```

把 `confirmAndRun()` 整個函式換成：

```ts
  /**
   * 依對映改寫 CSV 表頭後交給 workflow。
   *
   * 只改名、不刪欄位：使用者沒對應到的欄位在 workflow 那邊還是可以選用，
   * 在這裡刪掉只會讓他失去選擇。
   */
  async function confirmAndRun (): Promise<void> {
    if (!datasetFile.value) return
    confirming.value = true

    try {
      const mapping: Record<string, string> = {}
      for (const item of items.value) {
        if (item.matched_user_column && item.status !== 'SKIPPED') {
          mapping[item.paper_variable] = item.matched_user_column
        }
      }
      await projectStore.saveColumnMapping(projectId.value, mapping)

      // 使用者欄位 → 論文變數（改寫表頭時要反查）
      const renameByColumn = new Map<string, string>()
      for (const [variable, column] of Object.entries(mapping)) {
        renameByColumn.set(column, variable)
      }

      const text = await decodeFileText(datasetFile.value)
      const lines = text.replace(/\r\n/g, '\n').split('\n')
      const headerIndex = lines.findIndex(line => line.trim().length > 0)
      if (headerIndex >= 0) {
        const header = parseCsvLine(lines[headerIndex]!)
        lines[headerIndex] = header
          .map(name => escapeCsvCell(renameByColumn.get(name) ?? name))
          .join(',')
      }

      const renamed = new File(
        [lines.join('\n')],
        datasetFile.value.name,
        { type: datasetFile.value.type || 'text/csv' },
      )
      await saveWorkflowDataFileToStorage(renamed, String(projectId.value))
      projectStore.setActiveContext({
        projectId: projectId.value,
        datasetFile: renamed,
        frameworkId:
          projectStore.projects.find(p => p.id === projectId.value)?.frameworkId ?? null,
      })

      router.push(`/workflow?project=${projectId.value}`)
    } finally {
      confirming.value = false
    }
  }

  /** 欄位名含逗號或引號時要包起來，否則改寫後的表頭會被拆錯欄。 */
  function escapeCsvCell (value: string): string {
    if (!/[",\n]/.test(value)) return value
    return `"${value.replace(/"/g, '""')}"`
  }
```

在 `const chatScroll = ref<HTMLElement | null>(null)` 之後加上：

```ts
  const confirming = ref(false)
```

把 template 中的確認按鈕改成（加上 `confirming` 狀態）：

```vue
          <button class="confirm-btn" :disabled="!canConfirm || confirming" @click="confirmAndRun">
            {{ confirming ? '處理中…' : '確認並執行' }}
            <v-icon v-if="!confirming" icon="mdi-arrow-right" size="17" />
          </button>
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run build`

Expected: build 成功

- [ ] **Step 4: 端到端手動驗證**

前後端都要跑起來，`backend/.env` 需有 `GEMINI_API_KEY`。

1. `/hub/projects/new` 建專案：填名稱 → 選一個有 `workflowJson` 的框架 → 上傳 CSV → 執行分析
2. Expected: 自動導向 `/hub/projects/<id>/mapping`，看到自動配對結果
3. 在對齊頁按 F5 重新整理 → Expected: 資料集與對映狀態都還在
4. 用聊天改一個欄位 → Expected: 左側對應列被改到並閃一下
5. 把所有未對應處理掉，按「確認並執行」→ Expected: 導向 `/workflow?project=<id>`，Data Table 面板顯示的欄位名已經是論文變數名，workflow 可以正常執行到出結果

- [ ] **Step 5: Commit（需先取得使用者確認）**

```bash
git add frontend/src/views/hub/CreateProjectView.vue frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: route project creation through field mapping and rewrite CSV header"
```

---

### Task 15: 真實資料驗證與門檻校準

這個 task 沒有程式碼產出，但它是**驗收條件**。前面 14 個 task 的測試全部通過，不代表這個功能可用 —— 0.8 這個門檻準不準、Gemini 的 JSON 穩不穩，只有真實資料量得出來。

**Files:**
- Create: `backend/scripts/test_field_mapping.py`
- Modify（視驗證結果而定）: `backend/services/field_mapping_service.py`、`backend/services/field_mapping_prompts.py`

**Interfaces:**
- Consumes: Task 1~8 的全部後端程式碼

- [ ] **Step 1: 準備真實測試資料**

準備兩份東西放在 `backend/artifacts/`（不進版控）：

1. 一篇真實論文跑過 `/api/gemini/ai-analyze` 得到的 workflow JSON（取其中的 `features` 與 `target_col`）
2. 一份真實的資料表 CSV。**欄位名必須是實務上的縮寫風格**（如 `pt_age`、`adm_dt`、`bp_sys`、`braden_total`），不可用乾淨的示範檔 —— 用乾淨檔案測不出門檻的準確率，只會得到虛假的好成績。

另外手寫一份**正確答案對照表**（哪個論文變數該對到哪個欄位），驗證時拿來比對。

- [ ] **Step 2: 建立驗證腳本**

Create `backend/scripts/test_field_mapping.py` with exactly:

```python
"""欄位對齊真實資料驗證腳本。

用法（在 backend/ 目錄下）：
    python scripts/test_field_mapping.py <workflow_json> <dataset_csv> <answer_json>

answer_json 是人工寫的正確答案：{"論文變數名": "應該對到的欄位名或 null"}

量測四件事：自動配對正確率、假陽性數、Gemini JSON 解析成功率、target 是否正確。
"""

import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.field_mapping_service import (  # noqa: E402
    AUTO_MATCHED,
    merge_semantic_suggestions,
    normalize_user_columns,
    run_auto_mapping,
)
from services.gemini_service import GeminiService  # noqa: E402

GEMINI_ROUNDS = 5


def load_paper_variables(workflow_path: Path) -> list[dict]:
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = data.get("result", {}).get("workflow_json", data)
    target_col = workflow.get("target_col") or ""
    variables = [
        {
            "name": feature["name"],
            "type": feature.get("type", ""),
            "is_target": feature["name"] == target_col,
        }
        for feature in workflow.get("features", [])
    ]
    if target_col and not any(v["name"] == target_col for v in variables):
        variables.insert(0, {"name": target_col, "type": "categorical", "is_target": True})
    return variables


def load_user_columns(csv_path: Path, sample_rows: int = 5) -> list[dict]:
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for _, row in zip(range(sample_rows), reader)]
    return normalize_user_columns([
        {
            "name": name,
            "sample_values": [row[index] for row in rows if index < len(row)],
        }
        for index, name in enumerate(header)
    ])


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    paper_variables = load_paper_variables(Path(sys.argv[1]))
    user_columns = load_user_columns(Path(sys.argv[2]))
    answers = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

    print("=" * 70)
    print(f"論文變數 {len(paper_variables)} 個、資料表欄位 {len(user_columns)} 個")

    # ── 演算法層 ────────────────────────────────────────────────────────────
    result = run_auto_mapping(paper_variables, user_columns)
    pending = [i for i in result["mapping_status"] if i["status"] != AUTO_MATCHED]
    print(f"\n[演算法層] 自動配對 {result['matched_count']} 個，待處理 {len(pending)} 個")

    # ── Gemini 穩定性：連續 GEMINI_ROUNDS 次 ────────────────────────────────
    print(f"\n[Gemini] 連續呼叫 {GEMINI_ROUNDS} 次，量測 JSON 解析成功率")
    service = GeminiService()
    successes = 0
    last_suggestions = []
    for round_index in range(1, GEMINI_ROUNDS + 1):
        suggestions = service.semantic_match(pending, user_columns)
        if suggestions is None:
            print(f"  第 {round_index} 次：解析失敗")
            continue
        successes += 1
        last_suggestions = suggestions
        print(f"  第 {round_index} 次：成功，回傳 {len(suggestions)} 筆建議")
    print(f"  解析成功率：{successes}/{GEMINI_ROUNDS}")

    merge_semantic_suggestions(result, last_suggestions, user_columns)

    # ── 對答案 ─────────────────────────────────────────────────────────────
    auto_items = [i for i in result["mapping_status"] if i["status"] == AUTO_MATCHED]
    false_positives = []
    correct = 0
    for item in auto_items:
        expected = answers.get(item["paper_variable"])
        if item["matched_user_column"] == expected:
            correct += 1
        else:
            false_positives.append(
                f"{item['paper_variable']}：配到 {item['matched_user_column']}，"
                f"正確答案是 {expected}"
            )

    accuracy = correct / len(auto_items) if auto_items else 0.0
    target_item = next(
        (i for i in result["mapping_status"]
         if any(v["name"] == i["paper_variable"] and v["is_target"] for v in paper_variables)),
        None,
    )

    print("\n" + "=" * 70)
    print("驗收指標")
    print(f"  自動配對正確率：{correct}/{len(auto_items)} = {accuracy:.1%}　（需 >= 90%）")
    print(f"  假陽性：{len(false_positives)} 個　（需 <= 1）")
    print(f"  Gemini 解析成功率：{successes}/{GEMINI_ROUNDS}　（需 5/5）")
    print(f"  Target 出現且狀態正確："
          f"{'是' if target_item and target_item['status'] != AUTO_MATCHED else '否'}"
          f"　（需為「是」）")

    if false_positives:
        print("\n假陽性明細（這是最危險的錯誤：使用者信任綠勾勾，不會逐筆檢查）：")
        for line in false_positives:
            print(f"  - {line}")
        print("\n處置：調高 AUTO_THRESHOLD（0.85 / 0.9），"
              "寧可多幾筆待確認，也不要出現錯誤的自動配對。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 執行驗證**

Run: `cd backend && uv run python scripts/test_field_mapping.py artifacts/<workflow>.json artifacts/<dataset>.csv artifacts/<answers>.json`

Expected: 四項指標全部達標
- 自動配對正確率 >= 90%
- 假陽性 <= 1 個
- Gemini 解析成功率 5/5
- Target 出現且狀態不是 `AUTO_MATCHED`

- [ ] **Step 4: 沒過就調門檻，調完重跑**

若假陽性 > 1 或正確率 < 90%：把 `backend/services/field_mapping_service.py` 的 `AUTO_THRESHOLD` 從 `0.8` 調到 `0.85`，重跑 Step 3。還是沒過就調到 `0.9`。

**不要為了讓數字好看而放寬驗證邏輯或改答案檔。** 調門檻的代價只是多幾個要人確認的項目，錯誤的綠勾勾則會一路帶進實驗結果。

若 Gemini 解析成功率不是 5/5：先確認 `response_schema` 有正確傳進去（在 `semantic_match` 裡 log 出實際的 `response.text` 看看回了什麼）。schema 生效的情況下不應該解析失敗，失敗代表 schema 沒吃到，要先查清楚原因再繼續。

- [ ] **Step 5: 量測聊天的越權修改率**

在前端對齊頁連續下 5 次「只改一個變數」的指令（例如「Braden 分數是 braden_total」「年齡對到 pt_age」），每次都記錄實際被改動的列數。

Expected: 每次都只有 1 列被改動（加上被搶欄位的原持有者最多 2 列）。

若模型常常順手改別的：在 `field_mapping_prompts.py` 的 `build_chat_refine_prompt` 規則 2 後面加上反例，例如：

```
   錯誤示範：使用者說「braden 分數是 braden_total」，你卻同時把 age、gender
   也一併改掉。正確做法是 actions 只有 braden_score 這一筆。
```

改完重測。**不要改成放寬白名單驗證。**

- [ ] **Step 6: 記錄驗證結果並 commit（需先取得使用者確認）**

把最終採用的門檻值與量測到的四項指標寫進 spec 的 4.3 節（在表格下方加一段「實測結果」），然後：

```bash
git add backend/scripts/test_field_mapping.py backend/services/field_mapping_service.py backend/services/field_mapping_prompts.py docs/superpowers/specs/2026-07-31-field-mapping-design.md
git commit -m "test: add real-data validation script and calibrate matching thresholds"
```

---

## 附錄：完整測試指令

```bash
# 後端全部單元測試
cd backend && uv run --group dev pytest tests/ -v

# 確認既有論文分析邏輯沒被動到（應無輸出）
cd backend && git diff services/gemini_service.py | grep '^-' | grep -v '^---'
cd backend && git diff --stat routes/gemini.py services/workflow/ services/model/ routes/model.py

# 前端型別檢查與建置
cd frontend && npm run build

# 真實資料驗證
cd backend && uv run python scripts/test_field_mapping.py <workflow.json> <dataset.csv> <answers.json>
```
