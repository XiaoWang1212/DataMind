from flask import Blueprint, jsonify, request

from services.pycaret_service import PyCaretTrainingService

pycaret_bp = Blueprint("pycaret", __name__)


@pycaret_bp.post("/train")
def train_pycaret_model():
    payload = request.get_json(silent=True) or {}

    data_path = payload.get("data_path")
    if not data_path:
        return jsonify({"error": "data_path is required"}), 400

    target_col = payload.get("target_col", "是否跌倒")
    output_dir = payload.get("output_dir", "artifacts/pycaret")

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
