import os
import uuid
from pathlib import Path
from uuid import uuid4
from werkzeug.utils import secure_filename

from flask import Blueprint, jsonify, request
from services.pycaret_service import PyCaretTrainingService

pycaret_bp = Blueprint("pycaret", __name__)

ALLOWED_DATA_EXTENSIONS = {"csv"}


def _is_allowed_data_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_DATA_EXTENSIONS


@pycaret_bp.post("/train")
def train_pycaret_model():
    payload = request.get_json(silent=True) or {}
    target_col = request.form.get("target_col") or payload.get("target_col", "是否跌倒")
    output_dir = request.form.get("output_dir") or payload.get("output_dir", "artifacts/pycaret")

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Missing file field: file"}), 400

    raw_name = uploaded.filename
    if Path(raw_name).suffix.lower() != ".csv":
        return jsonify({"error": "Unsupported file format. Only .csv is allowed."}), 400

    safe_name = secure_filename(raw_name)
    if not safe_name.lower().endswith(".csv"):
        safe_name = f"{uuid4().hex}.csv"

    upload_dir = Path(os.getenv("PYCARET_UPLOAD_DIR", "uploads/pycaret"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    save_path = upload_dir / safe_name
    uploaded.save(str(save_path))
    data_path = str(save_path)
    temp_data_path = None

    if not data_path:
        return jsonify({"error": "file (form-data) or data_path (json) is required"}), 400

    try:
        service = PyCaretTrainingService()
        result = service.train_fall_model(
            data_path=data_path,
            target_col=target_col,
            output_dir=output_dir,
        )
        return jsonify({"success": True, "result": result})
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"PyCaret training failed: {str(exc)}"}), 500
    finally:
        if temp_data_path is not None:
            try:
                if temp_data_path.exists():
                    temp_data_path.unlink()
            except OSError:
                pass
