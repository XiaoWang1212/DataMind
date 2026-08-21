"""_build_citation_map 的段落級歸屬測試。

不連網：直接呼叫 staticmethod，不建構 PaperRAGService（會需要 GEMINI_API_KEY），
不需要任何外部依賴。
"""

from dataclasses import dataclass

from services.rag.paper_rag import PaperRAGService


@dataclass
class FakeChunk:
    paper_id: str
    content: str


def make_local_refs():
    return {
        1: {
            "global_ref_id": 1,
            "chunk": FakeChunk(paper_id="paper-a", content="空氣品質與心血管疾病的關聯研究"),
            "score": 0.91,
        },
        2: {
            "global_ref_id": 1,  # 跟 local_id=1 同一篇論文，不同 chunk
            "chunk": FakeChunk(paper_id="paper-a", content="PM2.5 濃度與呼吸道發炎反應"),
            "score": 0.85,
        },
        3: {
            "global_ref_id": 2,
            "chunk": FakeChunk(paper_id="paper-b", content="糖尿病患者的血糖控制策略"),
            "score": 0.88,
        },
    }


GLOBAL_REF_LIST = [
    {"ref_id": 1, "title": "Paper A", "author": "Wang", "year": "2024"},
    {"ref_id": 2, "title": "Paper B", "author": "Lee", "year": "2023"},
]


def test_same_paper_cited_in_different_paragraphs_gets_correct_chunk_each_time():
    local_refs = make_local_refs()
    section_text = "第一段引用了空氣品質相關的研究[1]。\n\n第二段引用同一篇論文但不同段落[2]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 2

    para0_sources = citation_map[0]["sources"]
    assert len(para0_sources) == 1
    assert para0_sources[0]["ref_id"] == 1
    assert para0_sources[0]["relevant_chunk"] == "空氣品質與心血管疾病的關聯研究"

    para1_sources = citation_map[1]["sources"]
    assert len(para1_sources) == 1
    assert para1_sources[0]["ref_id"] == 1
    # 這是這次修的核心 bug：兩段引用同一篇論文，但實際引用的 chunk 不同，
    # 修好之前這裡會跟 para0 顯示一模一樣的內容
    assert para1_sources[0]["relevant_chunk"] == "PM2.5 濃度與呼吸道發炎反應"


def test_combo_bracket_format_is_parsed_from_raw_local_id_text():
    """LLM 有時會把多個引用寫成 [1, 3] 這種逗號組合格式，不是分開的 [1][3]。"""
    local_refs = make_local_refs()
    section_text = "同時支持兩個論點[1, 3]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 1
    assert citation_map[0]["cited_ref_ids"] == [1, 2]
    sources_by_ref = {s["ref_id"]: s for s in citation_map[0]["sources"]}
    assert sources_by_ref[1]["relevant_chunk"] == "空氣品質與心血管疾病的關聯研究"
    assert sources_by_ref[2]["relevant_chunk"] == "糖尿病患者的血糖控制策略"


def test_same_paragraph_citing_same_paper_twice_keeps_first_occurrence():
    """同一段落用兩個不同 local_id 重複引用同一篇論文：取文字裡先出現的那個。"""
    local_refs = make_local_refs()
    section_text = "先引用[2]再引用同一篇的另一段[1]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    assert len(citation_map) == 1
    assert citation_map[0]["cited_ref_ids"] == [1]
    assert citation_map[0]["sources"][0]["relevant_chunk"] == "PM2.5 濃度與呼吸道發炎反應"


def test_citation_map_text_uses_global_ref_ids_not_local_ids():
    local_refs = make_local_refs()
    section_text = "第一段引用[1]。\n\n第二段引用[3]。"

    citation_map: list = []
    PaperRAGService._build_citation_map(
        "前言", section_text, local_refs, GLOBAL_REF_LIST, citation_map
    )

    # local_id=1 → global_ref_id=1（不變）、local_id=3 → global_ref_id=2
    assert citation_map[0]["text"] == "第一段引用[1]。"
    assert citation_map[1]["text"] == "第二段引用[2]。"
