"""專案 CRUD API"""

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from extensions import db
from models.dataset import Dataset
from models.project import Project, ProjectStatus
from models.rag_paper import RagChunk, RagPaper
from models.report import Citation, Report
from models.workflow_state import WorkflowState

project_bp = Blueprint("project", __name__)


def _serialize_project(project: Project) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "frameworkId": project.framework_id,
        "datasetName": project.dataset_name,
        "status": project.status.value,
        "progress": project.progress,
        "accuracy": project.accuracy,
        "keyFinding": project.key_finding,
        "variables": project.variables,
        "columnMapping": project.column_mapping,
        "date": project.created_at.strftime("%Y-%m-%d"),
    }


@project_bp.route("", methods=["GET"])
@login_required
def list_projects():
    projects = (
        Project.query.filter_by(user_id=current_user.id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return jsonify({"success": True, "result": [_serialize_project(p) for p in projects]})


@project_bp.route("", methods=["POST"])
@login_required
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    name = data.get("name")
    if not name:
        return jsonify({"success": False, "error": "name 為必填欄位"}), 400

    project = Project(
        user_id=current_user.id,
        name=name,
        description=data.get("description"),
        framework_id=data.get("frameworkId"),
        dataset_name=data.get("datasetName"),
        variables=data.get("variables") or 0,
    )
    db.session.add(project)
    db.session.commit()
    return jsonify({"success": True, "result": _serialize_project(project)})


@project_bp.route("/<int:project_id>", methods=["GET"])
@login_required
def get_project(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    return jsonify({"success": True, "result": _serialize_project(project)})


@project_bp.route("/<int:project_id>", methods=["PATCH"])
@login_required
def update_project(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    if "status" in data:
        try:
            project.status = ProjectStatus(data["status"])
        except ValueError:
            return (
                jsonify({"success": False, "error": "status 必須是 draft/running/completed 其中之一"}),
                400,
            )
    if "progress" in data:
        project.progress = data["progress"]
    if "datasetName" in data:
        project.dataset_name = data["datasetName"]
    if "accuracy" in data:
        project.accuracy = data["accuracy"]
    if "keyFinding" in data:
        project.key_finding = data["keyFinding"]
    if "columnMapping" in data:
        project.column_mapping = data["columnMapping"]
    if "variables" in data:
        project.variables = data["variables"]

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_project(project)})


@project_bp.route("/<int:project_id>", methods=["DELETE"])
@login_required
def delete_project(project_id):
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    # projects.id 被多張表外鍵參照、且都沒有設 cascade，直接刪 project 會撞到
    # 外鍵約束，所以要先手動清掉這些關聯列，最後才刪 project 本身
    report = Report.query.filter_by(project_id=project_id).first()
    if report:
        Citation.query.filter_by(report_id=report.id).delete()
        db.session.delete(report)

    rag_paper_ids = [
        p.id for p in RagPaper.query.filter_by(project_id=project_id).with_entities(RagPaper.id)
    ]
    if rag_paper_ids:
        RagChunk.query.filter(RagChunk.paper_id.in_(rag_paper_ids)).delete(synchronize_session=False)
        RagPaper.query.filter_by(project_id=project_id).delete()

    WorkflowState.query.filter_by(project_id=project_id).delete()
    Dataset.query.filter_by(project_id=project_id).delete()

    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True, "result": None})
