"""生成論文的中英文切換：
1. `_section_label()` 依語言把內部中文 canonical key 轉成顯示標籤
2. `_build_section_prompt()` 英文模式要輸出英文寫作指示，中文模式行為不變（回歸）
3. `_assemble_paper()`/`_build_citation_report()` 依語言輸出對應標題文字
4. 最關鍵的回歸測試：citation_map 的 section 欄位必須跟 _assemble_paper() 組出來的
   標題文字逐字一致——這是英文模式下「引用配對全部失效」這個 bug 的正確性契約

不連網：全部直接呼叫 staticmethod，或用 `PaperRAGService.__new__(PaperRAGService)`
繞過 `__init__`（不需要 GEMINI_API_KEY），跟現有測試檔案同一套模式。
"""

from services.rag.paper_rag import PaperRAGService


def _build_prompt(section_name: str, language: str, local_refs=None):
    service = PaperRAGService.__new__(PaperRAGService)
    return service._build_section_prompt(
        section_name=section_name,
        topic="Telecom Customer Churn Prediction",
        results_text="(experiment result summary)",
        local_refs=local_refs or {},
        language=language,
    )


class TestSectionLabel:
    def test_maps_known_section_to_english_label(self):
        assert PaperRAGService._section_label("前言", "en") == "Introduction"
        assert PaperRAGService._section_label("結論", "en") == "Conclusion"

    def test_unknown_section_falls_back_to_original_string(self):
        assert PaperRAGService._section_label("附錄", "en") == "附錄"

    def test_non_english_language_returns_original_chinese_key(self):
        assert PaperRAGService._section_label("前言", "zh-TW") == "前言"


class TestSectionPromptEnglish:
    def test_english_prompt_instructs_english_output(self):
        prompt = _build_prompt("前言", "en")
        assert "Language: English" in prompt
        assert "Introduction" in prompt
        assert "前言" not in prompt

    def test_english_prompt_keeps_citation_granularity_rules(self):
        prompt = _build_prompt("前言", "en")
        assert "1-2 sentences" in prompt
        assert "[1][2]" in prompt

    def test_chinese_prompt_unaffected_by_dispatcher_refactor(self):
        prompt = _build_prompt("前言", "zh-TW")
        assert "語言：繁體中文" in prompt
        assert "「前言」章節" in prompt


class TestAssemblePaperLanguage:
    def test_english_mode_uses_english_section_and_reference_headings(self):
        markdown = PaperRAGService._assemble_paper(
            topic="Telecom Churn",
            structure=["摘要", "前言"],
            sections_text={"摘要": "Summary text.", "前言": "Intro text."},
            global_ref_list=[{"ref_id": 1, "author": "Smith, J.", "year": 2020, "title": "A Paper"}],
            language="en",
        )
        assert "## Abstract" in markdown
        assert "## Introduction" in markdown
        assert "## References" in markdown
        assert "## 參考文獻" not in markdown

    def test_chinese_mode_unaffected_by_language_param(self):
        markdown = PaperRAGService._assemble_paper(
            topic="電信客戶流失",
            structure=["摘要", "前言"],
            sections_text={"摘要": "摘要內容。", "前言": "前言內容。"},
            global_ref_list=[{"ref_id": 1, "author": "Smith, J.", "year": 2020, "title": "A Paper"}],
            language="zh-TW",
        )
        assert "## 摘要" in markdown
        assert "## 前言" in markdown
        assert "## 參考文獻" in markdown


class TestCitationReportLanguage:
    def test_english_mode_uses_english_labels(self):
        citation_map = [{
            "section": "Introduction",
            "paragraph_index": 0,
            "text": "A claim[1].",
            "cited_ref_ids": [1],
            "sources": [{"ref_id": 1, "relevant_chunk": "source text", "similarity_score": 0.9}],
        }]
        report = PaperRAGService._build_citation_report(
            global_ref_list=[{"ref_id": 1, "author": "Smith, J.", "year": 2020, "title": "A Paper"}],
            citation_map=citation_map,
            language="en",
        )
        assert "# Citation Cross-Reference Report" in report
        assert "### Introduction · Paragraph 0" in report
        assert "**Cited excerpt:**" in report
        assert "**Source excerpt:**" in report
        assert "**Similarity:**" in report

    def test_chinese_mode_unaffected_by_language_param(self):
        citation_map = [{
            "section": "前言",
            "paragraph_index": 0,
            "text": "一個主張[1]。",
            "cited_ref_ids": [1],
            "sources": [{"ref_id": 1, "relevant_chunk": "原文摘錄", "similarity_score": 0.9}],
        }]
        report = PaperRAGService._build_citation_report(
            global_ref_list=[{"ref_id": 1, "author": "Smith, J.", "year": 2020, "title": "A Paper"}],
            citation_map=citation_map,
            language="zh-TW",
        )
        assert "# 引用對照報告" in report
        assert "### 前言 · 第 0 段" in report
        assert "**引用內文：**" in report

    def test_no_citations_message_matches_language(self):
        assert PaperRAGService._build_citation_report([], [], "en") == "(No references were cited in this paper.)"
        assert PaperRAGService._build_citation_report([], [], "zh-TW") == "（本文未實際引用任何參考文獻）"


class TestCitationMapHeadingConsistency:
    """回歸測試：citation_map 的 section 欄位必須跟 _assemble_paper() 組出來的標題
    文字逐字一致——否則前端 paperTransform.ts 用字串比對配引用來源會全部失敗。"""

    def test_resolved_section_label_matches_assembled_heading_in_english_mode(self):
        section_name = "前言"
        language = "en"
        section_label = PaperRAGService._section_label(section_name, language)

        citation_map: list = []
        local_refs = {1: {
            "global_ref_id": 1,
            "chunk": type("Chunk", (), {"paper_id": "p1", "content": "source excerpt"})(),
            "score": 0.9,
        }}
        PaperRAGService._build_citation_map(
            section_label, "A claim[1].", local_refs,
            [{"ref_id": 1, "title": "A Paper"}], citation_map,
        )

        markdown = PaperRAGService._assemble_paper(
            topic="Topic",
            structure=[section_name],
            sections_text={section_name: "A claim[1]."},
            global_ref_list=[],
            language=language,
        )
        assembled_heading = markdown.split("\n\n---\n\n")[1].split("\n\n")[0].removeprefix("## ")

        assert citation_map[0]["section"] == assembled_heading == "Introduction"
