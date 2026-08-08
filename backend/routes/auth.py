"""使用者註冊/登入/登出 API"""

import logging
import os

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from extensions import db
from models.user import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    email = data.get("email")
    password = data.get("password")
    display_name = data.get("displayName", "")

    if not email or not password:
        return jsonify({"success": False, "error": "email 和 password 為必填欄位"}), 400

    if len(password.encode("utf-8")) > 72:
        return jsonify({"success": False, "error": "password 過長（bcrypt 上限為 72 bytes）"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "error": "此 email 已被註冊"}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(email=email, password_hash=password_hash, display_name=display_name)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    return jsonify({"success": True, "result": {"id": user.id, "email": user.email}})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"success": False, "error": "email 和 password 為必填欄位"}), 400

    if len(password.encode("utf-8")) > 72:
        return jsonify({"success": False, "error": "帳號或密碼錯誤"}), 401

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        return jsonify({"success": False, "error": "帳號或密碼錯誤"}), 401

    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return jsonify({"success": False, "error": "帳號或密碼錯誤"}), 401

    login_user(user)
    return jsonify({"success": True, "result": {"id": user.id, "email": user.email}})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    return jsonify(
        {
            "success": True,
            "result": {
                "id": current_user.id,
                "email": current_user.email,
                "displayName": current_user.display_name,
                "isAdmin": current_user.is_admin,
            },
        }
    )


def verify_google_id_token(token: str) -> dict:
    """驗證 Google ID token 的簽章與 audience，回傳解碼後的 payload。

    Token 無效時，底層函式可能拋出 ValueError（過期、簽章錯誤、aud 不符）
    或 google.auth.exceptions.GoogleAuthError（issuer 不符，非 ValueError 子類別）。
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
    except (ValueError, google_auth_exceptions.GoogleAuthError):
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
