"""RAG 論文生成服務

流程：
  1. add_paper()  ─ 上傳參考論文 → 切塊 → 向量化 → 儲存
  2. generate_paper() ─ 接收 DataMind 輸出 → 逐章節 RAG 檢索 + Gemini 生成
     → 回傳 paper_markdown + citation_map（引用地圖）
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import google.generativeai as genai

from . import arxiv_source
from .chunker import Chunk, TextChunker
from .embedder import Embedder
from .reranker import Reranker
from .db_vector_store import DbVectorStore

logger = logging.getLogger(__name__)

# ── 每章節預設字數目標 ────────────────────────────────────────────────────────
_SECTION_WORD_TARGETS: Dict[str, int] = {
    "摘要": 300,
    "前言": 1000,
    "研究方法": 1200,
    "實驗結果": 800,
    "討論": 1000,
    "結論": 300,
}

# 前言需要更多引用背景，其他章節 5 筆即可
_SECTION_TOP_K: Dict[str, int] = {
    "前言": 8,
}

_DEFAULT_TOP_K = 5

# 引用標記的正則，[n] 或 [n, m, ...] 組合格式都要比對到。
# _localref_to_global 跟 _build_citation_map 共用同一份，避免兩處各寫一份、之後改一邊忘記改另一邊。
_CITATION_PATTERN = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

# 每章節的 RAG 搜尋 query 模板
_SECTION_QUERIES: Dict[str, str] = {
    "摘要": "{topic} 研究目的 方法概述 主要發現",
    "前言": "{topic} 研究背景 臨床問題 現有預測方法 研究缺口 動機",
    "研究方法": "{topic} 資料集 資料預處理 特徵選擇 機器學習模型 交叉驗證 重採樣",
    "實驗結果": "{topic} 模型效能 AUC F1 準確率 特徵重要性 模型比較",
    "討論": "{topic} 結果解讀 與文獻比較 臨床意義 研究限制",
    "結論": "{topic} 研究貢獻 臨床應用價值 未來研究方向",
}

# 每章節各自的寫作重點：只給「查詢用的關鍵字」（_SECTION_QUERIES）沒辦法讓 Gemini
# 知道「這段該寫什麼、不該重複別段已經寫過什麼」——尤其「討論」很容易變成把
# 「實驗結果」的數字用不同措辭再講一次，明講不要重複、要解讀，內容才會真的往前走
_SECTION_WRITING_FOCUS: Dict[str, str] = {
    "摘要": "濃縮全文重點：研究目的、方法概述、關鍵發現，一段話講完，不需要細節數據。",
    "前言": "鋪陳研究背景、臨床問題與現有方法的不足，帶出本研究的動機與目的，"
            "不需要提前講實驗結果的數字。",
    "研究方法": "客觀描述資料集、前處理、特徵工程、模型與驗證方式的實際作法，"
              "說明「怎麼做」，不需要評論效果好壞。",
    "實驗結果": "只客觀陳述各模型的量化指標、與彼此的比較、特徵重要性等實驗事實本身，"
              "不要加入原因推測或臨床意義的解讀，解讀留給「討論」處理。",
    "討論": "重點是解讀「實驗結果」數字背後的意義：為什麼會有這樣的結果、"
            "這些發現跟引用文獻的異同、對臨床或實務的意義、本研究方法或資料的限制。"
            "不要重複「實驗結果」已經列出的數字或比較，"
            "除非是為了進一步解讀才需要點出某個數字。",
    "結論": "扣回研究目的，總結本研究的貢獻、實務應用價值與未來研究方向，"
            "簡短有力，不需要重述前面章節的細節論證。",
}

_DEFAULT_STRUCTURE = ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"]

# ── 期刊評分準則 ──────────────────────────────────────────────────────────────
_JOURNAL_RUBRICS: List[Dict[str, str]] = [
    {
        "key": "jamia",
        "name": "JAMIA",
        "full_name": "Journal of the American Medical Informatics Association",
        "emphasis": "方法嚴謹度、可重現性、資訊系統與臨床決策整合的實用性",
    },
    {
        "key": "npj_digital_medicine",
        "name": "npj Digital Medicine",
        "full_name": "npj Digital Medicine",
        "emphasis": "臨床/實務影響力、創新性、跨領域整合、敘事簡潔清楚",
    },
    {
        "key": "bmc_midm",
        "name": "BMC Medical Informatics and Decision Making",
        "full_name": "BMC Medical Informatics and Decision Making",
        "emphasis": "技術細節完整度、統計報告透明度（如信賴區間）、開放科學規範",
    },
]

_SCORE_CRITERIA: List[str] = [
    "研究貢獻與新穎性",
    "方法嚴謹性",
    "結果呈現與統計報告完整度",
    "文獻回顧與引用品質",
    "臨床/實務意義與限制討論",
    "寫作結構與期刊格式規範",
]

_SCORE_MAX_ATTEMPTS = 3
_SCORE_RETRY_DELAY_SECONDS = 2


@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    rerank_score: Optional[float] = None


class PaperRAGService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 未設定")

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self._model = genai.GenerativeModel(model_name=model_name)

        search_arxiv_declaration = genai.protos.FunctionDeclaration(
            name="search_arxiv",
            description=(
                "搜尋 arXiv 上跟指定關鍵字相關的論文，回傳候選論文清單"
                "（標題、作者、年份、摘要、PDF連結）。當使用者的問題涉及"
                "「有沒有相關文獻／論文」「這個發現有沒有學術支持」之類需要"
                "查詢外部學術論文佐證的問題時才呼叫。"
            ),
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "query": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="英文搜尋關鍵字，適合直接拿去查 arXiv",
                    ),
                },
                required=["query"],
            ),
        )
        self._chat_model = genai.GenerativeModel(
            model_name=model_name,
            tools=[genai.protos.Tool(function_declarations=[search_arxiv_declaration])],
        )

        embed_model = os.getenv("RAG_EMBED_MODEL", "BAAI/bge-small-zh-v1.5")

        self._chunker = TextChunker(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", 500)),
            overlap=int(os.getenv("RAG_CHUNK_OVERLAP", 50)),
        )
        self._embedder = Embedder(model_name=embed_model)
        self._store = DbVectorStore(embedder=self._embedder)

        rerank_model = os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-base")
        rerank_enabled = os.getenv("RAG_RERANK_ENABLED", "true").strip().lower() not in ("false", "0")
        self._reranker = Reranker(model_name=rerank_model) if rerank_enabled else None

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_paper(self, project_id: int, title: str, content: str, metadata: dict | None = None) -> dict:
        if metadata is None:
            metadata = {}
        paper_id = self._store.create_paper(project_id, title, metadata)
        chunks = self._chunker.chunk(content, paper_id=paper_id, title=title, metadata=metadata)
        if not chunks:
            self._store.delete_paper(project_id, paper_id)
            return {"success": False, "error": "未能從文件中提取內容"}

        self._store.add_chunks(chunks)

        logger.info("add_paper: %s (%d chunks)", title, len(chunks))
        return {
            "success": True,
            "paper_id": paper_id,
            "title": title,
            "chunks_added": len(chunks),
        }

    def search(self, project_id: int, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
        should_rerank = use_rerank and self._reranker is not None and self._reranker.available
        overfetch_k = top_k * 4 if should_rerank else top_k

        raw = self._store.search(project_id, query, top_k=overfetch_k)

        if should_rerank and raw:
            reranked = self._reranker.rerank(query, raw)
            return [
                SearchResult(chunk=c, score=orig_score, rerank_score=rerank_score)
                for c, orig_score, rerank_score in reranked[:top_k]
            ]

        return [SearchResult(chunk=c, score=s) for c, s in raw[:top_k]]

    def generate_citation(self, project_id: int, query: str, top_k: int = 3, citation_style: str = "apa") -> dict:
        results = self.search(project_id, query, top_k=top_k)
        if not results:
            return {"citations": [], "sources": []}

        citations, sources = [], []
        for i, r in enumerate(results, 1):
            m = r.chunk.metadata
            author = m.get("author", "Unknown Author")
            year = m.get("year", "n.d.")
            title = r.chunk.title

            if citation_style == "apa":
                citations.append(f"{author} ({year}). {title}.")
            elif citation_style == "mla":
                citations.append(f'{author}. "{title}." {year}.')
            else:
                citations.append(f"[{i}] {author}, {title}, {year}.")

            sources.append({
                "ref_id": i,
                "paper_id": r.chunk.paper_id,
                "title": title,
                "score": r.score,
                "excerpt": r.chunk.content[:200],
            })

        return {"citations": citations, "sources": sources}

    def generate_paper(
        self,
        project_id: int,
        topic: str,
        mining_results: dict,
        structure: List[str] | None = None,
        language: str = "zh-TW",
    ) -> dict:
        """
        利用 DataMind 資料探勘輸出 + 參考論文庫，逐章節生成學術論文。

        回傳：
          paper_markdown  - 完整論文（Markdown 格式）
          citation_map    - 引用地圖（逐段記錄引用來源，供前端使用；僅含實際被引用的文獻）
          references      - 全域引用清單（APA 格式；僅含實際被引用的文獻，已重新連續編號）
          citation_report - 引用對照報告（Markdown，依參考文獻分組列出對應段落與原文摘錄）
          sections_generated - 實際生成的章節清單
          usage           - Gemini token 用量統計
        """
        if structure is None:
            structure = _DEFAULT_STRUCTURE

        results_text = self._format_datamind_output(mining_results)

        # 全域引用 registry：paper_id → global_ref_id（1-indexed）
        global_ref_map: Dict[str, int] = {}
        global_ref_list: List[dict] = []

        sections_text: Dict[str, str] = {}
        citation_map: List[dict] = []
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for section_name in structure:
            logger.info("生成章節：%s", section_name)

            # 1. RAG 檢索
            top_k = _SECTION_TOP_K.get(section_name, _DEFAULT_TOP_K)
            query_tmpl = _SECTION_QUERIES.get(section_name, "{topic}")
            query = query_tmpl.format(topic=topic)
            search_results = self.search(project_id, query, top_k=top_k)

            # 2. 建立本章節的本地 ref map（local_id → chunk + global_ref_id）
            local_refs: Dict[int, dict] = {}
            for local_id, sr in enumerate(search_results, 1):
                pid = sr.chunk.paper_id
                if pid not in global_ref_map:
                    global_ref_map[pid] = len(global_ref_map) + 1
                    global_ref_list.append({
                        "ref_id": global_ref_map[pid],
                        "paper_id": pid,
                        "title": sr.chunk.title,
                        **sr.chunk.metadata,
                    })
                local_refs[local_id] = {
                    "global_ref_id": global_ref_map[pid],
                    "chunk": sr.chunk,
                    "score": sr.score,
                    "rerank_score": sr.rerank_score,
                }

            # 3. Gemini 生成章節
            prompt = self._build_section_prompt(
                section_name, topic, results_text, local_refs, language
            )
            section_text = self._call_gemini(prompt, usage_total)

            # 4. 建立引用地圖（逐段）—— 要在轉換全域編號之前做，
            # 這樣才能用本地編號精準查表，不是用全域編號反查猜測
            self._build_citation_map(
                section_name, section_text, local_refs, global_ref_list, citation_map
            )

            # 5. 本地 [n] → 全域 [n]
            section_text_global = self._localref_to_global(section_text, local_refs)
            sections_text[section_name] = section_text_global

        # 6. 過濾未被實際引用的參考文獻，並重新連續編號
        cited_old_ids = sorted({rid for entry in citation_map for rid in entry["cited_ref_ids"]})
        old_to_new = {old_id: new_id for new_id, old_id in enumerate(cited_old_ids, 1)}

        global_ref_list = [
            {**ref, "ref_id": old_to_new[ref["ref_id"]]}
            for ref in global_ref_list
            if ref["ref_id"] in old_to_new
        ]

        for entry in citation_map:
            entry["cited_ref_ids"] = [old_to_new[rid] for rid in entry["cited_ref_ids"]]
            entry["text"] = re.sub(
                r"\[(\d+)\]",
                lambda m: f"[{old_to_new.get(int(m.group(1)), int(m.group(1)))}]",
                entry["text"],
            )
            for src in entry["sources"]:
                src["ref_id"] = old_to_new[src["ref_id"]]

        for section_name in list(sections_text.keys()):
            sections_text[section_name] = re.sub(
                r"\[(\d+)\]",
                lambda m: f"[{old_to_new.get(int(m.group(1)), int(m.group(1)))}]",
                sections_text[section_name],
            )

        # 7. 組合完整論文 + 引用對照報告
        paper_markdown = self._assemble_paper(topic, structure, sections_text, global_ref_list)
        citation_report = self._build_citation_report(global_ref_list, citation_map)

        return {
            "paper_markdown": paper_markdown,
            "citation_map": citation_map,
            "references": global_ref_list,
            "citation_report": citation_report,
            "sections_generated": [s for s in structure if s in sections_text],
            "usage": usage_total,
        }

    def classify_topic(self, mining_results: dict, user_title: str | None = None) -> dict:
        """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢字串。

        user_title 有值時，主題直接採用使用者給的標題，Gemini 只需要根據
        「使用者標題 + 實際資料探勘結果」產生符合兩者的 arXiv 查詢關鍵字。
        """
        results_text = self._format_datamind_output(mining_results)

        if user_title:
            prompt = (
                "你是學術論文寫作助手。使用者想寫一篇標題為"
                f"「{user_title}」的論文，以下是實際的資料探勘實驗結果。\n\n"
                f"【資料探勘實驗結果】\n{results_text}\n\n"
                "請判斷 2 到 6 個適合拿去查 arXiv 的英文關鍵字，"
                "這些關鍵字必須同時符合這個標題的方向、也跟上述實際的模型/資料/方法相關。\n"
                "請「只」輸出以下一行，不要有其他文字：\n"
                "QUERY: <2 到 6 個英文關鍵字，空白分隔，不要加引號或布林運算子>"
            )
            usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            text = self._call_gemini(prompt, usage_total)

            query_match = re.search(r"QUERY:\s*(.+)", text)
            arxiv_query = query_match.group(1).strip() if query_match else user_title

            return {"topic": user_title, "arxiv_query": arxiv_query}

        prompt = (
            "你是學術論文寫作助手。請根據以下資料探勘實驗結果，"
            "判斷這份研究適合的研究主題與 arXiv 查詢關鍵字。\n\n"
            f"【資料探勘實驗結果】\n{results_text}\n\n"
            "請「只」輸出以下兩行，不要有其他文字：\n"
            "TOPIC: <繁體中文的研究主題，一句話，供論文標題使用>\n"
            "QUERY: <2 到 6 個英文關鍵字，空白分隔，適合直接拿去查 arXiv，"
            "不要加引號或布林運算子>"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)

        topic_match = re.search(r"TOPIC:\s*(.+)", text)
        query_match = re.search(r"QUERY:\s*(.+)", text)

        topic = topic_match.group(1).strip() if topic_match else "資料探勘實驗研究"
        arxiv_query = query_match.group(1).strip() if query_match else topic

        return {"topic": topic, "arxiv_query": arxiv_query}

    def search_arxiv_candidates(self, mining_results: dict, user_title: str | None = None) -> dict:
        """分類 mining_results 產生查詢字，查詢 arXiv 取得候選論文清單（不寫入向量庫）。"""
        classification = self.classify_topic(mining_results, user_title)
        candidates = arxiv_source.search_arxiv(classification["arxiv_query"])
        return {
            "topic": classification["topic"],
            "arxiv_query": classification["arxiv_query"],
            "candidates": candidates,
        }

    def ingest_arxiv_selection(self, project_id: int, candidates: List[dict]) -> dict:
        """下載選中的 arXiv 論文全文並加入索引。

        單篇下載/解析失敗時跳過並記錄，不中斷整體流程；若全部失敗則回傳錯誤。
        同一個 project 裡，arxiv_id 已經存在就跳過，不重複塞進索引。
        """
        ingested: List[str] = []
        failed: List[str] = []

        for candidate in candidates:
            title = candidate.get("title", "")
            pdf_url = candidate.get("pdf_url", "")
            arxiv_id = candidate.get("arxiv_id", "")

            if arxiv_id and self._store.find_by_arxiv_id(project_id, arxiv_id) is not None:
                logger.info("跳過已存在的 arXiv 論文：%s (%s)", title, arxiv_id)
                ingested.append(title)
                continue

            try:
                content = arxiv_source.fetch_pdf_text(pdf_url)
                if not content.strip():
                    raise ValueError("PDF 未解析出任何文字")
            except Exception as e:
                logger.warning("下載/解析 arXiv PDF 失敗：%s (%s)", title, e)
                failed.append(title)
                continue

            result = self.add_paper(
                project_id=project_id,
                title=title,
                content=content,
                metadata={
                    "author": candidate.get("authors", ""),
                    "year": candidate.get("year", ""),
                    "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
                    "arxiv_id": arxiv_id,
                },
            )
            if result.get("success"):
                ingested.append(title)
            else:
                failed.append(title)

        if not ingested:
            return {
                "success": False,
                "error": "所有候選論文皆下載/解析失敗，無法建立參考文獻庫",
                "ingested": ingested,
                "failed": failed,
            }

        return {"success": True, "ingested": ingested, "failed": failed}

    def generate_insight(self, mining_results: dict) -> str:
        """讀 mining_results 摘要，用 Gemini 生成一段繁體中文洞察文字，供 /results 儀表板顯示。"""
        results_text = self._format_datamind_output(mining_results)
        prompt = (
            "你是資料科學顧問。請根據以下機器學習實驗結果，"
            "用繁體中文寫一段簡短的洞察摘要（約 2 到 3 句話），"
            "說明表現最好的模型、關鍵發現，以及是否適合投入實際應用。\n\n"
            f"【機器學習實驗結果】\n{results_text}\n\n"
            "請「只」輸出洞察摘要本身，不要加上任何標題、條列符號或多餘說明文字。"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        return text.strip()

    _TAB_PROMPT_HINTS: Dict[str, str] = {
        "matrix": "請指出模型最容易把哪個類別誤判成哪個類別，這對臨床判讀有什麼提醒。",
        "roc": "請說明這個 AUC 數值代表模型的判別力好不好，並簡述曲線形狀反映的意義。",
        "pr": "請說明在類別不平衡的情境下 PR 曲線的意義，以及這個結果顯示模型在少數類別上的表現如何。",
        "calibration": "請說明這個模型輸出的機率是否可信賴，是偏樂觀還是偏保守。",
        "perClass": "請指出表現最差的類別，並簡述可能的原因或後續建議。",
    }

    _TAB_LABELS: Dict[str, str] = {
        "matrix": "混淆矩陣",
        "roc": "ROC 曲線",
        "pr": "PR 曲線",
        "calibration": "校準曲線",
        "perClass": "各類別指標",
    }

    _MAX_TAB_TEXT_CHARS = 4000

    @staticmethod
    def _sample_curve_points(
        xs: List[float], ys: List[float], n: int = 5
    ) -> List[tuple]:
        """均勻取樣最多 n 個點，避免把整條曲線的完整座標陣列丟給 Gemini。"""
        if not xs or not ys:
            return []
        if len(xs) <= n:
            return list(zip(xs, ys))
        step = (len(xs) - 1) / (n - 1)
        indices = sorted({round(i * step) for i in range(n)})
        return [(xs[i], ys[i]) for i in indices]

    def _find_tab_result(
        self, mining_results: dict, model_name: str, split_name: str
    ) -> Optional[dict]:
        for r in mining_results.get("results", []):
            if (
                r.get("model_name") == model_name
                and r.get("split_name") == split_name
                and "error" not in r
            ):
                return r
        return None

    def _find_tab_results(
        self, mining_results: dict, model_names: List[str], split_name: str
    ) -> List[dict]:
        """依 model_names 的順序回傳所有符合的結果；跳過找不到或有 error 的模型，
        不因為某個模型缺資料就整批失敗——這是刻意的寬鬆行為，圖例上顯示中的模型
        理論上都該有資料，這裡只是防禦性處理。
        """
        by_key = {
            (r.get("model_name"), r.get("split_name")): r
            for r in mining_results.get("results", [])
            if "error" not in r
        }
        return [
            by_key[(name, split_name)]
            for name in model_names
            if (name, split_name) in by_key
        ]

    def _format_multi_model_curve_data(self, results: List[dict], tab: str) -> Optional[str]:
        """把多個模型的 ROC/PR 曲線資料組成一段文字，每個模型各自一個 ▶ 區塊，
        照抄 _format_datamind_output() 既有的分段慣例。"""
        blocks = []
        for result in results:
            curve_text = self._format_roc_pr_curve_text(result, tab)
            if curve_text is None:
                continue
            blocks.append(f"▶ {result.get('model_name', 'N/A')}\n{curve_text}")
        if not blocks:
            return None
        header = "【ROC 曲線】" if tab == "roc" else "【PR 曲線】"
        return f"{header}\n\n" + "\n\n".join(blocks)

    def _format_roc_pr_curve_text(self, result: dict, tab: str) -> Optional[str]:
        """單一模型的 ROC/PR 曲線格式化文字（不含【ROC 曲線】這種外層標題），
        給單模型跟多模型兩條路徑共用，各自決定要不要加標題/模型名稱前綴。
        """
        curve = result.get("roc_pr_curve")
        if not curve:
            return None
        metric_key = "auc" if tab == "roc" else "auprc"
        metric_val = next(
            (m.get("value") for m in result.get("metrics", []) if m.get("metric") == metric_key),
            None,
        )
        sub = curve.get("roc" if tab == "roc" else "pr", {})
        xs_key, ys_key = ("fpr", "tpr") if tab == "roc" else ("recall", "precision")
        points = self._sample_curve_points(sub.get(xs_key, []), sub.get(ys_key, []))
        points_str = "、".join(f"({x:.2f}, {y:.2f})" for x, y in points) or "N/A"
        metric_label = "AUC" if tab == "roc" else "AUPRC"
        metric_str = f"{metric_val:.4f}" if isinstance(metric_val, (int, float)) else "N/A"
        axis_label = "FPR, TPR" if tab == "roc" else "Recall, Precision"
        return (
            f"正類：{curve.get('pos_label', 'N/A')}\n"
            f"{metric_label}：{metric_str}\n"
            f"取樣座標點（{axis_label}）：{points_str}"
        )

    def _format_tab_data(self, result: dict, tab: str) -> Optional[str]:
        """只挑該分頁需要的欄位轉成精簡文字，不送整包原始資料。"""
        if tab == "matrix":
            cm = result.get("confusion_matrix")
            if not cm:
                return None
            labels = cm.get("labels", [])
            matrix = cm.get("matrix", [])
            rows = []
            for i, label in enumerate(labels):
                row = matrix[i] if i < len(matrix) else []
                row_str = "、".join(
                    f"預測{labels[j]}={row[j]}" for j in range(min(len(row), len(labels)))
                )
                rows.append(f"實際{label}：{row_str}")
            return "【混淆矩陣】\n" + "\n".join(rows)

        if tab in ("roc", "pr"):
            curve_text = self._format_roc_pr_curve_text(result, tab)
            if curve_text is None:
                return None
            return f"【{'ROC' if tab == 'roc' else 'PR'} 曲線】\n{curve_text}"

        if tab == "calibration":
            curve = result.get("calibration_curve")
            if not curve:
                return None
            prob_true = curve.get("prob_true", [])
            prob_pred = curve.get("prob_pred", [])
            points_str = "、".join(
                f"(預測{p:.2f}, 實際{t:.2f})"
                for p, t in zip(prob_pred, prob_true)
                if isinstance(p, (int, float)) and isinstance(t, (int, float))
            ) or "N/A"
            return (
                f"【校準曲線】\n"
                f"正類：{curve.get('pos_label', 'N/A')}\n"
                f"各 bin（預測機率, 實際正類比例）：{points_str}"
            )

        if tab == "perClass":
            pcm = result.get("per_class_metrics")
            if not pcm:
                return None
            labels = pcm.get("labels", [])
            precision = pcm.get("precision", [])
            recall = pcm.get("recall", [])
            f1 = pcm.get("f1", [])
            support = pcm.get("support", [])
            rows = []
            for i, label in enumerate(labels):
                p = precision[i] if i < len(precision) else None
                r = recall[i] if i < len(recall) else None
                f = f1[i] if i < len(f1) else None
                s = support[i] if i < len(support) else None
                p_str = f"{p:.4f}" if isinstance(p, (int, float)) else "N/A"
                r_str = f"{r:.4f}" if isinstance(r, (int, float)) else "N/A"
                f_str = f"{f:.4f}" if isinstance(f, (int, float)) else "N/A"
                rows.append(f"{label}：precision={p_str}, recall={r_str}, f1={f_str}, 樣本數={s}")
            return "【各類別指標】\n" + "\n".join(rows)

        return None

    def generate_tab_insight(
        self, mining_results: dict, tab: str, model_name: str, split_name: str,
        model_names: Optional[List[str]] = None,
    ) -> str:
        """針對 workflow 結果裡某個分頁生成一段繁體中文解讀。

        model_names 有帶值（非空 list）時走多模型比較路徑（目前只有 ROC/PR 分頁的
        前端會帶這個參數）；否則維持原本的單一 (model_name × split_name) 路徑，
        matrix/calibration/perClass 分頁完全不受影響。
        """
        if model_names:
            results = self._find_tab_results(mining_results, model_names, split_name)
            if not results:
                return "找不到對應的結果資料。"

            # Fix 2：先濾掉沒有曲線資料的模型，這樣下面 len(results) 用來組 prompt
            # 文字時，才會跟 _format_multi_model_curve_data() 實際列出的 ▶ 區塊數一致，
            # 不會出現「以下是 3 個模型」但只列出 2 個的落差。
            results = [r for r in results if r.get("roc_pr_curve")]

            # Fix 1：篩選/縮減圖例後如果只剩 1 個模型，這其實就是單模型情境，
            # 不該套用「請比較它們的表現」這種多模型 prompt——退回單模型路徑，
            # 讓它產生跟真的只傳單一 model_name 時完全相同的 prompt。
            if len(results) == 1:
                model_name = results[0].get("model_name") or model_name
                model_names = None

        if model_names:
            tab_text = self._format_multi_model_curve_data(results, tab)
            if tab_text is None:
                return "此分頁沒有可供解讀的資料。"

            if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
                tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

            ideal_hint = "ROC 曲線越靠左上角" if tab == "roc" else "PR 曲線越靠右上角"
            hint = self._TAB_PROMPT_HINTS.get(tab, "")
            prompt = (
                "你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果。\n"
                f"以下是 {len(results)} 個模型在「{split_name}」這筆結果的"
                f"{'ROC' if tab == 'roc' else 'PR'} 曲線資料，請比較它們的表現：\n\n"
                f"{tab_text}\n\n"
                f"請用繁體中文寫 3 到 5 句話的解讀，明確指出哪個模型的表現最接近理想"
                f"（{ideal_hint}），並簡短說明其他模型的相對表現。{hint}\n"
                "請「只」輸出解讀本身，不要加上任何標題、條列符號或多餘說明文字。"
            )
            usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            text = self._call_gemini(prompt, usage_total)
            if text.startswith("（生成失敗："):
                raise RuntimeError(text)
            return text.strip()

        # 單模型路徑（既有邏輯，完全不動；model_names 只剩 1 個符合模型時也會走這裡）
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        hint = self._TAB_PROMPT_HINTS.get(tab, "")
        prompt = (
            "你是資料科學顧問，正在協助解讀一份醫學研究的機器學習分類結果。\n"
            f"以下是模型「{model_name}」在「{split_name}」這筆結果的資料：\n\n"
            f"{tab_text}\n\n"
            f"請用繁體中文寫 2 到 4 句話的解讀。{hint}\n"
            "請「只」輸出解讀本身，不要加上任何標題、條列符號或多餘說明文字。"
        )
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        if text.startswith("（生成失敗："):
            raise RuntimeError(text)
        return text.strip()

    def chat_about_tab(
        self,
        mining_results: dict,
        tab: str,
        model_name: str,
        split_name: str,
        history: List[dict],
        message: str,
        model_names: Optional[List[str]] = None,
    ) -> str:
        """針對 workflow 結果裡某個分頁的資料，跟使用者進行範圍限定的多輪問答。

        model_names 有帶值時，context 涵蓋多個模型的資料（目前只有 ROC/PR 分頁的前端
        會帶這個參數）；否則維持原本單一 (model_name × split_name) 的既有邏輯。

        跟 chat_about_results() 不同：這裡不帶 arXiv 查詢工具（用不帶 tools 的 self._model，
        不是 self._chat_model），範圍限定在這個分頁的資料，不做例外處理——Gemini 呼叫本身的
        例外、resp.text 解析例外都直接往上拋，讓路由層統一接住、回傳 success:false。
        """
        tab_label = self._TAB_LABELS.get(tab, tab)

        if model_names:
            results = self._find_tab_results(mining_results, model_names, split_name)
            if not results:
                return "找不到對應的結果資料。"

            # Fix 2：同 generate_tab_insight()，先濾掉沒有曲線資料的模型，
            # 讓下面 context 文字裡的模型數跟實際列出的 ▶ 區塊數一致。
            results = [r for r in results if r.get("roc_pr_curve")]

            # Fix 1：篩選/縮減圖例後如果只剩 1 個模型，退回單模型路徑，
            # 產生跟真的只傳單一 model_name 時完全相同的 context 文字，
            # 不要問「這個模型比其他模型…」這種沒有其他模型可比的問題。
            if len(results) == 1:
                model_name = results[0].get("model_name") or model_name
                model_names = None

        if model_names:
            tab_text = self._format_multi_model_curve_data(results, tab)
            if tab_text is None:
                return "此分頁沒有可供解讀的資料。"

            if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
                tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

            context_turns = [
                {
                    "role": "user",
                    "parts": [
                        f"以下是這次機器學習實驗中「{tab_label}」的資料（{len(results)} 個模型的比較），"
                        "請記住這些資訊，之後我會針對這個圖表提問。"
                        "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                        "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                        "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                        f"{tab_text}"
                    ],
                },
                {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
            ]
            prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

            chat = self._model.start_chat(history=context_turns + prior_turns)
            resp = chat.send_message(message)
            return (getattr(resp, "text", "") or "").strip()

        # 單模型路徑（既有邏輯，完全不動；model_names 只剩 1 個符合模型時也會走這裡）
        result = self._find_tab_result(mining_results, model_name, split_name)
        if result is None:
            return "找不到對應的結果資料。"

        tab_text = self._format_tab_data(result, tab)
        if tab_text is None:
            return "此分頁沒有可供解讀的資料。"

        if len(tab_text) > self._MAX_TAB_TEXT_CHARS:
            tab_text = tab_text[: self._MAX_TAB_TEXT_CHARS] + "\n…（資料量過大，僅取部分內容）"

        context_turns = [
            {
                "role": "user",
                "parts": [
                    f"以下是這次機器學習實驗中「{tab_label}」的資料，請記住這些資訊，"
                    "之後我會針對這個圖表/表格提問。"
                    "你只能回答跟這個圖表或這次 workflow 執行結果直接相關的問題；"
                    "如果我問到無關的話題（例如其他學術文獻查證、與此資料無關的閒聊），"
                    "請禮貌地簡短說明你只能討論這個分頁的內容，不需要展開回答。\n\n"
                    f"{tab_text}"
                ],
            },
            {"role": "model", "parts": [f"好的，我已經了解「{tab_label}」這個分頁的資料，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._model.start_chat(history=context_turns + prior_turns)
        resp = chat.send_message(message)
        return (getattr(resp, "text", "") or "").strip()

    def score_paper(self, paper_text: str) -> dict:
        """依 _JOURNAL_RUBRICS 對論文全文逐期刊評分，各期刊各一次獨立的 Gemini JSON 呼叫。

        單一期刊評分失敗（Gemini 例外或 JSON 解析失敗）時，最多重試 _SCORE_MAX_ATTEMPTS 次
        （間隔 _SCORE_RETRY_DELAY_SECONDS 秒），全部嘗試皆失敗才跳過並記錄，不中斷整體流程；
        若全部期刊皆失敗則回傳 {"success": False, "error": ...}。
        """
        journal_scores: List[dict] = []
        failed_journals: List[str] = []
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for rubric in _JOURNAL_RUBRICS:
            prompt = self._build_score_prompt(paper_text, rubric)
            last_error: Exception | None = None

            for attempt in range(1, _SCORE_MAX_ATTEMPTS + 1):
                try:
                    raw = self._call_gemini_json(prompt, usage_total)
                except Exception as e:
                    # Gemini 呼叫本身失敗（網路、逾時等）屬於暫時性錯誤，值得重試。
                    last_error = e
                    logger.warning(
                        "期刊評分失敗（第 %d/%d 次嘗試，Gemini 呼叫失敗）：%s (%s)",
                        attempt, _SCORE_MAX_ATTEMPTS, rubric["name"], e,
                    )
                    if attempt < _SCORE_MAX_ATTEMPTS:
                        time.sleep(_SCORE_RETRY_DELAY_SECONDS)
                    continue

                try:
                    parsed = self._safe_parse_json(raw)
                    if parsed is None:
                        raise ValueError("Gemini 回傳非合法 JSON")
                    self._validate_score_shape(parsed)
                except (ValueError, TypeError, AttributeError) as e:
                    # temperature=0 下，同一個 prompt 的解析/驗證失敗幾乎是決定性的，
                    # 重試無法改變結果，直接判定此期刊失敗、不再重試以節省成本與時間。
                    last_error = e
                    logger.warning(
                        "期刊評分失敗（格式錯誤，不重試）：%s (%s)",
                        rubric["name"], e,
                    )
                    break

                journal_scores.append({
                    "journal": rubric["name"],
                    "journal_full_name": rubric["full_name"],
                    "overall_score": int(parsed["overall_score"]),
                    "overall_comment": str(parsed.get("overall_comment") or ""),
                    "criteria": [
                        {
                            "name": str(c["name"]),
                            "score": int(c["score"]),
                            "comment": str(c["comment"]),
                        }
                        for c in parsed["criteria"]
                    ],
                    "suggestions": [str(s) for s in parsed.get("suggestions", [])],
                })
                last_error = None
                break

            if last_error is not None:
                failed_journals.append(rubric["name"])

        if not journal_scores:
            return {
                "success": False,
                "error": "所有期刊評分皆失敗",
                "failed_journals": failed_journals,
            }

        return {
            "success": True,
            "journal_scores": journal_scores,
            "failed_journals": failed_journals,
            "usage": usage_total,
        }

    def generate_structured_analysis(self, mining_results: dict) -> dict:
        """讀 mining_results 摘要，用 Gemini 生成四個面向的結構化分析，供 ResultView.vue 顯示。"""
        results_text = self._format_datamind_output(mining_results)
        prompt = (
            "你是資料科學顧問。請根據以下機器學習實驗結果，"
            "用繁體中文分別針對四個面向各寫一段簡短分析（每段約 2 到 4 句話）：\n"
            "1. model_comparison：模型表現比較與選擇建議（哪個模型最好、為什麼、實務上該選哪個）\n"
            "2. data_insights：資料與特徵層面的洞察（哪些前處理／特徵工程步驟影響最大、資料品質相關發現）\n"
            "3. risks：風險與限制提示（例如樣本數、過擬合疑慮、指標本身的侷限性）\n"
            "4. recommendations：後續建議行動（建議再嘗試的模型/參數、建議收集的資料、下一步分析方向）\n\n"
            f"【機器學習實驗結果】\n{results_text}\n\n"
            "請輸出 JSON，格式如下（只輸出 JSON，不要有其他文字）：\n"
            '{"model_comparison": "...", "data_insights": "...", "risks": "...", "recommendations": "..."}'
        )

        try:
            resp = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    # gemini-2.5-flash 的隱藏「thinking」token 也算在 max_output_tokens 裡，
                    # 2048 對稍微複雜一點的實驗結果就會被吃光，JSON 輸出被截斷到一半失敗。
                    # 跟檔案內其他呼叫（_call_gemini 預設 8192）看齊，留足夠空間給 thinking + 實際輸出。
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
            )
            text = getattr(resp, "text", "") or ""
            data = json.loads(text)
            if not isinstance(data, dict):
                data = {}
        except Exception as e:
            logger.error("結構化分析生成失敗：%s", e)
            data = {}

        return {
            "model_comparison": str(data.get("model_comparison", "")),
            "data_insights": str(data.get("data_insights", "")),
            "risks": str(data.get("risks", "")),
            "recommendations": str(data.get("recommendations", "")),
        }

    def chat_about_results(self, mining_results: dict, history: List[dict], message: str) -> dict:
        """跟使用者針對 mining_results 進行多輪對話，AI 可自主呼叫 search_arxiv 工具查詢文獻。"""
        results_text = self._format_datamind_output(mining_results)
        context_turns = [
            {
                "role": "user",
                "parts": [
                    "以下是這次機器學習實驗的資料探勘結果，請記住這些資訊，"
                    "之後我會針對這份結果提問，如果我問到跟學術文獻相關的問題，"
                    "你可以呼叫 search_arxiv 工具查詢 arXiv 上的相關論文。\n\n"
                    f"【機器學習實驗結果】\n{results_text}"
                ],
            },
            {"role": "model", "parts": ["好的，我已經了解這次實驗結果，請問有什麼問題？"]},
        ]
        prior_turns = [{"role": h["role"], "parts": [h["text"]]} for h in history]

        chat = self._chat_model.start_chat(history=context_turns + prior_turns)

        try:
            resp = chat.send_message(message)
        except Exception as e:
            logger.error("對話生成失敗：%s", e)
            return {"reply": f"（對話發生錯誤：{e}）", "papers": []}

        function_call = None
        try:
            for part in resp.parts:
                if part.function_call and part.function_call.name:
                    function_call = part.function_call
                    break
        except Exception as e:
            # resp.parts 在回應被安全過濾／無候選結果等情況下會拋 ValueError，
            # 這裡跟其他分支一樣降級成錯誤訊息回覆，不讓整個 request 500
            logger.error("解析 Gemini 回應失敗：%s", e)
            return {"reply": f"（對話發生錯誤：{e}）", "papers": []}

        papers: List[dict] = []
        if function_call is not None:
            query = str(function_call.args.get("query", ""))
            try:
                papers = arxiv_source.search_arxiv(query, max_results=5)
                function_result: dict = {"result": papers}
            except Exception as e:
                logger.warning("對話中 arXiv 搜尋失敗：%s", e)
                papers = []
                function_result = {"error": f"查詢 arXiv 時發生錯誤：{e}"}

            function_response_part = genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_call.name,
                    response=function_result,
                )
            )
            try:
                resp = chat.send_message(function_response_part)
            except Exception as e:
                logger.error("對話生成失敗（function response 後）：%s", e)
                return {"reply": f"（對話發生錯誤：{e}）", "papers": papers}

        try:
            reply_text = (getattr(resp, "text", "") or "").strip()
        except Exception as e:
            # resp.text 跟 resp.parts 一樣，在回應被安全過濾等情況下會拋 ValueError
            logger.error("解析 Gemini 回應文字失敗：%s", e)
            return {"reply": f"（對話發生錯誤：{e}）", "papers": papers}

        return {"reply": reply_text, "papers": papers}

    def get_status(self, project_id: int) -> dict:
        return self._store.get_status(project_id)

    def delete_paper(self, project_id: int, paper_id: str) -> dict:
        ok = self._store.delete_paper(project_id, paper_id)
        if ok:
            return {"success": True, "message": f"已刪除論文 {paper_id}"}
        return {"success": False, "message": f"找不到論文 {paper_id}"}

    def clear(self, project_id: int) -> dict:
        self._store.clear(project_id)
        return {"success": True, "message": "已清空論文庫"}

    # ── DataMind 輸出格式化 ───────────────────────────────────────────────────

    def _format_datamind_output(self, mining_results: dict) -> str:
        """
        將 DataMind /api/models/workflow/execute 的回傳值轉成
        Gemini 可讀的摘要文字。
        """
        parts: List[str] = []

        # 類別分布
        dist = mining_results.get("class_distribution")
        if dist:
            counts = dist.get("counts", {})
            ratio = dist.get("imbalance_ratio")
            parts.append(
                f"【資料集類別分布】\n"
                f"類別統計：{counts}\n"
                f"不平衡比率：{ratio if ratio is not None else 'N/A'}"
            )

        # 前處理流程
        # 注意：不能讀 mining_results["preprocess_variants"]——那是 workflow_service.py 直接把
        # 原始 preprocess_pipelines（List[List[Dict]]，未與 feature engineering 配對）塞進去的，
        # 每個元素本身就是 list、不是 dict，對它呼叫 .get() 會噴 AttributeError。
        # 正確配對好的 preprocess_steps / feature_engineering_steps 其實在 results 的每一筆結果裡。
        seen_pipeline_indices: set = set()
        for r in mining_results.get("results", []):
            idx = r.get("preprocess_pipeline_index")
            if idx is None or idx in seen_pipeline_indices:
                continue
            seen_pipeline_indices.add(idx)
            pp = "、".join(s.get("type", "") for s in r.get("preprocess_steps", [])) or "無"
            fe = "、".join(s.get("type", "") for s in r.get("feature_engineering_steps", [])) or "無"
            parts.append(f"【前處理流程 {idx + 1}】\n預處理：{pp}\n特徵工程：{fe}")

        # 各模型結果
        valid_results = [r for r in mining_results.get("results", []) if "error" not in r]
        if valid_results:
            parts.append("【模型實驗結果】")
            for r in valid_results:
                model_name = r.get("model_name", "Unknown")
                split = r.get("split_name", "")
                fe_steps = r.get("feature_engineering_steps", []) or []
                fe_str = "、".join(s.get("type", "") for s in fe_steps) or "無"

                # 評估指標
                metric_strs: List[str] = []
                for m in r.get("metrics", []):
                    val = m.get("value")
                    if val is None:
                        continue
                    s = f"{m['metric'].upper()}={val:.4f}"
                    if m.get("ci_lower") is not None and m.get("ci_upper") is not None:
                        s += f" (95%CI {m['ci_lower']:.4f}–{m['ci_upper']:.4f})"
                    metric_strs.append(s)

                # 特徵重要性前 5
                fi = r.get("feature_importance") or []
                fi_str = (
                    "、".join(f"{f['feature']}({f['importance']:.4f})" for f in fi[:5])
                    if fi else "N/A"
                )

                # 驗證設定
                vc = r.get("validation_config", {})
                val_str = vc.get("method", "N/A")
                if vc.get("n_splits"):
                    val_str += f" (k={vc['n_splits']})"

                resampling = r.get("resampling_method", "none")
                best_params = r.get("best_params") or {}

                parts.append(
                    f"\n▶ {model_name}（{split}）\n"
                    f"  驗證方法：{val_str}\n"
                    f"  重採樣：{resampling}\n"
                    f"  特徵工程：{fe_str}\n"
                    f"  特徵數：{r.get('feature_count', 'N/A')}，"
                    f"訓練樣本：{r.get('row_count', 'N/A')}\n"
                    f"  評估指標：{', '.join(metric_strs) or 'N/A'}\n"
                    f"  重要特徵（前5）：{fi_str}\n"
                    f"  最佳超參數：{best_params or '無'}"
                )

        return "\n\n".join(parts)

    # ── Gemini 呼叫 ───────────────────────────────────────────────────────────

    def _call_gemini(self, prompt: str, usage_total: dict) -> str:
        try:
            resp = self._model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=8192,
                ),
            )
            text = getattr(resp, "text", "") or ""
            usage = getattr(resp, "usage_metadata", None)
            if usage:
                usage_total["prompt_tokens"] = (
                    (usage_total["prompt_tokens"] or 0) + (getattr(usage, "prompt_token_count", 0) or 0)
                )
                usage_total["completion_tokens"] = (
                    (usage_total["completion_tokens"] or 0)
                    + (getattr(usage, "candidates_token_count", 0) or 0)
                )
                usage_total["total_tokens"] = (
                    (usage_total["total_tokens"] or 0) + (getattr(usage, "total_token_count", 0) or 0)
                )
            return text
        except Exception as e:
            logger.error("Gemini 生成失敗：%s", e)
            return f"（生成失敗：{e}）"

    def _call_gemini_json(self, prompt: str, usage_total: dict) -> str:
        """比照 _call_gemini()，但要求 Gemini 以 JSON 格式回傳，且不吞掉例外——
        由呼叫端（如 score_paper()）自行決定失敗時是否跳過。"""
        resp = self._model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                # gemini-2.5-flash 的隱藏「thinking」token 也算在 max_output_tokens 裡，
                # 4096 對評分這種要求多項準則各自附中文理由的輸出會被吃光，JSON 被截斷到
                # 一半就不是合法 JSON 了。跟 generate_structured_analysis() 一樣抓 8192。
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )
        text = getattr(resp, "text", "") or ""
        usage = getattr(resp, "usage_metadata", None)
        if usage:
            usage_total["prompt_tokens"] = (
                (usage_total["prompt_tokens"] or 0) + (getattr(usage, "prompt_token_count", 0) or 0)
            )
            usage_total["completion_tokens"] = (
                (usage_total["completion_tokens"] or 0)
                + (getattr(usage, "candidates_token_count", 0) or 0)
            )
            usage_total["total_tokens"] = (
                (usage_total["total_tokens"] or 0) + (getattr(usage, "total_token_count", 0) or 0)
            )
        return text

    @staticmethod
    def _safe_parse_json(text: str) -> Optional[dict]:
        """容錯解析 Gemini 回傳的 JSON 文字：先直接解析，失敗則剝除 ```json 圍欄，
        再失敗則用正規表達式抓出第一個 {...} 區塊。全部失敗回傳 None。"""
        raw = text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        fenced = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        fenced = re.sub(r"\s*```$", "", fenced)
        try:
            return json.loads(fenced.strip())
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", fenced)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _validate_score_shape(parsed: dict) -> None:
        """檢查 score_paper() 解析出的 JSON 是否符合預期結構，不符合則拋出 ValueError，
        交由呼叫端的重試/失敗邏輯處理，避免不完整的 Gemini 回傳被當成成功結果。"""
        if not isinstance(parsed.get("overall_score"), (int, float)):
            raise ValueError(f"overall_score 缺漏或非數字：{parsed.get('overall_score')!r}")

        criteria = parsed.get("criteria")
        if not isinstance(criteria, list) or len(criteria) != len(_SCORE_CRITERIA):
            raise ValueError(
                f"criteria 應包含 {len(_SCORE_CRITERIA)} 項，實際：{criteria!r}"
            )
        for c in criteria:
            if not isinstance(c, dict) or not isinstance(c.get("score"), (int, float)) \
                    or not c.get("name") or not c.get("comment"):
                raise ValueError(f"criteria 項目格式不正確：{c!r}")

        suggestions = parsed.get("suggestions")
        if not isinstance(suggestions, list) or len(suggestions) == 0:
            raise ValueError(f"suggestions 應至少包含 1 項，實際：{suggestions!r}")

    # ── Prompt 建立 ───────────────────────────────────────────────────────────

    def _build_section_prompt(
        self,
        section_name: str,
        topic: str,
        results_text: str,
        local_refs: Dict[int, dict],
        language: str,
    ) -> str:
        target = _SECTION_WORD_TARGETS.get(section_name, 600)
        writing_focus = _SECTION_WRITING_FOCUS.get(section_name, "")

        ref_lines = [
            f"[{lid}] 論文：《{info['chunk'].title}》\n"
            f"     摘錄：{info['chunk'].content[:400]}"
            for lid, info in local_refs.items()
        ]
        ref_block = (
            "\n\n".join(ref_lines)
            if ref_lines
            else "（目前論文庫中無相關參考文獻，請根據一般醫學知識撰寫）"
        )

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

    @staticmethod
    def _build_score_prompt(paper_text: str, rubric: Dict[str, str]) -> str:
        criteria_list = "\n".join(f"- {c}" for c in _SCORE_CRITERIA)
        return (
            f"你是《{rubric['full_name']}》（{rubric['name']}）的資深審稿人。"
            f"該期刊特別重視：{rubric['emphasis']}。\n\n"
            "請依照以下 6 項準則評估這篇論文，每項給 0 到 100 分並附上簡短的中文理由，"
            "最後再給一個 0 到 100 的總分、一句總評，以及 2 到 5 條具體的修改建議。\n\n"
            f"【評分準則】\n{criteria_list}\n\n"
            f"【論文全文】\n{paper_text}\n\n"
            "請「只」輸出以下形狀的 JSON，不要有其他文字或 Markdown 圍欄：\n"
            "{\n"
            '  "overall_score": <0-100 整數>,\n'
            '  "overall_comment": "<一句話總評，20 到 40 字繁體中文，'
            '須具體點出本文相對於本期刊發表門檻的主要優勢與待加強之處，不可只是空泛的鼓勵語句>",\n'
            '  "criteria": [\n'
            '    {"name": "<準則名稱，須完全比照上面清單>", "score": <0-100 整數>, "comment": "<中文理由>"},\n'
            "    ...\n"
            "  ],\n"
            '  "suggestions": ["<修改建議1>", "<修改建議2>", ...]\n'
            "}"
        )

    # ── 引用處理 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _localref_to_global(text: str, local_refs: Dict[int, dict]) -> str:
        """將章節內的本地 [n]（含 [n, m] 組合引用）替換成全域 [n]，並去除相鄰重複引用。"""
        def replace(m: re.Match) -> str:
            local_ids = [int(n) for n in re.findall(r"\d+", m.group(1))]
            global_ids: List[str] = []
            for local_id in local_ids:
                info = local_refs.get(local_id)
                global_ids.append(str(info["global_ref_id"]) if info else str(local_id))
            return "".join(f"[{gid}]" for gid in global_ids)

        text = re.sub(_CITATION_PATTERN, replace, text)
        # 去除相鄰重複引用，如 [1][1] → [1]
        return re.sub(r"(\[\d+\])(?:\1)+", r"\1", text)

    @staticmethod
    def _build_citation_map(
        section_name: str,
        section_text: str,
        local_refs: Dict[int, dict],
        global_ref_list: List[dict],
        citation_map: List[dict],
    ) -> None:
        """
        逐段解析引用標記，填入 citation_map。

        section_text 是**尚未**把本地編號轉成全域編號的原始章節文字——
        必須用本地編號直接查 local_refs，才知道這段話實際引用的是哪個 chunk
        （同一篇論文在候選池裡可能有好幾個不同的 chunk，各自對應不同的 local_id）。

        citation_map 的每一筆結構：
        {
            section        : 章節名稱
            paragraph_index: 該段在章節中的位置（0-indexed）
            text           : 段落文字（含 [n] 標記，已轉成全域編號——
                              跟 _build_citation_report() 顯示的其他編號一致）
            cited_ref_ids  : 該段引用的全域 ref_id 列表（去重、由小到大）
            sources        : 每個引用的詳細資訊（供前端展示）
        }
        """
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
        for para_idx, para in enumerate(paragraphs):
            local_ids_in_para: List[int] = []
            for m in _CITATION_PATTERN.finditer(para):
                local_ids_in_para.extend(int(n) for n in re.findall(r"\d+", m.group(1)))
            if not local_ids_in_para:
                continue

            # 同一篇論文（同一個 global_ref_id）被段落內多個不同 local_id 重複引用時，
            # 取文字裡先出現的那個（閱讀順序），不做進一步仲裁
            first_local_id_for_gid: Dict[int, int] = {}
            for local_id in local_ids_in_para:
                info = local_refs.get(local_id)
                if not info:
                    continue
                gid = info["global_ref_id"]
                first_local_id_for_gid.setdefault(gid, local_id)

            if not first_local_id_for_gid:
                continue

            cited_gids = sorted(first_local_id_for_gid)
            sources: List[dict] = []
            for gid in cited_gids:
                info = local_refs[first_local_id_for_gid[gid]]
                ref_meta = next((r for r in global_ref_list if r["ref_id"] == gid), {})
                sources.append({
                    "ref_id": gid,
                    "paper_id": info["chunk"].paper_id,
                    "title": ref_meta.get("title", ""),
                    "author": ref_meta.get("author", ""),
                    "year": ref_meta.get("year", ""),
                    # 提供被引用的原始 chunk 內容，方便前端顯示引用依據
                    "relevant_chunk": info["chunk"].content[:400],
                    # 用 is not None 明確判斷，而不是靠 truthiness——rerank_score
                    # 合法值為 0.0 時，用 `or` 會被誤判成「沒有值」而錯誤 fall back 到 score
                    "similarity_score": round(
                        info.get("rerank_score")
                        if info.get("rerank_score") is not None
                        else info["score"],
                        4,
                    ),
                })

            citation_map.append({
                "section": section_name,
                "paragraph_index": para_idx,
                "text": PaperRAGService._localref_to_global(para, local_refs),
                "cited_ref_ids": cited_gids,
                "sources": sources,
            })

    # ── 引用對照報告 ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_citation_report(
        global_ref_list: List[dict],
        citation_map: List[dict],
    ) -> str:
        """
        依參考文獻分組，記錄文章中每一段引用內文對應到該文獻的哪一段原文摘錄。
        僅包含實際被引用（citation_map 中出現過）的文獻。
        """
        if not global_ref_list:
            return "（本文未實際引用任何參考文獻）"

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
                parts.append(f"### {entry['section']} · 第 {entry['paragraph_index']} 段")
                parts.append(f"**引用內文：** {entry['text']}")
                if src and src.get("relevant_chunk"):
                    parts.append(f"**對應原文摘錄：** {src['relevant_chunk']}")
                if src and src.get("similarity_score") is not None:
                    parts.append(f"**相似度：** {src['similarity_score']}")
                parts.append("")

        return "\n".join(parts)

    # ── 論文組裝 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _assemble_paper(
        topic: str,
        structure: List[str],
        sections_text: Dict[str, str],
        global_ref_list: List[dict],
    ) -> str:
        parts = [f"# {topic}"]

        for sec in structure:
            text = sections_text.get(sec, "")
            if text:
                parts.append(f"## {sec}\n\n{text}")

        # APA 格式參考文獻
        if global_ref_list:
            ref_lines = []
            for ref in global_ref_list:
                author = ref.get("author", "Unknown Author")
                year = ref.get("year", "n.d.")
                title = ref.get("title", "Untitled")
                ref_lines.append(f"[{ref['ref_id']}] {author} ({year}). {title}.")
            parts.append("## 參考文獻\n\n" + "\n\n".join(ref_lines))

        return "\n\n---\n\n".join(parts)


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[PaperRAGService] = None


def get_paper_rag_service() -> PaperRAGService:
    global _instance
    if _instance is None:
        _instance = PaperRAGService()
    return _instance
