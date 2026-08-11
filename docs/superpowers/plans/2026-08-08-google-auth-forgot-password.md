# Google 登入與忘記密碼 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓使用者可以用 Google 帳號登入/註冊，並在忘記密碼時透過 email 重設密碼。

**Architecture:** 後端在既有 `users` 表加三個欄位（`google_id`、`reset_token_hash`、`reset_token_expires_at`），`routes/auth.py` 新增 `/google`、`/forgot-password`、`/reset-password` 三支 API；寄信邏輯包成可插拔介面（先印 log）。前端新增一個共用的 Google 登入按鈕元件（Google Identity Services），以及忘記密碼/重設密碼兩個新頁面。

**Tech Stack:** Flask + Flask-Login + SQLAlchemy + Alembic（後端）、Vue 3 + Vue Router + Pinia（前端）、`google-auth`（後端驗證 ID token）、Google Identity Services（前端 GIS script）。

## Global Constraints

- 密碼一律用 bcrypt 雜湊，bcrypt 上限 72 bytes（沿用 `backend/routes/auth.py` 現有的檢查）
- 所有 API 回傳格式維持 `{"success": bool, "result": ...}` 或 `{"success": false, "error": "..."}`，與現有 `/login`、`/register` 一致
- 忘記密碼 API 不論 email 是否存在，一律回傳同一句訊息，避免 email 枚舉
- 重設密碼 token 不存明文，只存 SHA-256 雜湊
- 後端相依套件用 `uv add`／`pyproject.toml`管理（`requirements.txt` 是舊檔，不使用）
- 新環境變數只加值為空的預留位（`GOOGLE_CLIENT_ID`、`VITE_GOOGLE_CLIENT_ID`），實際值由使用者之後自行申請填入
- 前端沒有自動化測試框架，驗證方式是 `npm run type-check` / `npm run build` + 手動瀏覽器測試（沿用專案現有慣例）
- 後端資料庫相關邏輯（會實際查詢/寫入 `users` 表）沒有隔離測試資料庫，沿用專案現有慣例：純輸入驗證用 pytest（不碰 DB），實際 DB 行為用 `backend/scripts/test_*.py` 手動腳本對開發用 DB 驗證

---

## Task 1: User model 新增欄位 + migration

**Files:**
- Modify: `backend/models/user.py:16` (在 `display_name` 之後插入三個新欄位)
- Create: `backend/migrations/versions/b4f2a91d6c5e_add_google_and_reset_token_to_users.py`

**Interfaces:**
- Produces: `User.google_id: str | None`、`User.reset_token_hash: str | None`、`User.reset_token_expires_at: datetime.datetime | None` — Task 3、4、5 都會用到這三個欄位

- [ ] **Step 1: 修改 `backend/models/user.py`**

把：

```python
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

改成：

```python
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

- [ ] **Step 2: 建立 migration 檔案**

`backend/migrations/versions/b4f2a91d6c5e_add_google_and_reset_token_to_users.py`：

```python
"""add google_id and reset token fields to users

Revision ID: b4f2a91d6c5e
Revises: 8617ff021a1a
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4f2a91d6c5e'
down_revision: Union[str, Sequence[str], None] = '8617ff021a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('reset_token_expires_at', sa.DateTime(), nullable=True))
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token_hash')
    op.drop_column('users', 'google_id')
```

- [ ] **Step 3: 執行 migration**

Run（在 `backend/` 目錄下）: `uv run alembic upgrade head`
Expected: 最後一行輸出包含 `Running upgrade 8617ff021a1a -> b4f2a91d6c5e`

- [ ] **Step 4: 驗證欄位確實建立**

Run（在 `backend/` 目錄下）:

```bash
uv run python - <<'EOF'
from apps import create_app
from extensions import db
from sqlalchemy import inspect

app = create_app()
with app.app_context():
    cols = [c["name"] for c in inspect(db.engine).get_columns("users")]
    assert "google_id" in cols, cols
    assert "reset_token_hash" in cols, cols
    assert "reset_token_expires_at" in cols, cols
    print("OK", cols)
EOF
```

Expected: 印出 `OK [...]`，欄位清單包含 `google_id`、`reset_token_hash`、`reset_token_expires_at`，且不拋出 AssertionError

- [ ] **Step 5: Commit**

```bash
git add backend/models/user.py backend/migrations/versions/b4f2a91d6c5e_add_google_and_reset_token_to_users.py
git commit -m "feat: add google_id and reset token fields to users table"
```

---

## Task 2: 可插拔寄信介面

**Files:**
- Create: `backend/services/email_sender.py`
- Test: `backend/tests/test_email_sender.py`

**Interfaces:**
- Produces: `send_reset_password_email(to: str, reset_link: str) -> None` — Task 4 的 `/auth/forgot-password` 會呼叫這個函式

- [ ] **Step 1: 寫失敗的測試**

`backend/tests/test_email_sender.py`：

```python
"""寄信介面測試：目前實作只印到 log，之後要接真的 SMTP/SendGrid 時只需替換 send_reset_password_email 的實作。"""

import logging

from services.email_sender import send_reset_password_email


def test_send_reset_password_email_logs_recipient_and_link(caplog):
    with caplog.at_level(logging.INFO):
        send_reset_password_email(
            "user@example.com",
            "http://localhost:3000/reset-password?token=abc123",
        )

    assert "user@example.com" in caplog.text
    assert "http://localhost:3000/reset-password?token=abc123" in caplog.text
```

- [ ] **Step 2: 執行測試確認失敗**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_email_sender.py -v`
Expected: FAIL，錯誤訊息是 `ModuleNotFoundError: No module named 'services.email_sender'`

- [ ] **Step 3: 寫最小實作**

`backend/services/email_sender.py`：

```python
"""可插拔的寄信介面。

目前的實作只把重設連結印到 log，方便本地開發測試。
之後要接真的 SMTP/SendGrid 等服務時，只需要替換這支函式的內容，
呼叫端（backend/routes/auth.py）不需要修改。
"""

import logging

logger = logging.getLogger(__name__)


def send_reset_password_email(to: str, reset_link: str) -> None:
    logger.info("[password-reset] to=%s link=%s", to, reset_link)
```

- [ ] **Step 4: 執行測試確認通過**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_email_sender.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/email_sender.py backend/tests/test_email_sender.py
git commit -m "feat: add pluggable email sender for password reset links"
```

---

## Task 3: Google 登入後端 API

**Files:**
- Modify: `backend/pyproject.toml`（新增 `google-auth` 相依套件，透過 `uv add` 執行）
- Modify: `backend/routes/auth.py:1-14`（imports）
- Modify: `backend/routes/auth.py`（在檔案末尾新增 `verify_google_id_token` 與 `/google` route）
- Modify: `backend/.env.example`（新增 `GOOGLE_CLIENT_ID`）
- Test: `backend/tests/test_auth_routes.py`（新檔案）

**Interfaces:**
- Consumes: `User` model 的 `google_id` 欄位（Task 1 產生）
- Produces: `routes.auth.verify_google_id_token(token: str) -> dict`（Task 5 的手動腳本會 monkeypatch 這個函式）；`POST /api/auth/google` 端點

- [ ] **Step 1: 新增 `google-auth` 相依套件**

Run（在 `backend/` 目錄下）: `uv add google-auth`
Expected: `pyproject.toml` 的 `dependencies` 多一行 `"google-auth"`，`uv.lock` 也會更新

- [ ] **Step 2: 寫失敗的測試**

`backend/tests/test_auth_routes.py`：

```python
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
```

- [ ] **Step 3: 執行測試確認失敗**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_auth_routes.py -v`
Expected: FAIL，兩個測試都收到 404（`/api/auth/google` 還不存在）

- [ ] **Step 4: 修改 imports**

把 `backend/routes/auth.py` 開頭的：

```python
"""使用者註冊/登入/登出 API"""

import logging

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models.user import User
```

改成：

```python
"""使用者註冊/登入/登出 API"""

import logging
import os

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from extensions import db
from models.user import User
```

- [ ] **Step 5: 在檔案末尾新增 `verify_google_id_token` 與 `/google` route**

在 `backend/routes/auth.py` 檔案最後面（`me()` 函式之後）新增：

```python


def verify_google_id_token(token: str) -> dict:
    """驗證 Google ID token 的簽章與 audience，回傳解碼後的 payload。

    Token 無效（過期、簽章錯誤、aud 不符）時，底層函式會拋出 ValueError。
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID 未設定")
    return google_id_token.verify_oauth2_token(token, google_requests.Request(), client_id)


@auth_bp.route("/google", methods=["POST"])
def google_login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    id_token_value = data.get("idToken")
    if not id_token_value:
        return jsonify({"success": False, "error": "idToken 為必填欄位"}), 400

    try:
        payload = verify_google_id_token(id_token_value)
    except ValueError:
        return jsonify({"success": False, "error": "Google 登入驗證失敗"}), 401

    email = payload.get("email")
    google_sub = payload.get("sub")
    if not email or not google_sub:
        return jsonify({"success": False, "error": "Google 登入驗證失敗"}), 401

    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=None,
            display_name=payload.get("name", ""),
            google_id=google_sub,
        )
        db.session.add(user)
    elif not user.google_id:
        user.google_id = google_sub

    db.session.commit()
    login_user(user)
    return jsonify({"success": True, "result": {"id": user.id, "email": user.email}})
```

- [ ] **Step 6: 執行測試確認通過**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_auth_routes.py -v`
Expected: PASS（2 passed）

- [ ] **Step 7: 新增環境變數預留位**

在 `backend/.env.example` 最後新增一行：

```
GOOGLE_CLIENT_ID=
```

- [ ] **Step 8: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/routes/auth.py backend/tests/test_auth_routes.py backend/.env.example
git commit -m "feat: add Google login endpoint with ID token verification"
```

---

## Task 4: 忘記密碼／重設密碼後端 API

**Files:**
- Modify: `backend/routes/auth.py`（imports、新增 `RESET_TOKEN_TTL` 常數、`/forgot-password`、`/reset-password` route）
- Modify: `backend/tests/test_auth_routes.py`（新增兩個測試 class）

**Interfaces:**
- Consumes: `User.reset_token_hash`、`User.reset_token_expires_at`（Task 1）；`send_reset_password_email`（Task 2）
- Produces: `POST /api/auth/forgot-password`、`POST /api/auth/reset-password` 端點

- [ ] **Step 1: 寫失敗的測試**

在 `backend/tests/test_auth_routes.py` 檔案末尾新增：

```python


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
```

- [ ] **Step 2: 執行測試確認失敗**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_auth_routes.py -v`
Expected: 新增的 3 個測試 FAIL（404，路由還不存在），先前的 2 個測試仍然 PASS

- [ ] **Step 3: 修改 imports 與新增常數**

把 `backend/routes/auth.py` 開頭的：

```python
"""使用者註冊/登入/登出 API"""

import logging
import os

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from extensions import db
from models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)
```

改成：

```python
"""使用者註冊/登入/登出 API"""

import datetime
import hashlib
import logging
import os
import secrets

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from extensions import db
from models.user import User
from services.email_sender import send_reset_password_email

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)

RESET_TOKEN_TTL = datetime.timedelta(hours=1)
```

- [ ] **Step 4: 在檔案末尾新增 `_hash_reset_token`、`/forgot-password`、`/reset-password`**

在 `backend/routes/auth.py` 檔案最後面（`google_login()` 函式之後）新增：

```python


def _hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    email = data.get("email")
    if not email:
        return jsonify({"success": False, "error": "email 為必填欄位"}), 400

    generic_result = {"success": True, "result": {"message": "若此 email 已註冊，重設密碼信已寄出"}}

    user = User.query.filter_by(email=email).first()
    if user is not None and user.password_hash is not None:
        token = secrets.token_urlsafe(32)
        user.reset_token_hash = _hash_reset_token(token)
        user.reset_token_expires_at = datetime.datetime.utcnow() + RESET_TOKEN_TTL
        db.session.commit()

        frontend_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")
        reset_link = f"{frontend_origin}/reset-password?token={token}"
        send_reset_password_email(user.email, reset_link)

    return jsonify(generic_result)


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    token = data.get("token")
    password = data.get("password")
    if not token or not password:
        return jsonify({"success": False, "error": "token 和 password 為必填欄位"}), 400

    if len(password.encode("utf-8")) > 72:
        return jsonify({"success": False, "error": "password 過長（bcrypt 上限為 72 bytes）"}), 400

    user = User.query.filter_by(reset_token_hash=_hash_reset_token(token)).first()
    now = datetime.datetime.utcnow()
    if user is None or user.reset_token_expires_at is None or user.reset_token_expires_at < now:
        return jsonify({"success": False, "error": "重設連結已失效，請重新申請"}), 400

    user.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.session.commit()
    return jsonify({"success": True})
```

- [ ] **Step 5: 執行測試確認通過**

Run（在 `backend/` 目錄下）: `uv run pytest tests/test_auth_routes.py -v`
Expected: PASS（5 passed）

- [ ] **Step 6: Commit**

```bash
git add backend/routes/auth.py backend/tests/test_auth_routes.py
git commit -m "feat: add forgot-password and reset-password endpoints"
```

---

## Task 5: 對開發資料庫的手動整合驗證腳本

**Files:**
- Create: `backend/scripts/test_auth_google_and_reset.py`

**Interfaces:**
- Consumes: `POST /api/auth/google`、`POST /api/auth/forgot-password`、`POST /api/auth/reset-password`、`POST /api/auth/register`、`POST /api/auth/login`（Task 3、4 產生）；`routes.auth.verify_google_id_token`、`routes.auth.send_reset_password_email`（monkeypatch 對象）

這支腳本需要一個可連線的開發用 Postgres 資料庫（`backend/.env` 的 `DATABASE_URL`），跟 `backend/scripts/test_paper_gen.py`、`backend/scripts/seed_admin.py` 走一樣的手動驗證模式，不是 pytest。

- [ ] **Step 1: 建立腳本**

`backend/scripts/test_auth_google_and_reset.py`：

```python
"""Google 登入與忘記密碼流程的手動驗證腳本（需要可連線的開發用資料庫）

用法（在 backend/ 目錄下執行）：
    python scripts/test_auth_google_and_reset.py

涵蓋：
  1. 新 email 用 Google 登入 → 自動建立新帳號
  2. 既有密碼帳號用同 email 的 Google 登入 → 自動綁定 google_id
  3. 忘記密碼 → 重設密碼 → 用新密碼登入
  4. 已使用/過期的重設 token 再次使用 → 回傳失效錯誤

執行後會清除腳本建立的測試帳號，不會在資料庫留下垃圾資料。
"""

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
ORIGINAL_PASSWORD = "OriginalPass123"
NEW_PASSWORD = "NewPass456"


def cleanup(app):
    with app.app_context():
        User.query.filter(User.email.in_([GOOGLE_NEW_USER_EMAIL, PASSWORD_USER_EMAIL])).delete(
            synchronize_session=False
        )
        db.session.commit()


def test_google_login_creates_new_user(app, client):
    fake_payload = {"email": GOOGLE_NEW_USER_EMAIL, "sub": "google-sub-new-user", "name": "Google Test"}
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

    fake_payload = {"email": PASSWORD_USER_EMAIL, "sub": "google-sub-linked", "name": "Reset Test"}
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


def main():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    cleanup(app)
    try:
        test_google_login_creates_new_user(app, client)
        test_google_login_links_existing_password_account(app, client)
        used_token = test_forgot_and_reset_password_flow(app, client)
        test_used_token_is_rejected(client, used_token)
        print("\n全部通過")
    finally:
        cleanup(app)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 執行腳本**

Run（在 `backend/` 目錄下，需要 `.env` 裡的 `DATABASE_URL` 能連到開發用資料庫）: `uv run python scripts/test_auth_google_and_reset.py`
Expected: 依序印出四行 `[PASS] ...`，最後印出 `全部通過`，沒有 Traceback

- [ ] **Step 3: Commit**

```bash
git add backend/scripts/test_auth_google_and_reset.py
git commit -m "test: add manual DB integration script for Google login and password reset"
```

---

## Task 6: 前端 API client + authStore

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/store/authStore.ts`

**Interfaces:**
- Consumes: `POST /api/auth/google`、`/forgot-password`、`/reset-password`（Task 3、4）
- Produces: `loginWithGoogle(idToken: string): Promise<void>`、`forgotPassword(email: string): Promise<void>`、`resetPassword(token: string, password: string): Promise<void>`（`api/auth.ts`）；`authStore.loginWithGoogle(idToken: string): Promise<void>` — Task 7、9 會用到

- [ ] **Step 1: 在 `frontend/src/api/auth.ts` 檔案末尾新增三個函式**

```typescript

export async function loginWithGoogle (idToken: string): Promise<void> {
  const response = await fetch('/api/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ idToken }),
  })
  await parseAuthResponse(response)
}

export async function forgotPassword (email: string): Promise<void> {
  const response = await fetch('/api/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email }),
  })
  await parseAuthResponse(response)
}

export async function resetPassword (token: string, password: string): Promise<void> {
  const response = await fetch('/api/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ token, password }),
  })
  await parseAuthResponse(response)
}
```

- [ ] **Step 2: 修改 `frontend/src/store/authStore.ts`**

把：

```typescript
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  type AuthUser,
  fetchCurrentUser,
} from '@/api/auth'
```

改成：

```typescript
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  login as apiLogin,
  loginWithGoogle as apiLoginWithGoogle,
  logout as apiLogout,
  register as apiRegister,
  type AuthUser,
  fetchCurrentUser,
} from '@/api/auth'
```

把：

```typescript
  async function register (email: string, password: string, displayName: string): Promise<void> {
    await apiRegister(email, password, displayName)
    await checkSession()
  }

  async function logout (): Promise<void> {
    await apiLogout()
    user.value = null
  }

  return { user, isReady, isAuthenticated, checkSession, login, register, logout }
```

改成：

```typescript
  async function register (email: string, password: string, displayName: string): Promise<void> {
    await apiRegister(email, password, displayName)
    await checkSession()
  }

  async function loginWithGoogle (idToken: string): Promise<void> {
    await apiLoginWithGoogle(idToken)
    await checkSession()
  }

  async function logout (): Promise<void> {
    await apiLogout()
    user.value = null
  }

  return { user, isReady, isAuthenticated, checkSession, login, register, loginWithGoogle, logout }
```

- [ ] **Step 3: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/auth.ts frontend/src/store/authStore.ts
git commit -m "feat: add Google login, forgot-password, reset-password API client functions"
```

---

## Task 7: GoogleSignInButton 元件

**Files:**
- Create: `frontend/src/components/auth/GoogleSignInButton.vue`
- Modify: `frontend/.env.example`（新建立這個檔案，因為目前 frontend 沒有 `.env.example`）

**Interfaces:**
- Consumes: `import.meta.env.VITE_GOOGLE_CLIENT_ID`
- Produces: `<GoogleSignInButton @credential="(idToken: string) => void" />` — Task 8 會在 LoginView.vue、RegisterView.vue 使用

- [ ] **Step 1: 建立元件**

`frontend/src/components/auth/GoogleSignInButton.vue`：

```vue
<template>
  <div ref="buttonContainer" class="google-signin-button" />
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'

  declare global {
    interface Window {
      google: {
        accounts: {
          id: {
            initialize: (config: {
              client_id: string
              callback: (response: { credential: string }) => void
            }) => void
            renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void
          }
        }
      }
    }
  }

  const emit = defineEmits<{ credential: [idToken: string] }>()

  const buttonContainer = ref<HTMLElement | null>(null)

  const GIS_SCRIPT_SRC = 'https://accounts.google.com/gsi/client'

  function loadGisScript (): Promise<void> {
    if (document.querySelector(`script[src="${GIS_SCRIPT_SRC}"]`)) {
      return Promise.resolve()
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = GIS_SCRIPT_SRC
      script.async = true
      script.defer = true
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('無法載入 Google 登入元件'))
      document.head.appendChild(script)
    })
  }

  onMounted(async () => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined
    if (!clientId || !buttonContainer.value) return

    try {
      await loadGisScript()
    } catch {
      return
    }

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: response => emit('credential', response.credential),
    })
    window.google.accounts.id.renderButton(buttonContainer.value, {
      type: 'standard',
      theme: 'outline',
      size: 'large',
      width: 320,
    })
  })
</script>
```

- [ ] **Step 2: 建立 `frontend/.env.example`**

```
VITE_GOOGLE_CLIENT_ID=
```

- [ ] **Step 3: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/auth/GoogleSignInButton.vue frontend/.env.example
git commit -m "feat: add GoogleSignInButton component"
```

---

## Task 8: LoginView / RegisterView 加上 Google 按鈕與忘記密碼連結

**Files:**
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/RegisterView.vue`

**Interfaces:**
- Consumes: `GoogleSignInButton`（Task 7）、`authStore.loginWithGoogle`（Task 6）

- [ ] **Step 1: 修改 `frontend/src/views/LoginView.vue` 的 script**

把：

```typescript
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const DEV_ADMIN_EMAIL = 'admin@datamind.local'
  const DEV_ADMIN_PASSWORD = 'changeme-locally'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  function fillAdminCredentials (): void {
    email.value = DEV_ADMIN_EMAIL
    password.value = DEV_ADMIN_PASSWORD
  }

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.login(email.value, password.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>
```

改成：

```typescript
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import GoogleSignInButton from '@/components/auth/GoogleSignInButton.vue'
  import { useAuthStore } from '@/store/authStore'

  const DEV_ADMIN_EMAIL = 'admin@datamind.local'
  const DEV_ADMIN_PASSWORD = 'changeme-locally'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  function fillAdminCredentials (): void {
    email.value = DEV_ADMIN_EMAIL
    password.value = DEV_ADMIN_PASSWORD
  }

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.login(email.value, password.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }

  async function handleGoogleCredential (idToken: string): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.loginWithGoogle(idToken)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>
```

- [ ] **Step 2: 修改 `frontend/src/views/LoginView.vue` 的 template**

把：

```html
        <div class="form-field">
          <label class="form-label" for="login-password">密碼</label>
          <input
            id="login-password"
            v-model="password"
            class="form-input"
            placeholder="輸入密碼"
            required
            type="password"
          >
        </div>
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '登入中...' : '登入' }}
        </button>
      </form>

      <button class="auth-dev-btn" type="button" @click="fillAdminCredentials">
        使用管理員帳號（開發用）
      </button>
```

改成：

```html
        <div class="form-field">
          <div class="form-label-row">
            <label class="form-label" for="login-password">密碼</label>
            <RouterLink class="forgot-link" to="/forgot-password">忘記密碼？</RouterLink>
          </div>
          <input
            id="login-password"
            v-model="password"
            class="form-input"
            placeholder="輸入密碼"
            required
            type="password"
          >
        </div>
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '登入中...' : '登入' }}
        </button>
      </form>

      <div class="auth-divider"><span>或</span></div>
      <GoogleSignInButton class="google-btn" @credential="handleGoogleCredential" />

      <button class="auth-dev-btn" type="button" @click="fillAdminCredentials">
        使用管理員帳號（開發用）
      </button>
```

- [ ] **Step 3: 在 `frontend/src/views/LoginView.vue` 的 `<style scoped>` 新增樣式**

在 `.auth-switch a:hover { text-decoration: underline; }` 之後新增：

```css

.form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.forgot-link {
  font-size: 12.5px;
  color: var(--color-accent);
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0;
  font-size: 12px;
  color: var(--color-secondary);
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e8e8e8;
}

.google-btn {
  display: flex;
  justify-content: center;
}
```

- [ ] **Step 4: 修改 `frontend/src/views/RegisterView.vue` 的 script**

把：

```typescript
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const displayName = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.register(email.value, password.value, displayName.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>
```

改成：

```typescript
<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import GoogleSignInButton from '@/components/auth/GoogleSignInButton.vue'
  import { useAuthStore } from '@/store/authStore'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const displayName = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.register(email.value, password.value, displayName.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }

  async function handleGoogleCredential (idToken: string): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.loginWithGoogle(idToken)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>
```

- [ ] **Step 5: 修改 `frontend/src/views/RegisterView.vue` 的 template**

把：

```html
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '註冊中...' : '註冊' }}
        </button>
      </form>

      <p class="auth-switch">
        已經有帳號？<RouterLink to="/login">登入</RouterLink>
      </p>
```

改成：

```html
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '註冊中...' : '註冊' }}
        </button>
      </form>

      <div class="auth-divider"><span>或</span></div>
      <GoogleSignInButton class="google-btn" @credential="handleGoogleCredential" />

      <p class="auth-switch">
        已經有帳號？<RouterLink to="/login">登入</RouterLink>
      </p>
```

- [ ] **Step 6: 在 `frontend/src/views/RegisterView.vue` 的 `<style scoped>` 新增樣式**

在 `.auth-switch a:hover { text-decoration: underline; }` 之後新增（跟 Task 8 Step 3 完全一樣的 `.auth-divider`／`.google-btn`，不需要 `.form-label-row`／`.forgot-link`，RegisterView 沒有忘記密碼連結）：

```css

.auth-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 18px 0;
  font-size: 12px;
  color: var(--color-secondary);
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e8e8e8;
}

.google-btn {
  display: flex;
  justify-content: center;
}
```

- [ ] **Step 7: 執行 type-check 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run type-check`
Expected: 沒有錯誤訊息，指令成功結束

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/LoginView.vue frontend/src/views/RegisterView.vue
git commit -m "feat: wire Google sign-in button and forgot-password link into login/register pages"
```

---

## Task 9: 忘記密碼／重設密碼頁面 + 路由 + 最終驗證

**Files:**
- Create: `frontend/src/views/ForgotPasswordView.vue`
- Create: `frontend/src/views/ResetPasswordView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `forgotPassword`、`resetPassword`（Task 6，`frontend/src/api/auth.ts`）

- [ ] **Step 1: 建立 `frontend/src/views/ForgotPasswordView.vue`**

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">忘記密碼</h1>
      <p class="auth-sub">輸入註冊時使用的 email，我們會寄送重設密碼連結</p>

      <div v-if="submitted" class="auth-info">
        若此 email 已註冊，重設密碼信已寄出，請檢查你的信箱。
      </div>

      <form v-else class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="forgot-email">Email</label>
          <input
            id="forgot-email"
            v-model="email"
            class="form-input"
            placeholder="you@example.com"
            required
            type="email"
          >
        </div>
        <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
          {{ isSubmitting ? '送出中...' : '送出重設連結' }}
        </button>
      </form>

      <p class="auth-switch">
        想起密碼了？<RouterLink to="/login">回到登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink } from 'vue-router'
  import { forgotPassword } from '@/api/auth'

  const email = ref('')
  const isSubmitting = ref(false)
  const submitted = ref(false)

  async function handleSubmit (): Promise<void> {
    isSubmitting.value = true
    try {
      await forgotPassword(email.value)
    } catch {
      // 不論成功或失敗都顯示同一句訊息，避免洩漏 email 是否已註冊
    } finally {
      isSubmitting.value = false
      submitted.value = true
    }
  }
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 32px;
  color: var(--color-ink);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0 0 20px;
}

.auth-info {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #15803d;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-secondary);
}

.form-input:focus {
  border-color: var(--color-accent);
}

.auth-submit-btn {
  width: 100%;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.auth-submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-secondary);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 2: 建立 `frontend/src/views/ResetPasswordView.vue`**

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">重設密碼</h1>

      <template v-if="!token">
        <p class="auth-sub">這個連結不完整或已失效。</p>
        <p class="auth-switch">
          <RouterLink to="/forgot-password">重新申請重設密碼</RouterLink>
        </p>
      </template>

      <template v-else-if="success">
        <div class="auth-info">密碼已重設完成，請用新密碼登入。</div>
        <p class="auth-switch">
          <RouterLink to="/login">前往登入</RouterLink>
        </p>
      </template>

      <template v-else>
        <p class="auth-sub">設定一組新密碼</p>
        <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>
        <form class="auth-form" @submit.prevent="handleSubmit">
          <div class="form-field">
            <label class="form-label" for="reset-password">新密碼</label>
            <input
              id="reset-password"
              v-model="password"
              class="form-input"
              placeholder="設定新密碼"
              required
              type="password"
            >
          </div>
          <button class="auth-submit-btn" :disabled="isSubmitting" type="submit">
            {{ isSubmitting ? '重設中...' : '重設密碼' }}
          </button>
        </form>
        <p class="auth-switch">
          連結失效？<RouterLink to="/forgot-password">重新申請</RouterLink>
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRoute } from 'vue-router'
  import { resetPassword } from '@/api/auth'

  const route = useRoute()
  const token = (route.query.token as string | undefined) ?? ''

  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)
  const success = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await resetPassword(token, password.value)
      success.value = true
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 32px;
  color: var(--color-ink);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0 0 20px;
}

.auth-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.auth-info {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #15803d;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-secondary);
}

.form-input:focus {
  border-color: var(--color-accent);
}

.auth-submit-btn {
  width: 100%;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.auth-submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-secondary);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 3: 修改 `frontend/src/router/index.ts`**

把：

```typescript
const PUBLIC_PATHS = ["/login", "/register"];
```

改成：

```typescript
const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];
```

把：

```typescript
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
    },
```

改成：

```typescript
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
    },
    {
      path: "/forgot-password",
      name: "forgot-password",
      component: () => import("@/views/ForgotPasswordView.vue"),
    },
    {
      path: "/reset-password",
      name: "reset-password",
      component: () => import("@/views/ResetPasswordView.vue"),
    },
```

- [ ] **Step 4: 執行 build 確認沒有編譯錯誤**

Run（在 `frontend/` 目錄下）: `npm run build`
Expected: 沒有 TypeScript 或編譯錯誤，指令成功結束

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ForgotPasswordView.vue frontend/src/views/ResetPasswordView.vue frontend/src/router/index.ts
git commit -m "feat: add forgot-password and reset-password pages"
```

- [ ] **Step 6: 手動瀏覽器驗證（需要先在 `backend/.env` 填入真實的 `GOOGLE_CLIENT_ID`，`frontend/.env` 填入對應的 `VITE_GOOGLE_CLIENT_ID`，否則 Google 按鈕不會出現，屬於預期行為）**

啟動後端（`backend/` 目錄下）: `uv run python app.py`
啟動前端（`frontend/` 目錄下）: `npm run dev`

檢查清單：
1. 開啟 `/login`，密碼欄位下方看得到「忘記密碼？」連結
2. 點「忘記密碼？」導到 `/forgot-password`，輸入任意 email 送出後顯示同一句提示文字
3. 到後端終端機的 log 裡找到 `[password-reset] to=... link=...` 那一行，複製 `link` 貼到瀏覽器
4. 在 `/reset-password?token=...` 頁面輸入新密碼送出，顯示「密碼已重設完成」
5. 回到 `/login` 用新密碼登入成功
6. 若已設定 `GOOGLE_CLIENT_ID`／`VITE_GOOGLE_CLIENT_ID`：登入頁與註冊頁都看得到 Google 按鈕，點擊可以完成登入並導向 `/hub/dashboard`

---

## Self-Review

**Spec coverage：**
- 段落 A（資料模型變更）→ Task 1
- 段落 B（Google 登入流程）→ Task 3、6、7、8
- 段落 C（忘記密碼流程）→ Task 4、6、9
- 段落 D（可插拔寄信介面）→ Task 2
- 驗證方式（後端測試腳本、前端手動測試）→ Task 5、Task 9 Step 6

**Placeholder scan：** 每個 Step 都有完整可執行的程式碼與明確的 Run/Expected，沒有 TBD/TODO。

**Type consistency：** `verify_google_id_token(token: str) -> dict` 在 Task 3 定義、Task 5 用 `patch("routes.auth.verify_google_id_token", ...)` monkeypatch，名稱一致。`send_reset_password_email(to: str, reset_link: str) -> None` 在 Task 2 定義、Task 4 匯入使用、Task 5 用 `patch("routes.auth.send_reset_password_email", ...)` monkeypatch，名稱與參數順序一致。前端 `authStore.loginWithGoogle(idToken: string)` 在 Task 6 定義，Task 8 的 `handleGoogleCredential` 呼叫時參數型別一致。`GoogleSignInButton` 的 `credential` event payload 型別（`string`，也就是 `response.credential`）與 Task 8 `handleGoogleCredential (idToken: string)` 一致。
