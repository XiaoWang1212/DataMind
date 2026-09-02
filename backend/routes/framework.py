"""框架庫 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.framework import Framework
from services.framework_dedupe import normalize_hash, normalize_title

framework_bp = Blueprint("framework", __name__)


def _serialize_framework(framework: Framework) -> dict:
    return {
        "id": framework.id,
        "title": framework.title,
        "subtitle": framework.subtitle,
        "tag": framework.tag,
        "variables": framework.variables,
        "paperTitle": framework.paper_title,
        "description": framework.description,
        "independentVars": framework.independent_vars or [],
        "dependentVars": framework.dependent_vars or [],
        "hypotheses": framework.hypotheses or [],
        "workflowJson": framework.workflow_json,
        "date": framework.created_at.strftime("%Y-%m-%d"),
    }


@framework_bp.route("", methods=["GET"])
@login_required
def list_frameworks():
    frameworks = (
        Framework.query.filter_by(user_id=current_user.id)
        .order_by(Framework.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "result": [_serialize_framework(f) for f in frameworks]})


@framework_bp.route("", methods=["POST"])
@login_required
def create_framework():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    title = data.get("title")
    if not title:
        return jsonify({"success": False, "error": "title 為必填欄位"}), 400
    if len(title) > 255:
        return jsonify({"success": False, "error": "title 長度不可超過 255 字元"}), 400

    framework = Framework(
        user_id=current_user.id,
        title=title,
        subtitle=data.get("subtitle"),
        tag=data.get("tag"),
        variables=data.get("variables"),
        paper_title=data.get("paperTitle"),
        description=data.get("description"),
        independent_vars=data.get("independentVars"),
        dependent_vars=data.get("dependentVars"),
        hypotheses=data.get("hypotheses"),
        workflow_json=data.get("workflowJson"),
        pdf_hash=normalize_hash(data.get("pdfHash")) or None,
    )
    db.session.add(framework)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})


def _user_frameworks() -> list[Framework]:
    return (
        Framework.query.filter_by(user_id=current_user.id)
        .order_by(Framework.created_at.desc())
        .all()
    )


def _match(framework: Framework, match_type: str) -> dict:
    return {"id": framework.id, "title": framework.title, "matchType": match_type}


def _match_by_hash(pdf_hash: str) -> dict | None:
    """比對 PDF 內容。舊框架沒有 hash，跳過那些筆"""
    for framework in _user_frameworks():
        if framework.pdf_hash and normalize_hash(framework.pdf_hash) == pdf_hash:
            return _match(framework, "hash")
    return None


def _match_by_title(title: str) -> dict | None:
    """比對檔名。paper_title 不受框架改名影響，所以兩個欄位都比"""
    for framework in _user_frameworks():
        if title in {normalize_title(framework.title), normalize_title(framework.paper_title)}:
            return _match(framework, "title")
    return None


@framework_bp.route("/check-duplicate", methods=["POST"])
@login_required
def check_duplicate():
    """找出框架庫中同一份 PDF 或同名的框架

    hash 相同代表確定是同一份檔案；hash 比不到才比檔名，用來涵蓋沒有 hash 的
    舊框架，以及同一篇論文的不同檔案。沒有命中時 result 為 null。
    """
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    pdf_hash = normalize_hash(data.get("pdfHash"))
    if pdf_hash:
        match = _match_by_hash(pdf_hash)
        if match:
            return jsonify({"success": True, "result": match})

    title = normalize_title(data.get("title"))
    if title:
        return jsonify({"success": True, "result": _match_by_title(title)})

    return jsonify({"success": True, "result": None})


@framework_bp.route("/<int:framework_id>", methods=["GET"])
@login_required
def get_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404

    return jsonify({"success": True, "result": _serialize_framework(framework)})


@framework_bp.route("/<int:framework_id>", methods=["PATCH"])
@login_required
def update_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return jsonify({"success": False, "error": "title 不可為空"}), 400
        if len(title) > 255:
            return jsonify({"success": False, "error": "title 長度不可超過 255 字元"}), 400
        framework.title = title

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
