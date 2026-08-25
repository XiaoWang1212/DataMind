"""論文編輯內容儲存 API"""

import logging
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

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


@report_bp.route("/<int:project_id>/pdf", methods=["POST"])
@login_required
def download_report_pdf(project_id: int):
    """把前端排好版的分頁 HTML 轉成 PDF 回傳（下載用途，不寫入資料庫）

    JSON body:
        - html     : 完整的獨立 HTML 文件字串（含內嵌 CSS，前端已排好版），必填
        - filename : 下載檔名（不含副檔名，選填，預設 'paper'）
    """
    if not _get_owned_project(project_id):
        return jsonify({"success": False, "error": "找不到專案"}), 404

    data = request.get_json()
    if not data or not data.get("html"):
        return jsonify({"success": False, "error": "html 為必填欄位"}), 400

    # 匯入放驗證之後：WeasyPrint 匯入時會去載入系統的 Pango/Cairo 原生函式庫，
    # 不便宜，沒必要在請求會被 404/400 擋掉時還先付這個成本
    from services.report.pdf_export import html_to_pdf

    try:
        pdf_bytes = html_to_pdf(data["html"])
    except Exception as e:
        logger.exception("PDF 轉檔失敗")
        return jsonify({"success": False, "error": str(e)}), 500

    # 論文標題幾乎都是中文，secure_filename 會把非 ASCII 字元全部濾掉、
    # 中文標題會整個消失——filename 給舊客戶端當退路，filename* 才是
    # 瀏覽器實際顯示/存檔用的檔名（RFC 6266，可以放中文）
    raw_filename = f"{data.get('filename') or 'paper'}.pdf"
    ascii_fallback = secure_filename(raw_filename) or "paper.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename={ascii_fallback}; "
                f"filename*=UTF-8''{quote(raw_filename)}"
            ),
        },
    )
