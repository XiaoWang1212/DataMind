"""使用者註冊/登入/登出 API"""

import logging

import bcrypt
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user

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
