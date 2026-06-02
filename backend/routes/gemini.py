import logging
import os
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.gemini_service import AnalysisInput, GeminiService, truncate_content

logger = logging.getLogger(__name__)

gemini_bp = Blueprint("gemini", __name__)

UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "gemini"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(__file__).parent.parent / "artifacts" / "gemini"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


def parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        try:
            import fitz

            doc = fitz.open(str(file_path))
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except ImportError:
            logger.warning("PyMuPDF not installed, trying pdfplumber")
            try:
                import pdfplumber

                with pdfplumber.open(file_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            except ImportError as e:
                raise ImportError(
                    "PDF extraction requires PyMuPDF or pdfplumber. "
                    "Install with: pip install pymupdf or pip install pdfplumber"
                ) from e

    raise ValueError(f"Unsupported file format: {suffix}")


@gemini_bp.route("/ai-analyze", methods=["POST"])
def ai_analyze_paper():
    """純 AI 論文技術解讀（使用 Gemini，不使用 RAG）

    支援 mode:
    - summary: 一般技術摘要（預設）
    - extract: 結構化抽取「變數定義 + 模型使用」
    """
    try:
        service = GeminiService()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    title = ""
    content = ""
    focus = None
    language = "zh-TW"
    mode = "summary"
    save_output = False
    output_filename = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        original_name = file.filename
        ext = os.path.splitext(original_name)[1].lower() if original_name else ""
        if ext and ext[1:] not in ALLOWED_EXTENSIONS:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Unsupported file format. Allowed: {ALLOWED_EXTENSIONS}",
                    }
                ),
                400,
            )

        safe_name = secure_filename(original_name) or f"paper{ext}"
        file_path = UPLOAD_DIR / safe_name
        file.save(file_path)

        try:
            content = extract_text_from_file(file_path)
            title = request.form.get("title", original_name)
            focus = request.form.get("focus")
            language = request.form.get("language", "zh-TW")
            mode = request.form.get("mode", "summary")
            save_output = parse_bool(request.form.get("save_output"), default=False)
            output_filename = request.form.get("output_filename")
        finally:
            if file_path.exists():
                file_path.unlink()
    else:
        data = request.get_json()
        if not data:
            return (
                jsonify({"success": False, "error": "No file or JSON data provided"}),
                400,
            )

        title = data.get("title", "Untitled Paper")
        content = data.get("content", "")
        focus = data.get("focus")
        language = data.get("language", "zh-TW")
        mode = data.get("mode", "summary")
        save_output = parse_bool(data.get("save_output"), default=False)
        output_filename = data.get("output_filename")

    if not content.strip():
        return jsonify({"success": False, "error": "content is required"}), 400

    if mode not in {"summary", "extract"}:
        return (
            jsonify({"success": False, "error": "mode must be 'summary' or 'extract'"}),
            400,
        )

    try:
        analysis_input = AnalysisInput(
            title=title,
            content=truncate_content(content),
            focus=focus,
            language=language,
            mode=mode,
        )
        result = service.analyze(analysis_input)

        if save_output:
            default_name = (
                f"gemini_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            safe_output_name = secure_filename(output_filename or default_name)
            if not safe_output_name.endswith(".json"):
                safe_output_name = f"{safe_output_name}.json"

            output_path = OUTPUT_DIR / safe_output_name
            payload = {
                "success": True,
                "saved_at": datetime.now().isoformat(),
                "title": title,
                "mode": mode,
                "result": result,
            }
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return jsonify(
                {
                    "success": True,
                    "result": result,
                    "saved_file": {
                        "filename": safe_output_name,
                        "path": str(output_path),
                    },
                }
            )

        return jsonify({"success": True, "result": result})
    except Exception as e:
        logger.exception("Gemini analysis failed")
        return jsonify({"success": False, "error": str(e)}), 500
