"""Google 登入與忘記密碼流程的手動驗證腳本（需要可連線的開發用資料庫）

用法（在 backend/ 目錄下執行）：
    python scripts/test_auth_google_and_reset.py

涵蓋：
  1. 新 email 用 Google 登入 → 自動建立新帳號
  2. 既有密碼帳號用同 email 的 Google 登入 → 自動綁定 google_id
  3. 忘記密碼 → 重設密碼 → 用新密碼登入
  4. 已使用/過期的重設 token 再次使用 → 回傳失效錯誤
  5. 忘記密碼的反列舉（anti-enumeration）性質：不存在的 email、以及純 Google 帳號
     （無密碼）的 email，都必須回傳與「已有密碼帳號」完全相同的通用訊息，且都不寄信

執行後會清除腳本建立的測試帳號，不會在資料庫留下垃圾資料。
"""

import datetime
import os
import sys
from urllib.parse import parse_qs, urlparse
from pathlib import Path
from unittest.mock import patch

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

from apps import create_app  # noqa: E402
from extensions import db  # noqa: E402
from models.user import User  # noqa: E402

GOOGLE_NEW_USER_EMAIL = "google-test@example.com"
PASSWORD_USER_EMAIL = "reset-test@example.com"
GOOGLE_ONLY_EMAIL = "google-only-test@example.com"
NONEXISTENT_EMAIL = "nonexistent-test@example.com"
ORIGINAL_PASSWORD = "OriginalPass123"
NEW_PASSWORD = "NewPass456"


def cleanup(app):
    with app.app_context():
        User.query.filter(
            User.email.in_(
                [GOOGLE_NEW_USER_EMAIL, PASSWORD_USER_EMAIL, GOOGLE_ONLY_EMAIL, NONEXISTENT_EMAIL]
            )
        ).delete(synchronize_session=False)
        db.session.commit()


def test_google_login_creates_new_user(app, client):
    fake_payload = {
        "email": GOOGLE_NEW_USER_EMAIL,
        "sub": "google-sub-new-user",
        "name": "Google Test",
        "email_verified": True,
    }
    with patch("routes.auth.verify_google_id_token", return_value=fake_payload):
        response = client.post("/api/auth/google", json={"idToken": "fake-token"})

    body = response.get_json()
    assert response.status_code == 200, body
    assert body["success"] is True

    with app.app_context():
        user = User.query.filter_by(email=GOOGLE_NEW_USER_EMAIL).first()
        assert user is not None
        assert user.google_id == "google-sub-new-user"
        assert user.password_hash is None

    print("[PASS] Google 登入建立新帳號")


def test_google_login_links_existing_password_account(app, client):
    register_response = client.post(
        "/api/auth/register",
        json={"email": PASSWORD_USER_EMAIL, "password": ORIGINAL_PASSWORD, "displayName": "Reset Test"},
    )
    assert register_response.get_json()["success"] is True

    fake_payload = {
        "email": PASSWORD_USER_EMAIL,
        "sub": "google-sub-linked",
        "name": "Reset Test",
        "email_verified": True,
    }
    with patch("routes.auth.verify_google_id_token", return_value=fake_payload):
        response = client.post("/api/auth/google", json={"idToken": "fake-token"})

    body = response.get_json()
    assert response.status_code == 200, body
    assert body["success"] is True

    with app.app_context():
        user = User.query.filter_by(email=PASSWORD_USER_EMAIL).first()
        assert user is not None
        assert user.google_id == "google-sub-linked"
        assert user.password_hash is not None

    print("[PASS] 既有密碼帳號用 Google 登入後自動綁定 google_id")


def _create_google_only_user(app, client):
    """建立一個純 Google 帳號（無密碼）的測試使用者，供反列舉測試使用。"""
    fake_payload = {
        "email": GOOGLE_ONLY_EMAIL,
        "sub": "google-sub-only-account",
        "name": "Google Only",
        "email_verified": True,
    }
    with patch("routes.auth.verify_google_id_token", return_value=fake_payload):
        response = client.post("/api/auth/google", json={"idToken": "fake-token"})
    assert response.get_json()["success"] is True

    with app.app_context():
        user = User.query.filter_by(email=GOOGLE_ONLY_EMAIL).first()
        assert user is not None
        assert user.password_hash is None


def test_forgot_password_anti_enumeration(app, client):
    """/forgot-password 是這個功能最核心的安全性質：不管 email 是否已註冊、
    或該帳號是否有密碼，都必須回傳一模一樣的通用訊息，且都不能真的寄信。
    這裡涵蓋另外兩種先前完全沒被測到的分支：email 不存在、email 存在但是純
    Google 帳號（password_hash 為 None）。"""
    _create_google_only_user(app, client)

    with patch("routes.auth.send_reset_password_email") as mock_send_existing:
        baseline_response = client.post("/api/auth/forgot-password", json={"email": PASSWORD_USER_EMAIL})
    baseline_body = baseline_response.get_json()
    assert baseline_response.status_code == 200
    assert baseline_body["success"] is True
    baseline_message = baseline_body["result"]["message"]
    assert mock_send_existing.called, "已有密碼的帳號應該要寄出重設信"

    with patch("routes.auth.send_reset_password_email") as mock_send_nonexistent:
        nonexistent_response = client.post("/api/auth/forgot-password", json={"email": NONEXISTENT_EMAIL})
    nonexistent_body = nonexistent_response.get_json()
    assert nonexistent_response.status_code == 200
    assert nonexistent_body["success"] is True
    assert nonexistent_body["result"]["message"] == baseline_message, "不存在的 email 回傳的訊息必須與既有帳號完全相同"
    assert not mock_send_nonexistent.called, "不存在的 email 不應該寄出任何信"

    with patch("routes.auth.send_reset_password_email") as mock_send_google_only:
        google_only_response = client.post("/api/auth/forgot-password", json={"email": GOOGLE_ONLY_EMAIL})
    google_only_body = google_only_response.get_json()
    assert google_only_response.status_code == 200
    assert google_only_body["success"] is True
    assert google_only_body["result"]["message"] == baseline_message, "純 Google 帳號回傳的訊息必須與既有密碼帳號完全相同"
    assert not mock_send_google_only.called, "純 Google 帳號（無密碼）不應該寄出重設信"

    print("[PASS] 忘記密碼對「不存在的 email」與「純 Google 帳號」都回傳與既有密碼帳號完全相同的通用訊息，且皆未寄信")


def test_forgot_and_reset_password_flow(app, client):
    captured_links = {}

    def fake_send(to, reset_link):
        captured_links[to] = reset_link

    with patch("routes.auth.send_reset_password_email", side_effect=fake_send):
        response = client.post("/api/auth/forgot-password", json={"email": PASSWORD_USER_EMAIL})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert PASSWORD_USER_EMAIL in captured_links, "忘記密碼應該要寄出（印出）重設連結"

    reset_link = captured_links[PASSWORD_USER_EMAIL]
    token = parse_qs(urlparse(reset_link).query)["token"][0]

    reset_response = client.post("/api/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert reset_response.status_code == 200, reset_response.get_json()
    assert reset_response.get_json()["success"] is True

    login_response = client.post(
        "/api/auth/login", json={"email": PASSWORD_USER_EMAIL, "password": NEW_PASSWORD}
    )
    assert login_response.get_json()["success"] is True

    old_password_login = client.post(
        "/api/auth/login", json={"email": PASSWORD_USER_EMAIL, "password": ORIGINAL_PASSWORD}
    )
    assert old_password_login.status_code == 401

    print("[PASS] 忘記密碼 -> 重設密碼 -> 用新密碼登入，舊密碼失效")
    return token


def test_used_token_is_rejected(client, used_token):
    response = client.post("/api/auth/reset-password", json={"token": used_token, "password": "AnotherPass789"})
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    print("[PASS] 已使用過的重設 token 再次使用會被拒絕")


def test_expired_token_is_rejected(app, client):
    captured_links = {}

    def fake_send(to, reset_link):
        captured_links[to] = reset_link

    with patch("routes.auth.send_reset_password_email", side_effect=fake_send):
        response = client.post("/api/auth/forgot-password", json={"email": PASSWORD_USER_EMAIL})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert PASSWORD_USER_EMAIL in captured_links, "忘記密碼應該要寄出（印出）重設連結"

    reset_link = captured_links[PASSWORD_USER_EMAIL]
    token = parse_qs(urlparse(reset_link).query)["token"][0]

    with app.app_context():
        user = User.query.filter_by(email=PASSWORD_USER_EMAIL).first()
        user.reset_token_expires_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
        db.session.commit()

    response = client.post("/api/auth/reset-password", json={"token": token, "password": "ExpiredFlow789"})
    assert response.status_code == 400
    assert response.get_json()["success"] is False
    print("[PASS] 過期但未使用過的重設 token 會被拒絕")


def main():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    cleanup(app)
    try:
        test_google_login_creates_new_user(app, client)
        test_google_login_links_existing_password_account(app, client)
        test_forgot_password_anti_enumeration(app, client)
        used_token = test_forgot_and_reset_password_flow(app, client)
        test_used_token_is_rejected(client, used_token)
        test_expired_token_is_rejected(app, client)
        print("\n全部通過")
    finally:
        cleanup(app)


if __name__ == "__main__":
    main()
