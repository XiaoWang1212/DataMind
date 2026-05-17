import logging
import os
import re
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.mineru_service import AnalysisInput, MinerUService, truncate_content

logger = logging.getLogger(__name__)

mineru_bp = Blueprint("mineru", __name__)

UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "mineru"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = Path(__file__).parent.parent / "artifacts" / "mineru"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


def parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def split_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return paragraphs


def find_paragraph_by_keywords(
    paragraphs: list[str], keywords: list[str]
) -> str | None:
    lower_keywords = [kw.lower() for kw in keywords]
    for paragraph in paragraphs:
        lower_paragraph = paragraph.lower()
        if any(keyword in lower_paragraph for keyword in lower_keywords):
            return paragraph
    return None


def is_plain_heading_line(line: str, next_line: str | None) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 120:
        return False
    if stripped.endswith("."):
        return False
    if re.search(r"[a-z]", stripped) and not re.search(
        r"\b(MATERIALS|METHODS|RESULTS|DATA ANALYSIS|DISCUSSION|CONCLUSION|TABLES|STUDY|PARTICIPANTS)\b",
        stripped,
        re.IGNORECASE,
    ):
        return False
    if not re.match(r"^[A-Z0-9\s\-/,()%]+$", stripped):
        return False
    if next_line is None:
        return True
    if not next_line.strip():
        return True
    if re.match(r"^[A-Z ]+$", next_line.strip()):
        return True
    return False


def extract_markdown_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    title = ""
    content_lines: list[str] = []
    lines = text.splitlines()

    def flush_section() -> None:
        nonlocal title, content_lines
        if title or content_lines:
            sections.append((title.strip(), "\n".join(content_lines).strip()))
            title = ""
            content_lines = []

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()
        heading = re.match(r"^(#{1,6})\s*(.+)$", stripped)
        next_line = lines[idx + 1] if idx + 1 < len(lines) else None

        if heading:
            flush_section()
            title = heading.group(2).strip()
            idx += 1
            continue

        if next_line and re.match(r"^[-=]{3,}\s*$", next_line.strip()):
            flush_section()
            title = stripped
            idx += 2
            continue

        if is_plain_heading_line(stripped, next_line):
            flush_section()
            title = stripped
            idx += 1
            continue

        content_lines.append(line)
        idx += 1

    flush_section()
    return sections


def extract_heading_block(
    md_content: str,
    start_keywords: list[str],
    stop_keywords: list[str],
) -> str | None:
    start_regex = re.compile(
        r"(?im)^(?:#{1,6}\s*)?(?:"
        + "|".join(re.escape(k) for k in start_keywords)
        + r")\b.*$",
        re.MULTILINE,
    )
    stop_regex = re.compile(
        r"(?im)^(?:#{1,6}\s*)?(?:"
        + "|".join(re.escape(k) for k in stop_keywords)
        + r")\b.*$",
        re.MULTILINE,
    )

    start_match = start_regex.search(md_content)
    if not start_match:
        return None

    after = md_content[start_match.end() :]
    stop_match = stop_regex.search(after)
    end_pos = stop_match.start() if stop_match else len(after)
    return md_content[start_match.start() : start_match.end() + end_pos].strip()


def find_section_by_keywords(
    sections: list[tuple[str, str]], keywords: list[str]
) -> str | None:
    lower_keywords = [kw.lower() for kw in keywords]
    for title, content in sections:
        if title and any(keyword in title.lower() for keyword in lower_keywords):
            return f"{title}\n{content}".strip()
    for title, content in sections:
        block = f"{title}\n{content}".lower()
        if any(keyword in block for keyword in lower_keywords):
            return f"{title}\n{content}".strip()
    return None


def extract_table_block(md_content: str, table_number: int) -> str | None:
    table_label_pattern = re.compile(
        rf"(?is)table\s*{table_number}\b(?:\.[^\n]*)?\s*\n\s*<table>",
    )
    match = table_label_pattern.search(md_content)
    if not match:
        match = re.search(rf"(?i)\btable\s*{table_number}\b", md_content)
        if not match:
            return None

    after = md_content[match.end() :]
    next_table_number = table_number + 1
    stop_pattern = re.compile(
        rf"(?im)^(?:table\s*{next_table_number}\b|table\s*{next_table_number + 1}\b|#\s+|figure\s*\d+\b)",
        re.MULTILINE,
    )
    stop_match = stop_pattern.search(after)
    section = after[: stop_match.start() if stop_match else len(after)]

    last_table_end = section.lower().rfind("</table>")
    if last_table_end != -1:
        section = section[: last_table_end + len("</table>")]

    return md_content[match.start() : match.end() + len(section)].strip()


def extract_auto_training_details(md_content: str) -> dict[str, str]:
    materials_section = extract_heading_block(
        md_content,
        ["materials", "materials and methods", "data collection", "study population"],
        [
            "data analysis",
            "table 1",
            "table 2",
            "table 3",
            "# results",
            "# discussion",
            "# conclusion",
        ],
    )
    data_analysis_section = extract_heading_block(
        md_content,
        ["data analysis", "analysis", "data preprocessing", "pipeline"],
        [
            "table 1",
            "table 2",
            "table 3",
            "# results",
            "# discussion",
            "# conclusion",
        ],
    )

    if not materials_section:
        sections = extract_markdown_sections(md_content)
        materials_section = find_section_by_keywords(
            sections,
            [
                "materials",
                "materials and methods",
                "data sources",
                "participants",
                "subjects",
                "dataset",
                "study population",
                "materials/methods",
                "data collection",
            ],
        )

    if not data_analysis_section:
        sections = extract_markdown_sections(md_content)
        data_analysis_section = find_section_by_keywords(
            sections,
            [
                "data analysis",
                "analysis",
                "preprocessing",
                "data preprocessing",
                "pipeline",
                "workflow",
                "sampling",
                "resample",
                "bootstrap",
                "weka",
                "feature selection",
                "machine learning",
                "classification techniques",
            ],
        )

    table_1 = extract_table_block(md_content, 1)
    table_2 = extract_table_block(md_content, 2)
    table_3 = extract_table_block(md_content, 3)

    return {
        "materials_section": materials_section or "",
        "data_analysis_section": data_analysis_section or "",
        "table_1_variables": table_1 or "",
        "table_2_hyperparameters": table_2 or "",
        "table_3_variable_importance": table_3 or "",
    }


def summarize_md_content(md_content: str) -> dict[str, str | dict[str, str]]:
    paragraphs = split_paragraphs(md_content)
    objective = find_paragraph_by_keywords(
        paragraphs,
        [
            "purpose",
            "objective",
            "aim",
            "study aims",
            "we aimed",
            "the goal",
            "this study",
        ],
    )
    methods = find_paragraph_by_keywords(
        paragraphs,
        [
            "method",
            "data",
            "analysis",
            "conducted",
            "collected",
            "using",
            "approach",
            "study was",
        ],
    )
    main_results = find_paragraph_by_keywords(
        paragraphs,
        [
            "result",
            "find",
            "suggest",
            "show",
            "performance",
            "indicate",
            "was",
            "had",
        ],
    )
    conclusion = find_paragraph_by_keywords(
        list(reversed(paragraphs)),
        [
            "conclusion",
            "in conclusion",
            "therefore",
            "thus",
            "in summary",
            "this study",
            "overall",
            "future",
        ],
    )

    if not objective and paragraphs:
        objective = paragraphs[0]
    if not methods and len(paragraphs) > 1:
        methods = paragraphs[1]
    if not main_results and len(paragraphs) > 2:
        main_results = paragraphs[2]
    if not conclusion and paragraphs:
        conclusion = paragraphs[-1]

    training_section = extract_auto_training_details(md_content)

    summary = {
        "research_objective": objective or "",
        "methods": methods or "",
        "main_results": main_results or "",
        "conclusion": conclusion or "",
    }
    summary.update(training_section)
    return summary


def add_structured_summary_to_response(response: dict) -> None:
    results = response.get("results")
    if not isinstance(results, dict):
        return

    for pdf_name, data in results.items():
        if not isinstance(data, dict):
            continue
        md_content = data.get("md_content")
        if isinstance(md_content, str) and md_content.strip():
            data["structured_summary"] = summarize_md_content(md_content)


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md"}:
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


@mineru_bp.route("/ai-analyze-simple", methods=["POST"])
def ai_analyze_simple():
    """MinerU 簡化入口：只傳論文檔案即可返回分析結果"""
    try:
        service = MinerUService()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

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
        with open(file_path, "rb") as handle:
            file_bytes = handle.read()
        title = os.path.splitext(original_name)[0] or "Untitled Paper"
    finally:
        if file_path.exists():
            file_path.unlink()

    save_output = parse_bool(request.form.get("save_output"), default=False)
    output_filename = request.form.get("output_filename")
    structured_summary = parse_bool(
        request.form.get("structured_summary"), default=True
    )

    try:
        analysis_input = AnalysisInput(
            title=title,
            file_bytes=file_bytes,
            file_name=safe_name,
        )
        result = service.analyze(analysis_input)
        response_data = result.get("response") if isinstance(result, dict) else result

        if structured_summary and isinstance(response_data, dict):
            add_structured_summary_to_response(response_data)

        if save_output:
            default_name = (
                f"mineru_simple_{title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            safe_output_name = secure_filename(output_filename or default_name)
            if not safe_output_name.endswith(".json"):
                safe_output_name = f"{safe_output_name}.json"

            output_path = OUTPUT_DIR / safe_output_name
            payload = {
                "success": True,
                "saved_at": datetime.now().isoformat(),
                "title": title,
                "result": result,
            }
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            return jsonify(
                {
                    "success": True,
                    "result": response_data,
                    "saved_file": {
                        "filename": safe_output_name,
                        "path": str(output_path),
                    },
                }
            )

        return jsonify({"success": True, "result": response_data})
    except Exception as e:
        logger.exception("MinerU simple analysis failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mineru_bp.route("/ai-analyze", methods=["POST"])
def ai_analyze_paper():
    """MinerU 論文分析入口

    支持 file 上傳或 JSON body：
    - file: 論文文件 (txt, md, pdf)
    - title: 論文標題
    - focus: 分析重點
    - language: 輸出語言
    - mode: summary 或 extract
    - save_output: 是否儲存結果
    - output_filename: 儲存檔名
    """
    try:
        service = MinerUService()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

    title = ""
    content = ""
    focus = None
    language = "zh-TW"
    mode = "summary"
    save_output = False
    output_filename = None
    file_bytes = None
    file_name = None

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
            with open(file_path, "rb") as handle:
                file_bytes = handle.read()
            file_name = safe_name
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

    if file_bytes is None and not content.strip():
        return jsonify({"success": False, "error": "content is required"}), 400

    if mode not in {"summary", "extract"}:
        return (
            jsonify({"success": False, "error": "mode must be 'summary' or 'extract'"}),
            400,
        )

    structured_summary = False
    if "file" in request.files:
        structured_summary = parse_bool(
            request.form.get("structured_summary"), default=False
        )
    else:
        structured_summary = parse_bool(data.get("structured_summary"), default=False)

    try:
        if file_bytes is not None:
            analysis_input = AnalysisInput(
                title=title,
                file_bytes=file_bytes,
                file_name=file_name,
                focus=focus,
                language=language,
                mode=mode,
            )
        else:
            analysis_input = AnalysisInput(
                title=title,
                content=truncate_content(content),
                focus=focus,
                language=language,
                mode=mode,
            )
        result = service.analyze(analysis_input)

        if structured_summary and isinstance(result, dict):
            response_data = result.get("response")
            if isinstance(response_data, dict):
                add_structured_summary_to_response(response_data)

        if save_output:
            default_name = (
                f"mineru_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
        logger.exception("MinerU analysis failed")
        return jsonify({"success": False, "error": str(e)}), 500
