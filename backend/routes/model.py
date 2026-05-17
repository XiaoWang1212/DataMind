import json
from pathlib import Path
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request
from services.model.registry import extract_model_components

model_bp = Blueprint("model", __name__)

ALLOWED_DATA_EXTENSIONS = {"json"}


def _is_allowed_json_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_DATA_EXTENSIONS


@model_bp.post("/extract-components")
def extract_components():
    payload = None
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
