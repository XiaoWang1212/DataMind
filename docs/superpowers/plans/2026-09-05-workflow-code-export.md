# Workflow 程式碼匯出 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者在 workflow 畫布上按一個按鈕，把目前設定好的整個流程（前處理、特徵工程、模型、驗證方式、評估指標、信賴區間）匯出成一份帶中文註解、可直接執行的 Python 檔案。

**Architecture:** 後端新增 `code_export_service.py`，重用現有 `/api/models/workflow/execute` 已有的 payload 解析（`_parse_execute_params()`）跟 `ModelRegistry`；模型建構子程式碼用 `repr(model_config.create_estimator())` 產生（不手寫範本），前處理/特徵工程/驗證方式手寫範本並支援一部分 step type、其餘用 TODO 註解取代。前端重用 `useWorkflowExecution.ts` 既有的 `buildWorkflowPayload()`，新增一個按鈕打新路由、用 Blob 觸發下載。

**Tech Stack:** Python 3.11 + scikit-learn（後端產生程式碼的邏輯本身）；Vue 3 `<script setup>` + TypeScript（前端按鈕）。

## Global Constraints

- 產生的程式碼語言固定 Python
- 資料集路徑用 placeholder（`DATA_PATH = "your_dataset.csv"` + TODO 註解），`TARGET_COLUMN` 直接帶入這個 workflow 實際設定的目標欄位名稱
- 前處理支援 6 種 step type：`fill_na`、`standardize`、`normalize`、`one_hot`、`label_encode`、`drop_columns`；特徵工程支援 4 種：`pca`、`select_relevant_features`、`normalize_features`、`impute_missing`。其餘 step type 一律用固定格式 TODO 註解取代，不擋住整體產生
- 驗證方式 5 種全部支援：`k_fold`、`group_k_fold`、`random_sampling`、`test_on_train`、`test_on_test`
- **不**支援 `resampling_method`/`tuning_method`（SMOTE 重抽樣、超參數搜尋）——這兩個不在這次的範圍內，即使 workflow 有設定也不反映在匯出的程式碼裡（這是已知、刻意的限制，不是遺漏）
- 模型建構子一律用 `repr(model_config.create_estimator())` 產生，不手寫模型範本
- 產生的程式碼字串必須通過 `ast.parse()`（語法合法）
- 不動現有的 workflow 執行邏輯（`workflow_service.py`/`test_score_service.py`/`preprocess_service.py`/`feature_engineering_service.py`），這次是新增一個獨立、平行的功能

---

### Task 1: `code_export_service.py` 骨架 + 模型程式碼產生

**Files:**
- Create: `backend/services/workflow/code_export_service.py`
- Test: `backend/tests/test_code_export_service.py`

**Interfaces:**
- Produces: `MODEL_IMPORTS: Dict[str, List[str]]`（模型名稱 → import 陳述式清單）
- Produces: `render_model_construction(model_names: List[str]) -> Tuple[List[str], str]`（回傳 `(import 陳述式清單, 模型字典的程式碼區塊字串)`）

- [ ] **Step 1: 建立檔案，寫 `MODEL_IMPORTS` 對照表**

建立 `backend/services/workflow/code_export_service.py`：
```python
"""把 workflow 的設定（前處理、特徵工程、模型、驗證方式、評估指標、信賴區間）
轉成一份帶中文註解、可直接執行的 Python 程式碼字串。

跟 workflow_service.py／test_score_service.py／preprocess_service.py／
feature_engineering_service.py 是平行、獨立的功能，不會呼叫、也不會被它們呼叫，
純粹是「讀同一份設定、輸出成另一種形式」。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.model.registry import ModelRegistry

# 每個模型名稱需要的 import 陳述式，內容抄自 backend/services/model/models/*.py
# 各檔案開頭的 import 行。新增模型時記得同步更新這裡（有單元測試會檢查
# ModelRegistry 裡的每個模型名稱都能在這個表裡查到，忘記加會直接測試失敗）。
MODEL_IMPORTS: Dict[str, List[str]] = {
    "AdaBoost": ["from sklearn.ensemble import AdaBoostClassifier"],
    "Bagging": ["from sklearn.ensemble import BaggingClassifier"],
    "Balanced Random Forest": ["from imblearn.ensemble import BalancedRandomForestClassifier"],
    "Bernoulli NB": ["from sklearn.naive_bayes import BernoulliNB"],
    "Calibrated Classifier": [
        "from sklearn.linear_model import LogisticRegression",
        "from sklearn.calibration import CalibratedClassifierCV",
    ],
    "CatBoost": ["from catboost import CatBoostClassifier"],
    "Complement NB": ["from sklearn.naive_bayes import ComplementNB"],
    "Decision Tree": ["from sklearn.tree import DecisionTreeClassifier"],
    "Easy Ensemble": ["from imblearn.ensemble import EasyEnsembleClassifier"],
    "Extra Trees": ["from sklearn.ensemble import ExtraTreesClassifier"],
    "Gaussian NB": ["from sklearn.naive_bayes import GaussianNB"],
    "Gaussian Process": ["from sklearn.gaussian_process import GaussianProcessClassifier"],
    "Gradient Boosting": ["from sklearn.ensemble import GradientBoostingClassifier"],
    "HistGradient Boosting": ["from sklearn.ensemble import HistGradientBoostingClassifier"],
    "K-Nearest Neighbors": ["from sklearn.neighbors import KNeighborsClassifier"],
    "LightGBM": ["from lightgbm import LGBMClassifier"],
    "Linear Discriminant Analysis": ["from sklearn.discriminant_analysis import LinearDiscriminantAnalysis"],
    "Linear SVC": [
        "from sklearn.calibration import CalibratedClassifierCV",
        "from sklearn.svm import LinearSVC",
    ],
    "Logistic Regression": ["from sklearn.linear_model import LogisticRegression"],
    "Logistic Regression CV": ["from sklearn.linear_model import LogisticRegressionCV"],
    "MLP": ["from sklearn.neural_network import MLPClassifier"],
    "Multinomial NB": ["from sklearn.naive_bayes import MultinomialNB"],
    "Nu-SVC": ["from sklearn.svm import NuSVC"],
    "Passive Aggressive": ["from sklearn.linear_model import PassiveAggressiveClassifier"],
    "Quadratic Discriminant Analysis": ["from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis"],
    "Radius Neighbors": ["from sklearn.neighbors import RadiusNeighborsClassifier"],
    "Random Forest": ["from sklearn.ensemble import RandomForestClassifier"],
    "Ridge Classifier": ["from sklearn.linear_model import RidgeClassifier"],
    "Ridge Classifier CV": ["from sklearn.linear_model import RidgeClassifierCV"],
    "SGD Classifier": ["from sklearn.linear_model import SGDClassifier"],
    "Stacking Classifier": [
        "from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, StackingClassifier",
        "from sklearn.linear_model import LogisticRegression",
    ],
    "SVM": ["from sklearn.svm import SVC"],
    "Voting Classifier": [
        "from sklearn.ensemble import RandomForestClassifier, VotingClassifier",
        "from sklearn.linear_model import LogisticRegression",
        "from sklearn.svm import SVC",
    ],
    "XGBoost": ["from xgboost import XGBClassifier"],
}
```

- [ ] **Step 2: `render_model_construction()`**

在同一個檔案接著加：
```python
def render_model_construction(model_names: List[str]) -> Tuple[List[str], str]:
    """回傳 (需要的 import 陳述式清單, 模型字典的程式碼區塊字串)。

    模型建構子程式碼直接對後端真正建出來的 sklearn 物件呼叫 repr()——sklearn
    生態系的物件 __repr__ 本身就是合法可執行的建構子語法（例如
    RandomForestClassifier(class_weight='balanced', n_jobs=-1, random_state=42)），
    不用為每個模型手寫一份程式碼範本，新增模型時這裡不用跟著改。
    """
    import_lines: List[str] = []
    entries: List[str] = []

    for name in model_names:
        model_config = ModelRegistry.get_model_config(name)
        if model_config is None:
            entries.append(
                f"    # ⚠️ 找不到模型「{name}」，可能是後端模型清單已經變動，這裡略過。"
            )
            continue

        for line in MODEL_IMPORTS.get(name, []):
            if line not in import_lines:
                import_lines.append(line)

        try:
            estimator_repr = repr(model_config.create_estimator())
        except Exception as exc:  # pragma: no cover - 目前所有已註冊模型都能正常 repr()
            entries.append(
                f"    # ⚠️ TODO：模型「{name}」目前無法自動產生建構子程式碼（{exc}），"
                "請自行參考 DataMind 原始碼手動補上。"
            )
            continue

        entries.append(f"    {name!r}: {estimator_repr},")

    if not entries:
        body = "    # ⚠️ 沒有任何可用的模型，請回 workflow 的 Settings 節點至少新增一個模型。"
    else:
        body = "\n".join(entries)

    code = "models = {\n" + body + "\n}"
    return import_lines, code
```

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/code_export_service.py datamind-backend:/tmp/code_export_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/code_export_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 建測試檔，驗證 `MODEL_IMPORTS` 涵蓋所有已註冊模型 + `render_model_construction()` 產生合法程式碼**

建立 `backend/tests/test_code_export_service.py`：
```python
import ast

from services.model.registry import ModelRegistry
from services.workflow.code_export_service import MODEL_IMPORTS, render_model_construction


def test_model_imports_covers_every_registered_model():
    """新增模型卻忘記同步更新 MODEL_IMPORTS，這裡要抓到，不能讓匯出功能悄悄漏掉它。"""
    registered = set(ModelRegistry.list_models())
    covered = set(MODEL_IMPORTS.keys())
    missing = registered - covered
    assert not missing, f"MODEL_IMPORTS 缺少這些模型：{missing}"


def test_render_model_construction_produces_valid_python():
    import_lines, code = render_model_construction(["Random Forest", "Logistic Regression"])

    assert "from sklearn.ensemble import RandomForestClassifier" in import_lines
    assert "from sklearn.linear_model import LogisticRegression" in import_lines
    assert "RandomForestClassifier(" in code
    assert "LogisticRegression(" in code

    full_source = "\n".join(import_lines) + "\n" + code
    ast.parse(full_source)  # 語法必須合法，解析失敗就是測試失敗


def test_render_model_construction_unknown_model_does_not_crash():
    import_lines, code = render_model_construction(["Not A Real Model"])
    assert "找不到模型" in code
    ast.parse(code)
```

- [ ] **Step 5: 跑測試**

Run:
```bash
docker cp backend/tests/test_code_export_service.py datamind-backend:/tmp/test_code_export_service.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_code_export_service.py -v
```
Expected: 3 個測試全部 PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/code_export_service.py backend/tests/test_code_export_service.py
git commit -m "feat: add model construction code generation for workflow export"
```

---

### Task 2: 前處理 step 範本

**Files:**
- Modify: `backend/services/workflow/code_export_service.py`
- Modify: `backend/tests/test_code_export_service.py`

**Interfaces:**
- Consumes: 無（純函式，不依賴 Task 1 的產出）
- Produces: `render_preprocess_step(step: Dict[str, Any]) -> str`（回傳一段程式碼字串，會被組進迴圈裡，每行前面已經有正確縮排；不支援的 step type 回傳 TODO 註解）
- Produces: `PREPROCESS_STEP_LABELS: Dict[str, str]`（中文標籤，範本註解要用）

- [ ] **Step 1: 寫 6 種支援的 step type 範本**

在 `code_export_service.py` 裡 `render_model_construction()` 之後新增：
```python
PREPROCESS_STEP_LABELS: Dict[str, str] = {
    "fill_na": "缺值填補",
    "standardize": "Z-score 標準化",
    "normalize": "Min-Max 正規化",
    "one_hot": "One-Hot 編碼",
    "label_encode": "Label 編碼",
    "drop_columns": "移除欄位",
}

# 這 4 種目前沒有範本，遇到時用固定格式的 TODO 註解取代，不擋住其餘 step 的產生
_UNSUPPORTED_PREPROCESS_STEPS = {
    "knn_impute", "iterative_impute", "remove_outliers_iqr", "remove_outliers_zscore",
}


def _unsupported_step_comment(step_type: str, source_file: str) -> str:
    return (
        f"    # ⚠️ TODO：這個 workflow 用了「{step_type}」步驟，DataMind 程式碼匯出功能目前"
        "還不支援自動產生這段邏輯。\n"
        f"    # 請參考 backend/services/workflow/{source_file} 裡對應的實作，自行補上。"
    )


def render_preprocess_step(step: Dict[str, Any]) -> str:
    """產生單一前處理步驟的程式碼。呼叫端負責把回傳字串接在既有的 X_train/X_test 迴圈裡，
    每次呼叫都是「fit 在 X_train、同時套用到 X_train 和 X_test」，跟 preprocess_service.py
    的 apply_preprocess_pipeline_for_split() 語意一致，避免資料洩漏。
    """
    step_type = step.get("type")
    label = PREPROCESS_STEP_LABELS.get(step_type, step_type)
    columns = step.get("columns")
    columns_expr = repr(columns) if columns else "None"

    if step_type not in PREPROCESS_STEP_LABELS:
        if step_type in _UNSUPPORTED_PREPROCESS_STEPS:
            return _unsupported_step_comment(step_type, "preprocess_service.py")
        return _unsupported_step_comment(step_type or "(未知)", "preprocess_service.py")

    lines = [f"    # {label}"]

    if step_type == "fill_na":
        strategy = step.get("strategy", "constant")
        value = step.get("value", 0)
        cols_expr = columns_expr if columns else "X_train.columns"
        if strategy == "mean":
            lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
            lines.append("    _fill_values = X_train[_cols].mean()")
        elif strategy == "median":
            lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
            lines.append("    _fill_values = X_train[_cols].median()")
        elif strategy == "mode":
            lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
            lines.append("    _fill_values = X_train[_cols].mode().iloc[0]")
        else:
            lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
            lines.append(f"    _fill_values = pd.Series({value!r}, index=_cols)")
        lines.append("    X_train[_cols] = X_train[_cols].fillna(_fill_values)")
        lines.append("    X_test[_cols] = X_test[_cols].fillna(_fill_values)")

    elif step_type == "standardize":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    _scaler = StandardScaler().fit(X_train[_cols])")
        lines.append("    X_train[_cols] = _scaler.transform(X_train[_cols])")
        lines.append("    X_test[_cols] = _scaler.transform(X_test[_cols])")

    elif step_type == "normalize":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    _scaler = MinMaxScaler().fit(X_train[_cols])")
        lines.append("    X_train[_cols] = _scaler.transform(X_train[_cols])")
        lines.append("    X_test[_cols] = _scaler.transform(X_test[_cols])")

    elif step_type == "one_hot":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['object', 'category']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    _train_dummies = pd.get_dummies(X_train[_cols], drop_first=False)")
        lines.append("    _test_dummies = pd.get_dummies(X_test[_cols], drop_first=False)")
        lines.append("    for _c in _train_dummies.columns:")
        lines.append("        if _c not in _test_dummies.columns:")
        lines.append("            _test_dummies[_c] = 0")
        lines.append("    _test_dummies = _test_dummies[_train_dummies.columns]")
        lines.append("    X_train = pd.concat([X_train.drop(columns=_cols), _train_dummies], axis=1)")
        lines.append("    X_test = pd.concat([X_test.drop(columns=_cols), _test_dummies], axis=1)")

    elif step_type == "label_encode":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['object', 'category']).columns.tolist()"
        lines.append(f"    for _c in [c for c in ({cols_expr}) if c in X_train.columns]:")
        lines.append("        _enc = LabelEncoder().fit(X_train[_c].astype(str))")
        lines.append("        _known = set(_enc.classes_)")
        lines.append("        X_train[_c] = _enc.transform(X_train[_c].astype(str))")
        lines.append(
            "        X_test[_c] = X_test[_c].astype(str).map("
            "lambda v: _enc.transform([v])[0] if v in _known else -1)"
        )

    elif step_type == "drop_columns":
        lines.append(f"    _cols = {columns_expr if columns else '[]'}")
        lines.append("    X_train = X_train.drop(columns=[c for c in _cols if c in X_train.columns])")
        lines.append("    X_test = X_test.drop(columns=[c for c in _cols if c in X_test.columns])")

    return "\n".join(lines)
```

- [ ] **Step 2: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/code_export_service.py datamind-backend:/tmp/code_export_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/code_export_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 3: 加測試**

在 `backend/tests/test_code_export_service.py` 加：
```python
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler  # noqa: F401 (產生的程式碼會用到)

from services.workflow.code_export_service import render_preprocess_step


def _run_generated_preprocess(step, X_train, X_test):
    """組出一段可以直接 exec() 的程式碼，驗證產生的邏輯本身跑起來跟預期一致，
    不是只驗證語法合法。"""
    code = render_preprocess_step(step)
    namespace = {"pd": pd, "StandardScaler": StandardScaler, "MinMaxScaler": MinMaxScaler,
                 "LabelEncoder": LabelEncoder, "X_train": X_train.copy(), "X_test": X_test.copy()}
    exec(code, namespace)
    return namespace["X_train"], namespace["X_test"]


def test_render_preprocess_fill_na_mean():
    X_train = pd.DataFrame({"a": [1.0, None, 3.0]})
    X_test = pd.DataFrame({"a": [None, 5.0]})
    step = {"type": "fill_na", "strategy": "mean", "columns": ["a"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    assert out_train["a"].tolist() == [1.0, 2.0, 3.0]
    assert out_test["a"].tolist() == [2.0, 5.0]  # 用 train 的平均值（2.0）填 test，不是 test 自己的


def test_render_preprocess_standardize():
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    X_test = pd.DataFrame({"a": [4.0]})
    step = {"type": "standardize", "columns": ["a"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    assert abs(out_train["a"].mean()) < 1e-9  # 標準化後平均應為 0


def test_render_preprocess_one_hot():
    X_train = pd.DataFrame({"color": ["red", "blue"]})
    X_test = pd.DataFrame({"color": ["red", "green"]})  # green 是 train 沒看過的類別
    step = {"type": "one_hot", "columns": ["color"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    assert set(out_train.columns) == set(out_test.columns)  # 欄位要對齊


def test_render_preprocess_drop_columns():
    X_train = pd.DataFrame({"a": [1], "b": [2]})
    X_test = pd.DataFrame({"a": [3], "b": [4]})
    step = {"type": "drop_columns", "columns": ["b"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    assert "b" not in out_train.columns
    assert "b" not in out_test.columns


def test_render_preprocess_unsupported_step_returns_todo_comment():
    code = render_preprocess_step({"type": "knn_impute"})
    assert "TODO" in code
    assert "knn_impute" in code
```

- [ ] **Step 4: 跑測試**

Run:
```bash
docker cp backend/tests/test_code_export_service.py datamind-backend:/tmp/test_code_export_service.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_code_export_service.py -v
```
Expected: 之前 3 個 + 這次新增 5 個，共 8 個 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/code_export_service.py backend/tests/test_code_export_service.py
git commit -m "feat: add preprocessing step code templates for workflow export"
```

---

### Task 3: 特徵工程 step 範本

**Files:**
- Modify: `backend/services/workflow/code_export_service.py`
- Modify: `backend/tests/test_code_export_service.py`

**Interfaces:**
- Consumes: 無
- Produces: `render_feature_engineering_step(step: Dict[str, Any]) -> str`（跟 `render_preprocess_step` 同樣的呼叫慣例，回傳的程式碼假設 `X_train`/`X_test` 已存在）

- [ ] **Step 1: 寫 4 種支援的 step type 範本**

`feature_engineering_service.py` 的 4 種 step 都是「對 train、test 各自獨立套用同一個操作」（不是 fit-on-train-transform-both），這點要跟前處理不一樣，直接照抄該檔案 `apply_feature_engineering_pipeline_for_split()` 的實際行為。在 `code_export_service.py` 接著加：
```python
FEATURE_ENGINEERING_STEP_LABELS: Dict[str, str] = {
    "pca": "PCA 降維",
    "select_relevant_features": "特徵選擇",
    "normalize_features": "Min-Max 正規化（特徵工程）",
    "impute_missing": "缺值填補（特徵工程）",
}

_UNSUPPORTED_FE_STEPS = {
    "discretize_continuous", "continuize_discrete", "select_random_features",
    "randomize_rows", "remove_sparse_features", "cur_decomposition",
}


def render_feature_engineering_step(step: Dict[str, Any]) -> str:
    """特徵工程的 4 種支援 step，對 X_train / X_test 各自獨立套用同一個操作
    （不是像前處理那樣 fit 在 train、套用到兩邊——這是 feature_engineering_service.py
    現有的實際行為，這裡如實反映，不是這次新增的設計）。
    """
    step_type = step.get("type")

    if step_type not in FEATURE_ENGINEERING_STEP_LABELS:
        if step_type in _UNSUPPORTED_FE_STEPS:
            return _unsupported_step_comment(step_type, "feature_engineering_service.py")
        return _unsupported_step_comment(step_type or "(未知)", "feature_engineering_service.py")

    label = FEATURE_ENGINEERING_STEP_LABELS[step_type]
    lines = [f"    # {label}"]

    if step_type == "pca":
        n_components = int(step.get("n_components", 2))
        lines.append(f"    _n = min({n_components}, X_train.select_dtypes(include=['number']).shape[1])")
        lines.append("    _pca_train = PCA(n_components=_n).fit(X_train.select_dtypes(include=['number']))")
        lines.append(
            "    X_train = pd.DataFrame(_pca_train.transform(X_train.select_dtypes(include=['number'])), "
            "columns=[f'pca_{i + 1}' for i in range(_n)], index=X_train.index)"
        )
        lines.append("    _pca_test = PCA(n_components=_n).fit(X_test.select_dtypes(include=['number']))")
        lines.append(
            "    X_test = pd.DataFrame(_pca_test.transform(X_test.select_dtypes(include=['number'])), "
            "columns=[f'pca_{i + 1}' for i in range(_n)], index=X_test.index)"
        )

    elif step_type == "select_relevant_features":
        k = int(step.get("k", 10))
        lines.append(f"    _k = min({k}, X_train.select_dtypes(include=['number']).shape[1])")
        lines.append(
            "    _selector = SelectKBest(score_func=f_classif, k=_k).fit("
            "X_train.select_dtypes(include=['number']), y_train)"
        )
        lines.append(
            "    _selected = X_train.select_dtypes(include=['number']).columns[_selector.get_support()].tolist()"
        )
        lines.append("    X_train = X_train[[c for c in _selected if c in X_train.columns]]")
        lines.append("    X_test = X_test[[c for c in _selected if c in X_test.columns]]")

    elif step_type == "normalize_features":
        columns = step.get("columns")
        cols_expr = repr(columns) if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    X_train[_cols] = MinMaxScaler().fit_transform(X_train[_cols])")
        lines.append("    _cols_test = [c for c in _cols if c in X_test.columns]")
        lines.append("    X_test[_cols_test] = MinMaxScaler().fit_transform(X_test[_cols_test])")

    elif step_type == "impute_missing":
        strategy = step.get("strategy", "constant")
        value = step.get("value", 0)
        if strategy == "mean":
            lines.append("    X_train = X_train.fillna(X_train.mean(numeric_only=True))")
            lines.append("    X_test = X_test.fillna(X_test.mean(numeric_only=True))")
        elif strategy == "median":
            lines.append("    X_train = X_train.fillna(X_train.median(numeric_only=True))")
            lines.append("    X_test = X_test.fillna(X_test.median(numeric_only=True))")
        elif strategy == "mode":
            lines.append("    X_train = X_train.fillna(X_train.mode().iloc[0])")
            lines.append("    X_test = X_test.fillna(X_test.mode().iloc[0])")
        else:
            lines.append(f"    X_train = X_train.fillna({value!r})")
            lines.append(f"    X_test = X_test.fillna({value!r})")

    return "\n".join(lines)
```

- [ ] **Step 2: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/code_export_service.py datamind-backend:/tmp/code_export_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/code_export_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 3: 加測試**

在 `backend/tests/test_code_export_service.py` 加：
```python
from sklearn.decomposition import PCA  # noqa: F401
from sklearn.feature_selection import SelectKBest, f_classif  # noqa: F401

from services.workflow.code_export_service import render_feature_engineering_step


def _run_generated_fe(step, X_train, X_test, y_train=None):
    code = render_feature_engineering_step(step)
    namespace = {
        "pd": pd, "PCA": PCA, "SelectKBest": SelectKBest, "f_classif": f_classif,
        "MinMaxScaler": MinMaxScaler,
        "X_train": X_train.copy(), "X_test": X_test.copy(),
        "y_train": y_train,
    }
    exec(code, namespace)
    return namespace["X_train"], namespace["X_test"]


def test_render_fe_pca():
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
    X_test = pd.DataFrame({"a": [7.0], "b": [8.0]})
    out_train, out_test = _run_generated_fe({"type": "pca", "n_components": 1}, X_train, X_test)
    assert list(out_train.columns) == ["pca_1"]
    assert len(out_train) == 3


def test_render_fe_select_relevant_features():
    X_train = pd.DataFrame({"a": [1, 2, 3, 4], "b": [1, 1, 1, 1]})
    X_test = pd.DataFrame({"a": [5], "b": [1]})
    y_train = pd.Series([0, 0, 1, 1])
    out_train, out_test = _run_generated_fe(
        {"type": "select_relevant_features", "k": 1}, X_train, X_test, y_train=y_train,
    )
    assert list(out_train.columns) == list(out_test.columns)


def test_render_fe_unsupported_step_returns_todo_comment():
    code = render_feature_engineering_step({"type": "randomize_rows"})
    assert "TODO" in code
    assert "randomize_rows" in code
```

- [ ] **Step 4: 跑測試**

Run:
```bash
docker cp backend/tests/test_code_export_service.py datamind-backend:/tmp/test_code_export_service.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_code_export_service.py -v
```
Expected: 之前 8 個 + 這次新增 3 個，共 11 個 PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/code_export_service.py backend/tests/test_code_export_service.py
git commit -m "feat: add feature engineering step code templates for workflow export"
```

---

### Task 4: 驗證方式範本 + 補上一律套用的類別型欄位編碼

**Files:**
- Modify: `backend/services/workflow/code_export_service.py`
- Modify: `backend/tests/test_code_export_service.py`

**Interfaces:**
- Consumes: 無
- Produces: `render_validation_split(validation_config: Dict[str, Any]) -> Tuple[List[str], str]`（回傳 `(需要的 import 陳述式清單, 產生 splits 變數的程式碼字串)`；`splits` 是 `List[Tuple[np.ndarray, np.ndarray]]`，每個 tuple 是 `(train_idx, test_idx)` 的整數位置索引，用 `X.iloc[idx]` 取值）
- Produces: `render_categorical_fallback_encoding() -> str`（一律套用、不受任何 step type 設定影響的固定程式碼區塊，對應 `workflow_service.py` 的 `_prepare_categorical()`）

- [ ] **Step 1: 5 種驗證方式範本**

`workflow_service.py` 的 `_normalize_validation_config()`（第 99-133 行）決定了每個欄位的預設值，這裡的範本要用同樣的預設值。在 `code_export_service.py` 接著加：
```python
def render_validation_split(validation_config: Dict[str, Any]) -> Tuple[List[str], str]:
    """回傳 (import 陳述式清單, 產生 splits 的程式碼)。splits 統一是
    List[Tuple[np.ndarray, np.ndarray]]（train_idx, test_idx 都是整數位置索引），
    不管哪種驗證方式，下游都用同一種方式消費：`for train_idx, test_idx in splits: ...`。

    這段程式碼是頂層模組程式碼（在任何迴圈或函式之外，generate_workflow_script() 是把它
    直接接在檔案的最上層），所以每一行都不能有縮排，這點跟 render_preprocess_step() /
    render_feature_engineering_step() / render_metrics_block()（那三個都是插進迴圈裡面，
    需要縮排）不一樣。
    """
    method = str(validation_config.get("method", "test_on_test")).lower()
    n_splits = int(validation_config.get("n_splits") or 5)
    n_repeats = int(validation_config.get("n_repeats") or 1)
    train_size = float(validation_config.get("train_size") or 0.7)
    stratified = bool(validation_config.get("stratified", True))
    group_column = validation_config.get("group_column")
    shuffle = bool(validation_config.get("shuffle", True))
    random_state = int(validation_config.get("random_state") or 42)
    stratify_arg = "y" if stratified else "None"

    if method == "k_fold":
        cls_name = "StratifiedKFold" if stratified else "KFold"
        split_source = "y" if stratified else "X"
        code = (
            f"# 交叉驗證（{n_splits} 折）\n"
            f"_splitter = {cls_name}(n_splits={n_splits}, shuffle={shuffle}, random_state={random_state})\n"
            f"splits = list(_splitter.split(X, {split_source}))"
        )
        return [f"from sklearn.model_selection import {cls_name}"], code

    if method == "group_k_fold":
        code = (
            "# 依欄位分組的交叉驗證，同一組的資料不會同時出現在 train 跟 test\n"
            f"_groups = X[{group_column!r}]\n"
            f"_splitter = GroupKFold(n_splits={n_splits})\n"
            "splits = list(_splitter.split(X, y, _groups))"
        )
        return ["from sklearn.model_selection import GroupKFold"], code

    if method == "random_sampling":
        cls_name = "StratifiedShuffleSplit" if stratified else "ShuffleSplit"
        split_source = "y" if stratified else "X"
        code = (
            f"# 重複隨機切分（重複 {n_repeats} 次）\n"
            f"_splitter = {cls_name}(n_splits={n_repeats}, train_size={train_size}, "
            f"random_state={random_state})\n"
            f"splits = list(_splitter.split(X, {split_source}))"
        )
        return [f"from sklearn.model_selection import {cls_name}"], code

    if method == "test_on_train":
        code = (
            "# 訓練與測試用同一份資料（僅用於檢查模型是否過擬合，不是正式的效能評估）\n"
            "_train_idx, _ = train_test_split(\n"
            f"    np.arange(len(X)), train_size={train_size}, stratify={stratify_arg}, "
            f"shuffle={shuffle}, random_state={random_state},\n"
            ")\n"
            "splits = [(_train_idx, _train_idx)]"
        )
        return ["from sklearn.model_selection import train_test_split"], code

    # test_on_test（預設）
    code = (
        "# 單次切分成訓練集／測試集\n"
        "_train_idx, _test_idx = train_test_split(\n"
        f"    np.arange(len(X)), train_size={train_size}, stratify={stratify_arg}, "
        f"shuffle={shuffle}, random_state={random_state},\n"
        ")\n"
        "splits = [(_train_idx, _test_idx)]"
    )
    return ["from sklearn.model_selection import train_test_split"], code
```

- [ ] **Step 2: 一律套用的類別型欄位編碼**

`workflow_service.py` 的 `_prepare_categorical()`（第 73-96 行）不管使用者有沒有設定 one_hot 之類的 step，都會在前處理跑完後自動把「剩下還沒處理的類別型欄位」用 `pd.get_dummies(drop_first=True)` 編碼掉——這步驟一定要在匯出的程式碼裡出現，否則使用者的 workflow 如果沒特別設定編碼、剩餘欄位是字串型別，直接拿去訓練模型會報錯，跟畫布上實際執行的行為兜不起來。接著加：
```python
def render_categorical_fallback_encoding() -> str:
    """對應 workflow_service.py 的 _prepare_categorical()：前處理設定跑完後，
    任何還沒被處理掉的類別型欄位，一律 One-Hot 編碼（fit 在 train）。這一段
    不受任何 step type 設定影響，一定會出現在產生的程式碼裡。
    """
    return (
        "    # 前處理設定跑完後，任何還沒被處理掉的類別型欄位，一律 One-Hot 編碼\n"
        "    # （這一步不受上面的前處理設定影響，DataMind 執行 workflow 時一定會做這步）\n"
        "    _object_cols = X_train.select_dtypes(include=['object', 'category']).columns.tolist()\n"
        "    if _object_cols:\n"
        "        _train_dummies = pd.get_dummies(X_train[_object_cols], drop_first=True)\n"
        "        _test_dummies = pd.get_dummies(X_test[_object_cols], drop_first=True)\n"
        "        for _c in _train_dummies.columns:\n"
        "            if _c not in _test_dummies.columns:\n"
        "                _test_dummies[_c] = 0\n"
        "        _test_dummies = _test_dummies[_train_dummies.columns]\n"
        "        X_train = pd.concat([X_train.drop(columns=_object_cols), _train_dummies], axis=1)\n"
        "        X_test = pd.concat([X_test.drop(columns=_object_cols), _test_dummies], axis=1)"
    )
```

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/code_export_service.py datamind-backend:/tmp/code_export_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/code_export_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 加測試**

在 `backend/tests/test_code_export_service.py` 加：
```python
import numpy as np  # noqa: F401
from sklearn.model_selection import (  # noqa: F401
    GroupKFold, KFold, ShuffleSplit, StratifiedKFold, StratifiedShuffleSplit, train_test_split,
)

from services.workflow.code_export_service import render_categorical_fallback_encoding, render_validation_split


def _run_generated_split(validation_config, X, y=None):
    import_lines, code = render_validation_split(validation_config)
    full_source = "\n".join(import_lines) + "\n" + code
    ast.parse(full_source)  # import 陳述式 + 程式碼合起來也要是合法 Python
    namespace = {
        "pd": pd, "np": np, "X": X, "y": y if y is not None else pd.Series([0] * len(X)),
        "StratifiedKFold": StratifiedKFold, "KFold": KFold, "GroupKFold": GroupKFold,
        "StratifiedShuffleSplit": StratifiedShuffleSplit, "ShuffleSplit": ShuffleSplit,
        "train_test_split": train_test_split,
    }
    exec(full_source, namespace)
    return namespace["splits"]


def test_render_validation_split_k_fold():
    X = pd.DataFrame({"a": range(10)})
    y = pd.Series([0, 1] * 5)
    splits = _run_generated_split({"method": "k_fold", "n_splits": 5, "stratified": True}, X, y)
    assert len(splits) == 5
    for train_idx, test_idx in splits:
        assert len(train_idx) + len(test_idx) == 10


def test_render_validation_split_test_on_train_uses_same_indices_for_both():
    X = pd.DataFrame({"a": range(10)})
    splits = _run_generated_split({"method": "test_on_train", "train_size": 0.7}, X)
    assert len(splits) == 1
    train_idx, test_idx = splits[0]
    assert list(train_idx) == list(test_idx)


def test_render_validation_split_test_on_test_train_and_test_disjoint():
    X = pd.DataFrame({"a": range(10)})
    splits = _run_generated_split({"method": "test_on_test", "train_size": 0.7}, X)
    train_idx, test_idx = splits[0]
    assert set(train_idx).isdisjoint(set(test_idx))


def test_render_categorical_fallback_encoding_one_hots_remaining_object_columns():
    code = render_categorical_fallback_encoding()
    namespace = {
        "pd": pd,
        "X_train": pd.DataFrame({"color": ["red", "blue"], "n": [1, 2]}),
        "X_test": pd.DataFrame({"color": ["red", "green"], "n": [3, 4]}),
    }
    exec(code, namespace)
    assert "color" not in namespace["X_train"].columns
    assert list(namespace["X_train"].columns) == list(namespace["X_test"].columns)
```

- [ ] **Step 5: 跑測試**

Run:
```bash
docker cp backend/tests/test_code_export_service.py datamind-backend:/tmp/test_code_export_service.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_code_export_service.py -v
```
Expected: 之前 11 個 + 這次新增 4 個，共 15 個 PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/code_export_service.py backend/tests/test_code_export_service.py
git commit -m "feat: add validation split templates and mandatory categorical encoding"
```

---

### Task 5: 評估指標／信賴區間 + 整合成 `generate_workflow_script()`

**Files:**
- Modify: `backend/services/workflow/code_export_service.py`
- Modify: `backend/tests/test_code_export_service.py`

**Interfaces:**
- Consumes: Task 1-4 的所有 `render_*`/`MODEL_IMPORTS` 函式
- Produces: `generate_workflow_script(payload: Dict[str, Any]) -> str`（主要對外介面，`payload` 的鍵值沿用 `backend/routes/model.py` 的 `_parse_execute_params()` 回傳的 kwargs 形狀）

- [ ] **Step 1: 評估指標與 CI 程式碼**

10 種指標都是標準 `sklearn.metrics` 函式呼叫，不分階段支援。`precision`/`recall`/`f1` 這三個在多分類時要加 `average='macro'`（對照 `test_score_service.py` 第 401-424 行的邏輯，簡化：不處理 `pos_label`/`threshold` 自訂，只處理二元 vs 多分類），`auc`/`auprc` 假設是二元分類、用 `predict_proba` 的正類欄位（最後一欄）。在 `code_export_service.py` 接著加：
```python
_METRIC_LABELS: Dict[str, str] = {
    "accuracy": "準確率", "balanced_accuracy": "平衡準確率", "precision": "精準度",
    "recall": "召回率", "f1": "F1 分數", "auc": "AUC_ROC", "auprc": "AUPRC",
    "specificity": "特異度", "mcc": "MCC", "kappa": "Kappa 係數",
}

_METRIC_SKLEARN_FN: Dict[str, str] = {
    "accuracy": "accuracy_score", "balanced_accuracy": "balanced_accuracy_score",
    "mcc": "matthews_corrcoef", "kappa": "cohen_kappa_score",
}


def render_metrics_block(score_variants: List[Dict[str, Any]], compute_ci: bool) -> Tuple[List[str], str]:
    """回傳 (import 陳述式清單, 評估邏輯的程式碼字串)。程式碼假設 y_test / y_pred / y_score
    (predict_proba 的結果，可能是 None) 已經存在。二元/多分類的判定只看 y_test 的類別數，
    跟 test_score_service.py 用 y_true ∪ y_pred 判定不同——這裡是為了讓產生的程式碼保持簡短
    易讀，刻意的簡化，不是要跟後端逐位元對齊。

    這段程式碼會被插進兩層迴圈裡面（for fold ... / for model ...），所以每一行都是 8 個
    空白的縮排，不是 4 個——呼叫端（generate_workflow_script()）是直接把這段字串接在
    `for _model_name, _model in models.items():` 底下，縮排要跟同一層的其他敘述句對齊。
    """
    metrics = [str(v.get("metric", "")).lower() for v in score_variants]
    metrics = [m for m in metrics if m]

    sklearn_fns = sorted({_METRIC_SKLEARN_FN[m] for m in metrics if m in _METRIC_SKLEARN_FN})
    import_lines = []
    if sklearn_fns:
        import_lines.append(f"from sklearn.metrics import {', '.join(sklearn_fns)}")
    if any(m in {"precision", "recall", "f1"} for m in metrics):
        import_lines.append("from sklearn.metrics import precision_score, recall_score, f1_score")
    if any(m in {"auc", "auprc"} for m in metrics):
        import_lines.append("from sklearn.metrics import roc_auc_score, average_precision_score")
    if any(m == "specificity" for m in metrics):
        import_lines.append("from sklearn.metrics import confusion_matrix")

    lines = ["        _is_multiclass = y_test.nunique() > 2", "        _results = {}"]
    for metric in metrics:
        label = _METRIC_LABELS.get(metric, metric)
        if metric in _METRIC_SKLEARN_FN:
            fn = _METRIC_SKLEARN_FN[metric]
            lines.append(f"        _results[{metric!r}] = {fn}(y_test, y_pred)  # {label}")
        elif metric in {"precision", "recall", "f1"}:
            fn = f"{metric}_score"
            lines.append(
                f"        _results[{metric!r}] = {fn}(y_test, y_pred, "
                f"average='macro' if _is_multiclass else 'binary', zero_division=0)  # {label}"
            )
        elif metric == "specificity":
            lines.append("        _cm = confusion_matrix(y_test, y_pred)")
            lines.append(
                "        _results['specificity'] = (_cm[0, 0] / (_cm[0, 0] + _cm[0, 1])) "
                "if _cm.shape == (2, 2) and (_cm[0, 0] + _cm[0, 1]) else 0.0  # 特異度"
            )
        elif metric in {"auc", "auprc"}:
            fn = "roc_auc_score" if metric == "auc" else "average_precision_score"
            lines.append(
                f"        _results[{metric!r}] = {fn}(y_test, y_score[:, -1]) "
                f"if y_score is not None else None  # {label}（假設二元分類）"
            )
        else:
            lines.append(f"        # ⚠️ 不支援的指標「{metric}」，略過")

    lines.append("        for _name, _value in _results.items():")
    lines.append("            print(f'  {_name}: {_value}')")

    if compute_ci and metrics:
        lines.append("")
        lines.append("        # Bootstrap 95% 信賴區間（重抽樣 1000 次，跟 DataMind 後端算法一致）")
        lines.append("        _rng = np.random.RandomState(42)")
        lines.append("        _n = len(y_test)")
        lines.append("        _y_test_arr = y_test.to_numpy()")
        lines.append(
            "        _y_pred_arr = y_pred.to_numpy() if hasattr(y_pred, 'to_numpy') else np.asarray(y_pred)"
        )
        for metric in metrics:
            if metric in _METRIC_SKLEARN_FN:
                fn = _METRIC_SKLEARN_FN[metric]
                metric_call = f"{fn}(_yt, _yp)"
            elif metric in {"precision", "recall", "f1"}:
                fn = f"{metric}_score"
                metric_call = f"{fn}(_yt, _yp, average='macro' if _is_multiclass else 'binary', zero_division=0)"
            else:
                continue  # specificity/auc/auprc 的 CI 這裡不支援，維持點估計即可
            lines.append(f"        _boot_{metric} = []")
            lines.append("        for _ in range(1000):")
            lines.append("            _idx = _rng.randint(0, _n, _n)")
            lines.append("            try:")
            lines.append("                _yt, _yp = _y_test_arr[_idx], _y_pred_arr[_idx]")
            lines.append(f"                _boot_{metric}.append({metric_call})")
            lines.append("            except Exception:")
            lines.append("                pass")
            lines.append(f"        if _boot_{metric}:")
            lines.append(
                f"            print(f'  {metric} 95% CI: "
                f"[{{np.percentile(_boot_{metric}, 2.5):.4f}}, "
                f"{{np.percentile(_boot_{metric}, 97.5):.4f}}]')"
            )

    return import_lines, "\n".join(lines)
```

- [ ] **Step 2: `generate_workflow_script()` 整合所有區塊**

在檔案最後加：
```python
def _format_step_groups(steps: List[Dict[str, Any]], render_fn) -> str:
    if not steps:
        return "    pass  # 這個 workflow 沒有設定任何步驟"
    return "\n".join(render_fn(step) for step in steps)


def generate_workflow_script(payload: Dict[str, Any]) -> str:
    """payload 的形狀沿用 backend/routes/model.py 的 _parse_execute_params() 回傳的 kwargs：
    target_col, preprocess_pipelines, feature_engineering_pipelines, model_names,
    score_variants, validation_config, compute_ci（其餘鍵值如 resampling_method/tuning_method
    這次不支援，忽略不處理）。
    """
    target_col = payload.get("target_col") or ""
    preprocess_pipelines = payload.get("preprocess_pipelines") or []
    feature_engineering_pipelines = payload.get("feature_engineering_pipelines") or []
    model_names = payload.get("model_names") or []
    score_variants = payload.get("score_variants") or []
    validation_config = payload.get("validation_config") or {"method": "test_on_test"}
    compute_ci = bool(payload.get("compute_ci", False))

    if not model_names:
        raise ValueError("請至少選擇一個模型")

    preprocess_steps = preprocess_pipelines[0] if preprocess_pipelines else []
    feature_steps = feature_engineering_pipelines[0] if feature_engineering_pipelines else []

    model_import_lines, models_code = render_model_construction(model_names)
    split_import_lines, split_code = render_validation_split(validation_config)
    metrics_import_lines, metrics_code = render_metrics_block(score_variants, compute_ci)
    preprocess_code = _format_step_groups(preprocess_steps, render_preprocess_step)
    fe_code = _format_step_groups(feature_steps, render_feature_engineering_step)
    categorical_fallback_code = render_categorical_fallback_encoding()

    fixed_imports = [
        "import numpy as np",
        "import pandas as pd",
        "from sklearn.base import clone",
        "from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler",
        "from sklearn.decomposition import PCA",
        "from sklearn.feature_selection import SelectKBest, f_classif",
    ]
    all_import_lines = list(fixed_imports)
    for line in split_import_lines + model_import_lines + metrics_import_lines:
        if line and line not in all_import_lines:
            all_import_lines.append(line)

    return f'''"""DataMind Workflow 匯出程式碼

由 DataMind 自動產生，重現這個 workflow 在畫布上設定的完整流程：
前處理 → 特徵工程 → 資料切分 → 訓練 → 評估指標{"（含 95% 信賴區間）" if compute_ci else ""}。

部分步驟類型目前還不支援自動產生程式碼，會用「⚠️ TODO」標註，請自行補上對應邏輯。
"""
{chr(10).join(all_import_lines)}

# ── 1. 讀取資料集 ──
# TODO：換成你自己的資料集路徑
DATA_PATH = "your_dataset.csv"
TARGET_COLUMN = {target_col!r}

df = pd.read_csv(DATA_PATH)
y = df[TARGET_COLUMN]
X = df.drop(columns=[TARGET_COLUMN])

# ── 2. 切分資料 ──
{split_code}

# ── 3. 建立模型 ──
{models_code}

# ── 4. 對每個切分、每個模型：前處理 → 特徵工程 → 訓練 → 評估 ──
for _fold_idx, (train_idx, test_idx) in enumerate(splits):
    X_train, X_test = X.iloc[train_idx].copy(), X.iloc[test_idx].copy()
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    # 前處理（fit 在 train，同時套用到 train/test，避免資料洩漏）
{preprocess_code}

{categorical_fallback_code}

    # 特徵工程
{fe_code}

    for _model_name, _model in models.items():
        _clf = clone(_model)
        _clf.fit(X_train, y_train)
        y_pred = pd.Series(_clf.predict(X_test), index=X_test.index)
        y_score = _clf.predict_proba(X_test) if hasattr(_clf, "predict_proba") else None

        print(f"=== {{_model_name}} | Fold {{_fold_idx + 1}} ===")
{metrics_code}
'''
```

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/services/workflow/code_export_service.py datamind-backend:/tmp/code_export_service.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/code_export_service.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 加測試——完整流程 + `ast.parse()` + 實際 exec() 驗證跑得動**

在 `backend/tests/test_code_export_service.py` 加：
```python
from services.workflow.code_export_service import generate_workflow_script


def _sample_payload():
    return {
        "target_col": "label",
        "preprocess_pipelines": [[
            {"type": "fill_na", "strategy": "mean", "columns": ["age"]},
            {"type": "standardize", "columns": ["age"]},
            {"type": "one_hot", "columns": ["sex"]},
        ]],
        "feature_engineering_pipelines": [[
            {"type": "normalize_features", "columns": ["age"]},
        ]],
        "model_names": ["Random Forest", "Logistic Regression"],
        "score_variants": [{"metric": "accuracy"}, {"metric": "f1"}, {"metric": "auc"}],
        "validation_config": {"method": "k_fold", "n_splits": 3, "stratified": True},
        "compute_ci": True,
    }


def test_generate_workflow_script_is_valid_python():
    code = generate_workflow_script(_sample_payload())
    ast.parse(code)  # 語法必須合法


def test_generate_workflow_script_contains_expected_pieces():
    code = generate_workflow_script(_sample_payload())
    assert "RandomForestClassifier(" in code
    assert "LogisticRegression(" in code
    assert "StratifiedKFold(" in code
    assert "TARGET_COLUMN = 'label'" in code
    assert "accuracy_score" in code
    assert "95% 信賴區間" in code


def test_generate_workflow_script_marks_unsupported_step_with_todo():
    payload = _sample_payload()
    payload["preprocess_pipelines"] = [[{"type": "knn_impute"}]]
    code = generate_workflow_script(payload)
    assert "TODO" in code
    assert "knn_impute" in code


def test_generate_workflow_script_raises_without_models():
    payload = _sample_payload()
    payload["model_names"] = []
    with pytest.raises(ValueError, match="至少選擇一個模型"):
        generate_workflow_script(payload)


def test_generate_workflow_script_actually_runs_end_to_end(tmp_path):
    """不只驗證語法合法，實際 exec() 整份產生的程式碼，確認邏輯真的能跑得動、印出結果。"""
    import numpy as np

    rng = np.random.RandomState(0)
    n = 60
    fake_df = pd.DataFrame({
        "age": rng.normal(50, 10, n),
        "sex": rng.choice(["M", "F"], n),
        "label": rng.choice([0, 1], n),
    })
    data_path = tmp_path / "fake.csv"
    fake_df.to_csv(data_path, index=False)

    payload = _sample_payload()
    payload["validation_config"] = {"method": "test_on_test", "train_size": 0.7}
    code = generate_workflow_script(payload)
    code = code.replace('DATA_PATH = "your_dataset.csv"', f'DATA_PATH = {str(data_path)!r}')

    exec(compile(code, "<generated>", "exec"), {"__name__": "__main__"})
```
（最後這個測試需要 `import pytest` 跟 `import pandas as pd` 已經在檔案上方，`pytest.raises` 也要確認 import 進來。）

- [ ] **Step 5: 跑測試**

Run:
```bash
docker cp backend/tests/test_code_export_service.py datamind-backend:/tmp/test_code_export_service.py
docker exec -w /app datamind-backend .venv/bin/python -m pytest /tmp/test_code_export_service.py -v
```
Expected: 之前 15 個 + 這次新增 5 個，共 20 個 PASS。如果 `test_generate_workflow_script_actually_runs_end_to_end` 失敗，通常是產生的程式碼裡變數作用域或縮排有問題，逐段印出 `code` 字串比對縮排。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/services/workflow/code_export_service.py backend/tests/test_code_export_service.py
git commit -m "feat: add metrics/CI templates and assemble generate_workflow_script()"
```

---

### Task 6: 路由 `POST /api/models/workflow/export-code`

**Files:**
- Modify: `backend/routes/model.py`

**Interfaces:**
- Consumes: `generate_workflow_script(payload: Dict[str, Any]) -> str`（Task 5 產出）、既有的 `_parse_execute_params()`（第 149 行）
- Produces: `POST /api/models/workflow/export-code`，成功回傳 `{"success": true, "code": "...", "filename": "workflow_export.py"}`，失敗回傳 `{"success": false, "error": "..."}` + 400

- [ ] **Step 1: 加 import**

`backend/routes/model.py` 檔案開頭找到既有的 import 區塊（`from services.workflow...` 那幾行），新增：
```python
from services.workflow.code_export_service import generate_workflow_script
```

- [ ] **Step 2: 新增路由**

在 `backend/routes/model.py` 裡，`/workflow/execute` 路由（第 267-409 行）結束後、`/workflow/jobs`（第 412 行）之前，新增：
```python
@model_bp.post("/workflow/export-code")
@login_required
def export_workflow_code():
    """把目前 workflow 的設定匯出成一份帶註解的 Python 程式碼。

    跟 /workflow/execute 共用同一套 payload 解析（_parse_execute_params()），
    但不需要真的有資料集檔案——這個路由只是「讀設定、產生程式碼文字」，不執行任何訓練。

    回傳：
        - code：完整的 Python 原始碼字串
        - filename：建議的下載檔名
    """
    _data_path, kwargs = _parse_execute_params()

    if not kwargs.get("model_names"):
        return jsonify({"success": False, "error": "請至少選擇一個模型"}), 400

    try:
        code = generate_workflow_script(kwargs)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"程式碼產生失敗：{exc}"}), 500

    return jsonify({"success": True, "code": code, "filename": "workflow_export.py"})
```

- [ ] **Step 3: 語法檢查**

Run:
```bash
docker cp backend/routes/model.py datamind-backend:/tmp/model.py
docker exec datamind-backend .venv/bin/python -m py_compile /tmp/model.py
```
Expected: 沒有輸出（成功）

- [ ] **Step 4: 驗證路由確實註冊、方法正確**

這個路由背後的邏輯（`_parse_execute_params()` 的參數解析、`generate_workflow_script()` 的程式碼產生）已經分別在既有程式碼跟 Task 5 的單元測試裡驗證過，這裡只需要確認新路由本身有正確掛上去，不需要處理 `@login_required` 的登入機制（那個機制本身跟這次改動無關，其他既有路由已經驗證過它能正常運作）：

Run:
```bash
docker cp backend/routes/model.py datamind-backend:/tmp/model.py
docker exec -w /app datamind-backend .venv/bin/python -c "
from app import create_app
app = create_app()
matches = [r for r in app.url_map.iter_rules() if 'export-code' in r.rule]
assert len(matches) == 1, f'預期剛好 1 條路由，實際找到 {len(matches)} 條'
rule = matches[0]
assert rule.rule == '/api/models/workflow/export-code'
assert 'POST' in rule.methods
print('route registered OK:', rule.rule, sorted(rule.methods))
"
```
Expected: 印出 `route registered OK: /api/models/workflow/export-code [...'POST'...]`，沒有 AssertionError。實際透過瀏覽器登入後的端到端驗證留給 Task 7 完成後的人工驗證清單第 1 項。

- [ ] **Step 5: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add backend/routes/model.py
git commit -m "feat: add POST /api/models/workflow/export-code route"
```

---

### Task 7: 前端「匯出程式碼」按鈕

**Files:**
- Modify: `frontend/src/api/workflow.ts`
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue`

**Interfaces:**
- Consumes: `POST /api/models/workflow/export-code`（Task 6 產出）、既有的 `buildWorkflowPayload()`（`useWorkflowExecution.ts` 已匯出，`WorkflowWorkspace.vue` 透過 `useWorkflowExecution(...)` 取得）
- Produces: `exportWorkflowCode(payload: Record<string, unknown>): Promise<{ code: string, filename: string }>`

- [ ] **Step 1: 新增 API 函式**

`frontend/src/api/workflow.ts` 現有的 `executeWorkflowApi`（第 56-79 行）之後新增：
```typescript
export async function exportWorkflowCode (
  payload: Record<string, unknown>,
): Promise<{ code: string, filename: string }> {
  const response = await fetch('/api/models/workflow/export-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return { code: String(result.code ?? ''), filename: String(result.filename ?? 'workflow_export.py') }
}
```

- [ ] **Step 2: `WorkflowWorkspace.vue` 加按鈕**

現有的「查看結果」按鈕（第 16-23 行）：
```html
    <AppButton
      v-if="workflowResult"
      class="view-results-btn"
      variant="primary"
      @click="router.push(`/hub/projects/${projectId}/result`)"
    >
      查看結果
    </AppButton>
```
改成（新增第二顆按鈕，不需要 `workflowResult` 存在也能按，只要有模型設定就能匯出）：
```html
    <AppButton
      v-if="workflowResult"
      class="view-results-btn"
      variant="primary"
      @click="router.push(`/hub/projects/${projectId}/result`)"
    >
      查看結果
    </AppButton>

    <AppButton
      class="export-code-btn"
      :disabled="exportingCode"
      variant="secondary"
      @click="handleExportCode"
    >
      {{ exportingCode ? '產生中...' : '匯出程式碼' }}
    </AppButton>
```

- [ ] **Step 3: 加 script 邏輯**

`WorkflowWorkspace.vue` 的 `<script setup>` 找到 import 區塊，`import { fetchAvailableModels } from '@/api/workflow'` 那一行改成：
```typescript
  import { exportWorkflowCode, fetchAvailableModels } from '@/api/workflow'
```

找到 `useWorkflowExecution({...})` 呼叫的解構賦值（第 231-241 行附近，含 `workflowResult,` 那個區塊），確認 `buildWorkflowPayload` 有被解構出來——如果目前的解構列表沒有它，加上去：
```typescript
  const {
    workflowResult,
    // ...既有的其他欄位...
    buildWorkflowPayload,
  } = useWorkflowExecution({
```

在 `<script setup>` 裡（`handleExportCode` 適合放在其他 `handle*` 函式附近）新增：
```typescript
  const exportingCode = ref(false)

  async function handleExportCode (): Promise<void> {
    exportingCode.value = true
    try {
      const payload = buildWorkflowPayload()
      const { code, filename } = await exportWorkflowCode(payload)

      const blob = new Blob([code], { type: 'text/x-python' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      workflowError.value = error instanceof Error ? error.message : String(error)
    } finally {
      exportingCode.value = false
    }
  }
```
`ref` 應該已經從 `vue` import 進來（這個檔案已經大量使用 `ref`），不用額外加 import。

- [ ] **Step 4: 加樣式**

現有的 `.view-results-btn`（第 781-786 行）：
```css
  .view-results-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
  }
```
之後新增：
```css
  .export-code-btn {
    position: absolute;
    top: 14px;
    right: 128px;
    z-index: 5;
  }
```
（`workflowResult` 存在時兩顆按鈕併排；不存在時「匯出程式碼」自己單獨在右上角，位置不會因為另一顆按鈕的有無而跳動，因為用的是固定 `right` 值，不是相對排列——這是刻意的簡化，兩顆按鈕文字長度都不長，128px 足夠不重疊。）

- [ ] **Step 5: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 這個專案目前有 53 個既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件、跟本次改動無關）。用 `npm run type-check 2>&1 | grep -c "error TS"` 確認還是 53，或用 `grep -iE "WorkflowWorkspace|api/workflow"` 確認輸出裡沒有這兩個檔案的錯誤。

- [ ] **Step 6: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/api/workflow.ts frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: add export-code button to workflow canvas"
```

---

## 完成後的人工驗證

七個 task 都完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（前端/後端 dev server 都已在跑，直接測，不需要另開 worktree 連結）：

1. 開一個已經設定好前處理（用已支援的 6 種其中幾種）、特徵工程（4 種其中幾種）、至少一個模型、一種驗證方式的專案，進 workflow 畫布，點「匯出程式碼」，確認下載到 `workflow_export.py`
2. 打開下載的檔案，確認：檔頭有中文說明註解、每個前處理/特徵工程步驟前面都有中文註解、`TARGET_COLUMN` 是真實的目標欄位名稱（不是 placeholder）
3. 把 `DATA_PATH` 換成一份真實的資料集路徑，用 `python3 workflow_export.py` 實際執行，確認能跑完並印出評估指標數字
4. 開啟 Compute CI 後再匯出一次，確認程式碼裡有 bootstrap 信賴區間的區塊，實際執行後有印出信賴區間範圍
5. 在前處理步驟裡加一個目前不支援的 step type（例如 `knn_impute`——需要透過 API 或既有 UI 想辦法讓 workflow 設定包含這個 step type，如果目前 UI 沒有入口，可以先確認：至少後端邏輯正確、等以後真的有 UI 可以設定這些進階 step 時不用再改這裡），確認匯出的程式碼裡有清楚的 TODO 註解
6. 沒有選任何模型的狀態下點「匯出程式碼」，確認畫面顯示錯誤訊息、沒有觸發下載
7. 確認「匯出程式碼」按鈕不需要等 workflow 執行完成（`workflowResult` 為 null）也能正常運作
