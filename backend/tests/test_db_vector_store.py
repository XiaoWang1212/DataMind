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

    def test_metadata_omits_keys_when_author_year_arxiv_id_all_none(self):
        chunk = DbVectorStore._row_to_chunk(
            _fake_chunk_row(), _fake_paper_row(author=None, year=None, arxiv_id=None),
        )
        assert "author" not in chunk.metadata
        assert "year" not in chunk.metadata
        assert "arxiv_id" not in chunk.metadata
        assert "journal" not in chunk.metadata
