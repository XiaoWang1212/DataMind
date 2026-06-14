import re
import uuid
from dataclasses import dataclass, field
from typing import List


@dataclass
class Chunk:
    chunk_id: str
    paper_id: str
    title: str
    content: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class TextChunker:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        text: str,
        paper_id: str,
        title: str,
        metadata: dict | None = None,
    ) -> List[Chunk]:
        if metadata is None:
            metadata = {}

        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        chunks: List[Chunk] = []
        chunk_index = 0
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))

            # Prefer breaking at a sentence boundary (Chinese or English)
            if end < len(text):
                for sep in ["。", "！", "？", ".\n", "!\n", "?\n", ". ", "! ", "? "]:
                    pos = text.rfind(sep, start + self.chunk_size // 2, end)
                    if pos != -1:
                        end = pos + len(sep)
                        break

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        chunk_id=str(uuid.uuid4()),
                        paper_id=paper_id,
                        title=title,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        metadata=dict(metadata),
                    )
                )
                chunk_index += 1

            next_start = end - self.overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunks
