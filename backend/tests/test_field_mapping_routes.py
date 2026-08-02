"""路由層測試：用 Flask test client，Gemini 全部以 monkeypatch 取代，不連網。

這兩支 API 不碰資料庫，所以 DATABASE_URL 只要是合法的連線字串就好，
SQLAlchemy 是延遲連線的，不會真的去連。
LOGIN_DISABLED 讓 @login_required 變成 no-op，測試不必真的登入。
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.field_mapping as field_mapping_route  # noqa: E402
from apps import create_app  # noqa: E402

PAYLOAD = {
    "paper_variables": [
        {"name": "age", "type": "numerical"},
        {"name": "braden_score", "type": "numerical"},
    ],
    "user_columns": [
        {"name": "pt_age", "sample_values": ["65", "72"]},
        {"name": "braden_total", "sample_values": ["18", "14"]},
    ],
}


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    return app.test_client()


class FakeService:
    """假的 GeminiService：semantic_match / chat_refine 回傳預設好的東西。"""

    def __init__(self, semantic=None, chat=None):
        self._semantic = semantic
        self._chat = chat or {"actions": [], "reply": "ok"}

    def semantic_match(self, items, user_columns):
        return self._semantic

    def chat_refine(self, state, message, history):
        return self._chat


class TestInitRoute:
    def test_returns_mapping_status(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[]),
        )
        response = client.post("/api/field-mapping/init", json=PAYLOAD)
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        variables = [i["paper_variable"] for i in body["result"]["mapping_status"]]
        assert variables == ["age", "braden_score"]

    def test_applies_semantic_suggestions(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[{
                "paper_variable": "braden_score",
                "matched_user_column": "braden_total",
                "confidence_score": 0.95,
                "candidate_columns": [],
            }]),
        )
        body = client.post("/api/field-mapping/init", json=PAYLOAD).get_json()
        braden = [
            i for i in body["result"]["mapping_status"]
            if i["paper_variable"] == "braden_score"
        ][0]
        assert braden["matched_user_column"] == "braden_total"
        assert braden["status"] == "NEEDS_REVIEW"
        assert body["ai_available"] is True

    def test_survives_gemini_being_unavailable(self, client, monkeypatch):
        def boom():
            raise ValueError("GEMINI_API_KEY is required.")

        monkeypatch.setattr(field_mapping_route, "GeminiService", boom)
        response = client.post("/api/field-mapping/init", json=PAYLOAD)
        assert response.status_code == 200
        body = response.get_json()
        assert body["success"] is True
        assert body["ai_available"] is False
        assert len(body["result"]["mapping_status"]) == 2

    def test_semantic_match_returning_none_marks_ai_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=None),
        )
        body = client.post("/api/field-mapping/init", json=PAYLOAD).get_json()
        assert body["ai_available"] is False

    def test_accepts_plain_string_columns(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(semantic=[]),
        )
        response = client.post("/api/field-mapping/init", json={
            "paper_variables": [{"name": "age", "type": "numerical"}],
            "user_columns": ["pt_age", "gender"],
        })
        assert response.status_code == 200

    def test_rejects_missing_paper_variables(self, client):
        response = client.post("/api/field-mapping/init", json={"user_columns": ["a"]})
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_rejects_missing_user_columns(self, client):
        response = client.post("/api/field-mapping/init", json={
            "paper_variables": [{"name": "age"}],
        })
        assert response.status_code == 400

    def test_rejects_empty_body(self, client):
        assert client.post("/api/field-mapping/init", json={}).status_code == 400


class TestChatRoute:
    def test_returns_diff(self, client, monkeypatch):
        monkeypatch.setattr(
            field_mapping_route, "GeminiService",
            lambda: FakeService(chat={
                "actions": [{
                    "paper_variable": "braden_score",
                    "matched_user_column": "braden_total",
                    "status": "NEEDS_REVIEW",
                    "confidence_score": 0.9,
                }],
                "reply": "已更新",
            }),
        )
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "braden 分數是 braden_total",
            "chat_history": [],
        })
        assert response.status_code == 200
        body = response.get_json()
        assert body["result"]["reply"] == "已更新"
        assert len(body["result"]["actions"]) == 1

    def test_rejects_empty_message(self, client):
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "   ",
            "chat_history": [],
        })
        assert response.status_code == 400

    def test_returns_503_when_gemini_unavailable(self, client, monkeypatch):
        def boom():
            raise ValueError("GEMINI_API_KEY is required.")

        monkeypatch.setattr(field_mapping_route, "GeminiService", boom)
        response = client.post("/api/field-mapping/chat", json={
            "current_mapping_state": {"mapping_status": [], "user_columns": []},
            "user_message": "隨便",
            "chat_history": [],
        })
        assert response.status_code == 503
        assert response.get_json()["success"] is False
