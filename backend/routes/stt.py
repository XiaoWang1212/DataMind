import os
import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request

from services.whisper_service import WhisperSTTService

stt_bp = Blueprint("stt", __name__)

ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "webm", "ogg", "mp4", "mpeg", "mpga"}


def _is_allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@stt_bp.post("/transcribe")
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "Missing file field: audio"}), 400

    audio_file = request.files["audio"]
    if not audio_file.filename:
        return jsonify({"error": "Empty filename"}), 400

    if not _is_allowed_file(audio_file.filename):
        return jsonify({"error": "Unsupported audio format"}), 400

    language = request.form.get("language")
    prompt = request.form.get("prompt")

    temperature_raw = request.form.get("temperature")
    temperature = None
    if temperature_raw is not None and temperature_raw != "":
        try:
            temperature = float(temperature_raw)
        except ValueError:
            return jsonify({"error": "temperature must be a number"}), 400

    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    Path(upload_dir).mkdir(parents=True, exist_ok=True)

    ext = audio_file.filename.rsplit(".", 1)[1].lower()
    temp_name = f"{uuid.uuid4().hex}.{ext}"
    temp_path = Path(upload_dir) / temp_name

    try:
        audio_file.save(temp_path)

        stt_service = WhisperSTTService()
        result = stt_service.transcribe(
            audio_path=str(temp_path),
            language=language,
            prompt=prompt,
            temperature=temperature,
        )

        return jsonify({"success": True, "result": result.to_dict()})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        return jsonify({"error": f"Transcription failed: {str(exc)}"}), 500
    finally:
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass
