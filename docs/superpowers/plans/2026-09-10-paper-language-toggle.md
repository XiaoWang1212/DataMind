# 論文生成中英文切換 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓「生成論文」的 arXiv 流程支援使用者在生成前選擇繁體中文或 English，選英文時整份論文（正文、章節標題、參考文獻、引用對照報告）全部輸出英文，且不影響現有中文生成行為。

**Architecture:** 後端 `PaperRAGService` 依 `language` 參數分流出中/英兩份完整的章節寫作 prompt，並用一份共用的「章節顯示標籤」對照表統一「引用地圖裡的段落歸屬字串」跟「組裝出的標題文字」，避免兩者語言不一致導致前端引用配對失效。前端新增語言選單，把選到的值一路帶到後端 API，並把「判斷 markdown 裡哪個 block 是參考文獻」的邏輯從「比對中文標題字串」改成「用已知的正文章節數量切片」，讓這個判斷不再綁死任何語言。

**Tech Stack:** Flask + Python（後端 `backend/services/rag/paper_rag.py`、`backend/routes/rag.py`）；Vue 3 `<script setup>` + TypeScript（前端）。

## Global Constraints

- 只支援「生成前選語言」，不支援「已生成內容事後中英互換」——一份論文從生成到編輯完成只存在單一語言版本。
- 選英文時，正文、章節標題、參考文獻標題、引用對照報告的標籤文字全部輸出英文；不是機械式中翻英，是用英文學術寫作慣例重寫 prompt 指示。
- 章節顯示標籤對照表（僅用於顯示，不影響內部 key）：`摘要→Abstract`、`前言→Introduction`、`研究方法→Methods`、`實驗結果→Results`、`討論→Discussion`、`結論→Conclusion`。
- `_DEFAULT_STRUCTURE`、`_SECTION_WORD_TARGETS`、`_SECTION_QUERIES`、`_SECTION_WRITING_FOCUS`、`_SECTION_TOP_K` 這些內部 dict 的 key 維持中文不變，不建立英文版（它們是 RAG 檢索/寫作指示用的內部實作細節，使用者看不到）。
- **關鍵正確性要求**：`citation_map` 裡每一筆的 `section` 欄位，必須跟 `_assemble_paper()` 組出來的 `## {heading}` 標題文字逐字相同（透過同一個 `_section_label(section_name, language)` helper 算出），因為前端是用字串相等比對這兩者來決定引用來源要掛在哪個段落上。
- 前端判斷「`paper_markdown` 裡哪些 heading block 是正文、哪個是參考文獻」，一律用後端回傳的 `sections_generated.length` 做切片，不比對任何語言相關的標題文字。
- 語言選單預設值為 `en`；後端路由讀不到 `language` 時 fallback 為 `"zh-TW"`（維持向後相容）。
- 不動的部分：`/api/rag/generate-paper` 路由（前端目前沒有呼叫，不用補語言選單串接）、`_build_score_prompt()`/`_JOURNAL_RUBRICS` 期刊評分評語（維持中文）、`_SECTION_QUERIES` 的 RAG 查詢語言（維持中文）。

---

### Task 1: 後端 `PaperRAGService` 依語言分流生成內容

**Files:**
- Modify: `backend/services/rag/paper_rag.py:77`（插入 `_SECTION_LABELS_EN`）
- Modify: `backend/services/rag/paper_rag.py:265-347`（`generate_paper()` 章節迴圈與收尾）
- Modify: `backend/services/rag/paper_rag.py:1206-1255`（`_build_section_prompt` 拆成中英分流 + 共用 ref block helper）
- Modify: `backend/services/rag/paper_rag.py:1377-1411`（`_build_citation_report` 加 `language` 參數）
- Modify: `backend/services/rag/paper_rag.py:1416-1439`（`_assemble_paper` 加 `language` 參數）
- Test: `backend/tests/test_paper_rag_language.py`（新檔案）

**Interfaces:**
- Consumes：現有 `PaperRAGService._build_citation_map(section, section_text, local_refs, global_ref_list, citation_map)`（staticmethod，簽章不變，本任務只改「呼叫時傳什麼字串當 `section`」，不改這個方法本身）。
- Produces：
  - `PaperRAGService._section_label(section_name: str, language: str) -> str`（staticmethod，供 Task 1 內部與未來其他任務參考；英文模式回傳 `_SECTION_LABELS_EN` 對照後的英文標籤，找不到就回傳原字串；非英文回傳原字串）。
  - `PaperRAGService._build_section_prompt(self, section_name, topic, results_text, local_refs, language) -> str`（既有簽章不變，內部改為 dispatcher）。
  - `PaperRAGService._assemble_paper(topic, structure, sections_text, global_ref_list, language) -> str`（staticmethod，新增最後一個參數 `language`）。
  - `PaperRAGService._build_citation_report(global_ref_list, citation_map, language) -> str`（staticmethod，新增最後一個參數 `language`）。
  - `generate_paper()` 的回傳形狀不變（`paper_markdown`/`citation_map`/`references`/`citation_report`/`sections_generated`/`usage`），Task 2 直接沿用。

- [ ] **Step 1: 讀現有測試，確認起點**

現有的 `backend/tests/test_paper_rag_section_prompt.py`、`backend/tests/test_paper_rag_citation_map.py` 都是直接呼叫 `PaperRAGService` 的私有方法（用 `PaperRAGService.__new__(PaperRAGService)` 繞過 `__init__`，不需要 `GEMINI_API_KEY`）。本任務新增的測試延續同一個模式。

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_paper_rag_section_prompt.py tests/test_paper_rag_citation_map.py -v"`
Expected: 現有測試全部 PASS（這是本任務開始前的基準線，本任務結束後要再跑一次確認沒有壞掉）。

- [ ] **Step 2: 寫新測試檔案，涵蓋英文 prompt、標題切換、citation_map/heading 一致性**

建立 `backend/tests/test_paper_rag_language.py`：

```python
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
```

- [ ] **Step 3: 執行測試，確認全部失敗（方法還不存在）**

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_paper_rag_language.py -v"`
Expected: 全部 FAIL 或 ERROR（`_section_label` 不存在、`_assemble_paper`/`_build_citation_report` 還不接受 `language` 這個位置的參數等）。

- [ ] **Step 4: 插入 `_SECTION_LABELS_EN` 對照表**

在 `backend/services/rag/paper_rag.py:77`（`_DEFAULT_STRUCTURE = [...]` 那一行）之後插入：

```python

# 章節顯示標籤（僅用於輸出文字，內部 RAG 查詢/寫作指示的 key 維持中文不變）
_SECTION_LABELS_EN: Dict[str, str] = {
    "摘要": "Abstract",
    "前言": "Introduction",
    "研究方法": "Methods",
    "實驗結果": "Results",
    "討論": "Discussion",
    "結論": "Conclusion",
}
```

- [ ] **Step 5: 新增 `_section_label()` staticmethod**

插入在現有的 `_build_section_prompt` 方法（此時還沒被 Step 6 替換掉）正上方：

```python
    @staticmethod
    def _section_label(section_name: str, language: str) -> str:
        if language == "en":
            return _SECTION_LABELS_EN.get(section_name, section_name)
        return section_name
```

- [ ] **Step 6: 把 `_build_section_prompt` 拆成 dispatcher + 中/英兩份完整實作**

把 `backend/services/rag/paper_rag.py` 裡現有的 `_build_section_prompt` 整個方法（檔案最初的第 1206-1255 行；Step 4 在檔案前段插入了 `_SECTION_LABELS_EN`，實際行號會往後移，請用方法內容搜尋定位）替換成以下五個方法（`_build_reference_block` 是抽出來的共用邏輯，中英文共用同一份，內容不需要翻譯——它是內部 prompt 素材，不是使用者看到的輸出）：

```python
    @staticmethod
    def _build_reference_block(local_refs: Dict[int, dict]) -> str:
        ref_lines = [
            f"[{lid}] 論文：《{info['chunk'].title}》\n"
            f"     摘錄：{info['chunk'].content[:400]}"
            for lid, info in local_refs.items()
        ]
        return (
            "\n\n".join(ref_lines)
            if ref_lines
            else "（目前論文庫中無相關參考文獻，請根據一般醫學知識撰寫）"
        )

    def _build_section_prompt(
        self,
        section_name: str,
        topic: str,
        results_text: str,
        local_refs: Dict[int, dict],
        language: str,
    ) -> str:
        if language == "en":
            return self._build_section_prompt_en(section_name, topic, results_text, local_refs)
        return self._build_section_prompt_zh(section_name, topic, results_text, local_refs)

    def _build_section_prompt_zh(
        self,
        section_name: str,
        topic: str,
        results_text: str,
        local_refs: Dict[int, dict],
    ) -> str:
        target = _SECTION_WORD_TARGETS.get(section_name, 600)
        writing_focus = _SECTION_WRITING_FOCUS.get(section_name, "")
        ref_block = self._build_reference_block(local_refs)

        return (
            f"你是醫學資料科學領域的學術論文撰寫助手。"
            f"請根據以下資料，以繁體中文撰寫論文的「{section_name}」章節。\n\n"
            f"【研究主題】\n{topic}\n\n"
            f"【本章節寫作重點】\n{writing_focus}\n\n"
            f"【DataMind 資料探勘實驗結果】\n{results_text}\n\n"
            f"【可引用的參考文獻】\n"
            f"撰寫時，請在引用他人研究、方法或發現時，"
            f"於句末加入對應的引用標記（如 [1]、[2][3]）。\n\n"
            f"{ref_block}\n\n"
            f"【撰寫要求】\n"
            f"- 語言：繁體中文\n"
            f"- 目標字數：約 {target} 字\n"
            f"- 格式比照國際學術期刊論文（IMRaD）之標準寫作方式：以連貫的正式書面語段落敘述，"
            f"段落內部須為連續文字，不可插入條列項目、編號清單或子標題\n"
            f"- 學術寫作風格，使用正式用語與被動語態，避免口語化表達\n"
            f"- 禁止使用任何 Markdown 語法符號，包括 *、-、#、反引號、粗體標記；"
            f"提及資料前處理步驟或參數名稱時，請以中文敘述融入句子（例如「以平均值填補缺失值」），"
            f"不要直接照抄英文程式碼識別字或加上反引號\n"
            f"- 引用規則：每個引用標記只對應緊接在其前面的 1 到 2 句具體主張或數據，"
            f"不可讓一個引用標記涵蓋整段文字；如果同一段落有多個由不同來源支持的主張，"
            f"請在各自的主張後面分別標註引用，不要把整段的引用集中放在段落最後\n"
            f"- 如需在同一個主張後引用多篇文獻，請以相鄰獨立括號表示（如 [1][2]），"
            f"禁止在同一括號內以逗號列出多個編號（如 [1, 2] 為不允許的格式）\n"
            f"- 僅輸出「{section_name}」的段落內文，不需要章節標題\n"
            f"- 段落間以空行分隔\n\n"
            f"請直接輸出文章內容："
        )

    def _build_section_prompt_en(
        self,
        section_name: str,
        topic: str,
        results_text: str,
        local_refs: Dict[int, dict],
    ) -> str:
        target = _SECTION_WORD_TARGETS.get(section_name, 600)
        writing_focus = _SECTION_WRITING_FOCUS.get(section_name, "")
        ref_block = self._build_reference_block(local_refs)
        label = self._section_label(section_name, "en")

        return (
            f"You are an academic writing assistant specializing in medical data science.\n"
            f"Based on the following materials, write the \"{label}\" section of an "
            f"academic paper in English.\n\n"
            f"[Research Topic]\n{topic}\n\n"
            f"[Writing Focus for This Section]\n{writing_focus}\n\n"
            f"[DataMind Data Mining Experiment Results]\n{results_text}\n\n"
            f"[Citable References]\n"
            f"When citing prior research, methods, or findings, add the corresponding "
            f"citation marker at the end of the sentence (e.g. [1], [2][3]).\n\n"
            f"{ref_block}\n\n"
            f"[Writing Requirements]\n"
            f"- Language: English\n"
            f"- Target length: approximately {target} words\n"
            f"- Follow the standard writing conventions of international academic "
            f"journals (IMRaD): coherent, formal prose paragraphs; do not insert bullet "
            f"points, numbered lists, or sub-headings within a paragraph\n"
            f"- Use a formal academic register and passive voice where appropriate; "
            f"avoid colloquial phrasing\n"
            f"- Do not use any Markdown syntax, including *, -, #, backticks, or bold "
            f"markers; when referring to preprocessing steps or parameter names, "
            f"describe them in plain English prose (e.g. \"missing values were imputed "
            f"with the mean\") rather than copying code identifiers or wrapping them in "
            f"backticks\n"
            f"- Citation rule: each citation marker must correspond only to the 1-2 "
            f"sentences of specific claims or data immediately preceding it — a single "
            f"citation marker must not cover an entire paragraph; if a paragraph "
            f"contains multiple claims supported by different sources, cite each claim "
            f"separately right after it instead of grouping all citations at the end of "
            f"the paragraph\n"
            f"- When citing multiple references for the same claim, use adjacent "
            f"separate brackets (e.g. [1][2]); do not list multiple numbers inside one "
            f"bracket separated by commas (e.g. [1, 2] is not allowed)\n"
            f"- Output only the body text of the \"{label}\" section — do not include a "
            f"section heading\n"
            f"- Separate paragraphs with a blank line\n\n"
            f"Please output the section content directly:"
        )
```

- [ ] **Step 7: `_assemble_paper` 加上 `language` 參數**

把 `backend/services/rag/paper_rag.py` 裡現有的 `_assemble_paper`（檔案最初的第 1416-1439 行；前面幾個 Step 已經改動過檔案前段，實際行號會往後移，請用方法內容搜尋定位）替換成：

```python
    @staticmethod
    def _assemble_paper(
        topic: str,
        structure: List[str],
        sections_text: Dict[str, str],
        global_ref_list: List[dict],
        language: str,
    ) -> str:
        parts = [f"# {topic}"]

        for sec in structure:
            text = sections_text.get(sec, "")
            if text:
                label = PaperRAGService._section_label(sec, language)
                parts.append(f"## {label}\n\n{text}")

        # APA 格式參考文獻
        if global_ref_list:
            ref_lines = []
            for ref in global_ref_list:
                author = ref.get("author", "Unknown Author")
                year = ref.get("year", "n.d.")
                title = ref.get("title", "Untitled")
                ref_lines.append(f"[{ref['ref_id']}] {author} ({year}). {title}.")
            heading = "References" if language == "en" else "參考文獻"
            parts.append(f"## {heading}\n\n" + "\n\n".join(ref_lines))

        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 8: `_build_citation_report` 加上 `language` 參數**

把 `backend/services/rag/paper_rag.py` 裡現有的 `_build_citation_report`（檔案最初的第 1377-1411 行；前面幾個 Step 已經改動過檔案前段，實際行號會往後移，請用方法內容搜尋定位）替換成：

```python
    @staticmethod
    def _build_citation_report(
        global_ref_list: List[dict],
        citation_map: List[dict],
        language: str,
    ) -> str:
        """
        依參考文獻分組，記錄文章中每一段引用內文對應到該文獻的哪一段原文摘錄。
        僅包含實際被引用（citation_map 中出現過）的文獻。
        """
        if not global_ref_list:
            return (
                "(No references were cited in this paper.)"
                if language == "en"
                else "（本文未實際引用任何參考文獻）"
            )

        if language == "en":
            parts = [
                "# Citation Cross-Reference Report",
                "",
                "Records every citation in the body text and the source excerpt it corresponds to.",
                "",
            ]
        else:
            parts = ["# 引用對照報告", "", "記錄論文正文中每一處引用，對應到參考文獻原文的哪一段內容。", ""]

        for ref in global_ref_list:
            rid = ref["ref_id"]
            author = ref.get("author", "Unknown Author")
            year = ref.get("year", "n.d.")
            title = ref.get("title", "Untitled")
            parts.append(f"## [{rid}] {author} ({year}). {title}")
            parts.append("")

            entries = [
                entry for entry in citation_map if rid in entry["cited_ref_ids"]
            ]
            for entry in entries:
                src = next((s for s in entry["sources"] if s["ref_id"] == rid), None)
                if language == "en":
                    parts.append(f"### {entry['section']} · Paragraph {entry['paragraph_index']}")
                    parts.append(f"**Cited excerpt:** {entry['text']}")
                    if src and src.get("relevant_chunk"):
                        parts.append(f"**Source excerpt:** {src['relevant_chunk']}")
                    if src and src.get("similarity_score") is not None:
                        parts.append(f"**Similarity:** {src['similarity_score']}")
                else:
                    parts.append(f"### {entry['section']} · 第 {entry['paragraph_index']} 段")
                    parts.append(f"**引用內文：** {entry['text']}")
                    if src and src.get("relevant_chunk"):
                        parts.append(f"**對應原文摘錄：** {src['relevant_chunk']}")
                    if src and src.get("similarity_score") is not None:
                        parts.append(f"**相似度：** {src['similarity_score']}")
                parts.append("")

        return "\n".join(parts)
```

- [ ] **Step 9: `generate_paper()` 串接 — 傳 `language` 給 `_assemble_paper`/`_build_citation_report`，並修正 citation_map 的 section 一致性**

在 `backend/services/rag/paper_rag.py` 的 `generate_paper()` 做兩處修改。**注意**：Steps 4-8 已經在這個檔案裡插入/替換過程式碼，`generate_paper()` 的實際行號會比檔案最初的第 265-347 行往後移，請用下面的程式碼內容搜尋定位，不要依賴絕對行號：

1. 呼叫 `_build_section_prompt` 之後、`_build_citation_map` 之前，插入 section label 解析，並改傳解析後的字串：

```python
            # 3. Gemini 生成章節
            prompt = self._build_section_prompt(
                section_name, topic, results_text, local_refs, language
            )
            section_text = self._call_gemini(prompt, usage_total)

            # 4. 建立引用地圖（逐段）—— 要在轉換全域編號之前做，
            # 這樣才能用本地編號精準查表，不是用全域編號反查猜測
            #
            # 這裡刻意傳「解析後的顯示標籤」而不是內部 canonical key（section_name）：
            # _assemble_paper() 組標題時用同一個 _section_label() 算出同一個字串，
            # 前端是用逐字串比對這兩者來決定引用來源要掛在哪個段落上，兩邊沒有算出
            # 同一個字串的話，英文模式下所有引用配對都會失敗
            section_label = self._section_label(section_name, language)
            self._build_citation_map(
                section_label, section_text, local_refs, global_ref_list, citation_map
            )
```

2. 組裝完整論文與引用對照報告那兩行，多傳 `language`：

```python
        # 7. 組合完整論文 + 引用對照報告
        paper_markdown = self._assemble_paper(topic, structure, sections_text, global_ref_list, language)
        citation_report = self._build_citation_report(global_ref_list, citation_map, language)
```

- [ ] **Step 10: 執行新測試，確認全部通過**

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_paper_rag_language.py -v"`
Expected: 全部 PASS。

- [ ] **Step 11: 跑回歸測試，確認沒有壞掉既有行為**

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_paper_rag_section_prompt.py tests/test_paper_rag_citation_map.py tests/test_paper_rag_search.py tests/test_paper_rag_tab_insight.py -v"`
Expected: 全部 PASS（現有測試呼叫 `_build_section_prompt(..., language="zh-TW")`、`_build_citation_map(...)` 的地方完全不用改，因為簽章沒變、中文分支輸出逐字不變）。

Run: `docker cp backend/services/rag/paper_rag.py datamind-backend:/tmp/paper_rag.py && docker exec datamind-backend .venv/bin/python -m py_compile /tmp/paper_rag.py`
Expected: 無輸出（編譯成功）。

- [ ] **Step 12: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/tests/test_paper_rag_language.py
git commit -m "feat: support English output in paper section generation

Splits the section prompt builder into zh/en variants and threads a
language param through paper assembly and the citation report. The
citation_map section field is resolved through the same display-label
helper used for markdown headings, so citation-to-paragraph matching
in the frontend keeps working regardless of output language."
```

---

### Task 2: 後端路由把 `language` 傳到 `generate_paper()`

**Files:**
- Modify: `backend/routes/rag.py:474-522`（`arxiv_generate()`）
- Modify: `backend/tests/test_rag_routes.py:66-67`（`FakeService.generate_paper` 的 call 記錄要多帶 `language`，才能在新測試裡斷言）

**Interfaces:**
- Consumes：Task 1 產生的 `PaperRAGService.generate_paper(project_id, topic, mining_results, structure=None, language="zh-TW")`（簽章沒變，本任務只是讓路由層真的把 `language` 傳進去）。
- Produces：`/api/rag/arxiv/generate` 的 request body 多接受一個選填的 `language` 欄位（`"zh-TW"` 或 `"en"`，缺省 `"zh-TW"`），Task 4 的前端會送這個欄位。

- [ ] **Step 1: 修改 `FakeService.generate_paper`，讓它的 call 記錄包含 `language`**

`backend/tests/test_rag_routes.py:66-67` 現況：

```python
    def generate_paper(self, project_id, topic, mining_results, structure=None, language="zh-TW"):
        self.calls.append(("generate_paper", project_id))
```

改成：

```python
    def generate_paper(self, project_id, topic, mining_results, structure=None, language="zh-TW"):
        self.calls.append(("generate_paper", project_id, language))
```

這個檔案裡目前沒有任何測試斷言這個 tuple 的確切內容（唯一呼叫到 `arxiv_generate` 快樂路徑的既有測試只測 timeout 例外，用的是 `FakeServiceRaising` 不是 `FakeService`），所以這個修改不會破壞任何現有測試。

- [ ] **Step 2: 寫新測試，涵蓋 language 轉發與預設值**

在 `backend/tests/test_rag_routes.py` 檔案末尾（`test_tab_chat_requires_login` 之後）新增：

```python
def test_arxiv_generate_forwards_language_to_service(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/arxiv/generate", json={
        "project_id": 7,
        "topic": "t",
        "mining_results": {},
        "selected_candidates": [{"arxiv_id": "123"}],
        "language": "en",
    })

    assert response.status_code == 200
    assert ("generate_paper", 7, "en") in fake_service.calls


def test_arxiv_generate_defaults_language_to_zh_tw_when_omitted(client, monkeypatch):
    monkeypatch.setattr(rag_route, "_get_owned_project", lambda project_id: FakeProject(project_id))
    fake_service = FakeService()
    monkeypatch.setattr(paper_rag_module, "get_paper_rag_service", lambda: fake_service)

    response = client.post("/api/rag/arxiv/generate", json={
        "project_id": 7,
        "topic": "t",
        "mining_results": {},
        "selected_candidates": [{"arxiv_id": "123"}],
    })

    assert response.status_code == 200
    assert ("generate_paper", 7, "zh-TW") in fake_service.calls
```

- [ ] **Step 3: 執行測試，確認新測試失敗**

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_rag_routes.py -k arxiv_generate_forwards_language -v"`
Expected: FAIL（路由目前完全沒有讀取或轉發 `language`）。

- [ ] **Step 4: 修改 `arxiv_generate()` 路由**

`backend/routes/rag.py:498-516` 現況：

```python
    topic = data.get("topic", "").strip()
    mining_results = data.get("mining_results")
    selected_candidates = data.get("selected_candidates")

    if not topic:
        return jsonify({"success": False, "error": "topic 為必填欄位"}), 400
    if mining_results is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    if not selected_candidates:
        return jsonify({"success": False, "error": "selected_candidates 為必填欄位，至少需選擇一篇論文"}), 400

    service = get_paper_rag_service()

    try:
        ingest_result = service.ingest_arxiv_selection(project_id, selected_candidates)
        if not ingest_result.get("success"):
            return jsonify(ingest_result), 422

        result = service.generate_paper(project_id, topic=topic, mining_results=mining_results)
```

改成：

```python
    topic = data.get("topic", "").strip()
    mining_results = data.get("mining_results")
    selected_candidates = data.get("selected_candidates")
    language = data.get("language", "zh-TW")

    if not topic:
        return jsonify({"success": False, "error": "topic 為必填欄位"}), 400
    if mining_results is None:
        return jsonify({"success": False, "error": "mining_results 為必填欄位"}), 400
    if not selected_candidates:
        return jsonify({"success": False, "error": "selected_candidates 為必填欄位，至少需選擇一篇論文"}), 400

    service = get_paper_rag_service()

    try:
        ingest_result = service.ingest_arxiv_selection(project_id, selected_candidates)
        if not ingest_result.get("success"):
            return jsonify(ingest_result), 422

        result = service.generate_paper(
            project_id, topic=topic, mining_results=mining_results, language=language
        )
```

也順手把函式 docstring（第 479-484 行）加一行說明，跟 `/generate-paper` 路由的 docstring 風格一致：

```python
    """下載選中的 arXiv 論文、建立索引，並生成論文

    JSON body:
        - topic               : 研究主題（必填）
        - mining_results      : DataMind 探勘結果（必填）
        - selected_candidates : 使用者勾選的候選論文清單（必填，來自 /arxiv/search 的 candidates）
        - language            : 語言（選填，預設 zh-TW）

    回傳：與 /generate-paper 相同形狀，外加 ingested/failed 清單
    """
```

- [ ] **Step 5: 執行測試，確認全部通過**

Run: `docker exec datamind-backend sh -c "cd /app && .venv/bin/python -m pytest tests/test_rag_routes.py -v"`
Expected: 全部 PASS（含新增的兩個測試與所有既有測試）。

- [ ] **Step 6: Commit**

```bash
git add backend/routes/rag.py backend/tests/test_rag_routes.py
git commit -m "fix: forward language param through the arxiv paper generation route

/api/rag/arxiv/generate previously never read or forwarded the
language field, so PaperRAGService.generate_paper() always fell back
to its zh-TW default regardless of what the frontend sent."
```

---

### Task 3: 前端 — 修正參考文獻判斷的語言綁定 bug，並串接 `PaperReport.language`

**Files:**
- Modify: `frontend/src/utils/paperTransform.ts`
- Modify: `frontend/src/constants/reportData.ts`
- Modify: `frontend/src/components/paper/buildReferenceBlocks.ts`
- Modify: `frontend/src/components/paper/ReferencesSection.vue`
- Modify: `frontend/src/components/paper/PaginatedPaperView.vue`
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes：後端回傳的 `ArxivGenerateResult`（`frontend/src/api/arxiv.ts`，型別不變，本任務不改這個檔案）；`sections_generated: string[]` 欄位（長度＝實際生成的正文章節數，值本身是內部字串，不用關心）。
- Produces：
  - `transformArxivResultToPaperReport(result: ArxivGenerateResult, topic: string, language: 'zh-TW' | 'en'): PaperReport`（新增第三個必填參數，Task 4 會呼叫）。
  - `PaperReport.language?: 'zh-TW' | 'en'`（選填欄位，Task 4 產生報告時一定會帶值；既有的 `saveReport`/`getReport` 往返路徑不受影響，缺省時各元件 fallback 顯示中文標籤——這是刻意的已知限制，不在本次範圍內：透過「儲存並重新載入」的技術報告會遺失語言標記、參考文獻標題會顯示回中文，即使正文其實是英文）。
  - `buildReferenceBlocks(citations, citationStyle, language: 'zh-TW' | 'en' = 'zh-TW')`（新增第三個選填參數）。
  - `ReferencesSection.vue`/`PaginatedPaperView.vue` 新增選填的 `language` prop。

**已知限制（本任務不處理，如上）：** `PaperPage.vue` 的 `getReport()`/`save()` 往返沒有把 `language` 存進後端的技術報告持久化模型（那是另一個資料表/API，不在這次 spec 範圍內）。

- [ ] **Step 1: 用真實資料重現現有 bug，確認問題存在**

這個 repo 目前沒有設定前端測試框架（沒有 vitest/jest，`package.json` 沒有 `test` script）。`paperTransform.ts` 本身是純函式、沒有任何執行期依賴（所有 import 都是 `import type`，型別會在編譯時被完全抹除），所以可以直接用 Node 22 內建的 `--experimental-strip-types` 執行 `.ts` 原始檔驗證，不需要新增任何建置工具或依賴——這是一次性驗證用的暫存腳本，驗證完就刪除，不要 commit。

在 `datamind-frontend` container 內建立 `/tmp/verify_paper_transform.mjs`：

```js
import { transformArxivResultToPaperReport } from "/app/src/utils/paperTransform.ts"

function buildEnglishResult () {
  return {
    paper_markdown: [
      "# Test Topic",
      "## Abstract\n\nThis is the abstract[1].",
      "## Introduction\n\nBackground info.",
      "## References\n\n[1] Smith, J. (2020). A Paper.",
    ].join("\n\n---\n\n"),
    citation_map: [
      {
        section: "Abstract",
        paragraph_index: 0,
        text: "This is the abstract[1].",
        cited_ref_ids: [1],
        sources: [{ ref_id: 1, paper_id: "p1", title: "A Paper", relevant_chunk: "..." }],
      },
    ],
    references: [{ ref_id: 1, paper_id: "p1", title: "A Paper", author: "Smith, J.", year: 2020 }],
    citation_report: "",
    sections_generated: ["摘要", "前言"],
    usage: {},
  }
}

const enReport = transformArxivResultToPaperReport(buildEnglishResult(), "Test Topic", "en")
const headings = enReport.content.content.filter(n => n.type === "heading").map(n => n.content[0].text)
console.log("headings:", JSON.stringify(headings))
if (JSON.stringify(headings) !== JSON.stringify(["Abstract", "Introduction"])) {
  console.log("BUG CONFIRMED: References block leaked into body content")
} else {
  console.log("unexpected: bug not reproduced")
}
```

Run: `docker exec datamind-frontend node --experimental-strip-types /tmp/verify_paper_transform.mjs`
Expected: 印出 `headings: ["Abstract","Introduction","References"]` 跟 `BUG CONFIRMED: References block leaked into body content`（現在的程式碼呼叫 `transformArxivResultToPaperReport` 只接受兩個參數，第三個 `language` 引數會被忽略，但這一步的重點是先證明「參考文獻字串比對」這個 bug 本身，不是測試簽章）。

- [ ] **Step 2: 修正 `paperTransform.ts` — 用 `sections_generated.length` 切片，不比對標題文字**

`frontend/src/utils/paperTransform.ts:61-103` 現況（`transformArxivResultToPaperReport` 函式本體）：

```ts
export function transformArxivResultToPaperReport (result: ArxivGenerateResult, topic: string): PaperReport {
  const blocks = result.paper_markdown.split('\n\n---\n\n')
  const docContent: JSONContent[] = []

  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ') || trimmed.startsWith('## 參考文獻')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    docContent.push({
      type: 'heading',
      attrs: { level: 3 },
      content: [{ type: 'text', text: heading }],
    })

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const [index, paragraph] of paragraphs.entries()) {
      // 前端這裡切段落的規則（\n\n---\n\n 分章節、\n\n 分段落）跟後端組
      // paper_markdown、_build_citation_map 切 paragraph_index 用的是同一份文字、
      // 同一套規則，兩邊算出來的段落序號天生對得上，不需要後端多傳任何資料
      const sources = result.citation_map.find(
        entry => entry.section === heading && entry.paragraph_index === index,
      )?.sources
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph, sources) })
    }
  }

  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
    citationStyle: 'apa',
  }
}
```

改成：

```ts
export function transformArxivResultToPaperReport (
  result: ArxivGenerateResult,
  topic: string,
  language: PaperReport['language'],
): PaperReport {
  const blocks = result.paper_markdown.split('\n\n---\n\n')
  // blocks[0] 固定是 `# {topic}` 標題（不是章節，不會被下面的 `## ` 判斷選中）；
  // 接下來 sections_generated.length 個 block 才是實際生成的正文章節，再之後如果
  // 還有 block 就是參考文獻。用數量判斷而不是比對標題文字，因為標題文字會隨
  // language 改變（中文「參考文獻」、英文「References」），比對文字寫死其中一種
  // 語言，另一種語言就會判斷失效、把參考文獻誤植入正文
  const sectionBlocks = blocks.slice(1, 1 + result.sections_generated.length)
  const docContent: JSONContent[] = []

  for (const block of sectionBlocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    docContent.push({
      type: 'heading',
      attrs: { level: 3 },
      content: [{ type: 'text', text: heading }],
    })

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const [index, paragraph] of paragraphs.entries()) {
      // 前端這裡切段落的規則（\n\n---\n\n 分章節、\n\n 分段落）跟後端組
      // paper_markdown、_build_citation_map 切 paragraph_index 用的是同一份文字、
      // 同一套規則，兩邊算出來的段落序號天生對得上，不需要後端多傳任何資料
      const sources = result.citation_map.find(
        entry => entry.section === heading && entry.paragraph_index === index,
      )?.sources
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph, sources) })
    }
  }

  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
    citationStyle: 'apa',
    language,
  }
}
```

- [ ] **Step 3: `PaperReport` 型別加上 `language` 欄位，`mockPaperReport` 補上值**

`frontend/src/constants/reportData.ts:15-20` 現況：

```ts
export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
  citationStyle: CitationStyle
}
```

改成：

```ts
export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
  citationStyle: CitationStyle
  language?: 'zh-TW' | 'en'
}
```

`frontend/src/constants/reportData.ts:22-24`（`mockPaperReport` 的前三行）現況：

```ts
export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citationStyle: 'apa',
```

改成：

```ts
export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citationStyle: 'apa',
  language: 'zh-TW',
```

- [ ] **Step 4: `buildReferenceBlocks()` 加上 `language` 參數**

`frontend/src/components/paper/buildReferenceBlocks.ts` 現況：

```ts
export function buildReferenceBlocks (citations: Citation[], citationStyle: CitationStyle): ReferenceBlockInput[] {
  if (citations.length === 0) return []

  const blocks: ReferenceBlockInput[] = [
    { kind: 'referenceHeading', html: '<h3 class="references-title">參考文獻</h3>' },
  ]
```

改成：

```ts
export function buildReferenceBlocks (
  citations: Citation[],
  citationStyle: CitationStyle,
  language: 'zh-TW' | 'en' = 'zh-TW',
): ReferenceBlockInput[] {
  if (citations.length === 0) return []

  const title = language === 'en' ? 'References' : '參考文獻'
  const blocks: ReferenceBlockInput[] = [
    { kind: 'referenceHeading', html: `<h3 class="references-title">${title}</h3>` },
  ]
```

- [ ] **Step 5: `ReferencesSection.vue` 加上 `language` prop**

`frontend/src/components/paper/ReferencesSection.vue` 現況：

```vue
<template>
  <section v-if="citations.length > 0" class="references-section">
    <h3 class="references-title">參考文獻</h3>
```

```ts
  defineProps<{
    citations: Citation[]
    citationStyle: CitationStyle
  }>()
```

改成：

```vue
<template>
  <section v-if="citations.length > 0" class="references-section">
    <h3 class="references-title">{{ language === 'en' ? 'References' : '參考文獻' }}</h3>
```

```ts
  defineProps<{
    citations: Citation[]
    citationStyle: CitationStyle
    language?: 'zh-TW' | 'en'
  }>()
```

- [ ] **Step 6: `PaginatedPaperView.vue` 加上 `language` prop，傳給 `buildReferenceBlocks()`**

`frontend/src/components/paper/PaginatedPaperView.vue:26-30` 現況：

```ts
  const props = defineProps<{
    content: JSONContent
    citations: Citation[]
    citationStyle: CitationStyle
  }>()
```

改成：

```ts
  const props = defineProps<{
    content: JSONContent
    citations: Citation[]
    citationStyle: CitationStyle
    language?: 'zh-TW' | 'en'
  }>()
```

第 75 行：

```ts
    const referenceInputs = buildReferenceBlocks(props.citations, props.citationStyle)
```

改成：

```ts
    const referenceInputs = buildReferenceBlocks(props.citations, props.citationStyle, props.language)
```

第 115-119 行的 `watch` 依賴陣列也要加上 `language`：

```ts
  watch(
    [() => props.content, () => props.citations, () => props.citationStyle],
    computePages,
    { deep: true },
  )
```

改成：

```ts
  watch(
    [() => props.content, () => props.citations, () => props.citationStyle, () => props.language],
    computePages,
    { deep: true },
  )
```

- [ ] **Step 7: `PaperPage.vue` 把 `report.language` 傳給兩個消費它的元件**

`frontend/src/views/PaperPage.vue:58-64`（`<PaginatedPaperView>` 用法）現況：

```vue
          <PaginatedPaperView
            ref="paginatedViewRef"
            :citation-style="report.citationStyle"
            :citations="report.citations"
            :content="report.content"
            @citation-click="onCitationClick"
          />
```

改成：

```vue
          <PaginatedPaperView
            ref="paginatedViewRef"
            :citation-style="report.citationStyle"
            :citations="report.citations"
            :content="report.content"
            :language="report.language"
            @citation-click="onCitationClick"
          />
```

第 74 行（`<ReferencesSection>` 用法）現況：

```vue
          <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" />
```

改成：

```vue
          <ReferencesSection :citation-style="report.citationStyle" :citations="report.citations" :language="report.language" />
```

- [ ] **Step 8: 重新執行驗證腳本，確認 bug 修好**

把 Step 1 的腳本改成呼叫三個參數版本（`language` 傳 `"en"`），並改用型別中已存在的 `sections_generated` 長度斷言：

Run（在 `datamind-frontend` container 內，`/app` 目錄）：

```bash
cat > /tmp/verify_paper_transform.mjs << 'SCRIPT'
import { transformArxivResultToPaperReport } from "/app/src/utils/paperTransform.ts"

function buildResult (overrides = {}) {
  return {
    paper_markdown: [
      "# Test Topic",
      "## Abstract\n\nThis is the abstract[1].",
      "## Introduction\n\nBackground info.",
      "## References\n\n[1] Smith, J. (2020). A Paper.",
    ].join("\n\n---\n\n"),
    citation_map: [
      {
        section: "Abstract",
        paragraph_index: 0,
        text: "This is the abstract[1].",
        cited_ref_ids: [1],
        sources: [{ ref_id: 1, paper_id: "p1", title: "A Paper", relevant_chunk: "..." }],
      },
    ],
    references: [{ ref_id: 1, paper_id: "p1", title: "A Paper", author: "Smith, J.", year: 2020 }],
    citation_report: "",
    sections_generated: ["摘要", "前言"],
    usage: {},
    ...overrides,
  }
}

function assertEqual (actual, expected, label) {
  const a = JSON.stringify(actual)
  const e = JSON.stringify(expected)
  if (a !== e) throw new Error(`${label}: expected ${e}, got ${a}`)
  console.log(`OK: ${label}`)
}

const enReport = transformArxivResultToPaperReport(buildResult(), "Test Topic", "en")
const enHeadings = enReport.content.content.filter(n => n.type === "heading").map(n => n.content[0].text)
assertEqual(enHeadings, ["Abstract", "Introduction"], "English mode excludes References block")
assertEqual(enReport.language, "en", "English mode sets language field")

const firstParagraph = enReport.content.content.find(n => n.type === "paragraph")
const hasCitationMark = firstParagraph.content.some(node => node.marks?.some(m => m.type === "citation"))
if (!hasCitationMark) throw new Error("Expected the first paragraph to carry a citation mark")
console.log("OK: citation mark still attaches correctly")

const zhResult = buildResult({
  paper_markdown: [
    "# 測試主題",
    "## 摘要\n\n這是摘要[1]。",
    "## 前言\n\n背景資訊。",
    "## 參考文獻\n\n[1] Smith, J. (2020). A Paper.",
  ].join("\n\n---\n\n"),
})
const zhReport = transformArxivResultToPaperReport(zhResult, "測試主題", "zh-TW")
const zhHeadings = zhReport.content.content.filter(n => n.type === "heading").map(n => n.content[0].text)
assertEqual(zhHeadings, ["摘要", "前言"], "zh-TW mode excludes References block (regression)")
assertEqual(zhReport.language, "zh-TW", "zh-TW mode sets language field")

console.log("All paperTransform assertions passed")
SCRIPT
node --experimental-strip-types /tmp/verify_paper_transform.mjs
rm /tmp/verify_paper_transform.mjs
```

Expected: 印出五行 `OK: ...` 加上最後一行 `All paperTransform assertions passed`，沒有任何 `Error` 拋出。跑完後腳本會被刪除（`rm` 那一行），不要把這個暫存腳本 commit 進 repo。

- [ ] **Step 9: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 無型別錯誤（沿用本 session 已知的基準線：目前應為 0 錯誤）。

- [ ] **Step 10: Commit**

```bash
git add frontend/src/utils/paperTransform.ts frontend/src/constants/reportData.ts frontend/src/components/paper/buildReferenceBlocks.ts frontend/src/components/paper/ReferencesSection.vue frontend/src/components/paper/PaginatedPaperView.vue frontend/src/views/PaperPage.vue
git commit -m "fix: stop matching the references block by hardcoded Chinese heading text

transformArxivResultToPaperReport() used to detect the references
block by checking for a literal '## 參考文獻' string, which silently
broke for any other output language (e.g. English's '## References')
and let the whole references section leak into the editable body.
Switched to slicing by sections_generated.length instead, and threaded
a language field through PaperReport so the reference heading UI can
follow the paper's actual output language."
```

---

### Task 4: 前端 — 語言選單 UI 與 API 串接

**Files:**
- Modify: `frontend/src/api/arxiv.ts`
- Modify: `frontend/src/views/PaperSourcesView.vue`

**Interfaces:**
- Consumes：Task 3 產生的 `transformArxivResultToPaperReport(result, topic, language)`（三個參數版本）；`CustomSelect.vue` 既有的 `modelValue: string` / `options: {value, label}[]` / `@update:model-value` 介面（`frontend/src/components/common/CustomSelect.vue`，本任務不改這個元件）。
- Produces：`generateFromArxiv(params)` 的 `params` 多一個必填欄位 `language: 'zh-TW' | 'en'`；這是整條串接的最後一棒，完成後功能端對端可用。

- [ ] **Step 1: `generateFromArxiv()` 加上 `language` 參數**

`frontend/src/api/arxiv.ts:78-93` 現況：

```ts
export async function generateFromArxiv (params: {
  topic: string
  miningResults: Record<string, unknown>
  selectedCandidates: ArxivCandidate[]
  projectId: string
}): Promise<ArxivGenerateResult> {
  const response = await fetch('/api/rag/arxiv/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: params.topic,
      mining_results: params.miningResults,
      selected_candidates: params.selectedCandidates,
      project_id: params.projectId,
    }),
  })
```

改成：

```ts
export async function generateFromArxiv (params: {
  topic: string
  miningResults: Record<string, unknown>
  selectedCandidates: ArxivCandidate[]
  projectId: string
  language: 'zh-TW' | 'en'
}): Promise<ArxivGenerateResult> {
  const response = await fetch('/api/rag/arxiv/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: params.topic,
      mining_results: params.miningResults,
      selected_candidates: params.selectedCandidates,
      project_id: params.projectId,
      language: params.language,
    }),
  })
```

- [ ] **Step 2: `PaperSourcesView.vue` 引入 `CustomSelect`，新增語言選單狀態**

`frontend/src/views/PaperSourcesView.vue:99-111`（import 區）現況：

```ts
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import { saveReport } from '@/api/report'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperGeneratingOverlay from '@/components/paper/PaperGeneratingOverlay.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import AppCheckbox from '@/components/ui/AppCheckbox.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { usePaperStore } from '@/store/paperStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'
```

改成（新增 `CustomSelect` import）：

```ts
  import { computed, onMounted, ref } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import { type ArxivCandidate, generateFromArxiv, searchArxivCandidates } from '@/api/arxiv'
  import { saveReport } from '@/api/report'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import PaperGeneratingOverlay from '@/components/paper/PaperGeneratingOverlay.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import AppCheckbox from '@/components/ui/AppCheckbox.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { usePaperStore } from '@/store/paperStore'
  import { transformArxivResultToPaperReport } from '@/utils/paperTransform'
```

在 `const selectedIds = ref<string[]>([])`（第 125 行）之後新增：

```ts
  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'zh-TW', label: '繁體中文' },
  ]
  const selectedLanguage = ref<'zh-TW' | 'en'>('en')

  function onLanguageChange (value: string): void {
    selectedLanguage.value = value as 'zh-TW' | 'en'
  }
```

- [ ] **Step 3: 在生成按鈕旁加上語言選單**

`frontend/src/views/PaperSourcesView.vue:79-89` 現況：

```vue
            <div class="sources-actions">
              <AppButton
                :disabled="selectedIds.length === 0"
                :loading="generating"
                variant="primary"
                @click="handleGenerate"
              >
                確認並生成技術報告 ({{ selectedIds.length }})
              </AppButton>
              <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
            </div>
```

改成：

```vue
            <div class="sources-actions">
              <div class="language-select-row">
                <span class="sources-title-label">論文語言</span>
                <CustomSelect
                  aria-label="論文語言"
                  class="language-select"
                  :model-value="selectedLanguage"
                  :options="languageOptions"
                  @update:model-value="onLanguageChange"
                />
              </div>
              <AppButton
                :disabled="selectedIds.length === 0"
                :loading="generating"
                variant="primary"
                @click="handleGenerate"
              >
                確認並生成技術報告 ({{ selectedIds.length }})
              </AppButton>
              <p v-if="generateError" class="sources-status sources-status--error">{{ generateError }}</p>
            </div>
```

在 `<style scoped>` 區塊、`.sources-actions` 規則（第 357-363 行）之後新增：

```css
  .language-select-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .language-select {
    width: 140px;
  }
```

- [ ] **Step 4: `handleGenerate()` 把選到的語言帶進 API 呼叫與報告轉換**

`frontend/src/views/PaperSourcesView.vue:172-181` 現況：

```ts
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
        projectId: projectId.value,
      })
      if (token !== generationToken) return
      const report = transformArxivResultToPaperReport(result, topic.value)
```

改成：

```ts
      const selectedCandidates = candidates.value.filter(c => selectedIds.value.includes(c.arxiv_id))
      const result = await generateFromArxiv({
        topic: topic.value,
        miningResults: miningResults.value,
        selectedCandidates,
        projectId: projectId.value,
        language: selectedLanguage.value,
      })
      if (token !== generationToken) return
      const report = transformArxivResultToPaperReport(result, topic.value, selectedLanguage.value)
```

- [ ] **Step 5: 型別檢查**

Run: `docker exec datamind-frontend sh -c "cd /app && npm run type-check"`
Expected: 無型別錯誤。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/arxiv.ts frontend/src/views/PaperSourcesView.vue
git commit -m "feat: add a language selector to the paper generation flow

Lets users pick zh-TW or English before generating a paper from the
selected arXiv sources, defaulting to English since most source
papers are English. Wires the choice through generateFromArxiv() and
transformArxivResultToPaperReport()."
```

---

## 手動驗證（非阻塞，完成所有 task 後建議做一次）

自動化測試涵蓋了核心邏輯正確性，但沒有涵蓋「畫面上語言選單看起來如何」「一次真實的 Gemini 生成跑起來的輸出品質」。建議在合併前手動跑一次：
1. 進入「選擇參考文獻」頁面，確認語言選單預設顯示 English、可以切換成繁體中文。
2. 選 English、生成一份論文，確認畫面上的章節標題、參考文獻標題都是英文，且引用標記（`[1]`、`[2]`）點擊後能正確彈出對應來源（這是 Task 1 修的 citation_map 一致性問題的最終驗證）。
3. 選繁體中文、生成一份論文，確認行為跟這個功能上線前完全一樣（回歸）。
