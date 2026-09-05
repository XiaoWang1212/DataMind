import ast
from typing import Any, Dict

import numpy as np

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


def test_render_model_construction_xgboost_produces_valid_syntax():
    """回歸測試：XGBoost repr 曾因截斷而產生語法錯誤（Finding 1），
    以及包含未定義的 `nan` 符號（Finding 2）。確保這些都已修正。
    """
    import_lines, code = render_model_construction(["XGBoost"])

    # 驗證語法合法
    full_source = "\n".join(import_lines) + "\n" + code
    ast.parse(full_source)

    # 驗證包含完整的參數（未被截斷）
    assert "XGBClassifier(" in code
    # 確保 XGBoost 的參數沒有被截斷成 `...`
    assert "..." not in code or code.count("...") == 0  # 允許註解中有 `...`，但模型定義中不應有

    # 驗證含有 `nan` import 來修正 Finding 2
    assert "from numpy import nan" in import_lines or "nan" not in code


def test_render_model_construction_all_models_produce_valid_syntax():
    """全面回歸測試：每個已註冊的模型都應產生合法的、可執行的 Python 程式碼。

    這個測試本應在原始提交時就存在，能夠抓到 XGBoost 的截斷和 `nan` 問題。
    """
    registered_models = ModelRegistry.list_models()

    for model_name in registered_models:
        import_lines, code = render_model_construction([model_name])

        # 驗證程式碼語法合法
        full_source = "\n".join(import_lines) + "\n" + code
        try:
            ast.parse(full_source)
        except SyntaxError as e:
            raise AssertionError(
                f"模型 {model_name!r} 產生的程式碼語法不合法：{e}\n"
                f"Import：{import_lines}\n"
                f"Code：{code}"
            )


def test_render_model_construction_all_models_are_executable():
    """全面執行測試：產生的程式碼應該能在真實 Python 環境中執行，
    不應有 NameError/SyntaxError/未定義的符號等。

    這會捕捉到例如 XGBoost 的 `nan` 不在作用域內的問題。
    """
    registered_models = ModelRegistry.list_models()

    for model_name in registered_models:
        import_lines, code = render_model_construction([model_name])

        # 建立執行環境，包含所有必要的 import
        namespace: Dict[str, Any] = {}

        # 先執行 import 語句
        for import_stmt in import_lines:
            try:
                exec(import_stmt, namespace)
            except Exception as e:
                raise AssertionError(
                    f"模型 {model_name!r} 的 import 語句執行失敗：{import_stmt}\n{e}"
                )

        # 再執行模型構造程式碼
        try:
            exec(code, namespace)
        except Exception as e:
            raise AssertionError(
                f"模型 {model_name!r} 的程式碼執行失敗：{e}\n"
                f"Import：{import_lines}\n"
                f"Code：{code}"
            )

        # 驗證產生了 models 字典
        assert "models" in namespace, f"模型 {model_name!r} 的程式碼未定義 models 字典"
