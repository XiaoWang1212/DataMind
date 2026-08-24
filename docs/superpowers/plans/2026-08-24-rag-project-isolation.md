# RAG 論文索引依 Project 隔離 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 RAG 論文索引從一個全 process 共用的檔案式 `VectorStore` 改成依 project 隔離、資料庫（pgvector）儲存，關掉子專案 #1 稽核發現的跨帳號資料洩漏／覆蓋問題。

**Architecture:** 重新啟用目前完全沒人用的 `rag_papers`/`rag_chunks` 兩張表，新增 `DbVectorStore` 取代檔案式 `VectorStore`，靠 `project_id` 外鍵 + SQL `WHERE` 過濾做隔離。`PaperRAGService` 對外的 `Chunk`/`SearchResult` 介面完全不變，只是儲存層換血、8 個會碰儲存的方法加一個 `project_id` 參數。`Embedder`/`Reranker`（sentence-transformers 模型）維持 process 共用單例。

**Tech Stack:** Flask + SQLAlchemy + pgvector（Postgres 擴充套件）+ Alembic migration + sentence-transformers（可能落到 TF-IDF 備援）+ Vue 3/TypeScript 前端。

**Spec:** `docs/superpowers/specs/2026-08-24-rag-project-isolation-design.md`

## Global Constraints

- 兩張目標表（`rag_papers`/`rag_chunks`）目前完全是空的、沒有任何程式碼讀寫——已用 `psql` 確認 row count 皆為 0，schema 改動零資料風險。
- 已確認 `RAG_EMBED_MODEL` 預設值 `BAAI/bge-small-zh-v1.5` 的真實輸出維度是 **512**（查證自 Hugging Face 上該模型的 `config.json`：`hidden_size: 512`，且 `modules.json` 確認 pipeline 是 Transformer → Pooling → Normalize，沒有額外的 Dense 投影層改變維度）。現有 `backend/models/rag_paper.py` 寫死的 `EMBEDDING_DIM = 384` 是錯的，這次一併修正。
- 本機開發環境（Windows 本地 venv 跟 docker `datamind-backend` 容器）目前 sentence-transformers 都因為 torch/torchvision 版本問題載入失敗、會落到 TF-IDF 備援模式——這是既有環境問題，不在本次任務範圍內修，但代表本次改動的手動驗證腳本必須讓 TF-IDF 路徑也能正確運作（`DbVectorStore.search()` 的兩條路徑都要跑得通）。
- 資料庫遷移／手動驗證腳本一律透過 `datamind-backend` 容器執行（`.env` 的 `DATABASE_URL` 用 docker-compose 服務名稱 `postgres`，只有容器網路內解析得到，本機 venv 連不到）。指令格式：`MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python <script>`（Windows Git Bash 環境；`MSYS_NO_PATHCONV=1` 是為了避免 Git Bash 把 `/app/...` 誤判成 Windows 路徑再亂轉換）。
- 現有的 `rag_chunks_paper_id_fkey` 外鍵約束名稱（已用 `\d rag_chunks` 確認）：`rag_chunks_paper_id_fkey`，`rag_papers_project_id_fkey`。
- 這個 repo 的既有慣例是**自動化測試不連真的資料庫**（`DATABASE_URL` 給假字串即可，SQLAlchemy 延遲連線；`test_auth_routes.py`/`test_field_mapping_routes.py` 開頭註解都明講這件事）。真的碰資料庫的驗證，這個 repo 的慣例是寫成 `backend/scripts/test_*.py` 手動腳本（例如 `test_auth_google_and_reset.py`），不是 pytest。本計畫沿用這個慣例：`DbVectorStore` 的 SQL 查詢邏輯用手動腳本驗證，純邏輯（不碰 DB 的部分）才寫 pytest。

---

### Task 1: Migration — 修正 `rag_papers`/`rag_chunks` 的 schema 缺陷

**Files:**
- Modify: `backend/models/rag_paper.py`
- Create: `backend/migrations/versions/<alembic 自動產生的檔名>.py`

**Interfaces:**
- Consumes: 無（這是最底層的任務，不依賴其他任務）
- Produces: `RagChunk.embedding` 變成 `Mapped[list[float] | None]`（nullable），維度 512；`rag_chunks.paper_id` 外鍵有 `ON DELETE CASCADE`；`rag_papers.project_id`、`rag_chunks.paper_id` 各有索引。後續任務（Task 2 的 `DbVectorStore`）直接依賴這個最終 schema。

- [ ] **Step 1: 修改 `backend/models/rag_paper.py`**

把整個檔案內容改成：

```python
import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from extensions import db

EMBEDDING_DIM = 512  # BAAI/bge-small-zh-v1.5 的實際輸出維度（hidden_size，無額外投影層）


class RagPaper(db.Model):
    __tablename__ = "rag_papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )


class RagChunk(db.Model):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("rag_papers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
```

（跟原本比：`embedding` 加 `| None` 且 `nullable=True`；`EMBEDDING_DIM` 從 384 改 512，並補上為什麼的註解。）

- [ ] **Step 2: 產生 migration 檔案骨架**

在容器內執行（會用真的 DB 連線讀目前的 head revision，自動填好 `down_revision`）：

```bash
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python -m alembic revision -m "rag project isolation schema fixes"
```

記下輸出的檔案路徑（在 `backend/migrations/versions/` 底下）。

- [ ] **Step 3: 編輯產生的 migration 檔案**

把 `upgrade()`/`downgrade()` 改成：

```python
from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


def upgrade() -> None:
    op.drop_constraint("rag_chunks_paper_id_fkey", "rag_chunks", type_="foreignkey")
    op.create_foreign_key(
        "rag_chunks_paper_id_fkey", "rag_chunks", "rag_papers",
        ["paper_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_rag_papers_project_id", "rag_papers", ["project_id"])
    op.create_index("ix_rag_chunks_paper_id", "rag_chunks", ["paper_id"])
    op.drop_column("rag_chunks", "embedding")
    op.add_column(
        "rag_chunks",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("rag_chunks", "embedding")
    op.add_column(
        "rag_chunks",
        sa.Column("embedding", pgvector.sqlalchemy.Vector(384), nullable=False),
    )
    op.drop_index("ix_rag_chunks_paper_id", table_name="rag_chunks")
    op.drop_index("ix_rag_papers_project_id", table_name="rag_papers")
    op.drop_constraint("rag_chunks_paper_id_fkey", "rag_chunks", type_="foreignkey")
    op.create_foreign_key(
        "rag_chunks_paper_id_fkey", "rag_chunks", "rag_papers",
        ["paper_id"], ["id"],
    )
```

（`import pgvector.sqlalchemy` 這行如果 alembic 自動產生的檔案開頭沒有，要自己加上去；`revision`/`down_revision` 欄位維持 alembic 自動填的值，不要手動改。）

- [ ] **Step 4: 套用 migration，確認 schema 正確**

```bash
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python -m alembic upgrade head
MSYS_NO_PATHCONV=1 docker exec datamind-postgres psql -U datamind -d datamind -c "\d rag_chunks"
```

Expected：`embedding` 欄位型別 `vector(512)`、`Nullable` 那欄是空的（代表可為 NULL，不是 `not null`）；`Foreign-key constraints` 那行要有 `ON DELETE CASCADE`；`Indexes` 要多一個 `ix_rag_chunks_paper_id`。

```bash
MSYS_NO_PATHCONV=1 docker exec datamind-postgres psql -U datamind -d datamind -c "\d rag_papers"
```

Expected：`Indexes` 要多一個 `ix_rag_papers_project_id`。

- [ ] **Step 5: 確認 downgrade 可逆，再重新 upgrade**

```bash
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python -m alembic downgrade -1
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python -m alembic upgrade head
```

Expected：兩個指令都成功、無錯誤。最後要停留在 `upgrade head` 之後的狀態（下一個任務要用）。

- [ ] **Step 6: Commit**

```bash
git add backend/models/rag_paper.py backend/migrations/versions/
git commit -m "fix: correct rag_chunks embedding dim/nullability and add project_id/paper_id indexes + cascade delete"
```

---

### Task 2: `DbVectorStore` — 新的資料庫儲存層

**Files:**
- Create: `backend/services/rag/db_vector_store.py`
- Create: `backend/tests/test_db_vector_store.py`
- Create: `backend/scripts/verify_db_vector_store.py`

**Interfaces:**
- Consumes: Task 1 的 `RagPaper`/`RagChunk`（`backend/models/rag_paper.py`）；既有的 `Chunk`（`backend/services/rag/chunker.py`）、`Embedder`（`backend/services/rag/embedder.py`，`encode(texts) -> np.ndarray`、`encode_query(query) -> np.ndarray`、`.backend` 屬性是 `"transformers"` 或 `"tfidf"`）
- Produces：`DbVectorStore` class，方法簽章：
  - `__init__(self, embedder: Embedder)`
  - `create_paper(self, project_id: int, title: str, metadata: dict) -> str`
  - `add_chunks(self, chunks: list[Chunk]) -> None`
  - `search(self, project_id: int, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]`
  - `delete_paper(self, project_id: int, paper_id: str) -> bool`
  - `clear(self, project_id: int) -> None`
  - `get_status(self, project_id: int) -> dict`
  - `find_by_arxiv_id(self, project_id: int, arxiv_id: str) -> RagPaper | None`

  這些簽章是 Task 3（`PaperRAGService`）直接依賴的介面，名稱/參數順序不能改。

- [ ] **Step 1: 寫 `_row_to_chunk` 的失敗測試**

Create `backend/tests/test_db_vector_store.py`:

```python
"""DbVectorStore 的純邏輯測試：只測不碰資料庫的部分（_row_to_chunk 的欄位組裝）。
真的會下 SQL 的方法（create_paper/add_chunks/search/...）用
backend/scripts/verify_db_vector_store.py 對開發用資料庫手動驗證，
理由跟 test_auth_routes.py 開頭註解一致：這個 repo 的自動化測試不連真的資料庫。
"""

import os
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from services.rag.db_vector_store import DbVectorStore  # noqa: E402


def _fake_chunk_row(id=1, paper_id=10, content="hello", chunk_index=0):
    return SimpleNamespace(id=id, paper_id=paper_id, content=content, chunk_index=chunk_index)


def _fake_paper_row(title="Title", author="Author", year=2024, arxiv_id=None):
    return SimpleNamespace(title=title, author=author, year=year, arxiv_id=arxiv_id)


class TestRowToChunk:
    def test_builds_chunk_with_stringified_ids(self):
        chunk = DbVectorStore._row_to_chunk(_fake_chunk_row(id=5, paper_id=10), _fake_paper_row())
        assert chunk.chunk_id == "5"
        assert chunk.paper_id == "10"

    def test_copies_content_title_and_index(self):
        chunk = DbVectorStore._row_to_chunk(
            _fake_chunk_row(content="some text", chunk_index=3),
            _fake_paper_row(title="My Paper"),
        )
        assert chunk.content == "some text"
        assert chunk.title == "My Paper"
        assert chunk.chunk_index == 3

    def test_metadata_has_author_year_arxiv_id(self):
        chunk = DbVectorStore._row_to_chunk(
            _fake_chunk_row(), _fake_paper_row(author="Smith", year=2023, arxiv_id="1234.5678"),
        )
        assert chunk.metadata["author"] == "Smith"
        assert chunk.metadata["year"] == 2023
        assert chunk.metadata["arxiv_id"] == "1234.5678"

    def test_journal_derived_from_arxiv_id_when_present(self):
        chunk = DbVectorStore._row_to_chunk(_fake_chunk_row(), _fake_paper_row(arxiv_id="1234.5678"))
        assert chunk.metadata["journal"] == "arXiv:1234.5678"

    def test_no_journal_key_when_arxiv_id_missing(self):
        chunk = DbVectorStore._row_to_chunk(_fake_chunk_row(), _fake_paper_row(arxiv_id=None))
        assert "journal" not in chunk.metadata
```

- [ ] **Step 2: 跑測試，確認因為模組不存在而失敗**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_db_vector_store.py -v
```

Expected: FAIL，錯誤訊息類似 `ModuleNotFoundError: No module named 'services.rag.db_vector_store'`。

- [ ] **Step 3: 實作 `DbVectorStore`**

Create `backend/services/rag/db_vector_store.py`:

```python
"""取代 services/rag/vector_store.py 的資料庫版本，依 project_id 隔離。"""

from extensions import db
from models.rag_paper import RagChunk, RagPaper
from services.rag.chunker import Chunk
from services.rag.embedder import Embedder


class DbVectorStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder  # 共用單例，注入進來，不自己持有

    # ── 論文/段落寫入 ──────────────────────────────────────────────────────

    def create_paper(self, project_id: int, title: str, metadata: dict) -> str:
        paper = RagPaper(
            project_id=project_id,
            title=title,
            author=metadata.get("author") or None,
            year=self._parse_year(metadata.get("year")),
            arxiv_id=metadata.get("arxiv_id") or None,
        )
        db.session.add(paper)
        db.session.commit()
        return str(paper.id)

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        if self.embedder.backend == "transformers":
            vectors = self.embedder.encode([c.content for c in chunks])
        else:
            vectors = [None] * len(chunks)
        for chunk, vector in zip(chunks, vectors):
            db.session.add(RagChunk(
                paper_id=int(chunk.paper_id),
                content=chunk.content,
                embedding=vector,
                chunk_index=chunk.chunk_index,
            ))
        db.session.commit()

    # ── 查詢 ──────────────────────────────────────────────────────────────

    def search(self, project_id: int, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        if self.embedder.backend == "transformers":
            return self._transformer_search(project_id, query, top_k)
        return self._tfidf_search(project_id, query, top_k)

    def _transformer_search(self, project_id: int, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        query_vec = self.embedder.encode_query(query)
        distance_expr = RagChunk.embedding.cosine_distance(query_vec)
        rows = (
            db.session.query(RagChunk, RagPaper, distance_expr.label("distance"))
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id, RagChunk.embedding.isnot(None))
            .order_by(distance_expr)
            .limit(top_k)
            .all()
        )
        return [
            (self._row_to_chunk(chunk, paper), 1.0 - float(distance))
            for chunk, paper, distance in rows
        ]

    def _tfidf_search(self, project_id: int, query: str, top_k: int) -> list[tuple[Chunk, float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        rows = (
            db.session.query(RagChunk, RagPaper)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id)
            .all()
        )
        if not rows:
            return []

        corpus = [chunk.content for chunk, _ in rows]
        vec = TfidfVectorizer(max_features=8000, analyzer="char_wb", ngram_range=(2, 4))
        corpus_mat = vec.fit_transform(corpus)
        query_vec = vec.transform([query])
        scores = cosine_similarity(query_vec, corpus_mat).flatten()

        ranked = sorted(zip(rows, scores), key=lambda item: item[1], reverse=True)[:top_k]
        return [(self._row_to_chunk(chunk, paper), float(score)) for (chunk, paper), score in ranked]

    def find_by_arxiv_id(self, project_id: int, arxiv_id: str) -> RagPaper | None:
        if not arxiv_id:
            return None
        return RagPaper.query.filter_by(project_id=project_id, arxiv_id=arxiv_id).first()

    def get_status(self, project_id: int) -> dict:
        papers = RagPaper.query.filter_by(project_id=project_id).all()
        total_chunks = (
            db.session.query(RagChunk)
            .join(RagPaper, RagChunk.paper_id == RagPaper.id)
            .filter(RagPaper.project_id == project_id)
            .count()
        )
        return {
            "total_papers": len(papers),
            "total_chunks": total_chunks,
            "embedding_backend": self.embedder.backend,
            "embedding_model": self.embedder.model_name,
            "papers": [
                {
                    "paper_id": str(p.id),
                    "title": p.title,
                    "author": p.author,
                    "year": p.year,
                    "arxiv_id": p.arxiv_id,
                }
                for p in papers
            ],
        }

    # ── 刪除 ──────────────────────────────────────────────────────────────

    def delete_paper(self, project_id: int, paper_id: str) -> bool:
        try:
            pid = int(paper_id)
        except (TypeError, ValueError):
            return False

        paper = RagPaper.query.filter_by(id=pid, project_id=project_id).first()
        if paper is None:
            return False
        db.session.delete(paper)  # ON DELETE CASCADE 會連帶刪除 RagChunk
        db.session.commit()
        return True

    def clear(self, project_id: int) -> None:
        RagPaper.query.filter_by(project_id=project_id).delete(synchronize_session=False)
        db.session.commit()

    # ── 內部工具 ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_year(value) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _row_to_chunk(chunk_row, paper_row) -> Chunk:
        metadata = {
            "author": paper_row.author,
            "year": paper_row.year,
            "arxiv_id": paper_row.arxiv_id,
        }
        if paper_row.arxiv_id:
            metadata["journal"] = f"arXiv:{paper_row.arxiv_id}"
        return Chunk(
            chunk_id=str(chunk_row.id),
            paper_id=str(chunk_row.paper_id),
            title=paper_row.title,
            content=chunk_row.content,
            chunk_index=chunk_row.chunk_index,
            metadata=metadata,
        )
```

- [ ] **Step 4: 跑測試，確認通過**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_db_vector_store.py -v
```

Expected: 5 個測試全部 PASS。

- [ ] **Step 5: 寫手動驗證腳本**

Create `backend/scripts/verify_db_vector_store.py`:

```python
"""手動驗證：DbVectorStore 直接操作（不經過 HTTP），需要真的 Postgres + app context。

執行方式（docker-compose 要先啟動）：
    MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_db_vector_store.py

會借用資料庫裡第一個既有的 user 建立兩個測試用 project，跑完自動清理（連帶刪除
建立的論文，靠 migration 加的 ON DELETE CASCADE）。如果資料庫完全沒有 user，
先跑過 backend/scripts/seed_admin.py 建一個。
"""

from apps import create_app
from extensions import db
from models.project import Project
from models.user import User
from services.rag.chunker import TextChunker
from services.rag.db_vector_store import DbVectorStore
from services.rag.embedder import Embedder


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    app = create_app()
    with app.app_context():
        user = User.query.first()
        if user is None:
            raise SystemExit("資料庫沒有任何 user，先跑 backend/scripts/seed_admin.py")

        created_project_ids: list[int] = []
        try:
            project = Project(user_id=user.id, name="verify_db_vector_store")
            db.session.add(project)
            db.session.commit()
            created_project_ids.append(project.id)
            project_id = project.id

            other_project = Project(user_id=user.id, name="verify_db_vector_store (other)")
            db.session.add(other_project)
            db.session.commit()
            created_project_ids.append(other_project.id)

            embedder = Embedder()
            print(f"embedder backend: {embedder.backend}")
            store = DbVectorStore(embedder=embedder)
            chunker = TextChunker()

            paper_id = store.create_paper(
                project_id, "Verify Paper",
                {"author": "Tester", "year": "2024", "arxiv_id": "9999.99999"},
            )
            check("create_paper 回傳字串 paper_id", isinstance(paper_id, str))

            chunks = chunker.chunk(
                "Deep learning models improve medical diagnosis accuracy significantly. "
                "Convolutional neural networks are widely used for image classification tasks.",
                paper_id=paper_id, title="Verify Paper", metadata={},
            )
            store.add_chunks(chunks)
            check("add_chunks 沒有拋例外", True)

            results = store.search(project_id, "deep learning diagnosis", top_k=3)
            check("search 找得到剛存進去的段落", len(results) > 0)
            check("search 回傳的 Chunk.title 正確", results and results[0][0].title == "Verify Paper")

            empty_results = store.search(other_project.id, "deep learning diagnosis", top_k=3)
            check("不同 project 搜不到（隔離生效）", len(empty_results) == 0)

            found = store.find_by_arxiv_id(project_id, "9999.99999")
            check("find_by_arxiv_id 找得到剛存的論文", found is not None and str(found.id) == paper_id)

            not_found = store.find_by_arxiv_id(other_project.id, "9999.99999")
            check("find_by_arxiv_id 在別的 project 找不到", not_found is None)

            status = store.get_status(project_id)
            check("get_status 回報 1 篇論文", status["total_papers"] == 1)
            check("get_status 回報 chunks 數量 > 0", status["total_chunks"] > 0)

            deleted = store.delete_paper(project_id, paper_id)
            check("delete_paper 成功", deleted is True)

            after_delete = store.search(project_id, "deep learning diagnosis", top_k=3)
            check("刪除後搜不到（chunks 被 cascade 一併刪除）", len(after_delete) == 0)

            deleted_again = store.delete_paper(project_id, paper_id)
            check("重複刪除同一篇回傳 False", deleted_again is False)
        finally:
            for pid in created_project_ids:
                p = Project.query.get(pid)
                if p:
                    db.session.delete(p)
            db.session.commit()

    print("\n全部通過。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 執行手動驗證腳本**

```bash
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_db_vector_store.py
```

Expected: 全部行印出 `[PASS]`，最後印出「全部通過。」。如果印出 `embedder backend: tfidf`（目前這個環境的已知狀況），代表走的是 TF-IDF 備援路徑，這樣也要全部 PASS——這條路徑跟 transformers 路徑都要能力驗證過。

- [ ] **Step 7: Commit**

```bash
git add backend/services/rag/db_vector_store.py backend/tests/test_db_vector_store.py backend/scripts/verify_db_vector_store.py
git commit -m "feat: add DbVectorStore, a per-project pgvector-backed replacement for the file-based VectorStore"
```

---

### Task 3: `PaperRAGService` — 換掉儲存層、加 `project_id`、arXiv 去重複

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Modify: `backend/tests/test_paper_rag_search.py`

（`backend/tests/test_paper_rag_citation_map.py` 讀過確認過**不用改**——它測的是 `PaperRAGService._build_citation_map` 這個 staticmethod，只吃 `local_refs`/`section_text`/`global_ref_list`，完全不碰 `_store`、不呼叫 `search()`，跟 `project_id` 無關。）

**Interfaces:**
- Consumes: Task 2 的 `DbVectorStore`（方法簽章見上）
- Produces：`PaperRAGService` 的 `add_paper`/`search`/`generate_citation`/`generate_paper`/`ingest_arxiv_selection`/`get_status`/`delete_paper`/`clear` 全部第一個參數變成 `project_id: int`。這是 Task 4（路由層）直接依賴的介面。

- [ ] **Step 1: 看現有測試怎麼注入假 store**

讀 `backend/tests/test_paper_rag_search.py` 全文（已經讀過，確切寫法如下，不是用 fixture 或 helper 函式，是每個測試各自 inline 寫）：

```python
service = PaperRAGService.__new__(PaperRAGService)  # 繞過 __init__，不需要 GEMINI_API_KEY
store = FakeStore(make_chunks(10))
service._store = store
service._reranker = FakeRerankerAvailable()

results = service.search("query", top_k=3, use_rerank=True)
```

`FakeStore.search(self, query, top_k=5)` 目前只接 `query`/`top_k`。接下來要把 `FakeStore.search` 加一個 `project_id` 當第一個參數（記錄下來但不用來過濾，是假物件），並把三個測試裡 `service.search("query", ...)` 的呼叫都改成 `service.search(1, "query", ...)`（`1` 是任意固定值，這個檔案的假 `FakeStore` 不會真的按 project_id 過濾）。

- [ ] **Step 2: 修改 `test_paper_rag_search.py`，先讓測試失敗**

把 `FakeStore` 改成：

```python
class FakeStore:
    def __init__(self, chunks_with_scores):
        self._chunks_with_scores = chunks_with_scores
        self.last_top_k = None
        self.last_project_id = None

    def search(self, project_id, query, top_k=5):
        self.last_project_id = project_id
        self.last_top_k = top_k
        return self._chunks_with_scores[:top_k]
```

三個既有測試裡 `service.search("query", top_k=3, use_rerank=...)` 都改成 `service.search(1, "query", top_k=3, use_rerank=...)`。改完先跑：

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_paper_rag_search.py -v
```

Expected: FAIL（`PaperRAGService.search()` 目前的簽章還沒有 `project_id`，會是 `TypeError: search() takes from 2 to 4 positional arguments but 5 were given` 之類的錯誤——因為 `1` 會被塞進原本 `top_k` 的位置，型別/數量對不上）。

- [ ] **Step 3: 在同一個檔案新增 arXiv 去重複的測試**

在檔案尾端新增（沿用檔案既有的 `PaperRAGService.__new__(PaperRAGService)` 手法，不用任何 fixture）：

```python
class TestIngestArxivSelectionDedup:
    def test_skips_candidate_already_in_project(self, monkeypatch):
        """同一個 project 裡，arxiv_id 已經存在就不該再呼叫 add_paper。"""
        service = PaperRAGService.__new__(PaperRAGService)
        service._store = FakeStore([])
        service._store.find_by_arxiv_id = lambda project_id, arxiv_id: (
            object() if arxiv_id == "1111.1111" else None
        )
        add_paper_calls = []
        service.add_paper = lambda project_id, title, content, metadata=None: (
            add_paper_calls.append(title) or {"success": True}
        )
        monkeypatch.setattr(
            "services.rag.paper_rag.arxiv_source.fetch_pdf_text",
            lambda pdf_url: "some fetched text",
        )

        result = service.ingest_arxiv_selection(
            project_id=1,
            candidates=[
                {"title": "Already ingested", "pdf_url": "http://x/1", "arxiv_id": "1111.1111"},
                {"title": "New paper", "pdf_url": "http://x/2", "arxiv_id": "2222.2222"},
            ],
        )

        # 去重複的那篇不會呼叫 add_paper（沒有真的重複寫入），但仍然算「已在索引裡」，
        # 所以 result["ingested"] 兩篇都要有——這是給呼叫端看的「這個 project 現在有沒有
        # 這篇論文」，不是「這次呼叫有沒有真的寫入新資料」。
        assert add_paper_calls == ["New paper"]
        assert result["ingested"] == ["Already ingested", "New paper"]
```

- [ ] **Step 4: 跑測試確認新測試也是預期失敗**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_paper_rag_search.py -v
```

Expected: `TestIngestArxivSelectionDedup::test_skips_candidate_already_in_project` FAIL（`ingest_arxiv_selection()` 還沒有 `project_id` 參數、也還沒有去重複邏輯）；前面 Step 2 改過的三個測試這時應該已經 PASS 不動，因為它們跟 `ingest_arxiv_selection` 無關，等 Step 5 改完 `search()` 就會通過——如果這時候還沒過也沒關係，Step 6 會一次改完 `paper_rag.py`。

- [ ] **Step 5: 修改 `backend/services/rag/paper_rag.py`**

檔案開頭的 import（原本第 25 行 `from .vector_store import VectorStore`）改成：

```python
from .db_vector_store import DbVectorStore
```

`__init__` 裡原本建立 `self._store = VectorStore(index_dir=index_dir, embedder=self._embedder)` 那一段，以及前面計算 `index_dir` 的那幾行（`index_dir = (Path(__file__).parent.parent.parent / os.getenv("RAG_INDEX_DIR", "artifacts/rag_index"))`），整段改成：

```python
self._store = DbVectorStore(embedder=self._embedder)
```

（不用再算 `index_dir`，`os.getenv("RAG_INDEX_DIR", ...)` 這行也一併刪掉。）

`add_paper`（原本 157-174 行附近）整個換成：

```python
def add_paper(self, project_id: int, title: str, content: str, metadata: dict | None = None) -> dict:
    if metadata is None:
        metadata = {}
    paper_id = self._store.create_paper(project_id, title, metadata)
    chunks = self._chunker.chunk(content, paper_id=paper_id, title=title, metadata=metadata)
    if not chunks:
        self._store.delete_paper(project_id, paper_id)
        return {"success": False, "error": "未能從文件中提取內容"}

    self._store.add_chunks(chunks)

    logger.info("add_paper: %s (%d chunks)", title, len(chunks))
    return {
        "success": True,
        "paper_id": paper_id,
        "title": title,
        "chunks_added": len(chunks),
    }
```

`search`（原本 176-189 行附近）簽章與內部呼叫改成：

```python
def search(self, project_id: int, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
    should_rerank = use_rerank and self._reranker is not None and self._reranker.available
    overfetch_k = top_k * 4 if should_rerank else top_k

    raw = self._store.search(project_id, query, top_k=overfetch_k)

    if should_rerank and raw:
        reranked = self._reranker.rerank(query, raw)
        return [
            SearchResult(chunk=c, score=orig_score, rerank_score=rerank_score)
            for c, orig_score, rerank_score in reranked[:top_k]
        ]

    return [SearchResult(chunk=c, score=s) for c, s in raw[:top_k]]
```

`generate_citation` 簽章加 `project_id: int`（放在 `query` 前面），內部 `self.search(query, top_k=top_k)` 改成 `self.search(project_id, query, top_k=top_k)`。

`generate_paper` 簽章加 `project_id: int`（放在 `topic` 前面），內部 `self.search(query, top_k=top_k)` 改成 `self.search(project_id, query, top_k=top_k)`。

`ingest_arxiv_selection` 整個換成：

```python
def ingest_arxiv_selection(self, project_id: int, candidates: List[dict]) -> dict:
    """下載選中的 arXiv 論文全文並加入索引。

    單篇下載/解析失敗時跳過並記錄，不中斷整體流程；若全部失敗則回傳錯誤。
    同一個 project 裡，arxiv_id 已經存在就跳過，不重複塞進索引。
    """
    ingested: List[str] = []
    failed: List[str] = []

    for candidate in candidates:
        title = candidate.get("title", "")
        pdf_url = candidate.get("pdf_url", "")
        arxiv_id = candidate.get("arxiv_id", "")

        if arxiv_id and self._store.find_by_arxiv_id(project_id, arxiv_id) is not None:
            logger.info("跳過已存在的 arXiv 論文：%s (%s)", title, arxiv_id)
            ingested.append(title)
            continue

        try:
            content = arxiv_source.fetch_pdf_text(pdf_url)
            if not content.strip():
                raise ValueError("PDF 未解析出任何文字")
        except Exception as e:
            logger.warning("下載/解析 arXiv PDF 失敗：%s (%s)", title, e)
            failed.append(title)
            continue

        result = self.add_paper(
            project_id=project_id,
            title=title,
            content=content,
            metadata={
                "author": candidate.get("authors", ""),
                "year": candidate.get("year", ""),
                "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
                "arxiv_id": arxiv_id,
            },
        )
        if result.get("success"):
            ingested.append(title)
        else:
            failed.append(title)

    if not ingested:
        return {
            "success": False,
            "error": "所有候選論文皆下載/解析失敗，無法建立參考文獻庫",
            "ingested": ingested,
            "failed": failed,
        }

    return {"success": True, "ingested": ingested, "failed": failed}
```

`get_status`、`delete_paper`、`clear` 分別改成：

```python
def get_status(self, project_id: int) -> dict:
    return self._store.get_status(project_id)

def delete_paper(self, project_id: int, paper_id: str) -> dict:
    ok = self._store.delete_paper(project_id, paper_id)
    if ok:
        return {"success": True, "message": f"已刪除論文 {paper_id}"}
    return {"success": False, "message": f"找不到論文 {paper_id}"}

def clear(self, project_id: int) -> dict:
    self._store.clear(project_id)
    return {"success": True, "message": "已清空論文庫"}
```

- [ ] **Step 6: 跑測試，確認全部通過**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_paper_rag_search.py -v
```

Expected: 全部 PASS，包含新增的去重複測試。

- [ ] **Step 7: 跑整個 backend 測試套件確認沒有連帶弄壞別的**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 全部 PASS（含沒有改動的 `test_paper_rag_citation_map.py`）。

- [ ] **Step 8: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/tests/test_paper_rag_search.py
git commit -m "feat: thread project_id through PaperRAGService, switch to DbVectorStore, dedup arXiv ingestion by project"
```

---

### Task 4: `routes/rag.py` — `project_id` + 擁有權驗證

**Files:**
- Modify: `backend/routes/rag.py`
- Create: `backend/tests/test_rag_routes.py`

**Interfaces:**
- Consumes: Task 3 的 `PaperRAGService`（8 個方法都需要 `project_id` 當第一個參數）；`backend/models/project.py` 的 `Project`（`id`、`user_id` 欄位）
- Produces: 8 條路由（`/upload`、`/search`、`/cite`、`/status`、`/clear`、`/paper/<paper_id>` DELETE、`/generate-paper`、`/arxiv/generate`）都要求帶 `project_id`，驗證擁有權。Task 5（前端）依賴這個 request/response 合約。

- [ ] **Step 1: 寫路由層測試（TDD：先寫測試，這次會全部 FAIL 因為路由還沒改）**

Create `backend/tests/test_rag_routes.py`:

```python
"""路由層測試：只測 project_id 驗證/擁有權檢查/登入檢查，不碰資料庫、不碰真的 PaperRAGService
（monkeypatch 掉），理由同 test_field_mapping_routes.py 開頭註解。
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

import routes.rag as rag_route  # noqa: E402
import services.rag.paper_rag as paper_rag_module  # noqa: E402
from apps import create_app  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["LOGIN_DISABLED"] = True
    return app.test_client()


@pytest.fixture
def client_with_login_required():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


class FakeProject:
    def __init__(self, project_id=7, user_id=1):
        self.id = project_id
        self.user_id = user_id


class FakeService:
    def __init__(self):
        self.calls = []

    def search(self, project_id, query, top_k=5, use_rerank=True):
        self.calls.append(("search", project_id))
        return []

    def get_status(self, project_id):
        self.calls.append(("get_status", project_id))
        return {"total_papers": 0, "total_chunks": 0}

    def add_paper(self, project_id, title, content, metadata=None):
        self.calls.append(("add_paper", project_id))
        return {"success": True, "paper_id": "1", "title": title, "chunks_added": 1}

    def generate_citation(self, project_id, query, top_k=3, citation_style="apa"):
        self.calls.append(("generate_citation", project_id))
        return {"citations": [], "sources": []}

    def clear(self, project_id):
        self.calls.append(("clear", project_id))
        return {"success": True, "message": "已清空論文庫"}

    def delete_paper(self, project_id, paper_id):
        self.calls.append(("delete_paper", project_id, paper_id))
        return {"success": True, "message": "已刪除論文"}

    def generate_paper(self, project_id, topic, mining_results, structure=None, language="zh-TW"):
        self.calls.append(("generate_paper", project_id))
        return {
            "paper_markdown": "", "citation_map": [], "references": [],
            "citation_report": "", "sections_generated": [], "usage": {},
        }

    def ingest_arxiv_selection(self, project_id, candidates):
        self.calls.append(("ingest_arxiv_selection", project_id))
        return {"success": True, "ingested": [], "failed": []}


MISSING_PROJECT_ID_CASES = [
    ("post", "/api/rag/upload", {"json": {"title": "t", "content": "c"}}),
    ("post", "/api/rag/search", {"json": {"query": "q"}}),
    ("post", "/api/rag/cite", {"json": {"query": "q"}}),
    ("get", "/api/rag/status", {}),
    ("post", "/api/rag/clear", {"json": {}}),
    ("delete", "/api/rag/paper/1", {}),
    ("post", "/api/rag/generate-paper", {"json": {"topic": "t", "mining_results": {}}}),
    (
        "post", "/api/rag/arxiv/generate",
        {"json": {"topic": "t", "mining_results": {}, "selected_candidates": [{}]}},
    ),
]


@pytest.mark.parametrize("method,path,kwargs", MISSING_PROJECT_ID_CASES)
def test_missing_project_id_returns_400(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_search_rejects_project_not_owned(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: None)
    response = client.post("/api/rag/search", json={"project_id": 7, "query": "q"})
    assert response.status_code == 404


def test_search_delegates_with_project_id(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/search", json={"project_id": 7, "query": "deep learning"})

    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert fake_service.calls == [("search", 7)]


def test_status_reads_project_id_from_query_string(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.get("/api/rag/status?project_id=7")

    assert response.status_code == 200
    assert fake_service.calls == [("get_status", 7)]


def test_delete_paper_reads_project_id_from_query_string(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.delete("/api/rag/paper/42?project_id=7")

    assert response.status_code == 200
    assert fake_service.calls == [("delete_paper", 7, "42")]


def test_search_requires_login(client_with_login_required):
    response = client_with_login_required.post(
        "/api/rag/search", json={"project_id": 1, "query": "q"}
    )
    assert response.status_code == 401
```

- [ ] **Step 2: 跑測試，確認目前的失敗原因合理**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_rag_routes.py -v
```

Expected: 大部分 FAIL（`rag_route` 還沒有 `_get_owned_project`，路由也還沒有檢查 `project_id`）。`test_search_requires_login` 應該已經 PASS（`@login_required` 子專案 #1 已經加過）。

- [ ] **Step 3: 修改 `backend/routes/rag.py`**

在檔案開頭 import 區塊加：

```python
from flask_login import current_user, login_required
from models.project import Project
```

（`login_required` 已經有 import，只需要補 `current_user`；確認不要重複 import。）

在 `ALLOWED_EXTENSIONS = {"txt", "md", "pdf"}` 之後、`extract_text_from_file` 之前，加兩個 helper：

```python
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
```

以下每個路由函式，在**現有的 `@login_required` 之後、函式邏輯最開頭**插入 project_id 解析與擁有權檢查。8 個路由分兩種讀取方式：

**JSON body 讀取（`/upload`、`/search`、`/cite`、`/clear`、`/generate-paper`、`/arxiv/generate`）**——以 `/search` 為例，改動後開頭變成：

```python
@rag_bp.route("/search", methods=["POST"])
@login_required
def search_papers():
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
```

（`data = request.get_json()` 要移到最前面，`project_id` 檢查排在 `query` 必填檢查之前——project_id 缺漏或不合法直接 400，不必等到檢查 query。其餘回傳邏輯跟原本完全一樣，沒有變。）

`upload_paper()`：檔案上傳分支用 `request.form.get("project_id")`，JSON 分支用 `data.get("project_id")`，同一個函式裡兩個分支各自要檢查一次（因為兩個分支目前是互斥的 if/else，各自提早 return）：

```python
@rag_bp.route("/upload", methods=["POST"])
@login_required
def upload_paper():
    from services.rag.paper_rag import get_paper_rag_service

    service = get_paper_rag_service()

    # 處理文件上傳
    if "file" in request.files:
        project_id = _parse_project_id(request.form.get("project_id"))
        if project_id is None:
            return jsonify({"success": False, "error": "project_id 為必填欄位，且必須是整數"}), 400
        if _get_owned_project(project_id) is None:
            return jsonify({"success": False, "error": "找不到專案"}), 404

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
```

`generate_citation()`、`generate_paper()`、`arxiv_generate()` 都比照 `/search` 的模式（`data = request.get_json()` 先拿到，檢查 `project_id`，再檢查各自原本就有的必填欄位），完整改動如下：

```python
@rag_bp.route("/cite", methods=["POST"])
@login_required
def generate_citation():
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


@rag_bp.route("/generate-paper", methods=["POST"])
@login_required
def generate_paper():
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


@rag_bp.route("/arxiv/generate", methods=["POST"])
@login_required
def arxiv_generate():
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

    except Exception as e:
        logger.exception("arXiv 論文生成失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

**Query string 讀取（`/status`、`/paper/<paper_id>` DELETE）：**

```python
@rag_bp.route("/status", methods=["GET"])
@login_required
def get_status():
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


@rag_bp.route("/paper/<paper_id>", methods=["DELETE"])
@login_required
def delete_paper(paper_id: str):
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
```

`/clear` 因為原本沒有必填 body，改成接受可選 JSON body，只為了拿 `project_id`：

```python
@rag_bp.route("/clear", methods=["POST"])
@login_required
def clear_index():
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
```

- [ ] **Step 4: 跑測試，確認全部通過**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/test_rag_routes.py -v
```

Expected: 全部 PASS。

- [ ] **Step 5: 跑整個 backend 測試套件**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 全部 PASS。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/rag.py backend/tests/test_rag_routes.py
git commit -m "feat: require project_id + ownership check on the 8 storage-touching RAG routes"
```

---

### Task 5: 前端 — `/arxiv/generate` 補送 `project_id`

**Files:**
- Modify: `frontend/src/api/arxiv.ts`
- Modify: `frontend/src/views/PaperSourcesView.vue`

**Interfaces:**
- Consumes: Task 4 的 `/api/rag/arxiv/generate`（現在要求 body 帶 `project_id`，否則 400）
- Produces: 無（UI 呼叫端，沒有其他任務依賴這裡）

- [ ] **Step 1: 修改 `frontend/src/api/arxiv.ts` 的 `generateFromArxiv`**

```typescript
export async function generateFromArxiv (params: {
  topic: string
  miningResults: Record<string, unknown>
  selectedCandidates: ArxivCandidate[]
  projectId: string
}): Promise<ArxivGenerateResult> {
  const response = await fetch('/api/rag/arxiv/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: params.topic,
      mining_results: params.miningResults,
      selected_candidates: params.selectedCandidates,
      project_id: params.projectId,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as ArxivGenerateResult
}
```

（只改了 `params` 型別多一個 `projectId: string`，跟 `body` 多一個 `project_id` 欄位；其他都不變。）

- [ ] **Step 2: 修改 `frontend/src/views/PaperSourcesView.vue` 的 `handleGenerate`**

原本（第 145-159 行附近）：

```typescript
  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
```

改成：

```typescript
  async function handleGenerate (): Promise<void> {
    if (!miningResults.value) return
    if (!projectId.value) {
      generateError.value = '缺少 project 資訊，請從專案頁面重新進入'
      return
    }
    generating.value = true
    generateError.value = null
    try {
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
        projectId: projectId.value,
      })
      const report = transformArxivResultToPaperReport(result, topic.value)
      paperStore.setGeneratedReport(report)
      router.push(`/paper?project=${projectId.value}`)
    } catch (error) {
```

（只多了一個提早 return 的 guard，跟 `generateFromArxiv` 呼叫多帶 `projectId: projectId.value`；`generateError` 這個 ref 沿用檔案裡已經存在的，不用新增。）

- [ ] **Step 3: Type-check**

```bash
cd frontend && npm run type-check
```

Expected: 無錯誤。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/arxiv.ts frontend/src/views/PaperSourcesView.vue
git commit -m "feat: send project_id when generating a paper from arXiv sources"
```

---

### Task 6: 刪除已被取代的檔案式 `VectorStore`

**Files:**
- Delete: `backend/services/rag/vector_store.py`
- Delete: `backend/tests/test_vector_store_self_heal.py`
- Delete: `backend/scripts/test_rag.sh`

**Interfaces:**
- Consumes: 無（純刪除，前面的任務已經把所有呼叫點換成 `DbVectorStore`）
- Produces: 無

- [ ] **Step 1: 確認沒有其他地方還在 import 舊的 `VectorStore`**

```bash
cd backend && grep -rn "from services.rag.vector_store\|import vector_store\|VectorStore(" --include="*.py" . | grep -v ".venv" | grep -v "services/rag/vector_store.py" | grep -v "tests/test_vector_store_self_heal.py"
```

（排除 `services/rag/vector_store.py` 自己跟 `tests/test_vector_store_self_heal.py`——這兩個檔案本來就會 import 舊的 `VectorStore`，它們是 Step 2 要刪除的對象，不算「其他地方」。）

Expected: 沒有任何輸出（如果有，代表 Task 3 沒改乾淨，要先回頭處理，不能進到下一步）。

- [ ] **Step 2: 刪除檔案**

```bash
git rm backend/services/rag/vector_store.py
git rm backend/tests/test_vector_store_self_heal.py
git rm backend/scripts/test_rag.sh
```

（`test_rag.sh` 是舊的、沒有登入/`project_id` 的 curl 手動測試腳本，子專案 #1 加 `login_required` 時就已經讓它跑不動了，這次 `project_id` 一加會徹底過時；已經有 Task 2 的 `verify_db_vector_store.py` 和 Task 7 的端對端腳本取代它的角色。）

- [ ] **Step 3: 跑整個測試套件確認沒有東西壞掉**

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
```

Expected: 全部 PASS，測試數量比 Task 4 結束時少（因為刪掉了 `test_vector_store_self_heal.py` 的測試）。

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove file-based VectorStore, its test, and the stale unauthenticated curl script (superseded by DbVectorStore)"
```

---

### Task 7: 端對端手動驗證（透過真的 HTTP API，兩個帳號互相隔離）

**Files:**
- Create: `backend/scripts/verify_rag_project_isolation.py`

**Interfaces:**
- Consumes: Task 4 的路由（`/api/rag/upload`、`/search`、`/paper/<id>` DELETE、`/clear`）、`/api/auth/register`、`/api/projects`
- Produces: 無（這是最終驗收腳本，不是其他任務依賴的介面）

- [ ] **Step 1: 寫端對端驗證腳本**

Create `backend/scripts/verify_rag_project_isolation.py`:

```python
"""手動驗證：兩個不同帳號、不同 project，RAG 論文索引完全互相隔離。

執行方式（docker-compose 要先啟動，backend 服務對外開在 5002 → 容器內 5001，
所以從容器內執行用 5001）：
    MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_rag_project_isolation.py

會自建兩個測試帳號、兩個 project、上傳一篇論文，全部是真實 HTTP 請求（跟前端呼叫
的路徑完全一樣）。留下的測試帳號不會自動刪除（沒有帳號刪除 API），但都是明顯的
測試用 email，不影響正常使用者資料。
"""

import os
import uuid

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")


def register_and_login(email: str) -> requests.Session:
    session = requests.Session()
    resp = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"email": email, "password": "test-password-123", "displayName": "RAG isolation test"},
    )
    assert resp.status_code == 200, f"register failed: {resp.status_code} {resp.text}"
    return session


def create_project(session: requests.Session, name: str) -> int:
    resp = session.post(f"{BASE_URL}/api/projects", json={"name": name})
    assert resp.status_code == 200, f"create project failed: {resp.status_code} {resp.text}"
    return resp.json()["result"]["id"]


def check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    suffix = uuid.uuid4().hex[:8]
    session_a = register_and_login(f"rag-isolation-a-{suffix}@test.local")
    session_b = register_and_login(f"rag-isolation-b-{suffix}@test.local")

    project_a = create_project(session_a, "RAG isolation test A")
    project_b = create_project(session_b, "RAG isolation test B")

    upload_resp = session_a.post(
        f"{BASE_URL}/api/rag/upload",
        json={
            "project_id": project_a,
            "title": "Isolation Test Paper",
            "content": (
                "Deep learning models improve medical diagnosis accuracy significantly. "
                "Convolutional neural networks are widely used for image classification tasks."
            ),
            "author": "Test Author",
            "year": "2024",
        },
    )
    check("A 上傳論文成功", upload_resp.status_code == 200 and upload_resp.json().get("success") is True)
    paper_id = upload_resp.json()["result"]["paper_id"]

    search_a = session_a.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_a, "query": "deep learning medical diagnosis", "top_k": 3},
    )
    check(
        "A 在自己的 project 搜得到剛上傳的論文",
        search_a.status_code == 200 and len(search_a.json().get("results", [])) > 0,
    )

    search_b = session_b.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_b, "query": "deep learning medical diagnosis", "top_k": 3},
    )
    check(
        "B 在自己的 project 搜不到 A 上傳的論文（隔離生效）",
        search_b.status_code == 200 and len(search_b.json().get("results", [])) == 0,
    )

    search_cross = session_b.post(
        f"{BASE_URL}/api/rag/search",
        json={"project_id": project_a, "query": "deep learning", "top_k": 3},
    )
    check("B 不能用 A 的 project_id 搜尋（回 404）", search_cross.status_code == 404)

    delete_cross = session_b.delete(
        f"{BASE_URL}/api/rag/paper/{paper_id}", params={"project_id": project_a}
    )
    check("B 不能刪除 A 的論文（回 404）", delete_cross.status_code == 404)

    delete_own = session_a.delete(
        f"{BASE_URL}/api/rag/paper/{paper_id}", params={"project_id": project_a}
    )
    check("A 刪除自己的論文成功", delete_own.status_code == 200 and delete_own.json().get("success") is True)

    session_a.post(f"{BASE_URL}/api/rag/clear", json={"project_id": project_a})
    session_b.post(f"{BASE_URL}/api/rag/clear", json={"project_id": project_b})

    print("\n全部通過。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 確認 `requests` 套件在容器裡可用**

```bash
MSYS_NO_PATHCONV=1 docker exec datamind-backend /app/.venv/bin/python -c "import requests; print('ok')"
```

Expected: 印出 `ok`。如果沒有，執行 `MSYS_NO_PATHCONV=1 docker exec datamind-backend /app/.venv/bin/pip install requests` 補裝（只裝在容器內，不動 `requirements.txt`——這是手動驗證腳本專用的依賴，不是應用程式本身需要的）。

- [ ] **Step 3: 執行端對端驗證**

```bash
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_rag_project_isolation.py
```

Expected: 全部行印出 `[PASS]`，最後印出「全部通過。」。任何一行印出 `[FAIL]` 就代表隔離或擁有權驗證沒有正確生效，要回頭檢查對應的 Task（多半是 Task 4 的路由邏輯）。

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/verify_rag_project_isolation.py
git commit -m "test: add end-to-end manual verification script for RAG project isolation"
```

---

## 完成後的整體驗收

跑一次完整流程確認所有任務串起來沒問題：

```bash
cd backend && .venv/Scripts/python.exe -m pytest tests/ -q
cd frontend && npm run type-check
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_db_vector_store.py
MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/verify_rag_project_isolation.py
```

四個都要全部通過，才算子專案 #2 完成。
