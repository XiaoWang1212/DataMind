# 論文生成中英文切換 Design Spec

## 背景與目標

目前「生成論文」功能（`PaperSourcesView.vue` → `/api/rag/arxiv/generate` → `PaperRAGService.generate_paper()`）產生的論文內容永遠是繁體中文，但實際被分析、引用的參考文獻大多是英文論文。使用者希望能在生成前選擇輸出語言（繁體中文 / English）。

**範圍決策（已與使用者確認）：**
- 只支援「生成時選語言」，**不支援**「已生成內容事後中英互換」。一份論文從生成到編輯完成，全程只存在單一語言版本，不做雙語同步。這個決策直接消除了「螢光筆」等未來可能綁定文字位置/內容的功能會被雙語版本拖垮的風險——因為根本不會有兩個版本並存。
- 選英文時，**全部改成英文**：不只是正文內容，章節標題（Abstract/Introduction/...）、參考文獻標題、引用對照報告的標籤文字都要一併變成英文，讀起來要像一篇真正的英文論文，不是中英混雜。
- 語言選單**預設 English**（因為多數來源論文本身是英文，讓新行為對齊多數使用情境）。

## 現況架構（探索結果）

- `PaperSourcesView.vue` 是唯一觸發論文生成的畫面，呼叫 `generateFromArxiv()`（`frontend/src/api/arxiv.ts`），送到後端 `/api/rag/arxiv/generate`（`backend/routes/rag.py` 的 `arxiv_generate()`），內部呼叫 `service.generate_paper(project_id, topic=topic, mining_results=mining_results)`——**目前完全沒有傳 `language`**。
- `PaperRAGService.generate_paper()`（`backend/services/rag/paper_rag.py`）雖然簽章已經有 `language: str = "zh-TW"`，也確實往下傳給 `_build_section_prompt()`，但 `_build_section_prompt()` 內部**完全沒有用到這個參數**，prompt 文字寫死繁體中文（「請根據以下資料，以繁體中文撰寫論文」「語言：繁體中文」）。也就是說 `language` 目前是「有傳但沒效果」的死參數。
- 章節本身是用**中文字串**當內部 canonical key（`_DEFAULT_STRUCTURE = ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"]`），同時也直接是 `_assemble_paper()` 組出來的 `## {sec}` 標題文字——也就是說今天輸出的章節標題文字＝內部 key，沒有分離「內部識別碼」跟「顯示文字」。
- `_assemble_paper()` 另外固定輸出 `## 參考文獻` 區塊；`_build_citation_report()` 輸出一份獨立的「引用對照報告」markdown，標題與各種標籤（引用內文、對應原文摘錄、相似度…）全部寫死中文。
- 前端 `frontend/src/utils/paperTransform.ts:67` 在把 `paper_markdown` 轉成 Tiptap 文件時，用 `trimmed.startsWith('## 參考文獻')` 判斷「這個 block 是參考文獻、要跳過不當正文」（因為參考文獻改用結構化的 `result.references` 資料另外渲染）。**這個判斷寫死中文字串**，一旦後端在英文模式輸出 `## References`，這個判斷會失效，導致整段參考文獻被誤判成正文段落，錯誤地塞進編輯器內容裡（且還會被拿去跟 `citation_map` 做段落比對，產生垃圾資料）。這正是使用者一開始擔心的「文字內容綁定的功能難以擴展」的具體案例，需要在這次一併修掉。
- `frontend/src/components/paper/buildReferenceBlocks.ts:13`（編輯器內參考文獻標題）與 `frontend/src/components/paper/ReferencesSection.vue:3`（論文預覽頁的參考文獻標題）兩處也各自寫死中文「參考文獻」四個字，是 UI 顯示用途，不是解析用途，但既然選了英文論文全篇要一致，這兩處也要跟著切換。
- `PaperReport`（`frontend/src/constants/reportData.ts`）目前沒有語言欄位。
- `/api/rag/generate-paper` 這條路由（非 arXiv 流程）目前前端完全没有呼叫，是死路徑；但它已經正確把 `language` 傳給 `generate_paper()`，這次修好 `_build_section_prompt()` 之後它會自動受益，不需要額外改動。
- 期刊評分（`_build_score_prompt()` / `_JOURNAL_RUBRICS`）產生的評語維持繁體中文，不在這次範圍內。

## 設計

### 1. 前端：語言選單

`PaperSourcesView.vue` 新增一個語言選擇器，沿用既有的 `CustomSelect.vue` 樣式，選項為「繁體中文」/「English」（value 分別對應 `zh-TW` / `en`），**預設 `en`**。放置位置與生成按鈕（「確認並生成技術報告」）同一區域，讓使用者在按下生成前就能看到並調整。

`handleGenerate()` 呼叫 `generateFromArxiv()` 時，把選到的語言值一併帶入。

### 2. API 層：把 language 傳到底

- `frontend/src/api/arxiv.ts` 的 `generateFromArxiv()`：request body 加上 `language`。
- `backend/routes/rag.py` 的 `arxiv_generate()`：從 request JSON 讀取 `language`（缺省時 fallback `"zh-TW"`，維持向後相容），呼叫 `service.generate_paper(..., language=language)` 時一併傳入（目前這裡完全沒傳這個參數，是本次要修的缺口）。

### 3. 後端：依語言生成內容與標題

**章節顯示標籤**：新增一個顯示層對照表：

```python
_SECTION_LABELS_EN: Dict[str, str] = {
    "摘要": "Abstract",
    "前言": "Introduction",
    "研究方法": "Methods",
    "實驗結果": "Results",
    "討論": "Discussion",
    "結論": "Conclusion",
}
```

**重要邊界**：`_DEFAULT_STRUCTURE`、`_SECTION_WORD_TARGETS`、`_SECTION_QUERIES`、`_SECTION_WRITING_FOCUS`、`_SECTION_TOP_K` 這些內部 dict 的 key **維持中文不變**，不建立英文對照版本。理由：
- 這些是「RAG 檢索關鍵字」跟「給 Gemini 的寫作重點指示」，使用者從頭到尾看不到，純粹是內部實作細節；Gemini 完全有能力理解中文指示、同時被要求輸出英文內容，不需要指示文字本身也翻譯。
- 避免維護兩套內容幾乎相同、只是語言不同的 dict，日後改寫作重點只要改一處。

**Prompt 產生**：`_build_section_prompt()` 依 `language` 分流成兩個獨立、完整改寫的 prompt 產生方法（不是把中文 prompt 機械式翻成英文再插入，而是各自用該語言的學術寫作慣例重新表述指示，包含格式要求、引用標記規則、禁止事項等）：
- `_build_section_prompt_zh(...)`：現有邏輯原封不動搬過去。
- `_build_section_prompt_en(...)`：新寫的英文版，指示 Gemini 用英文撰寫該章節內容，章節名稱顯示用 `_SECTION_LABELS_EN` 對照後的英文標籤（例如提示詞裡出現的是 "Introduction" 而不是 "前言"），其餘規則（字數目標、引用格式、段落規則、禁止 Markdown 語法等）比照現有中文版的規則對應改寫成英文措辭。

`_build_section_prompt()` 本身變成一個依 `language` 分派到上述兩者的小 dispatcher。

**論文組裝與引用報告**：`_assemble_paper()`、`_build_citation_report()` 都新增 `language` 參數：
- `_assemble_paper()`：章節標題輸出 `_SECTION_LABELS_EN.get(sec, sec)`（英文模式）或 `sec`（中文模式，行為不變）；參考文獻區塊標題 `## 參考文獻` → `## References`（英文模式）。
- `_build_citation_report()`：報告標題 `# 引用對照報告` → `# Citation Cross-Reference Report`，說明文字、`### {section} · 第 {n} 段` → `### {section_label} · Paragraph {n}`（`section_label` 同樣經過 `_SECTION_LABELS_EN` 對照）、「引用內文：/對應原文摘錄：/相似度：」→「Cited excerpt: / Source excerpt: / Similarity:」、無引用時的說明文字「（本文未實際引用任何參考文獻）」→「(No references were cited in this paper.)」。

**關鍵正確性要求：citation_map 的 section 欄位必須跟輸出標題文字一致**：前端 `paperTransform.ts` 是用「從 `paper_markdown` 解析出的標題文字」去比對 `citation_map[i].section` 來決定某段引用來源要掛在哪個段落上（`entry.section === heading`，逐字串相等比對）。目前 `_build_citation_map()` 是在 `generate_paper()` 的章節迴圈中用**內部中文 canonical key**（`section_name`，例如 `"前言"`）呼叫的，但英文模式下 `_assemble_paper()` 組出來的標題會是 `_SECTION_LABELS_EN` 對照後的英文標籤（`"Introduction"`）。如果不處理，英文模式下這個字串比對會全部失敗，所有段落都配不到引用來源，整篇論文的引用標記等於失效。

修法：在 `generate_paper()` 的章節迴圈裡，用同一份 `_SECTION_LABELS_EN` 對照表，在呼叫 `_build_citation_map()` 之前**先把 `section_name` 解析成跟輸出標題相同的顯示字串**（新增一個共用的小 helper，例如 `_section_label(section_name, language)`，回傳英文模式下的對照標籤或原始中文字串），再把這個「解析後的顯示字串」傳給 `_build_citation_map()` 存進 `citation_map[i].section`，而不是傳原始的內部 key。`_assemble_paper()` 组標題時也呼叫同一個 helper，確保兩邊永遠算出同一個字串。`_build_citation_report()` 因為讀的是 `citation_map[i].section`（已經是解析後的顯示字串），不需要再自己額外轉換章節名稱。

`sections_text`、`structure`、RAG 檢索關鍵字等其餘流程仍然用內部中文 canonical key 運作（`generate_paper()` 的章節迴圈、`_assemble_paper()` 的 `structure` 參數都不變），只有「寫入 citation_map 的 section 欄位」跟「組裝標題」這兩處要改成呼叫同一個 helper，才能保證永遠一致。

### 4. 前端：修掉文字綁定的解析 bug + 補上顯示標籤

**`paperTransform.ts` 的判斷邏輯改寫**：不再比對任何語言相關字串。後端回應本來就有 `sections_generated: string[]`（本次實際生成了哪幾個章節，數量固定等於正文的 heading block 數）。改成：把 `paper_markdown` 依 `\n\n---\n\n` 切出的 heading block 陣列，**只取前 `sections_generated.length` 個**當作正文，其餘（也就是參考文獻區塊，如果存在的話）一律跳過，不再判斷任何標題文字內容。這個改法不管未來加中文、英文或任何其他語言的標題文字都不會壞。

**`PaperReport` 型別**（`frontend/src/constants/reportData.ts`）新增 `language: 'zh-TW' | 'en'` 欄位。`transformArxivResultToPaperReport()` 新增一個 `language` 參數（由呼叫端——也就是 `PaperSourcesView.vue`——傳入使用者剛剛選的語言，不需要後端額外回傳，因為前端呼叫生成 API 時本來就知道自己傳了什麼語言），寫入回傳的 `PaperReport.language`。

`buildReferenceBlocks.ts` 的 `buildReferenceBlocks()` 新增 `language` 參數，標題文字依語言輸出 `參考文獻` 或 `References`。`ReferencesSection.vue` 新增 `language` prop，同樣依語言切換標題文字，並把這個 prop 從 `PaperPage.vue` 用 `report.language` 帶入。

### 5. 不動的部分

- `/api/rag/generate-paper`（非 arXiv 流程的生成路由）：本次修好 `_build_section_prompt()` 後它會自動具備語言切換能力，但因為前端目前完全沒有呼叫這條路由，不特別為它補上語言選單或其他串接。
- 期刊評分（`_build_score_prompt()`）的評語文字維持繁體中文，不在本次範圍內。
- RAG 檢索的 query 語言（`_SECTION_QUERIES`）維持中文不變——這是現有行為（中文 query 對英文來源論文做檢索），本次不改動，且與輸出語言無關。

## 測試計畫

**後端：**
- `_build_section_prompt`：`language="en"` 時回傳的 prompt 包含英文寫作指示與 `_SECTION_LABELS_EN` 對照後的英文章節名稱；`language="zh-TW"`（或未傳）時行為與現況完全一致（回歸測試）。
- `_assemble_paper`：`language="en"` 時輸出 `## Abstract`/`## Introduction`/.../`## References`；`language="zh-TW"` 時輸出維持 `## 摘要`/`## 前言`/.../`## 參考文獻`。
- `_build_citation_report`：`language="en"` 時標題與各標籤為英文版本；`language="zh-TW"` 行為不變。
- `arxiv_generate` route：`language` 有從 request body 正確讀出並傳進 `service.generate_paper()`；未傳 `language` 時 fallback 為 `"zh-TW"`。
- `generate_paper()` 端對端：`language="en"` 時，回傳的 `citation_map[i].section` 必須跟 `paper_markdown` 裡對應的 `## {heading}` 標題文字逐字相等（例如都是 `"Introduction"`，不能一邊是 `"Introduction"` 一邊是 `"前言"`）——這是防止「引用配對規則基於文字比對，跨語言就失效」這個修過的 bug 再度出現的回歸測試。

**前端：**
- `paperTransform.ts` 的 `transformArxivResultToPaperReport()`：給定英文模式的假資料（`paper_markdown` 含 `## References` 而非 `## 參考文獻`，`sections_generated` 長度為 6），驗證參考文獻 block 正確被排除、不會混入 `docContent`；給定中文模式假資料驗證行為與現況一致（回歸測試）。
- `buildReferenceBlocks.ts`：`language="en"` 時標題輸出 `References`，`language="zh-TW"` 時輸出 `參考文獻`。
