"""手動驗證腳本：GET/PATCH /api/frameworks/<id>（需要可連線的開發用資料庫）

用法（在 backend/ 目錄下執行）：
    uv run python scripts/test_framework_rename.py

涵蓋：
  1. 已登入使用者建立框架後，PATCH title 可以成功改名，GET 讀回同一個值
  2. PATCH title 為空字串/純空白 → 回 400，資料庫裡的 title 不變
  3. 用另一個使用者的 client 對別人的框架 GET/PATCH → 回 404
  4. PATCH 不存在的 framework id → 回 404

執行後會清除腳本建立的測試帳號與框架，不會在資料庫留下垃圾資料。
"""

import os
import sys
from pathlib import Path

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
from models.framework import Framework  # noqa: E402
from models.user import User  # noqa: E402

OWNER_EMAIL = "framework-rename-owner@example.com"
OTHER_EMAIL = "framework-rename-other@example.com"
PASSWORD = "TestPass123"


def cleanup(app):
    with app.app_context():
        users = User.query.filter(User.email.in_([OWNER_EMAIL, OTHER_EMAIL])).all()
        user_ids = [u.id for u in users]
        if user_ids:
            Framework.query.filter(Framework.user_id.in_(user_ids)).delete(synchronize_session=False)
        User.query.filter(User.email.in_([OWNER_EMAIL, OTHER_EMAIL])).delete(synchronize_session=False)
        db.session.commit()


def _register(client, email):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "displayName": "Test User"},
    )
    assert response.get_json()["success"] is True, response.get_json()


def test_patch_updates_title(owner_client):
    create_response = owner_client.post("/api/frameworks", json={"title": "原始標題"})
    framework_id = create_response.get_json()["result"]["id"]

    response = owner_client.patch(f"/api/frameworks/{framework_id}", json={"title": "新標題"})
    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["success"] is True
    assert body["result"]["title"] == "新標題"

    get_response = owner_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.get_json()["result"]["title"] == "新標題"

    print("[PASS] PATCH title 成功改名，GET 讀回同一個值")
    return framework_id


def test_patch_rejects_empty_title(owner_client, framework_id):
    response = owner_client.patch(f"/api/frameworks/{framework_id}", json={"title": "   "})
    assert response.status_code == 400
    assert response.get_json()["success"] is False

    get_response = owner_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.get_json()["result"]["title"] == "新標題", "空白 title 不該真的寫進資料庫"

    print("[PASS] PATCH 空白 title 回 400，資料庫裡的值不變")


def test_patch_and_get_reject_other_users_framework(owner_client, other_client, framework_id):
    patch_response = other_client.patch(f"/api/frameworks/{framework_id}", json={"title": "搶別人的框架"})
    assert patch_response.status_code == 404

    get_response = other_client.get(f"/api/frameworks/{framework_id}")
    assert get_response.status_code == 404

    print("[PASS] 非本人操作別人的框架，GET/PATCH 都回 404")


def test_patch_nonexistent_framework_returns_404(owner_client):
    response = owner_client.patch("/api/frameworks/999999999", json={"title": "不存在"})
    assert response.status_code == 404
    print("[PASS] PATCH 不存在的框架 id 回 404")


def main():
    app = create_app()
    app.config["TESTING"] = True
    owner_client = app.test_client()
    other_client = app.test_client()

    cleanup(app)
    try:
        _register(owner_client, OWNER_EMAIL)
        _register(other_client, OTHER_EMAIL)

        framework_id = test_patch_updates_title(owner_client)
        test_patch_rejects_empty_title(owner_client, framework_id)
        test_patch_and_get_reject_other_users_framework(owner_client, other_client, framework_id)
        test_patch_nonexistent_framework_returns_404(owner_client)
        print("\n全部通過")
    finally:
        cleanup(app)


if __name__ == "__main__":
    main()
