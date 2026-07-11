"""arXiv API 查詢與 PDF 全文解析

純函式模組,不依賴 Gemini。供 PaperRAGService 分類/入庫流程使用。
"""

import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_API_URL = "http://export.arxiv.org/api/query"


def search_arxiv(query: str, max_results: int = 8) -> List[dict]:
    """呼叫 arXiv Export API,回傳候選論文清單。

    回傳每筆:{arxiv_id, title, authors, year, abstract, pdf_url}
    """
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
    })
    url = f"{_ARXIV_API_URL}?{params}"

    with urllib.request.urlopen(url, timeout=15) as resp:
        raw = resp.read()

    root = ET.fromstring(raw)
    candidates: List[dict] = []

    for entry in root.findall(f"{_ATOM_NS}entry"):
        entry_id = entry.findtext(f"{_ATOM_NS}id", default="") or ""
        arxiv_id = entry_id.rsplit("/abs/", 1)[-1] if "/abs/" in entry_id else entry_id

        title = " ".join((entry.findtext(f"{_ATOM_NS}title", default="") or "").split())
        summary = " ".join((entry.findtext(f"{_ATOM_NS}summary", default="") or "").split())
        published = entry.findtext(f"{_ATOM_NS}published", default="") or ""
        year: Optional[int] = int(published[:4]) if published[:4].isdigit() else None

        authors = [
            (author.findtext(f"{_ATOM_NS}name", default="") or "").strip()
            for author in entry.findall(f"{_ATOM_NS}author")
        ]

        pdf_url = ""
        for link in entry.findall(f"{_ATOM_NS}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "") or ""
                break

        candidates.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": ", ".join(a for a in authors if a),
            "year": year,
            "abstract": summary,
            "pdf_url": pdf_url,
        })

    return candidates


def fetch_pdf_text(pdf_url: str) -> str:
    """下載 PDF 到暫存檔,用 pymupdf 解析全文,結束後清除暫存檔。

    下載或解析失敗時讓例外往外拋,由呼叫端(PaperRAGService.ingest_arxiv_selection）
    決定要跳過這一篇還是中止。
    """
    import fitz  # PyMuPDF

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            with urllib.request.urlopen(pdf_url, timeout=30) as resp:
                tmp.write(resp.read())

        doc = fitz.open(str(tmp_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
