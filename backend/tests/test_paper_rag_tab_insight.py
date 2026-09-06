"""ROC/PR 多模型 AI 解讀的新函式測試。

不連網：用 PaperRAGService.__new__(PaperRAGService) 繞過 __init__（不需要
GEMINI_API_KEY），純邏輯的函式（_find_tab_results/_format_multi_model_curve_data/
_format_roc_pr_curve_text）直接呼叫；需要呼叫 Gemini 的函式（generate_tab_insight/
chat_about_tab）monkeypatch 掉 service._call_gemini，理由同
test_paper_rag_section_prompt.py 開頭註解。
"""

from services.rag.paper_rag import PaperRAGService


def make_result(model_name, split_name="fold_1", fpr=None, tpr=None, recall=None, precision=None, auc=0.85):
    return {
        "model_name": model_name,
        "split_name": split_name,
        "roc_pr_curve": {
            "pos_label": "1",
            "roc": {"fpr": fpr or [0.0, 0.5, 1.0], "tpr": tpr or [0.0, 0.8, 1.0]},
            "pr": {"recall": recall or [0.0, 0.5, 1.0], "precision": precision or [1.0, 0.9, 0.5]},
        },
        "metrics": [{"metric": "auc", "value": auc}, {"metric": "auprc", "value": 0.75}],
    }


def make_service():
    return PaperRAGService.__new__(PaperRAGService)


def test_find_tab_results_returns_in_requested_order():
    service = make_service()
    mining_results = {
        "results": [
            make_result("SVM"),
            make_result("Random Forest"),
            make_result("Logistic Regression"),
        ]
    }
    results = service._find_tab_results(
        mining_results, ["Logistic Regression", "SVM"], "fold_1",
    )
    assert [r["model_name"] for r in results] == ["Logistic Regression", "SVM"]


def test_find_tab_results_skips_missing_models():
    service = make_service()
    mining_results = {"results": [make_result("SVM")]}
    results = service._find_tab_results(
        mining_results, ["SVM", "不存在的模型"], "fold_1",
    )
    assert [r["model_name"] for r in results] == ["SVM"]


def test_find_tab_results_skips_error_rows():
    service = make_service()
    errored = make_result("SVM")
    errored["error"] = "訓練失敗"
    mining_results = {"results": [errored]}
    results = service._find_tab_results(mining_results, ["SVM"], "fold_1")
    assert results == []


def test_format_multi_model_curve_data_builds_one_block_per_model():
    service = make_service()
    results = [make_result("SVM"), make_result("Random Forest")]
    text = service._format_multi_model_curve_data(results, "roc")
    assert text is not None
    assert "【ROC 曲線】" in text
    assert "▶ SVM" in text
    assert "▶ Random Forest" in text
    assert text.index("▶ SVM") < text.index("▶ Random Forest")


def test_format_multi_model_curve_data_skips_models_without_curve():
    service = make_service()
    no_curve = make_result("SVM")
    no_curve["roc_pr_curve"] = None
    results = [no_curve, make_result("Random Forest")]
    text = service._format_multi_model_curve_data(results, "roc")
    assert text is not None
    assert "▶ SVM" not in text
    assert "▶ Random Forest" in text


def test_format_multi_model_curve_data_returns_none_when_all_missing():
    service = make_service()
    no_curve = make_result("SVM")
    no_curve["roc_pr_curve"] = None
    text = service._format_multi_model_curve_data([no_curve], "roc")
    assert text is None


def test_generate_tab_insight_multi_model_prompt_mentions_all_models_and_asks_for_comparison():
    service = make_service()
    captured_prompt = {}

    def fake_call_gemini(prompt, usage_total):
        captured_prompt["value"] = prompt
        return "SVM 的表現最好。"

    service._call_gemini = fake_call_gemini
    mining_results = {"results": [make_result("SVM"), make_result("Random Forest")]}

    text = service.generate_tab_insight(
        mining_results, "roc", "SVM", "fold_1", model_names=["SVM", "Random Forest"],
    )

    assert text == "SVM 的表現最好。"
    prompt = captured_prompt["value"]
    assert "SVM" in prompt
    assert "Random Forest" in prompt
    assert "請比較它們的表現" in prompt
    assert "明確指出哪個模型的表現最接近理想" in prompt
    assert "2 個模型" in prompt


def test_generate_tab_insight_without_model_names_uses_single_model_path_unchanged():
    service = make_service()
    captured_prompt = {}

    def fake_call_gemini(prompt, usage_total):
        captured_prompt["value"] = prompt
        return "解讀內容。"

    service._call_gemini = fake_call_gemini
    mining_results = {"results": [make_result("SVM")]}

    text = service.generate_tab_insight(mining_results, "roc", "SVM", "fold_1")

    assert text == "解讀內容。"
    prompt = captured_prompt["value"]
    assert '模型「SVM」在「fold_1」這筆結果的資料' in prompt
    assert "請比較它們的表現" not in prompt


def test_generate_tab_insight_multi_model_no_matching_results():
    service = make_service()
    mining_results = {"results": [make_result("SVM")]}
    text = service.generate_tab_insight(
        mining_results, "roc", "SVM", "fold_1", model_names=["不存在的模型"],
    )
    assert text == "找不到對應的結果資料。"


def test_chat_about_tab_multi_model_context_mentions_model_count():
    service = make_service()
    captured = {}

    class FakeChat:
        def send_message(self, message):
            captured["message"] = message
            class Resp:
                text = "SVM 表現比較好。"
            return Resp()

    class FakeModel:
        def start_chat(self, history):
            captured["history"] = history
            return FakeChat()

    service._model = FakeModel()
    mining_results = {"results": [make_result("SVM"), make_result("Random Forest")]}

    reply = service.chat_about_tab(
        mining_results, "roc", "SVM", "fold_1", [], "哪個模型比較好？",
        model_names=["SVM", "Random Forest"],
    )

    assert reply == "SVM 表現比較好。"
    first_turn_text = captured["history"][0]["parts"][0]
    assert "2 個模型的比較" in first_turn_text
    assert "SVM" in first_turn_text
    assert "Random Forest" in first_turn_text
