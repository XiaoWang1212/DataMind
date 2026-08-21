"""VectorStore 在舊索引（沒有 embeddings 或筆數對不上）遇到 transformers backend 時的自癒測試。

不連網：用假的 embedder，不載入真的模型。
"""

import json
from pathlib import Path

import numpy as np
import pytest

from services.rag.chunker import Chunk
from services.rag.vector_store import VectorStore


class FakeTransformersEmbedder:
    backend = "transformers"
    model_name = "fake-model"

    def encode(self, texts):
        # 用文字長度當假向量，方便斷言筆數與內容有沒有對上
        return np.array([[float(len(t))] for t in texts], dtype=np.float32)

    def encode_query(self, query):
        return np.array([1.0], dtype=np.float32)


def write_chunks_only_index(index_dir: Path, chunks: list[Chunk]) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    chunks_data = [
        {
            "chunk_id": c.chunk_id,
            "paper_id": c.paper_id,
            "title": c.title,
            "content": c.content,
            "chunk_index": c.chunk_index,
            "metadata": c.metadata,
        }
        for c in chunks
    ]
    (index_dir / "chunks.json").write_text(json.dumps(chunks_data, ensure_ascii=False), encoding="utf-8")
    (index_dir / "papers.json").write_text("{}", encoding="utf-8")
    # 刻意不寫 embeddings.npy，模擬舊的 tfidf-only 索引


def test_load_reencodes_when_embeddings_file_missing(tmp_path):
    chunks = [
        Chunk(chunk_id="c1", paper_id="p1", title="t", content="hello world", chunk_index=0),
        Chunk(chunk_id="c2", paper_id="p1", title="t", content="foo", chunk_index=1),
    ]
    write_chunks_only_index(tmp_path, chunks)

    store = VectorStore(index_dir=tmp_path, embedder=FakeTransformersEmbedder())

    assert store._embeddings is not None
    assert len(store._embeddings) == len(chunks)
    # search() 不該再因為 None @ ndarray 而炸掉
    results = store.search("query", top_k=2)
    assert len(results) == 2


def test_load_reencodes_when_embeddings_count_mismatches_chunks(tmp_path):
    chunks = [
        Chunk(chunk_id="c1", paper_id="p1", title="t", content="hello world", chunk_index=0),
        Chunk(chunk_id="c2", paper_id="p1", title="t", content="foo", chunk_index=1),
    ]
    write_chunks_only_index(tmp_path, chunks)
    # 只存一筆 embedding，模擬 add() 曾經在筆數不一致狀態下被呼叫過
    np.save(str(tmp_path / "embeddings.npy"), np.array([[1.0]], dtype=np.float32))

    store = VectorStore(index_dir=tmp_path, embedder=FakeTransformersEmbedder())

    assert len(store._embeddings) == len(chunks)
