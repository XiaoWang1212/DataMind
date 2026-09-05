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
