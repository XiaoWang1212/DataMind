"""論文編輯內容儲存 API"""

import logging

from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__)


@report_bp.route("/<project_id>", methods=["POST"])
def save_report(project_id: str):
    """儲存論文編輯內容

    JSON body:
        - title    : 論文標題（必填）
        - content  : Tiptap JSON 文件內容（必填）
        - citations: 參考文獻清單（選填，預設空陣列）
    """
    from services.report.report_store import get_report_store

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    title = data.get("title")
    content = data.get("content")
    citations = data.get("citations", [])

    if not title or content is None:
        return jsonify({"success": False, "error": "title 和 content 為必填欄位"}), 400

    store = get_report_store()

    try:
        result = store.save(project_id, title, content, citations)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("儲存論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route("/<project_id>", methods=["GET"])
def get_report(project_id: str):
    """讀取論文編輯內容，查無資料回 404"""
    from services.report.report_store import get_report_store

    store = get_report_store()

    try:
        result = store.load(project_id)
        if result is None:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("讀取論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500
