"""_build_section_prompt() 的兩個修正：

1. 引用要精準對應緊接在前面的具體主張（1-2 句），不能整段共用一個引用標記
2. 每個章節要有各自的寫作重點，且明講不要重複別章（尤其「討論」不要炒「實驗結果」的
   數字冷飯，要解讀意義）

不連網：繞過 __init__（不需要 GEMINI_API_KEY），這個方法本身也不用 _store/_reranker。
"""

from services.rag.paper_rag import PaperRAGService


def _build_prompt(section_name: str, local_refs=None):
    service = PaperRAGService.__new__(PaperRAGService)
    return service._build_section_prompt(
        section_name=section_name,
        topic="電信客戶流失預測",
        results_text="（實驗結果摘要）",
        local_refs=local_refs or {},
        language="zh-TW",
    )


class TestCitationGranularity:
    def test_prompt_instructs_citation_scoped_to_nearby_claim(self):
        prompt = _build_prompt("前言")
        assert "整段" in prompt
        assert "1" in prompt and "2" in prompt  # 「1-2 句」之類的用字，不強求逐字比對

    def test_prompt_instructs_separate_citations_for_separate_claims(self):
        prompt = _build_prompt("前言")
        assert "分別標註" in prompt or "各自" in prompt


class TestSectionWritingFocus:
    def test_discussion_section_asks_for_interpretation_not_repetition(self):
        prompt = _build_prompt("討論")
        assert "實驗結果" in prompt
        assert "解讀" in prompt or "意義" in prompt
        assert "重複" in prompt

    def test_results_section_asks_to_stay_objective(self):
        prompt = _build_prompt("實驗結果")
        assert "客觀" in prompt
        assert "解讀留給" in prompt or "留給討論" in prompt
