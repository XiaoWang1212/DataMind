"""欄位對齊 API：把論文變數對映到使用者資料表欄位。

薄路由層，寫法比照 routes/gemini.py。所有配對邏輯在
services/field_mapping_service.py，Gemini 相關在 services/gemini_service.py。

這兩支不碰資料庫：對映結果的持久化由前端在使用者確認時，
透過既有的 PATCH /api/projects/<id> 完成。

無狀態設計：/chat 每次都由前端帶完整 current_mapping_state 上來，
伺服器不保留任何對話。這樣前端重新整理不會對不上。
"""

import logging

from flask import Blueprint, jsonify, request
from flask_login import login_required

from services.field_mapping_service import (
    AUTO_MATCHED,
    merge_semantic_suggestions,
    normalize_user_columns,
    run_auto_mapping,
)
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

field_mapping_bp = Blueprint("field_mapping", __name__)


@field_mapping_bp.post("/init")
@login_required
def init_field_mapping():
    """初始化對映狀態。

    輸入：{ paper_variables: [...], user_columns: [...] }
    流程：演算法自動配對 → 配不到的交給 Gemini 語意判斷 → 合併
    回傳：{ success, result: {...}, ai_available }

    Gemini 不可用不會讓這支 API 失敗 —— 演算法層不需要 API key 就能運作，
    沒有理由讓整個功能不可用。改用 ai_available 告訴前端要不要顯示提示。
    """
    data = request.get_json(silent=True) or {}
    paper_variables = data.get("paper_variables") or []
    user_columns = data.get("user_columns") or []

    if not paper_variables:
        return jsonify({"success": False, "error": "paper_variables is required"}), 400
    if not user_columns:
        return jsonify({"success": False, "error": "user_columns is required"}), 400

    columns = normalize_user_columns(user_columns)
    if not columns:
        return jsonify({"success": False, "error": "user_columns has no valid column"}), 400

    result = run_auto_mapping(paper_variables, columns)
    pending = [
        item for item in result["mapping_status"] if item["status"] != AUTO_MATCHED
    ]

    if not pending:
        return jsonify({"success": True, "result": result, "ai_available": True})

    try:
        suggestions = GeminiService().semantic_match(pending, columns)
    except Exception:
        logger.exception("semantic_match 階段失敗，改用純演算法結果")
        suggestions = None

    if suggestions is None:
        return jsonify({"success": True, "result": result, "ai_available": False})

    merge_semantic_suggestions(result, suggestions, columns)
    return jsonify({"success": True, "result": result, "ai_available": True})


@field_mapping_bp.post("/chat")
@login_required
def chat_field_mapping():
    """對話式修正對映。

    輸入：{ current_mapping_state, user_message, chat_history }
    回傳：{ success, result: { actions: [...], reply: str } }

    只回這一輪的 diff，不回整包 mapping_status —— 由前端自行套用到本地狀態。
    """
    data = request.get_json(silent=True) or {}
    state = data.get("current_mapping_state") or {}
    message = (data.get("user_message") or "").strip()
    history = data.get("chat_history") or []

    if not message:
        return jsonify({"success": False, "error": "user_message is required"}), 400

    try:
        service = GeminiService()
    except Exception as exc:
        logger.exception("GeminiService 初始化失敗")
        return jsonify({"success": False, "error": str(exc)}), 503

    try:
        result = service.chat_refine(state, message, history)
    except Exception as exc:
        logger.exception("chat_refine 失敗")
        return jsonify({"success": False, "error": str(exc)}), 500

    return jsonify({"success": True, "result": result})
