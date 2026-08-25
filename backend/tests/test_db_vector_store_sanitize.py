"""_sanitize_text 濾掉字串裡的 NUL byte（\\x00）。

PDF/arXiv 抽字有時會殘留 NUL byte，Postgres 的 text 欄位不接受，插入時會噴
`ValueError: A string literal cannot contain NUL (0x00) characters.`，讓整批
chunk insert 因為一筆髒資料就全部失敗（見 add_chunks 的 insertmany）。
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from services.rag.db_vector_store import DbVectorStore  # noqa: E402


def test_sanitize_text_strips_embedded_nul_bytes():
    assert DbVectorStore._sanitize_text("abc\x00def") == "abcdef"


def test_sanitize_text_leaves_clean_text_untouched():
    assert DbVectorStore._sanitize_text("hello world") == "hello world"


def test_sanitize_text_passes_through_none():
    assert DbVectorStore._sanitize_text(None) is None
