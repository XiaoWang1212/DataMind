"""論文編輯內容儲存 API"""

import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from models.project import Project

logger = logging.getLogger(__name__)

report_bp = Blueprint("report", __name__)

VALID_CITATION_STYLES = {"apa", "ieee", "mla"}


def _get_owned_project(project_id: int) -> Project | None:
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return None
    return project


@report_bp.route("/<int:project_id>", methods=["POST"])
@login_required
def save_report(project_id: int):
    """儲存論文編輯內容

    JSON body:
        - title        : 論文標題（必填）
        - content      : Tiptap JSON 文件內容（必填）
        - citations    : 參考文獻清單（選填，預設空陣列）
        - citationStyle: 參考文獻格式，'apa'/'ieee'/'mla'（選填，預設 'apa'）
    """
    from services.report.report_store import get_report_store

    if not _get_owned_project(project_id):
        return jsonify({"success": False, "error": "找不到專案"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    title = data.get("title")
    content = data.get("content")
    citations = data.get("citations", [])
    citation_style = data.get("citationStyle", "apa")
    if citation_style not in VALID_CITATION_STYLES:
        citation_style = "apa"

    if not title or content is None:
        return jsonify({"success": False, "error": "title 和 content 為必填欄位"}), 400

    store = get_report_store()

    try:
        result = store.save(str(project_id), title, content, citations, citation_style)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("儲存論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route("/<int:project_id>", methods=["GET"])
@login_required
def get_report(project_id: int):
    """讀取論文編輯內容，查無資料回 404"""
    from services.report.report_store import get_report_store

    if not _get_owned_project(project_id):
        return jsonify({"success": False, "error": "not found"}), 404

    store = get_report_store()

    try:
        result = store.load(str(project_id))
        if result is None:
            return jsonify({"success": False, "error": "not found"}), 404
        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("讀取論文失敗")
        return jsonify({"success": False, "error": str(e)}), 500
