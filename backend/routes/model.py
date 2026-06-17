import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request
from services.model.registry import extract_model_components
from services.workflow import WorkflowService
from services.workflow.extraction_mapper import build_workflow_payload
from services.workflow.job_manager import get_job, start_job

model_bp = Blueprint("model", __name__)

ALLOWED_DATA_EXTENSIONS = {"json"}
ALLOWED_DATA_FILE_EXTENSIONS = {"csv", "xlsx", "xls"}


def _is_allowed_json_file(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_DATA_EXTENSIONS


def _is_allowed_data_file(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_DATA_FILE_EXTENSIONS


def _save_uploaded_file(uploaded, upload_dir: Path) -> Path:
    raw_name = uploaded.filename or "data"
    ext = raw_name.rsplit(".", 1)[1].lower() if "." in raw_name else "csv"
    safe_stem = secure_filename(raw_name.rsplit(".", 1)[0]) or "data"
    safe_name = f"{safe_stem}.{ext}"

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
        if not _is_allowed_json_file(uploaded.filename):
            return jsonify({"error": "Unsupported file format. Only .json is allowed."}), 400
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
        return jsonify({"error": f"Failed to extract model components: {str(exc)}"}), 500


@model_bp.post("/preprocess/variants")
def preprocess_variants():
    payload = request.get_json(silent=True) or {}
    step_groups = payload.get("step_groups", [])

    try:
        variants = WorkflowService.generate_preprocess_variants(step_groups)
        return jsonify({"success": True, "variants": variants})
    except Exception as exc:
        return jsonify({"error": f"Failed to generate preprocess variants: {str(exc)}"}), 500


@model_bp.get("/available")
def available_models():
    try:
        available = WorkflowService.list_registered_models()
        return jsonify({"success": True, "models": available})
    except Exception as exc:
        return jsonify({"error": f"Failed to load available models: {str(exc)}"}), 500


@model_bp.post("/score/variants")
def score_variants():
    payload = request.get_json(silent=True) or {}
    score_groups = payload.get("score_groups", [])

    try:
        variants = WorkflowService.generate_score_variants(score_groups)
        return jsonify({"success": True, "variants": variants})
    except Exception as exc:
        return jsonify({"error": f"Failed to generate score variants: {str(exc)}"}), 500


def _parse_execute_params() -> Tuple[Optional[str], Dict[str, Any]]:
    """解析 workflow 執行共用的 request 參數，回傳 (data_path, kwargs)。"""
    payload = _load_request_payload()
    uploaded = request.files.get("file")

    data_path = payload.get("data_path")
    target_col = payload.get("target_col") or payload.get("targetCol") or payload.get("target") or "是否跌倒"

    preprocess_pipelines = _parse_json_field(payload.get("preprocess_pipelines", []))
    feature_engineering_pipelines = _parse_json_field(payload.get("feature_engineering_pipelines", []))
    model_names = payload.get("model_names") or payload.get("models") or []
    score_variants_raw = _parse_json_field(payload.get("score_variants", []))
    validation_config = _parse_json_field(payload.get("validation_config") or payload.get("validation") or {})
    column_config = _parse_json_field(payload.get("column_config") or payload.get("columnConfig") or [])

    resampling_method = str(payload.get("resampling_method", "none"))
    resampling_config = _parse_json_field(payload.get("resampling_config") or {})
    tuning_method = str(payload.get("tuning_method", "none"))
    tuning_cv = int(payload.get("tuning_cv", 3))
    tuning_n_iter = int(payload.get("tuning_n_iter", 20))
    tuning_scoring = str(payload.get("tuning_scoring", "roc_auc"))
    compute_ci = bool(payload.get("compute_ci", False))
    ci_n_bootstrap = int(payload.get("ci_n_bootstrap", 1000))
    train_size = float(payload.get("train_size", 0.7))
    random_state = int(payload.get("random_state", 42))

    menu_keys = {"preprocessing", "featureEngineering", "feature_engineering", "models", "validation", "metrics"}
    if any(k in payload for k in menu_keys):
        mapped = build_workflow_payload(payload)
        preprocess_pipelines = mapped.get("preprocess_pipelines") or preprocess_pipelines
        feature_engineering_pipelines = mapped.get("feature_engineering_pipelines") or feature_engineering_pipelines
        model_names = mapped.get("model_names") or model_names
        validation_config = mapped.get("validation_config") or validation_config
        score_variants_raw = mapped.get("score_variants") or score_variants_raw
        column_config = mapped.get("column_config") or column_config
        if mapped.get("target_col"):
            target_col = mapped["target_col"]
        resampling_method = mapped.get("resampling_method") or resampling_method
        resampling_config = mapped.get("resampling_config") or resampling_config
        tuning_method = mapped.get("tuning_method") or tuning_method
        tuning_cv = mapped.get("tuning_cv") or tuning_cv
        tuning_n_iter = mapped.get("tuning_n_iter") or tuning_n_iter
        tuning_scoring = mapped.get("tuning_scoring") or tuning_scoring
        compute_ci = mapped.get("compute_ci", compute_ci)
        ci_n_bootstrap = mapped.get("ci_n_bootstrap", ci_n_bootstrap)

    if isinstance(column_config, dict):
        column_config = [column_config]
    if not isinstance(column_config, list):
        column_config = []

    if isinstance(model_names, list):
        normalised = []
        for item in model_names:
            if isinstance(item, str):
                normalised.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("model") or item.get("type")
                if name:
                    normalised.append(name)
        model_names = normalised
    else:
        model_names = [model_names] if model_names else []

    if not preprocess_pipelines:
        preprocess_pipelines = _parse_json_field(payload.get("preprocessing", []))
    if isinstance(preprocess_pipelines, dict):
        preprocess_pipelines = [preprocess_pipelines]
    if not isinstance(preprocess_pipelines, list):
        preprocess_pipelines = []
    elif preprocess_pipelines and isinstance(preprocess_pipelines[0], dict):
        preprocess_pipelines = [preprocess_pipelines]

    if not feature_engineering_pipelines:
        feature_engineering_pipelines = _parse_json_field(payload.get("featureEngineering", []))
    if isinstance(feature_engineering_pipelines, dict):
        feature_engineering_pipelines = [feature_engineering_pipelines]
    if not isinstance(feature_engineering_pipelines, list):
        feature_engineering_pipelines = []
    elif feature_engineering_pipelines and isinstance(feature_engineering_pipelines[0], dict):
        feature_engineering_pipelines = [feature_engineering_pipelines]

    if not score_variants_raw:
        score_variants_raw = _parse_json_field(payload.get("metrics", []))
    if isinstance(score_variants_raw, dict):
        score_variants_raw = [score_variants_raw]
    if not isinstance(score_variants_raw, list):
        score_variants_raw = []

    if uploaded and uploaded.filename:
        if not _is_allowed_data_file(uploaded.filename):
            raise ValueError("Unsupported file format. Accepted: .csv, .xlsx, .xls")
        data_path = str(_save_uploaded_file(uploaded, Path("uploads/workflow")))

    kwargs: Dict[str, Any] = dict(
        target_col=target_col,
        preprocess_pipelines=preprocess_pipelines,
        feature_engineering_pipelines=feature_engineering_pipelines,
        model_names=model_names,
        score_variants=score_variants_raw,
        validation_config=validation_config,
        column_config=column_config,
        resampling_method=resampling_method,
        resampling_config=resampling_config if isinstance(resampling_config, dict) else {},
        tuning_method=tuning_method,
        tuning_cv=tuning_cv,
        tuning_n_iter=tuning_n_iter,
        tuning_scoring=tuning_scoring,
        compute_ci=compute_ci,
        ci_n_bootstrap=ci_n_bootstrap,
        train_size=train_size,
        random_state=random_state,
    )
    return data_path, kwargs


@model_bp.post("/workflow/execute")
def execute_workflow():
    payload = _load_request_payload()
    uploaded = request.files.get("file")

    # ── Base params from payload ────────────────────────────────────────────
    data_path = payload.get("data_path")
    target_col = payload.get("target_col") or payload.get("targetCol") or payload.get("target") or "是否跌倒"

    preprocess_pipelines = _parse_json_field(payload.get("preprocess_pipelines", []))
    feature_engineering_pipelines = _parse_json_field(payload.get("feature_engineering_pipelines", []))
    model_names = payload.get("model_names") or payload.get("models") or []
    score_variants_raw = _parse_json_field(payload.get("score_variants", []))
    validation_config = _parse_json_field(payload.get("validation_config") or payload.get("validation") or {})
    column_config = _parse_json_field(payload.get("column_config") or payload.get("columnConfig") or [])

    # ── New params ──────────────────────────────────────────────────────────
    resampling_method = str(payload.get("resampling_method", "none"))
    resampling_config = _parse_json_field(payload.get("resampling_config") or {})
    tuning_method = str(payload.get("tuning_method", "none"))
    tuning_cv = int(payload.get("tuning_cv", 3))
    tuning_n_iter = int(payload.get("tuning_n_iter", 20))
    tuning_scoring = str(payload.get("tuning_scoring", "roc_auc"))
    compute_ci = bool(payload.get("compute_ci", False))
    ci_n_bootstrap = int(payload.get("ci_n_bootstrap", 1000))
    train_size = float(payload.get("train_size", 0.7))
    random_state = int(payload.get("random_state", 42))

    # ── If payload uses "menu" format (models/preprocessing/...), remap it ──
    menu_keys = {"preprocessing", "featureEngineering", "feature_engineering", "models", "validation", "metrics"}
    if any(k in payload for k in menu_keys):
        mapped = build_workflow_payload(payload)
        preprocess_pipelines = mapped.get("preprocess_pipelines") or preprocess_pipelines
        feature_engineering_pipelines = mapped.get("feature_engineering_pipelines") or feature_engineering_pipelines
        model_names = mapped.get("model_names") or model_names
        validation_config = mapped.get("validation_config") or validation_config
        score_variants_raw = mapped.get("score_variants") or score_variants_raw
        column_config = mapped.get("column_config") or column_config
        if mapped.get("target_col"):
            target_col = mapped["target_col"]
        # Prefer mapped values but fall back to direct payload values
        resampling_method = mapped.get("resampling_method") or resampling_method
        resampling_config = mapped.get("resampling_config") or resampling_config
        tuning_method = mapped.get("tuning_method") or tuning_method
        tuning_cv = mapped.get("tuning_cv") or tuning_cv
        tuning_n_iter = mapped.get("tuning_n_iter") or tuning_n_iter
        tuning_scoring = mapped.get("tuning_scoring") or tuning_scoring
        compute_ci = mapped.get("compute_ci", compute_ci)
        ci_n_bootstrap = mapped.get("ci_n_bootstrap", ci_n_bootstrap)

    # ── Normalise column_config ─────────────────────────────────────────────
    if isinstance(column_config, dict):
        column_config = [column_config]
    if not isinstance(column_config, list):
        column_config = []

    # ── Normalise model_names ───────────────────────────────────────────────
    if isinstance(model_names, list):
        normalised = []
        for item in model_names:
            if isinstance(item, str):
                normalised.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("model") or item.get("type")
                if name:
                    normalised.append(name)
        model_names = normalised
    else:
        model_names = [model_names] if model_names else []

    # ── Normalise preprocess_pipelines ─────────────────────────────────────
    if not preprocess_pipelines:
        preprocess_pipelines = _parse_json_field(payload.get("preprocessing", []))
    if isinstance(preprocess_pipelines, dict):
        preprocess_pipelines = [preprocess_pipelines]
    if not isinstance(preprocess_pipelines, list):
        preprocess_pipelines = []
    elif preprocess_pipelines and isinstance(preprocess_pipelines[0], dict):
        preprocess_pipelines = [preprocess_pipelines]

    # ── Normalise feature_engineering_pipelines ─────────────────────────────
    if not feature_engineering_pipelines:
        feature_engineering_pipelines = _parse_json_field(payload.get("featureEngineering", []))
    if isinstance(feature_engineering_pipelines, dict):
        feature_engineering_pipelines = [feature_engineering_pipelines]
    if not isinstance(feature_engineering_pipelines, list):
        feature_engineering_pipelines = []
    elif feature_engineering_pipelines and isinstance(feature_engineering_pipelines[0], dict):
        feature_engineering_pipelines = [feature_engineering_pipelines]

    # ── Normalise score_variants ────────────────────────────────────────────
    if not score_variants_raw:
        score_variants_raw = _parse_json_field(payload.get("metrics", []))
    if isinstance(score_variants_raw, dict):
        score_variants_raw = [score_variants_raw]
    if not isinstance(score_variants_raw, list):
        score_variants_raw = []

    # ── Save uploaded data file ─────────────────────────────────────────────
    if uploaded and uploaded.filename:
        if not _is_allowed_data_file(uploaded.filename):
            return jsonify({
                "error": "Unsupported file format. Accepted: .csv, .xlsx, .xls"
            }), 400
        data_path = str(_save_uploaded_file(uploaded, Path("uploads/workflow")))

    if not data_path:
        return jsonify({"error": "data_path or file upload is required."}), 400

    try:
        result = WorkflowService.execute_workflow(
            data_path=data_path,
            target_col=target_col,
            preprocess_pipelines=preprocess_pipelines,
            feature_engineering_pipelines=feature_engineering_pipelines,
            model_names=model_names,
            score_variants=score_variants_raw,
            validation_config=validation_config,
            column_config=column_config,
            resampling_method=resampling_method,
            resampling_config=resampling_config if isinstance(resampling_config, dict) else {},
            tuning_method=tuning_method,
            tuning_cv=tuning_cv,
            tuning_n_iter=tuning_n_iter,
            tuning_scoring=tuning_scoring,
            compute_ci=compute_ci,
            ci_n_bootstrap=ci_n_bootstrap,
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


@model_bp.post("/workflow/jobs")
def create_workflow_job():
    """背景執行 workflow：立即回傳 job_id，模型訓練在獨立 thread 跑，不綁定這條 HTTP 連線。"""
    try:
        data_path, kwargs = _parse_execute_params()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not data_path:
        return jsonify({"error": "data_path or file upload is required."}), 400

    job_id = start_job(data_path=data_path, **kwargs)
    job = get_job(job_id)
    return jsonify({"job_id": job_id, "total_models": job.total_models if job else 0})


@model_bp.get("/workflow/jobs/<job_id>")
def get_workflow_job(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job.status,
        "total_models": job.total_models,
        "completed_models": [c["model_name"] for c in job.completed],
        "result": job.result if job.status == "done" else None,
        "error": job.error,
    })
