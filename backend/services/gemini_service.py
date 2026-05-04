import os
import logging
import json
import re
from dataclasses import dataclass

import google.generativeai as genai

logger = logging.getLogger(__name__)


@dataclass
class AnalysisInput:
    title: str
    content: str
    focus: str | None = None
    language: str = "zh-TW"
    mode: str = "summary"


class GeminiService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required.")

        genai.configure(api_key=api_key)
        self.requested_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_name = self.requested_model
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def _build_prompt(self, analysis_input: AnalysisInput) -> str:
        focus_text = (
            analysis_input.focus or "整體技術架構、核心方法、實驗設計、限制與風險"
        )

        if analysis_input.mode == "extract":
            return (
                "你是論文資訊抽取助手。請只根據提供內容抽取，不可臆測。\\n"
                f"輸出語言：{analysis_input.language}\\n"
                "請只輸出 JSON（不要 markdown、不要多餘文字），格式如下：\\n"
                "{\\n"
                '  "variable_definitions": [\\n'
                "    {\\n"
                '      "name": "變數名稱",\\n'
                '      "type": "類別/連續/二元/未知",\\n'
                '      "definition": "論文中對該變數的定義",\\n'
                '      "role": "feature/target/control/unknown",\\n'
                '      "evidence": "對應原文句子",\\n'
                '      "confidence": 0.0\\n'
                "    }\\n"
                "  ],\\n"
                '  "model_usage": [\\n'
                "    {\\n"
                '      "model_name": "模型名稱",\\n'
                '      "task": "分類/回歸/其他",\\n'
                '      "why_used": "使用原因",\\n'
                '      "input_features": ["特徵1"],\\n'
                '      "target": "目標變數",\\n'
                '      "training_strategy": "訓練/驗證方式",\\n'
                '      "hyperparameters": {"參數": "值"},\\n'
                '      "metrics": [{"name": "Precision", "value": "若有"}],\\n'
                '      "evidence": "對應原文句子",\\n'
                '      "confidence": 0.0\\n'
                "    }\\n"
                "  ],\\n"
                '  "dataset": {"source": "", "size": "", "imbalance_handling": "", "split": ""},\\n'
                '  "notes": ["若資訊不足請明確寫出不足點"]\\n'
                "}\\n"
                "規則：\\n"
                "1) 沒看到就填 unknown 或空陣列，不可杜撰。\\n"
                "2) confidence 範圍 0~1。\\n"
                "3) evidence 必須是原文片段。\\n\\n"
                "4) variable_definitions 最多回傳 15 筆，優先關鍵變數。\\n"
                "5) model_usage 最多回傳 5 筆，優先主模型。\\n"
                "6) evidence 每筆僅保留 1~2 句最關鍵原文。\\n\\n"
                f"特別關注：{focus_text}\\n"
                f"論文標題：{analysis_input.title}\\n"
                "--- 論文內容開始 ---\\n"
                f"{analysis_input.content}\\n"
                "--- 論文內容結束 ---"
            )

        return (
            "你是一位資深研究工程師。請只根據提供的論文內容做技術解讀，不要捏造來源。\\n"
            f"輸出語言：{analysis_input.language}\\n"
            "請輸出以下段落（使用清楚標題）：\\n"
            "1) 研究目標與問題定義\\n"
            "2) 核心技術方法（演算法/模型/流程）\\n"
            "3) 關鍵實驗設計與評估指標\\n"
            "4) 主要技術貢獻（條列）\\n"
            "5) 可能限制、假設與實務風險\\n"
            "6) 給工程實作團隊的落地建議（條列）\\n"
            "7) 三行結論\\n\\n"
            f"特別關注：{focus_text}\\n"
            f"論文標題：{analysis_input.title}\\n"
            "--- 論文內容開始 ---\\n"
            f"{analysis_input.content}\\n"
            "--- 論文內容結束 ---"
        )

    def _safe_parse_json(self, text: str) -> dict | None:
        raw = text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        fenced = re.sub(r"^```(?:json)?\\s*", "", raw, flags=re.IGNORECASE)
        fenced = re.sub(r"\\s*```$", "", fenced)
        try:
            return json.loads(fenced.strip())
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", fenced)
        if match:
            candidate = match.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None
        return None

    def _normalize_to_json(self, raw_text: str) -> dict | None:
        normalize_prompt = (
            "請把下面內容轉為『合法 JSON』，只輸出 JSON 本體，不要 markdown。"
            "若欄位缺失請保留原有結構並用 unknown 或空陣列。\n\n"
            "--- 原始內容開始 ---\n"
            f"{raw_text}\n"
            "--- 原始內容結束 ---"
        )

        response = self.model.generate_content(
            normalize_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=2048,
            ),
        )
        normalized = getattr(response, "text", "") or ""
        return self._safe_parse_json(normalized)

    def _is_sparse_extract(self, extracted: dict | None) -> bool:
        if not isinstance(extracted, dict):
            return True
        variables = extracted.get("variable_definitions") or []
        models = extracted.get("model_usage") or []
        return len(variables) < 3 or len(models) < 1

    def _retry_full_extract(self, analysis_input: AnalysisInput) -> dict | None:
        retry_prompt = (
            "請重新做一次高完整度抽取，並只輸出合法 JSON。\n"
            "重點：\n"
            "1) variable_definitions 至少 8 筆（若原文不足可少於 8，但要在 notes 說明）\n"
            "2) model_usage 需列出所有有提到的模型\n"
            "3) 每筆保留 evidence（短句）\n"
            "4) 不可杜撰，缺失用 unknown\n\n"
            "JSON 格式：\n"
            "{\n"
            '  "variable_definitions": [{"name":"","type":"","definition":"","role":"","evidence":"","confidence":0.0}],\n'
            '  "model_usage": [{"model_name":"","task":"","why_used":"","input_features":[],"target":"","training_strategy":"","hyperparameters":{},"metrics":[],"evidence":"","confidence":0.0}],\n'
            '  "dataset": {"source":"","size":"","imbalance_handling":"","split":""},\n'
            '  "notes": []\n'
            "}\n\n"
            f"論文標題：{analysis_input.title}\n"
            f"特別關注：{analysis_input.focus or '變數定義與模型使用'}\n"
            "--- 論文內容開始 ---\n"
            f"{analysis_input.content}\n"
            "--- 論文內容結束 ---"
        )

        response = self.model.generate_content(
            retry_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        retry_text = getattr(response, "text", "") or ""
        return self._safe_parse_json(retry_text)

    def analyze(self, analysis_input: AnalysisInput) -> dict:
        prompt = self._build_prompt(analysis_input)

        generation_kwargs = {
            "temperature": 0.2,
        }
        if analysis_input.mode == "extract":
            generation_kwargs["response_mime_type"] = "application/json"
            generation_kwargs["max_output_tokens"] = 2048

        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(**generation_kwargs),
        )

        answer = getattr(response, "text", "") or ""
        extracted = None
        extracted_raw = None
        if analysis_input.mode == "extract" and answer:
            extracted = self._safe_parse_json(answer)
            if extracted is None:
                logger.warning("extract JSON parse failed, trying normalization pass")
                extracted = self._normalize_to_json(answer)
            if self._is_sparse_extract(extracted):
                logger.warning("extract result is sparse, trying full extraction retry")
                retried = self._retry_full_extract(analysis_input)
                if not self._is_sparse_extract(retried):
                    extracted = retried
            if extracted is None:
                extracted_raw = answer.strip()

        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata

        return {
            "provider": "gemini",
            "model": self.model_name,
            "mode": analysis_input.mode,
            "analysis": answer,
            "extracted": extracted,
            "extracted_raw": extracted_raw,
            "usage": {
                "prompt_tokens": (
                    getattr(usage, "prompt_token_count", None) if usage else None
                ),
                "completion_tokens": (
                    getattr(usage, "candidates_token_count", None) if usage else None
                ),
                "total_tokens": (
                    getattr(usage, "total_token_count", None) if usage else None
                ),
            },
        }


def truncate_content(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\\n\\n[內容過長，已截斷以避免超出模型上下文限制]"
