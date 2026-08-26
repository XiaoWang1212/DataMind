"""驗證 _normalize_validation_config 能處理欄位值為 JSON null（Python None）的情況。

Gemini 論文提取的系統提示（gemini_service.py 的 _WORKFLOW_SYSTEM_PROMPT）明確允許
validation.n_repeats / validation.group_column 在不適用時填 null，而不是省略欄位。
dict.get(key, default) 只在 key 不存在時才用 default，key 存在但值是 None 時仍會回傳
None，導致後面的 int(None) 噴 TypeError。
"""

from services.workflow.workflow_service import WorkflowService


def test_normalize_validation_config_treats_explicit_null_n_repeats_as_default():
    config = {
        "method": "k_fold",
        "n_splits": 10,
        "stratified": True,
        "train_size": 0.8,
        "n_repeats": None,
        "group_column": None,
    }

    result = WorkflowService._normalize_validation_config(config)

    assert result["n_repeats"] == 1
    assert result["group_column"] is None


def test_normalize_validation_config_treats_explicit_null_n_splits_and_random_state_as_default():
    config = {
        "method": "k_fold",
        "n_splits": None,
        "random_state": None,
    }

    result = WorkflowService._normalize_validation_config(config)

    assert result["n_splits"] == 5
    assert result["random_state"] == 42
