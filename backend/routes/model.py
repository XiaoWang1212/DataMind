import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request
from services.model.registry import extract_model_components
from services.workflow import WorkflowService
from services.workflow.extraction_mapper import build_workflow_payload

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


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _load_request_payload() -> Dict[str, Any]:
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload

    payload_text = request.form.get("workflow_payload") or request.form.get("payload")
    if payload_text:
        try:
            return json.loads(payload_text)
        except json.JSONDecodeError:
            return {}

    return {}


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
    payload = _load_request_payload()
    uploaded = request.files.get("file")
    data_path = payload.get("data_path")
    target_col = payload.get(
        "target_col",
        payload.get("targetCol", payload.get("target", "是否跌倒")),
    )
    preprocess_pipelines = _parse_json_field(payload.get("preprocess_pipelines", []))
    feature_engineering_pipelines = _parse_json_field(
        payload.get("feature_engineering_pipelines", [])
    )
    model_names = payload.get("model_names", payload.get("models", []))
    score_variants = _parse_json_field(payload.get("score_variants", []))
    validation_config = _parse_json_field(
        payload.get("validation_config", payload.get("validation", {}))
    )
    train_size = float(payload.get("train_size", 0.7))
    random_state = int(payload.get("random_state", 42))

    if any(
        key in payload
        for key in [
            "preprocessing",
            "featureEngineering",
            "feature_engineering",
            "models",
            "validation",
            "metrics",
        ]
    ):
        mapped = build_workflow_payload(payload)
        preprocess_pipelines = (
            mapped.get("preprocess_pipelines", preprocess_pipelines)
            or preprocess_pipelines
        )
        feature_engineering_pipelines = (
            mapped.get("feature_engineering_pipelines", feature_engineering_pipelines)
            or feature_engineering_pipelines
        )
        model_names = mapped.get("model_names", model_names) or model_names
        validation_config = (
            mapped.get("validation_config", validation_config) or validation_config
        )
        score_variants = mapped.get("score_variants", score_variants) or score_variants
        if mapped.get("target_col") is not None:
            payload["target_col"] = mapped["target_col"]
            target_col = payload.get(
                "target_col",
                payload.get("targetCol", payload.get("target", "是否跌倒")),
            )

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

    if isinstance(model_names, list):
        normalized_models = []
        for item in model_names:
            if isinstance(item, str):
                normalized_models.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("model") or item.get("type")
                if name:
                    normalized_models.append(name)
        model_names = normalized_models
    else:
        model_names = [model_names]

    if not preprocess_pipelines:
        preprocess_pipelines = _parse_json_field(payload.get("preprocessing", []))
    if isinstance(preprocess_pipelines, dict):
        preprocess_pipelines = [preprocess_pipelines]
    if not isinstance(preprocess_pipelines, list):
        preprocess_pipelines = []
    elif preprocess_pipelines and isinstance(preprocess_pipelines[0], dict):
        preprocess_pipelines = [preprocess_pipelines]

    if not feature_engineering_pipelines:
        feature_engineering_pipelines = _parse_json_field(
            payload.get("featureEngineering", [])
        )
    if isinstance(feature_engineering_pipelines, dict):
        feature_engineering_pipelines = [feature_engineering_pipelines]
    if not isinstance(feature_engineering_pipelines, list):
        feature_engineering_pipelines = []
    elif feature_engineering_pipelines and isinstance(
        feature_engineering_pipelines[0], dict
    ):
        feature_engineering_pipelines = [feature_engineering_pipelines]

    if not score_variants:
        score_variants = _parse_json_field(payload.get("metrics", []))
    if isinstance(score_variants, dict):
        score_variants = [score_variants]
    if not isinstance(score_variants, list):
        score_variants = []

    try:
        result = WorkflowService.execute_workflow(
            data_path=data_path,
            target_col=target_col,
            preprocess_pipelines=preprocess_pipelines,
            feature_engineering_pipelines=feature_engineering_pipelines,
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
