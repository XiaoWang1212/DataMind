import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request
from services.model.registry import extract_model_components
from services.workflow import WorkflowService

model_bp = Blueprint("model", __name__)

ALLOWED_DATA_EXTENSIONS = {"json"}
ALLOWED_CSV_EXTENSIONS = {"csv"}


def _is_allowed_json_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_DATA_EXTENSIONS


def _is_allowed_csv_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_CSV_EXTENSIONS


def _save_uploaded_file(uploaded, upload_dir: Path) -> Path:
    raw_name = uploaded.filename
    safe_name = secure_filename(raw_name)
    if not safe_name.lower().endswith(".csv"):
        safe_name = f"{uploaded.filename}.csv"

    upload_dir.mkdir(parents=True, exist_ok=True)
    destination = upload_dir / safe_name
    uploaded.save(str(destination))
    return destination


@model_bp.post("/extract-components")
def extract_components():
    payload: Optional[Dict[str, Any]] = None
    uploaded = request.files.get("file")

    if uploaded and uploaded.filename:
        raw_name = uploaded.filename
        if not _is_allowed_json_file(raw_name):
            return (
                jsonify({"error": "Unsupported file format. Only .json is allowed."}),
                400,
            )

        try:
            payload = json.load(uploaded)
        except json.JSONDecodeError as exc:
            return jsonify({"error": f"Invalid JSON file: {str(exc)}"}), 400
    else:
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Missing JSON payload or file upload."}), 400

    model_names = request.args.getlist("model_names") or payload.get("model_names")
    if isinstance(model_names, str):
        model_names = [model_names]

    try:
        components = extract_model_components(payload, model_names=model_names)
        return jsonify({"success": True, "components": components})
    except Exception as exc:
        return (
            jsonify({"error": f"Failed to extract model components: {str(exc)}"}),
            500,
        )


@model_bp.post("/preprocess/variants")
def preprocess_variants():
    payload = request.get_json(silent=True) or {}
    step_groups = payload.get("step_groups", [])

    try:
        variants = WorkflowService.generate_preprocess_variants(step_groups)
        return jsonify({"success": True, "variants": variants})
    except Exception as exc:
        return (
            jsonify({"error": f"Failed to generate preprocess variants: {str(exc)}"}),
            500,
        )


@model_bp.post("/score/variants")
def score_variants():
    payload = request.get_json(silent=True) or {}
    score_groups = payload.get("score_groups", [])

    try:
        variants = WorkflowService.generate_score_variants(score_groups)
        return jsonify({"success": True, "variants": variants})
    except Exception as exc:
        return jsonify({"error": f"Failed to generate score variants: {str(exc)}"}), 500


@model_bp.post("/workflow/execute")
def execute_workflow():
    payload = request.get_json(silent=True) or {}
    uploaded = request.files.get("file")
    data_path = payload.get("data_path")
    target_col = payload.get("target_col", "是否跌倒")
    preprocess_pipelines = payload.get("preprocess_pipelines", [])
    model_names = payload.get("model_names", [])
    score_variants = payload.get("score_variants", [])
    validation_config = payload.get("validation_config", {})
    train_size = float(payload.get("train_size", 0.7))
    random_state = int(payload.get("random_state", 42))

    if uploaded and uploaded.filename:
        if not _is_allowed_csv_file(uploaded.filename):
            return (
                jsonify(
                    {
                        "error": "Unsupported file format. Only .csv is allowed for workflow execution."
                    }
                ),
                400,
            )
        data_path = str(_save_uploaded_file(uploaded, Path("uploads/workflow")))

    if not data_path:
        return jsonify({"error": "data_path or CSV file upload is required."}), 400

    if not isinstance(model_names, list):
        model_names = [model_names]

    if not isinstance(preprocess_pipelines, list):
        preprocess_pipelines = []

    if not isinstance(score_variants, list):
        score_variants = []

    try:
        result = WorkflowService.execute_workflow(
            data_path=data_path,
            target_col=target_col,
            preprocess_pipelines=preprocess_pipelines,
            model_names=model_names,
            score_variants=score_variants,
            validation_config=validation_config,
            train_size=train_size,
            random_state=random_state,
        )
        return jsonify(result)
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Workflow execution failed: {str(exc)}"}), 500
