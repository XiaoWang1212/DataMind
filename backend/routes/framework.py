"""框架庫 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.framework import Framework

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
    )
    db.session.add(framework)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
