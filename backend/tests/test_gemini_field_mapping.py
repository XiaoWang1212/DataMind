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
