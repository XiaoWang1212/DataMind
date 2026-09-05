"""把 workflow 的設定（前處理、特徵工程、模型、驗證方式、評估指標、信賴區間）
轉成一份帶中文註解、可直接執行的 Python 程式碼字串。

跟 workflow_service.py／test_score_service.py／preprocess_service.py／
feature_engineering_service.py 是平行、獨立的功能，不會呼叫、也不會被它們呼叫，
純粹是「讀同一份設定、輸出成另一種形式」。
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sklearn.utils._pprint import _EstimatorPrettyPrinter

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


def _render_estimator(estimator: Any) -> str:
    """渲染 sklearn 估計子的完整、未截斷的 repr。

    避免 sklearn 的預設 __repr__() 因 n_max_elements_to_show=30 而截斷參數列表
    （例如 XGBoost 有 ~40 個參數），導致產生的程式碼包含 `...` 在關鍵字參數之間，
    造成語法錯誤。改為直接使用 _EstimatorPrettyPrinter 並提升 n_max_elements_to_show。
    """
    pp = _EstimatorPrettyPrinter(
        compact=True,
        indent=1,
        indent_at_name=True,
        n_max_elements_to_show=1000,
    )
    return pp.pformat(estimator)


def _inject_missing_imports(rendered_code: str, import_lines: List[str]) -> None:
    """檢查渲染的程式碼是否包含裸露的 `nan`/`inf`/`array`/`dtype` 等符號，
    並將必要的 import 語句注入 import_lines（去重）。

    例如 XGBoost 的 repr 會包含 `missing=nan`，但 `nan` 沒有在作用域內定義。
    """
    # 檢查裸露的 nan、inf 等 tokens（word boundary 確保不在識別符內部）
    if re.search(r'\bnan\b', rendered_code):
        import_stmt = "from numpy import nan"
        if import_stmt not in import_lines:
            import_lines.append(import_stmt)

    if re.search(r'\binf\b', rendered_code):
        import_stmt = "from numpy import inf"
        if import_stmt not in import_lines:
            import_lines.append(import_stmt)

    if re.search(r'\barray\b', rendered_code):
        import_stmt = "from numpy import array"
        if import_stmt not in import_lines:
            import_lines.append(import_stmt)

    if re.search(r'\bdtype\b', rendered_code):
        import_stmt = "from numpy import dtype"
        if import_stmt not in import_lines:
            import_lines.append(import_stmt)


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
            estimator_repr = _render_estimator(model_config.create_estimator())
        except Exception as exc:  # pragma: no cover - 目前所有已註冊模型都能正常 repr()
            entries.append(
                f"    # ⚠️ TODO：模型「{name}」目前無法自動產生建構子程式碼（{exc}），"
                "請自行參考 DataMind 原始碼手動補上。"
            )
            continue

        # 檢查渲染的程式碼是否包含需要額外 import 的裸露符號（例如 XGBoost 的 `nan`）
        _inject_missing_imports(estimator_repr, import_lines)

        entries.append(f"    {name!r}: {estimator_repr},")

    if not entries:
        body = "    # ⚠️ 沒有任何可用的模型，請回 workflow 的 Settings 節點至少新增一個模型。"
    else:
        body = "\n".join(entries)

    code = "models = {\n" + body + "\n}"
    return import_lines, code


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
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    if _cols:")
        if strategy == "mean":
            lines.append("        _fill_values = X_train[_cols].mean()")
        elif strategy == "median":
            lines.append("        _fill_values = X_train[_cols].median()")
        elif strategy == "mode":
            lines.append("        _fill_values = X_train[_cols].mode().iloc[0]")
        else:
            lines.append(f"        _fill_values = pd.Series({value!r}, index=_cols)")
        lines.append("        X_train[_cols] = X_train[_cols].fillna(_fill_values)")
        lines.append("        _cols_test = [c for c in _cols if c in X_test.columns]")
        lines.append("        if _cols_test:")
        lines.append("            X_test[_cols_test] = X_test[_cols_test].fillna(_fill_values)")

    elif step_type == "standardize":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    if _cols:")
        lines.append("        _scaler = StandardScaler().fit(X_train[_cols])")
        lines.append("        X_train[_cols] = _scaler.transform(X_train[_cols])")
        lines.append("        _cols_test = [c for c in _cols if c in X_test.columns]")
        lines.append("        if _cols_test == _cols:")
        lines.append("            X_test[_cols_test] = _scaler.transform(X_test[_cols_test])")

    elif step_type == "normalize":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    if _cols:")
        lines.append("        _scaler = MinMaxScaler().fit(X_train[_cols])")
        lines.append("        X_train[_cols] = _scaler.transform(X_train[_cols])")
        lines.append("        _cols_test = [c for c in _cols if c in X_test.columns]")
        lines.append("        if _cols_test == _cols:")
        lines.append("            X_test[_cols_test] = _scaler.transform(X_test[_cols_test])")

    elif step_type == "one_hot":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['object', 'category']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    if _cols:")
        lines.append("        _train_dummies = pd.get_dummies(X_train[_cols], drop_first=False)")
        lines.append("        X_train = pd.concat([X_train.drop(columns=_cols), _train_dummies], axis=1)")
        lines.append("        _cols_test = [c for c in _cols if c in X_test.columns]")
        lines.append("        if _cols_test:")
        lines.append("            _test_dummies = pd.get_dummies(X_test[_cols_test], drop_first=False)")
        lines.append("            for _c in _train_dummies.columns:")
        lines.append("                if _c not in _test_dummies.columns:")
        lines.append("                    _test_dummies[_c] = 0")
        lines.append("            _test_dummies = _test_dummies[_train_dummies.columns]")
        lines.append("            X_test = pd.concat([X_test.drop(columns=_cols_test), _test_dummies], axis=1)")

    elif step_type == "label_encode":
        cols_expr = columns_expr if columns else "X_train.select_dtypes(include=['object', 'category']).columns.tolist()"
        lines.append(f"    for _c in [c for c in ({cols_expr}) if c in X_train.columns]:")
        lines.append("        _enc = LabelEncoder().fit(X_train[_c].astype(str))")
        lines.append("        _known = set(_enc.classes_)")
        lines.append("        X_train[_c] = _enc.transform(X_train[_c].astype(str))")
        lines.append("        if _c in X_test.columns:")
        lines.append(
            "            X_test[_c] = X_test[_c].astype(str).map("
            "lambda v: _enc.transform([v])[0] if v in _known else -1)"
        )

    elif step_type == "drop_columns":
        lines.append(f"    _cols = {columns_expr if columns else '[]'}")
        lines.append("    X_train = X_train.drop(columns=[c for c in _cols if c in X_train.columns])")
        lines.append("    X_test = X_test.drop(columns=[c for c in _cols if c in X_test.columns])")

    return "\n".join(lines)


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
        lines.append("    _numeric_train = X_train.select_dtypes(include=['number'])")
        lines.append("    if not _numeric_train.empty:")
        lines.append(f"        _n = min({n_components}, _numeric_train.shape[1])")
        lines.append("        _pca_train = PCA(n_components=_n).fit(_numeric_train)")
        lines.append(
            "        X_train = pd.DataFrame(_pca_train.transform(_numeric_train), "
            "columns=[f'pca_{i + 1}' for i in range(_n)], index=X_train.index)"
        )
        lines.append("    _numeric_test = X_test.select_dtypes(include=['number'])")
        lines.append("    if not _numeric_test.empty:")
        lines.append(f"        _n_test = min({n_components}, _numeric_test.shape[1])")
        lines.append("        _pca_test = PCA(n_components=_n_test).fit(_numeric_test)")
        lines.append(
            "        X_test = pd.DataFrame(_pca_test.transform(_numeric_test), "
            "columns=[f'pca_{i + 1}' for i in range(_n_test)], index=X_test.index)"
        )

    elif step_type == "select_relevant_features":
        k = int(step.get("k", 10))
        lines.append("    _numeric_train = X_train.select_dtypes(include=['number'])")
        lines.append("    if not _numeric_train.empty:")
        lines.append(f"        _k = min({k}, _numeric_train.shape[1])")
        lines.append(
            "        _selector = SelectKBest(score_func=f_classif, k=_k).fit(_numeric_train, y_train)"
        )
        lines.append("        _selected = _numeric_train.columns[_selector.get_support()].tolist()")
        lines.append("    else:")
        lines.append("        _selected = []")
        lines.append("    X_train = X_train[[c for c in _selected if c in X_train.columns]]")
        lines.append("    X_test = X_test[[c for c in _selected if c in X_test.columns]]")

    elif step_type == "normalize_features":
        columns = step.get("columns")
        cols_expr = repr(columns) if columns else "X_train.select_dtypes(include=['number']).columns.tolist()"
        lines.append(f"    _cols = [c for c in ({cols_expr}) if c in X_train.columns]")
        lines.append("    if _cols:")
        lines.append("        X_train[_cols] = MinMaxScaler().fit_transform(X_train[_cols])")
        lines.append(f"    _cols_test = [c for c in ({cols_expr}) if c in X_test.columns]")
        lines.append("    if _cols_test:")
        lines.append("        X_test[_cols_test] = MinMaxScaler().fit_transform(X_test[_cols_test])")

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
            lines.append("    for _col in X_train.columns:")
            lines.append("        _mode = X_train[_col].mode()")
            lines.append(f"        X_train[_col] = X_train[_col].fillna(_mode.iloc[0] if not _mode.empty else {value!r})")
            lines.append("    for _col in X_test.columns:")
            lines.append("        _mode = X_test[_col].mode()")
            lines.append(f"        X_test[_col] = X_test[_col].fillna(_mode.iloc[0] if not _mode.empty else {value!r})")
        else:
            lines.append(f"    X_train = X_train.fillna({value!r})")
            lines.append(f"    X_test = X_test.fillna({value!r})")

    return "\n".join(lines)


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
