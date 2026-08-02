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

    def test_malformed_state_degrades_gracefully_instead_of_raising(self, service, monkeypatch):
        # mapping_status 裡的項目缺少 build_chat_refine_prompt 會直接用 [] 索引的 key，
        # 這種格式錯誤必須在 try 內被擋下，不能讓例外往上炸穿整頁。
        patch_model(service, monkeypatch, FakeModel(action()))
        malformed_state = {
            "mapping_status": [{"no_such_key": 1}],
            "user_columns": [{"name": "a", "sample_values": []}],
        }
        result = service.chat_refine(malformed_state, "隨便", [])
        assert result["actions"] == []
        assert isinstance(result["reply"], str) and result["reply"]
