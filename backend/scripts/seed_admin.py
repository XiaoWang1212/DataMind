"""建立管理員測試帳號的種子腳本

用法（在 backend/ 目錄下執行）：
    python scripts/seed_admin.py

如果 users 表已經有任何資料，此腳本不會做任何事（避免重複建立）。
Email/密碼透過環境變數 ADMIN_EMAIL / ADMIN_PASSWORD 設定，未設定時使用預設值。
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

import bcrypt

from apps import create_app
from extensions import db
from models.user import User


def main():
    app = create_app()
    with app.app_context():
        if User.query.first() is not None:
            print("users 表已有資料，略過建立管理員帳號。")
            return

        email = os.getenv("ADMIN_EMAIL", "admin@datamind.local")
        password = os.getenv("ADMIN_PASSWORD", "changeme")
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        admin = User(
            email=email,
            password_hash=password_hash,
            display_name="Admin",
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()
        print(f"已建立管理員帳號：{email}")


if __name__ == "__main__":
    main()
