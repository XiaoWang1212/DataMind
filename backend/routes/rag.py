"""RAG API Routes - 論文引用生成 API

提供論文上傳、搜尋、引用生成等功能
"""

import logging
import os
from pathlib import Path
from urllib.error import HTTPError, URLError

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from models.project import Project

logger = logging.getLogger(__name__)

rag_bp = Blueprint("rag", __name__)

_ARXIV_TIMEOUT_ERROR_MESSAGE = "查詢 arXiv 逾時，請稍後再試"

# 上傳目錄
UPLOAD_DIR = Path(__file__).parent.parent / "uploads" / "rag"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}


def _get_owned_project(project_id: int) -> Project | None:
    project = Project.query.get(project_id)
    if not project or project.user_id != current_user.id:
        return None
    return project


def _parse_project_id(raw) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


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
@login_required
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

    # 處理文件上傳
    if "file" in request.files:
        project_id = _parse_project_id(request.form.get("project_id"))
        if project_id is None:
            return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
        if _get_owned_project(project_id) is None:
            return jsonify({"success": False, "error": "找不到專案"}), 404

        service = get_paper_rag_service()

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
                project_id,
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
        return (
            jsonify({"success": False, "error": "No file or JSON data provided"}),
            400,
        )

    project_id = _parse_project_id(data.get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

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

    service = get_paper_rag_service()

    try:
        result = service.add_paper(
            project_id,
            title=title,
            content=content,
            metadata=metadata,
        )
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Failed to add paper")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/search", methods=["POST"])
@login_required
def search_papers():
    """搜尋論文

    JSON body:
        - query: 搜尋查詢 (必填)
        - top_k: 返回結果數量 (預設 5)
        - use_rerank: 是否使用 reranker (預設 true)
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    project_id = _parse_project_id((data or {}).get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    if not data or not data.get("query"):
        return jsonify({"success": False, "error": "query is required"}), 400

    service = get_paper_rag_service()

    try:
        results = service.search(
            project_id,
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
@login_required
def generate_citation():
    """生成論文引用

    JSON body:
        - query: 搜尋查詢 (必填)
        - top_k: 引用論文數量 (預設 3)
        - style: 引用格式 (apa, mla, chicago，預設 apa)
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    project_id = _parse_project_id((data or {}).get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    if not data or not data.get("query"):
        return jsonify({"success": False, "error": "query is required"}), 400

    service = get_paper_rag_service()

    try:
        result = service.generate_citation(
            project_id,
            query=data["query"],
            top_k=data.get("top_k", 3),
            citation_style=data.get("style", "apa"),
        )

        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Citation generation failed")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/status", methods=["GET"])
@login_required
def get_status():
    """獲取 RAG 服務狀態"""
    from services.rag.paper_rag import get_paper_rag_service

    project_id = _parse_project_id(request.args.get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    service = get_paper_rag_service()

    try:
        status = service.get_status(project_id)
        return jsonify({"success": True, "status": status})

    except Exception as e:
        logger.exception("Failed to get status")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/clear", methods=["POST"])
@login_required
def clear_index():
    """清空所有索引"""
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json(silent=True)
    project_id = _parse_project_id((data or {}).get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    service = get_paper_rag_service()

    try:
        result = service.clear(project_id)
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Failed to clear index")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/paper/<paper_id>", methods=["DELETE"])
@login_required
def delete_paper(paper_id: str):
    """刪除指定論文"""
    from services.rag.paper_rag import get_paper_rag_service

    project_id = _parse_project_id(request.args.get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    service = get_paper_rag_service()

    try:
        result = service.delete_paper(project_id, paper_id)
        if not result.get("success"):
            return jsonify(result), 404
        return jsonify(result)

    except Exception as e:
        logger.exception("Failed to delete paper")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/generate-paper", methods=["POST"])
@login_required
def generate_paper():
    """利用 DataMind 資料探勘結果 + 參考論文庫，生成學術論文

    JSON body:
        - topic          : 研究主題（必填）
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - structure      : 論文章節列表（選填，預設六章）
        - language       : 語言（選填，預設 zh-TW）

    回傳：
        - paper_markdown  : 完整論文（Markdown 格式）
        - citation_map    : 引用地圖（逐段記錄引用來源，供前端使用）
        - references      : 全域引用清單
        - sections_generated : 實際生成的章節
        - usage           : Gemini token 用量
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    project_id = _parse_project_id(data.get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"success": False, "error": "topic 為必填欄位"}), 400

    mining_results = data.get("mining_results")
    if mining_results is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    structure = data.get("structure")
    language = data.get("language", "zh-TW")

    service = get_paper_rag_service()

    try:
        result = service.generate_paper(
            project_id,
            topic=topic,
            mining_results=mining_results,
            structure=structure,
            language=language,
        )
        return jsonify({"success": True, "result": result})

    except Exception as e:
        logger.exception("Paper generation failed")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/arxiv/search", methods=["POST"])
@login_required
def arxiv_search():
    """分類 DataMind 探勘結果並查詢 arXiv 候選論文（不寫入向量庫）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - user_title     : 使用者想要的論文標題（選填，留空則主題完全由 AI 推論）

    回傳：
        - topic       : 使用者標題（若有填）或 AI 產生的研究主題
        - arxiv_query : 用於查詢 arXiv 的關鍵字字串
        - candidates  : 候選論文清單（arxiv_id/title/authors/year/abstract/pdf_url）
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    user_title = str(data.get("user_title") or "").strip() or None
    service = get_paper_rag_service()

    try:
        result = service.search_arxiv_candidates(data["mining_results"], user_title)
        return jsonify({"success": True, **result})

    except HTTPError as e:
        logger.exception("arXiv 查詢失敗")
        return jsonify({"success": False, "error": str(e)}), 500
    except (TimeoutError, URLError):
        logger.exception("arXiv 查詢逾時")
        return jsonify({"success": False, "error": _ARXIV_TIMEOUT_ERROR_MESSAGE}), 504
    except Exception as e:
        logger.exception("arXiv 查詢失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/arxiv/generate", methods=["POST"])
@login_required
def arxiv_generate():
    """下載選中的 arXiv 論文、建立索引，並生成論文

    JSON body:
        - topic               : 研究主題（必填）
        - mining_results      : DataMind 探勘結果（必填）
        - selected_candidates : 使用者勾選的候選論文清單（必填，來自 /arxiv/search 的 candidates）

    回傳：與 /generate-paper 相同形狀，外加 ingested/failed 清單
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    project_id = _parse_project_id(data.get("project_id"))
    if project_id is None:
        return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
    if _get_owned_project(project_id) is None:
        return jsonify({"success": False, "error": "找不到專案"}), 404

    topic = data.get("topic", "").strip()
    mining_results = data.get("mining_results")
    selected_candidates = data.get("selected_candidates")

    if not topic:
        return jsonify({"success": False, "error": "topic 為必填欄位"}), 400
    if mining_results is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    if not selected_candidates:
        return jsonify({"success": False, "error": "selected_candidates 為必填欄位，至少需選擇一篇論文"}), 400

    service = get_paper_rag_service()

    try:
        ingest_result = service.ingest_arxiv_selection(project_id, selected_candidates)
        if not ingest_result.get("success"):
            return jsonify(ingest_result), 422

        result = service.generate_paper(project_id, topic=topic, mining_results=mining_results)
        return jsonify({
            "success": True,
            "result": result,
            "ingested": ingest_result["ingested"],
            "failed": ingest_result["failed"],
        })

    except HTTPError as e:
        logger.exception("arXiv 論文生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
    except (TimeoutError, URLError):
        logger.exception("arXiv 論文生成逾時")
        return jsonify({"success": False, "error": _ARXIV_TIMEOUT_ERROR_MESSAGE}), 504
    except Exception as e:
        logger.exception("arXiv 論文生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/insight", methods=["POST"])
@login_required
def generate_insight():
    """根據 DataMind 探勘結果，用 Gemini 生成一段洞察摘要

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - insight : AI 生成的洞察文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_insight(data["mining_results"])
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("洞察生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/tab-insight", methods=["POST"])
@login_required
def generate_tab_insight():
    """針對 workflow 結果裡某個分頁（混淆矩陣/ROC/PR/校準曲線/各類別指標）生成 AI 解讀文字

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - tab             : 'matrix' | 'roc' | 'pr' | 'calibration' | 'perClass'（必填）
        - model_name      : 要解讀哪個模型（必填）
        - split_name      : 要解讀哪個 fold/split（必填）

    回傳：
        - insight : AI 生成的解讀文字
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    tab = data.get("tab")
    model_name = data.get("model_name")
    split_name = data.get("split_name")
    if not tab or not model_name or not split_name:
        return jsonify({"success": False, "error": "tab、model_name、split_name 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        insight = service.generate_tab_insight(data["mining_results"], tab, model_name, split_name)
        return jsonify({"success": True, "insight": insight})

    except Exception as e:
        logger.exception("分頁解讀生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/score-paper", methods=["POST"])
@login_required
def score_paper():
    """對論文全文，依固定的期刊評分準則逐一評分

    JSON body:
        - paper_text : 論文全文純文字（必填）

    回傳：
        - journal_scores  : 各期刊評分結果（journal/journal_full_name/overall_score/overall_comment/criteria/suggestions）
        - failed_journals : 評分失敗的期刊名稱清單
        - usage           : Gemini token 用量
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    paper_text = (data or {}).get("paper_text", "").strip()
    if not paper_text:
        return jsonify({"success": False, "error": "paper_text 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        result = service.score_paper(paper_text)
        status_code = 200 if result.get("success") else 422
        return jsonify(result), status_code

    except Exception as e:
        logger.exception("期刊評分失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/structured-analysis", methods=["POST"])
@login_required
def structured_analysis():
    """根據 DataMind 探勘結果，用 Gemini 生成結構化分析（模型比較、資料洞察、風險、建議）

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）

    回傳：
        - analysis : { model_comparison, data_insights, risks, recommendations }
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        analysis = service.generate_structured_analysis(data["mining_results"])
        return jsonify({"success": True, "analysis": analysis})

    except Exception as e:
        logger.exception("結構化分析生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500


@rag_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """跟 AI 對話，針對 mining_results 提問，AI 可自主查詢 arXiv 論文

    JSON body:
        - mining_results : DataMind /api/models/workflow/execute 的完整回傳值（必填）
        - history         : 對話歷史 [{role: "user"|"model", text: str}]（選填，預設空陣列）
        - message         : 本輪使用者輸入（必填）

    回傳：
        - reply  : AI 回覆文字
        - papers : 本輪若觸發 arXiv 搜尋，附上候選論文清單；否則為空陣列
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    if not data or data.get("mining_results") is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"success": False, "error": "message 為必填欄位"}), 400

    history = data.get("history") or []

    service = get_paper_rag_service()

    try:
        result = service.chat_about_results(data["mining_results"], history, message)
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.exception("對話失敗")
        return jsonify({"success": False, "error": str(e)}), 500
