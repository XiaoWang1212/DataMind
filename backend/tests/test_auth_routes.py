"""路由層測試：只測輸入驗證與錯誤處理，不碰資料庫（跟 test_field_mapping_routes.py 同樣的理由——
DATABASE_URL 只要是合法字串即可，SQLAlchemy 延遲連線，不會真的去連）。
會實際查詢/寫入 users 表的行為（新使用者建立、帳號自動綁定、重設密碼完整流程），
改用 backend/scripts/test_auth_google_and_reset.py 對開發用資料庫手動驗證。
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.auth as auth_route  # noqa: E402
from apps import create_app  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class TestGoogleLoginRoute:
    def test_missing_id_token_returns_400(self, client):
        response = client.post("/api/auth/google", json={"foo": "bar"})
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_invalid_token_returns_401(self, client, monkeypatch):
        def fake_verify(token):
            raise ValueError("invalid token")

        monkeypatch.setattr(auth_route, "verify_google_id_token", fake_verify)
        response = client.post("/api/auth/google", json={"idToken": "bad-token"})
        assert response.status_code == 401
        assert response.get_json()["success"] is False
