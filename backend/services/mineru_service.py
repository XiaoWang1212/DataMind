import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AnalysisInput:
    title: str
    content: Optional[str] = None
    file_bytes: Optional[bytes] = None
    file_name: Optional[str] = None
    focus: Optional[str] = None
    language: str = "zh-TW"
    mode: str = "summary"


class MinerUService:
    def __init__(self) -> None:
        self.model_name = os.getenv("MINERU_MODEL", "mineru-default")
        self.backend = os.getenv("MINERU_BACKEND", "hybrid-auto-engine")
        self.lang_list = os.getenv("MINERU_LANG_LIST", "ch").split(",")
        self.parse_method = os.getenv("MINERU_PARSE_METHOD", "auto")

    def _call_mineru(self, file_bytes: bytes, file_name: str) -> dict:
        try:
            from starlette.testclient import TestClient
            from mineru.cli.fast_api import app as mineru_app
        except ImportError as exc:
            raise RuntimeError(
                "MinerU package is not installed. Install mineru[all] in the backend environment."
            ) from exc

        with TestClient(mineru_app) as client:
            files = [
                (
                    "files",
                    (
                        file_name,
                        file_bytes,
                        "application/octet-stream",
                    ),
                )
            ]
            data = {
                "lang_list": [lang.strip() for lang in self.lang_list if lang.strip()],
                "backend": self.backend,
                "parse_method": self.parse_method,
                "formula_enable": "true",
                "table_enable": "true",
                "return_md": "true",
                "return_middle_json": "false",
                "return_model_output": "false",
                "return_content_list": "false",
                "return_images": "false",
                "response_format_zip": "false",
                "return_original_file": "false",
                "start_page_id": "0",
                "end_page_id": "99999",
            }

            response = client.post("/file_parse", data=data, files=files)
            if response.status_code != 200:
                raise RuntimeError(
                    f"MinerU package parse error: {response.status_code} {response.text}"
                )

            return response.json()

    def analyze(self, analysis_input: AnalysisInput) -> dict:
        if analysis_input.file_bytes is not None:
            file_name = analysis_input.file_name or "input.txt"
            response = self._call_mineru(analysis_input.file_bytes, file_name)
        elif analysis_input.content is not None:
            file_name = f"{analysis_input.title or 'input'}.txt"
            response = self._call_mineru(
                analysis_input.content.encode("utf-8"),
                file_name,
            )
        else:
            raise ValueError(
                "Either content or file_bytes must be provided for MinerU analysis."
            )

        return {
            "provider": "mineru",
            "model": self.model_name,
            "mode": analysis_input.mode,
            "request": {
                "backend": self.backend,
                "parse_method": self.parse_method,
                "title": analysis_input.title,
                "focus": analysis_input.focus,
            },
            "response": response,
        }


def truncate_content(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[內容過長，已截斷以避免超出模型上下文限制]"
