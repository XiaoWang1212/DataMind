"""論文編輯內容持久化服務

以 project_id 為 key，把論文的 Tiptap 文件內容 + 參考文獻清單存成 JSON 檔案。
沒有資料庫，比照 services/rag/vector_store.py 的 JSON 檔案持久化模式。
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ReportStore:
    def __init__(self, index_dir: str | Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, project_id: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", project_id)
        return self.index_dir / f"{safe_id}.json"

    def save(self, project_id: str, title: str, content: dict, citations: list, citation_style: str = "apa") -> dict:
        record = {
            "title": title,
            "content": content,
            "citations": citations,
            "citationStyle": citation_style,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path_for(project_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record

    def load(self, project_id: str) -> Optional[dict]:
        path = self._path_for(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[ReportStore] = None


def get_report_store() -> ReportStore:
    global _instance
    if _instance is None:
        index_dir = (
            Path(__file__).parent.parent.parent
            / os.getenv("REPORT_STORE_DIR", "artifacts/paper_reports")
        )
        _instance = ReportStore(index_dir=index_dir)
    return _instance
