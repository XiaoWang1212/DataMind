"""RAG API Routes - 論文引用生成 API

提供論文上傳、搜尋、引用生成等功能
"""

import logging
import os
from pathlib import Path

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

rag_bp = Blueprint("rag", __name__)

# 上傳目錄
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "rag"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(file_path: Path) -> str:
    """從文件中提取文本"""
    suffix = file_path.suffix.lower()

    if suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8")

    if suffix == ".pdf":
        try:
            # 嘗試使用 PyMuPDF (fitz)
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
            except ImportError:
                raise ImportError(
                    "PDF extraction requires PyMuPDF or pdfplumber. "
                    "Install with: pip install pymupdf or pip install pdfplumber"
                )

    raise ValueError(f"Unsupported file format: {suffix}")


@rag_bp.route("/upload", methods=["POST"])
def upload_paper():
    """上傳論文

    支持 multipart/form-data 上傳文件或 JSON body 提供文本

    Form data:
        - file: 論文文件 (txt, md, pdf)
        - title: 論文標題 (可選，預設使用檔名)
        - author: 作者 (可選)
        - year: 年份 (可選)

    JSON body:
        - title: 論文標題
        - content: 論文內容
        - author: 作者 (可選)
        - year: 年份 (可選)
    """
    from services.rag.paper_rag import get_paper_rag_service

    service = get_paper_rag_service()

    # 處理文件上傳
    if "file" in request.files:
        file = request.files["file"]

        if file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # 檢查副檔名
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

        # 儲存文件
        safe_name = secure_filename(original_name) or f"paper{ext}"
        file_path = UPLOAD_DIR / safe_name
        file.save(file_path)

        try:
            content = extract_text_from_file(file_path)
            title = request.form.get("title", original_name)
            author = request.form.get("author")
            year = request.form.get("year")

            metadata = {}
            if author:
                metadata["author"] = author
            if year:
                metadata["year"] = year

            result = service.add_paper(
                title=title,
                content=content,
                metadata=metadata,
            )

            return jsonify({"success": True, "result": result})

        except Exception as e:
            logger.exception("Failed to process paper")
            return jsonify({"success": False, "error": str(e)}), 500

        finally:
            # 清理上傳的文件
            if file_path.exists():
                file_path.unlink()

    # 處理 JSON body
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No file or JSON data provided"}), 400

    title = data.get("title")
    content = data.get("content")

    if not title or not content:
        return (
            jsonify({"success": False, "error": "title and content are required"}),
            400,
        )

    metadata = {}
    if data.get("author"):
        metadata["author"] = data["author"]
    if data.get("year"):
        metadata["year"] = data["year"]

    try:
        result = service.add_paper(
            title=title,
            content=content,
            metadata=metadata,
        )
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Failed to add paper")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/search", methods=["POST"])
def search_papers():
    """搜尋論文

    JSON body:
        - query: 搜尋查詢 (必填)
        - top_k: 返回結果數量 (預設 5)
        - use_rerank: 是否使用 reranker (預設 true)
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"success": False, "error": "query is required"}), 400

    service = get_paper_rag_service()

    try:
        results = service.search(
            query=data["query"],
            top_k=data.get("top_k", 5),
            use_rerank=data.get("use_rerank", True),
        )

        return jsonify(
            {
                "success": True,
                "results": [
                    {
                        "chunk_id": r.chunk.chunk_id,
                        "paper_id": r.chunk.paper_id,
                        "title": r.chunk.title,
                        "content": r.chunk.content,
                        "score": r.score,
                        "rerank_score": r.rerank_score,
                    }
                    for r in results
                ],
            }
        )

    except Exception as e:
        logger.exception("Search failed")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/cite", methods=["POST"])
def generate_citation():
    """生成論文引用

    JSON body:
        - query: 搜尋查詢 (必填)
        - top_k: 引用論文數量 (預設 3)
        - style: 引用格式 (apa, mla, chicago，預設 apa)
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"success": False, "error": "query is required"}), 400

    service = get_paper_rag_service()

    try:
        result = service.generate_citation(
            query=data["query"],
            top_k=data.get("top_k", 3),
            citation_style=data.get("style", "apa"),
        )

        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Citation generation failed")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/status", methods=["GET"])
def get_status():
    """獲取 RAG 服務狀態"""
    from services.rag.paper_rag import get_paper_rag_service

    service = get_paper_rag_service()

    try:
        status = service.get_status()
        return jsonify({"success": True, "status": status})

    except Exception as e:
        logger.exception("Failed to get status")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/clear", methods=["POST"])
def clear_index():
    """清空所有索引"""
    from services.rag.paper_rag import get_paper_rag_service

    service = get_paper_rag_service()

    try:
        result = service.clear()
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Failed to clear index")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/paper/<paper_id>", methods=["DELETE"])
def delete_paper(paper_id: str):
    """刪除指定論文"""
    from services.rag.paper_rag import get_paper_rag_service

    service = get_paper_rag_service()

    try:
        result = service.delete_paper(paper_id)
        if not result.get("success"):
            return jsonify(result), 404
        return jsonify(result)

    except Exception as e:
        logger.exception("Failed to delete paper")
        return jsonify({"success": False, "error": str(e)}), 500
