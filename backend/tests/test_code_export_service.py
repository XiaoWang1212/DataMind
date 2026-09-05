import ast
import textwrap
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, StandardScaler  # noqa: F401 (產生的程式碼會用到)
from sklearn.decomposition import PCA  # noqa: F401
from sklearn.feature_selection import SelectKBest, f_classif  # noqa: F401
from sklearn.model_selection import (  # noqa: F401
    GroupKFold, KFold, ShuffleSplit, StratifiedKFold, StratifiedShuffleSplit, train_test_split,
)

from services.model.registry import ModelRegistry
from services.workflow.code_export_service import (
    MODEL_IMPORTS, _comment_safe, _unsupported_step_comment, generate_workflow_script,
    render_categorical_fallback_encoding, render_feature_engineering_step, render_metrics_block,
    render_model_construction, render_preprocess_step, render_validation_split,
)


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


def _run_generated_preprocess(step, X_train, X_test):
    """組出一段可以直接 exec() 的程式碼，驗證產生的邏輯本身跑起來跟預期一致，
    不是只驗證語法合法。"""
    code = render_preprocess_step(step)
    # 去掉迴圈層級的縮排，讓程式碼可以在模組層級執行
    code = textwrap.dedent(code)
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


# Regression tests: column mismatch between X_train and X_test
def test_render_preprocess_fill_na_train_only_column():
    """X_train has a column that X_test lacks — should not crash, just skip X_test side."""
    X_train = pd.DataFrame({"a": [1.0, None, 3.0], "b": [10.0, 20.0, 30.0]})
    X_test = pd.DataFrame({"a": [None, 5.0]})  # Missing "b"
    step = {"type": "fill_na", "strategy": "mean", "columns": ["a", "b"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify no crash and output is sensible
    assert out_train["a"].tolist() == [1.0, 2.0, 3.0]
    assert out_test["a"].tolist() == [2.0, 5.0]


def test_render_preprocess_standardize_train_only_column():
    """X_train has a column that X_test lacks — should not crash."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    X_test = pd.DataFrame({"a": [4.0]})  # Missing "b"
    step = {"type": "standardize", "columns": ["a", "b"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify no crash
    assert "a" in out_train.columns
    assert "a" in out_test.columns


def test_render_preprocess_normalize_train_only_column():
    """X_train has a column that X_test lacks — should not crash."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    X_test = pd.DataFrame({"a": [4.0]})  # Missing "b"
    step = {"type": "normalize", "columns": ["a", "b"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify no crash
    assert "a" in out_train.columns
    assert "a" in out_test.columns


def test_render_preprocess_one_hot_train_only_column():
    """X_train has a column that X_test lacks — should not crash."""
    X_train = pd.DataFrame({"color": ["red", "blue"], "size": ["small", "large"]})
    X_test = pd.DataFrame({"color": ["red"]})  # Missing "size"
    step = {"type": "one_hot", "columns": ["color", "size"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify no crash and column count changed (dummies added)
    assert "color" not in out_train.columns  # Original should be replaced with dummies
    assert "color" not in out_test.columns


def test_render_preprocess_label_encode_train_only_column():
    """X_train has a column that X_test lacks — should not crash."""
    X_train = pd.DataFrame({"cat": ["a", "b"], "size": ["S", "L"]})
    X_test = pd.DataFrame({"cat": ["a"]})  # Missing "size"
    step = {"type": "label_encode", "columns": ["cat", "size"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify no crash
    assert "cat" in out_train.columns
    assert "cat" in out_test.columns


# Regression tests: configured columns don't exist in X_train
def test_render_preprocess_fill_na_mode_nonexistent_columns():
    """Configured columns don't exist in X_train — should skip without crashing."""
    X_train = pd.DataFrame({"a": [1, 2, 3]})
    X_test = pd.DataFrame({"a": [4, 5]})
    step = {"type": "fill_na", "strategy": "mode", "columns": ["nonexistent"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify unchanged (since nonexistent columns don't exist in X_train)
    assert out_train.equals(X_train)
    assert out_test.equals(X_test)


def test_render_preprocess_standardize_nonexistent_columns():
    """Configured columns don't exist in X_train — should skip without crashing."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    X_test = pd.DataFrame({"a": [4.0]})
    step = {"type": "standardize", "columns": ["nonexistent"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify unchanged
    assert out_train.equals(X_train)
    assert out_test.equals(X_test)


def test_render_preprocess_normalize_nonexistent_columns():
    """Configured columns don't exist in X_train — should skip without crashing."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    X_test = pd.DataFrame({"a": [4.0]})
    step = {"type": "normalize", "columns": ["nonexistent"]}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    # Verify unchanged
    assert out_train.equals(X_train)
    assert out_test.equals(X_test)


def _run_generated_fe(step, X_train, X_test, y_train=None):
    code = render_feature_engineering_step(step)
    # 去掉迴圈層級的縮排，讓程式碼可以在模組層級執行
    code = textwrap.dedent(code)
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


def test_render_fe_pca_zero_numeric_columns():
    """PCA with zero numeric columns should not crash, just leave frame unchanged."""
    X_train = pd.DataFrame({"a": ["x", "y", "z"]})  # All non-numeric
    X_test = pd.DataFrame({"a": ["w"]})
    out_train, out_test = _run_generated_fe({"type": "pca", "n_components": 1}, X_train, X_test)
    # Should not crash and frame should be unchanged
    assert out_train.equals(X_train)
    assert out_test.equals(X_test)


def test_render_fe_select_relevant_features_zero_numeric_columns():
    """SelectKBest with zero numeric columns should not crash, return zero-column frame."""
    X_train = pd.DataFrame({"a": ["x", "y", "z", "w"]})  # All non-numeric
    X_test = pd.DataFrame({"a": ["v"]})
    y_train = pd.Series([0, 0, 1, 1])
    out_train, out_test = _run_generated_fe(
        {"type": "select_relevant_features", "k": 1}, X_train, X_test, y_train=y_train,
    )
    # Should not crash, and result should have no columns (all non-numeric filtered out)
    assert len(out_train.columns) == 0
    assert len(out_test.columns) == 0


def test_render_fe_normalize_features_happy_path():
    """normalize_features with valid numeric columns should work."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [10.0, 20.0, 30.0]})
    X_test = pd.DataFrame({"a": [4.0], "b": [40.0]})
    out_train, out_test = _run_generated_fe(
        {"type": "normalize_features", "columns": ["a", "b"]}, X_train, X_test
    )
    # Verify normalized (values should be in [0, 1] range)
    assert (out_train["a"] >= 0).all() and (out_train["a"] <= 1).all()
    assert (out_train["b"] >= 0).all() and (out_train["b"] <= 1).all()


def test_render_fe_normalize_features_nonexistent_columns():
    """normalize_features with nonexistent column spec should not crash."""
    X_train = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    X_test = pd.DataFrame({"a": [4.0]})
    out_train, out_test = _run_generated_fe(
        {"type": "normalize_features", "columns": ["nonexistent"]}, X_train, X_test
    )
    # Should not crash and frame should be unchanged
    assert out_train.equals(X_train)
    assert out_test.equals(X_test)


def test_render_fe_impute_missing_mode_happy_path():
    """impute_missing with mode strategy should work on normal data."""
    X_train = pd.DataFrame({"a": [1, 1, 2, None], "b": [5, 5, 5, 5]})
    X_test = pd.DataFrame({"a": [None], "b": [5]})
    out_train, out_test = _run_generated_fe(
        {"type": "impute_missing", "strategy": "mode"}, X_train, X_test
    )
    # Mode of "a" in train is 1, should be filled
    assert out_train["a"].isna().sum() == 0
    assert out_test["a"].isna().sum() == 0


def test_render_fe_impute_missing_mode_entirely_nan_column():
    """impute_missing with mode strategy should handle entirely NaN columns with fallback."""
    X_train = pd.DataFrame({"a": [None, None, None], "b": [1, 2, 3]})
    X_test = pd.DataFrame({"a": [None], "b": [4]})
    out_train, out_test = _run_generated_fe(
        {"type": "impute_missing", "strategy": "mode", "value": 0}, X_train, X_test
    )
    # Should not crash; column with all NaN should be filled with fallback value (0)
    assert out_train["a"].isna().sum() == 0
    assert out_test["a"].isna().sum() == 0
    # Verify fallback value was used
    assert out_train["a"].iloc[0] == 0


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
    exec(textwrap.dedent(code), namespace)
    assert "color" not in namespace["X_train"].columns
    assert list(namespace["X_train"].columns) == list(namespace["X_test"].columns)


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


def test_generate_workflow_script_multiclass_target_with_auc_and_ci_runs_end_to_end(tmp_path):
    """迴歸測試：Finding 1 — 多分類 target + auc/auprc 之前會讓 roc_auc_score() 直接
    crash，炸掉整個 export（因為插在雙層迴圈裡，第一次出錯就中斷後面所有 fold/model）。
    修正後應該優雅地把該指標值設成 None，而不是中止整個腳本。"""
    rng = np.random.RandomState(1)
    n = 90
    fake_df = pd.DataFrame({
        "age": rng.normal(50, 10, n),
        "sex": rng.choice(["M", "F"], n),
        "label": rng.choice([0, 1, 2], n),  # 3 類，觸發 _is_multiclass
    })
    data_path = tmp_path / "fake_multiclass.csv"
    fake_df.to_csv(data_path, index=False)

    payload = _sample_payload()
    payload["score_variants"] = [
        {"metric": "accuracy"}, {"metric": "f1"}, {"metric": "auc"}, {"metric": "auprc"},
    ]
    payload["validation_config"] = {"method": "test_on_test", "train_size": 0.7}
    payload["compute_ci"] = True
    code = generate_workflow_script(payload)
    code = code.replace('DATA_PATH = "your_dataset.csv"', f'DATA_PATH = {str(data_path)!r}')

    exec(compile(code, "<generated>", "exec"), {"__name__": "__main__"})


def test_render_metrics_block_dedupes_duplicate_metric_names():
    """迴歸測試：Finding 2 — score_variants 裡同一個 metric 重複出現時（真實的
    generate_score_variants() 會產生 cartesian product，同名 metric 合法地重複），
    不應該重複產生同一個 bootstrap 迴圈區塊，否則 CI 會用不同的隨機抽樣算出兩個
    互相矛盾的結果，且浪費一倍運算時間。"""
    score_variants = [{"metric": "accuracy"}, {"metric": "accuracy"}, {"metric": "f1"}]
    _, code = render_metrics_block(score_variants, compute_ci=True)
    assert code.count("_boot_accuracy = []") == 1
    assert code.count("_results['accuracy']") == 1


def test_generate_workflow_script_string_labeled_binary_target_runs_end_to_end(tmp_path):
    """迴歸測試：Finding 3 — target 是字串標籤（例如 "yes"/"no"）時，precision/recall/f1
    在 average='binary' 底下預設 pos_label=1，會直接 crash（1 不是合法的字串類別標籤）。
    修正後應該用 sorted(y_test.unique())[-1] 當作 pos_label，跟 confusion_matrix 的
    升冪排序慣例一致。"""
    rng = np.random.RandomState(2)
    n = 60
    fake_df = pd.DataFrame({
        "age": rng.normal(50, 10, n),
        "sex": rng.choice(["M", "F"], n),
        "label": rng.choice(["yes", "no"], n),
    })
    data_path = tmp_path / "fake_string_label.csv"
    fake_df.to_csv(data_path, index=False)

    payload = _sample_payload()
    payload["score_variants"] = [{"metric": "accuracy"}, {"metric": "f1"}]
    payload["validation_config"] = {"method": "test_on_test", "train_size": 0.7}
    code = generate_workflow_script(payload)
    code = code.replace('DATA_PATH = "your_dataset.csv"', f'DATA_PATH = {str(data_path)!r}')

    exec(compile(code, "<generated>", "exec"), {"__name__": "__main__"})


def test_generate_workflow_script_string_labeled_binary_target_with_auprc_runs_end_to_end(tmp_path):
    """最終整合審查 Fix 1 迴歸測試：target 是字串標籤（例如 "yes"/"no"）且指標包含 auprc 時，
    average_precision_score() 預設 pos_label=1 會直接 crash（ValueError: pos_label=1 is not
    a valid label）。修正後 auprc 要跟其他二元分類指標一樣，用 _pos_label（sorted(y_test.unique())[-1]）。
    """
    rng = np.random.RandomState(3)
    n = 60
    fake_df = pd.DataFrame({
        "age": rng.normal(50, 10, n),
        "sex": rng.choice(["M", "F"], n),
        "label": rng.choice(["yes", "no"], n),
    })
    data_path = tmp_path / "fake_string_label_auprc.csv"
    fake_df.to_csv(data_path, index=False)

    payload = _sample_payload()
    payload["score_variants"] = [{"metric": "accuracy"}, {"metric": "f1"}, {"metric": "auprc"}]
    payload["validation_config"] = {"method": "test_on_test", "train_size": 0.7}
    code = generate_workflow_script(payload)
    code = code.replace('DATA_PATH = "your_dataset.csv"', f'DATA_PATH = {str(data_path)!r}')

    # 確認產生的程式碼真的把 pos_label=_pos_label 接在 average_precision_score 呼叫上，
    # 而不是跟 auc 共用同一段沒有 pos_label 的程式碼
    assert "average_precision_score(y_test, y_score[:, -1], pos_label=_pos_label)" in code
    assert "roc_auc_score(y_test, y_score[:, -1], pos_label=_pos_label)" not in code

    exec(compile(code, "<generated>", "exec"), {"__name__": "__main__"})


def test_render_validation_split_leave_one_out_produces_todo_warning():
    """Fix 2 迴歸測試：leave_one_out 是真實、使用者可選的驗證方式，但目前沒有對應的
    程式碼範本，會悄悄退回成 test_on_test（單次 70/30 切分），卻沒有任何警告。
    修正後應該在退回的程式碼裡加上明顯的 TODO 警告註解，說明用了哪種不支援的方式。"""
    _, code = render_validation_split({"method": "leave_one_out"})
    assert "TODO" in code
    assert "leave_one_out" in code


def test_render_validation_split_group_k_fold_without_group_column_raises_clear_error():
    """Fix 3 迴歸測試：group_k_fold 沒有指定 group_column 時，原本會產生 `X[None]`，
    執行時丟出不易理解的 KeyError: None。修正後應該產生清楚的 raise ValueError，
    比照 workflow_service.py 遇到同樣情況時的錯誤訊息。"""
    _, code = render_validation_split({"method": "group_k_fold", "group_column": None})
    assert "raise ValueError" in code
    assert "X[None]" not in code


def test_render_validation_split_group_k_fold_missing_group_column_key_raises_clear_error():
    """同上，但 group_column 這個 key 完全沒有出現在 config 裡（而不是明確傳 None）。"""
    _, code = render_validation_split({"method": "group_k_fold"})
    assert "raise ValueError" in code
    assert "X[None]" not in code


def test_render_preprocess_fill_na_mode_entirely_nan_column():
    """Fix 4 迴歸測試：fill_na/mode 遇到整欄都是 NaN 的欄位時，原本的
    `X_train[_cols].mode().iloc[0]` 會因為 .mode() 回傳空結果而丟出
    IndexError: single positional indexer is out-of-bounds。修正後應該逐欄計算，
    遇到空的 mode 就退回指定的 fallback 值，跟 impute_missing/mode 的處理方式一致。"""
    X_train = pd.DataFrame({"a": [None, None, None], "b": [1.0, 2.0, 3.0]})
    X_test = pd.DataFrame({"a": [None], "b": [4.0]})
    step = {"type": "fill_na", "strategy": "mode", "columns": ["a", "b"], "value": 0}
    out_train, out_test = _run_generated_preprocess(step, X_train, X_test)
    assert out_train["a"].isna().sum() == 0
    assert out_test["a"].isna().sum() == 0
    assert out_train["a"].iloc[0] == 0


def test_comment_safe_strips_embedded_newlines():
    """Fix 5 迴歸測試：外部字串（例如 step type）如果包含換行，直接塞進 `#` 開頭的
    註解行會讓換行後面的內容變成產生檔案裡真的會被執行的程式碼（ast.parse() 逐行看
    仍然合法，但下載下來的 .py 檔案就被注入了）。_comment_safe() 應該要把換行拿掉。"""
    malicious = "evil\nimport os\nos.system('rm -rf /')\n#"
    safe = _comment_safe(malicious)
    assert "\n" not in safe
    assert "\r" not in safe


def test_unsupported_step_comment_with_embedded_newline_stays_single_logical_comment():
    """Fix 5 迴歸測試：確認 _unsupported_step_comment() 真的套用了 _comment_safe()，
    含有換行的 step type 不會讓產生的程式碼行數暴增（也就是不會有內容跳出註解）。"""
    malicious_type = "evil\nimport os\nos.system('echo pwned')\n#"
    code = _unsupported_step_comment(malicious_type, "preprocess_service.py")
    # 原本這個函式回傳固定 2 行（TODO 說明 + 參考路徑），套用 _comment_safe 後應該還是 2 行，
    # 不應該因為 step_type 裡的換行而多出額外的、會被當成獨立陳述句執行的行數。
    assert len(code.splitlines()) == 2
    assert "\nimport os" not in code
    assert "os.system" in code  # 內容還在，只是不再是獨立一行的可執行敘述


def test_render_preprocess_step_unsupported_type_with_embedded_newline_is_comment_safe():
    """比照上一個測試，但走完整的 render_preprocess_step() 路徑（走 _UNSUPPORTED_PREPROCESS_STEPS
    以外的未知 step type 分支）。"""
    malicious_type = "unknown_step\nimport os\nos.system('echo pwned')\n#"
    code = render_preprocess_step({"type": malicious_type})
    assert "\nimport os" not in code
