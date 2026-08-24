import logging
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, stream_with_context
from flask_login import login_required
from werkzeug.utils import secure_filename

from services.gemini_service import AnalysisInput, GeminiService, truncate_content

logger = logging.getLogger(__name__)

gemini_bp = Blueprint("gemini", __name__)

OUTPUT_DIR = Path(__file__).parent.parent / "artifacts" / "gemini"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}
MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB — Gemini inline_data limit


def _parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _save_result(title: str, result: dict, filename: str | None) -> Path:
    default_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    safe_name = secure_filename(filename or default_name)
    if not safe_name.endswith(".json"):
        safe_name = f"{safe_name}.json"
    output_path = OUTPUT_DIR / safe_name
    payload = {
        "saved_at": datetime.now().isoformat(),
        "title": title,
        "result": result,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


@gemini_bp.post("/ai-analyze")
@login_required
def ai_analyze_paper():
    """論文 → Workflow JSON 生成

    輸入方式（擇一）：
    - multipart/form-data，欄位 `file`（.pdf / .txt / .md）
    - application/json，欄位 `content`（純文字）

    選用參數：
    - `title`：論文標題（輔助 prompt）
    - `focus`：特別關注的面向（如「特徵選擇」「類別不平衡」）
    - `save_output`：true 時把結果存到 artifacts/gemini/
    - `output_filename`：儲存檔名（預設自動生成）

    回傳：
    - `workflow_json`：可直接上傳到前端 workflow 的 JSON
    - `raw`：若 JSON 解析失敗時的原始輸出（方便除錯）
    """
    try:
        service = GeminiService()
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    title = ""
    focus = None
    save_output = False
    output_filename = None
    result: dict | None = None

    # ── PDF or text file upload ──────────────────────────────────────────────
    if "file" in request.files:
        file = request.files["file"]
        if not file.filename:
            return jsonify({"success": False, "error": "No file selected"}), 400

        ext = Path(file.filename).suffix.lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                "success": False,
                "error": f"Unsupported format. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
            }), 400

        title = request.form.get("title", file.filename)
        focus = request.form.get("focus") or None
        save_output = _parse_bool(request.form.get("save_output"))
        output_filename = request.form.get("output_filename") or None

        pdf_bytes = file.read()

        if ext == "pdf":
            if len(pdf_bytes) > MAX_PDF_BYTES:
                return jsonify({
                    "success": False,
                    "error": f"PDF exceeds {MAX_PDF_BYTES // 1024 // 1024} MB limit for inline processing.",
                }), 413

            try:
                result = service.analyze_pdf(pdf_bytes, title=title, focus=focus)
            except Exception as exc:
                logger.exception("analyze_pdf failed")
                return jsonify({"success": False, "error": str(exc)}), 500
        else:
            # txt / md — decode and pass as text
            try:
                content = pdf_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = pdf_bytes.decode("latin-1")

            if not content.strip():
                return jsonify({"success": False, "error": "File is empty"}), 400

            try:
                result = service.analyze(AnalysisInput(
                    title=title,
                    content=truncate_content(content),
                    focus=focus,
                ))
            except Exception as exc:
                logger.exception("analyze failed")
                return jsonify({"success": False, "error": str(exc)}), 500

    # ── JSON body (plain text content) ──────────────────────────────────────
    else:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "Provide a file upload or JSON body"}), 400

        title = data.get("title", "Untitled Paper")
        content = data.get("content", "")
        focus = data.get("focus") or None
        save_output = _parse_bool(data.get("save_output"))
        output_filename = data.get("output_filename") or None

        if not content.strip():
            return jsonify({"success": False, "error": "content is required"}), 400

        try:
            result = service.analyze(AnalysisInput(
                title=title,
                content=truncate_content(content),
                focus=focus,
            ))
        except Exception as exc:
            logger.exception("analyze failed")
            return jsonify({"success": False, "error": str(exc)}), 500

    # ── Save output if requested ─────────────────────────────────────────────
    if save_output and result:
        output_path = _save_result(title, result, output_filename)
        return jsonify({
            "success": True,
            "result": result,
            "saved_file": str(output_path),
        })

    return jsonify({"success": True, "result": result})


@gemini_bp.post("/ai-analyze/stream")
@login_required
def ai_analyze_paper_stream():
    """論文 PDF → 即時思考串流 + 最終 Workflow JSON（SSE）

    僅支援 multipart/form-data PDF 上傳：
    - `file`：PDF 檔案（必填）
    - `title`：論文標題（選填）

    回傳 text/event-stream，事件：
    - event: thought  data: {"text": "..."}
    - event: result   data: {"data": {...}}
    - event: error    data: {"message": "..."}
    """
    try:
        service = GeminiService()
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "PDF file is required"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "No file selected"}), 400

    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext != "pdf":
        return jsonify({"success": False, "error": "Only PDF is supported for streaming"}), 400

    title = request.form.get("title", file.filename)
    pdf_bytes = file.read()

    if len(pdf_bytes) > MAX_PDF_BYTES:
        return jsonify({
            "success": False,
            "error": f"PDF exceeds {MAX_PDF_BYTES // 1024 // 1024} MB limit for inline processing.",
        }), 413

    def _sse_events():
        for event in service.analyze_pdf_stream(pdf_bytes, title=title):
            event_type = event["type"]
            payload = {k: v for k, v in event.items() if k != "type"}
            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

    return Response(stream_with_context(_sse_events()), mimetype="text/event-stream")
