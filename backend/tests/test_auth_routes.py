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

    def test_wrong_issuer_google_auth_error_returns_401(self, client, monkeypatch):
        """google.oauth2.id_token.verify_oauth2_token 在 issuer 不符時拋出的是
        google.auth.exceptions.GoogleAuthError，並非 ValueError 子類別，
        必須確認路由也能把它轉成 401 而非未攔截的 500。"""

        def fake_verify(token):
            raise auth_route.google_auth_exceptions.GoogleAuthError("Wrong issuer.")

        monkeypatch.setattr(auth_route, "verify_google_id_token", fake_verify)
        response = client.post("/api/auth/google", json={"idToken": "bad-issuer-token"})
        assert response.status_code == 401
        assert response.get_json()["success"] is False

    def test_email_not_verified_returns_401(self, client, monkeypatch):
        """email_verified 為 False 時應在任何 User.query 之前就被拒絕（不碰資料庫）。"""

        def fake_verify(token):
            return {
                "email": "unverified@example.com",
                "sub": "google-sub-unverified",
                "email_verified": False,
            }

        monkeypatch.setattr(auth_route, "verify_google_id_token", fake_verify)
        response = client.post("/api/auth/google", json={"idToken": "unverified-token"})
        assert response.status_code == 401
        assert response.get_json()["success"] is False

    def test_missing_email_verified_returns_401(self, client, monkeypatch):
        """payload 缺少 email_verified 欄位時也應視為未驗證並拒絕。"""

        def fake_verify(token):
            return {
                "email": "no-flag@example.com",
                "sub": "google-sub-no-flag",
            }

        monkeypatch.setattr(auth_route, "verify_google_id_token", fake_verify)
        response = client.post("/api/auth/google", json={"idToken": "no-flag-token"})
        assert response.status_code == 401
        assert response.get_json()["success"] is False


class TestForgotPasswordRoute:
    def test_missing_email_returns_400(self, client):
        response = client.post("/api/auth/forgot-password", json={"foo": "bar"})
        assert response.status_code == 400
        assert response.get_json()["success"] is False


class TestResetPasswordRoute:
    def test_missing_fields_returns_400(self, client):
        response = client.post("/api/auth/reset-password", json={"foo": "bar"})
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_password_too_long_returns_400(self, client):
        response = client.post(
            "/api/auth/reset-password",
            json={"token": "sometoken", "password": "a" * 100},
        )
        assert response.status_code == 400
        assert response.get_json()["success"] is False
