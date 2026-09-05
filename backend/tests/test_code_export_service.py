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
