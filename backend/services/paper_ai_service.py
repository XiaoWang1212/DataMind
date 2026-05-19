import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class AnalysisInput:
    title: str
    content: str
    focus: str | None = None
    language: str = "zh-TW"


class PaperAIService:
    def __init__(self) -> None:
        provider = os.getenv("PAPER_AI_PROVIDER", "openai").lower()
        self.provider = provider

        if provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
            api_key = os.getenv("OLLAMA_API_KEY", "ollama")
        else:
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY is required when PAPER_AI_PROVIDER=openai. "
                    "Or set PAPER_AI_PROVIDER=ollama to use local LLM."
                )

        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _build_prompt(self, analysis_input: AnalysisInput) -> str:
        focus_text = (
            analysis_input.focus or "整體技術架構、核心方法、實驗設計、限制與風險"
        )
        return (
            f"你是一位資深研究工程師。請只根據提供的論文內容做技術解讀。\\n"
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

    def analyze(self, analysis_input: AnalysisInput) -> dict:
        prompt = self._build_prompt(analysis_input)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "你是嚴謹且可執行導向的論文技術分析助手。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        answer = response.choices[0].message.content if response.choices else ""
        usage = getattr(response, "usage", None)

        return {
            "provider": self.provider,
            "model": self.model,
            "analysis": answer or "",
            "usage": {
                "prompt_tokens": (
                    getattr(usage, "prompt_tokens", None) if usage else None
                ),
                "completion_tokens": (
                    getattr(usage, "completion_tokens", None) if usage else None
                ),
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            },
        }


def truncate_content(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\\n\\n[內容過長，已截斷以避免超出模型上下文限制]"
