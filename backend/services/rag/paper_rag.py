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
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai

from . import arxiv_source
from .chunker import Chunk, TextChunker
from .embedder import Embedder
from .vector_store import VectorStore

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

# 每章節的 RAG 搜尋 query 模板
_SECTION_QUERIES: Dict[str, str] = {
    "摘要": "{topic} 研究目的 方法概述 主要發現",
    "前言": "{topic} 研究背景 臨床問題 現有預測方法 研究缺口 動機",
    "研究方法": "{topic} 資料集 資料預處理 特徵選擇 機器學習模型 交叉驗證 重採樣",
    "實驗結果": "{topic} 模型效能 AUC F1 準確率 特徵重要性 模型比較",
    "討論": "{topic} 結果解讀 與文獻比較 臨床意義 研究限制",
    "結論": "{topic} 研究貢獻 臨床應用價值 未來研究方向",
}

_DEFAULT_STRUCTURE = ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"]


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
        index_dir = (
            Path(__file__).parent.parent.parent
            / os.getenv("RAG_INDEX_DIR", "artifacts/rag_index")
        )

        self._chunker = TextChunker(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", 500)),
            overlap=int(os.getenv("RAG_CHUNK_OVERLAP", 50)),
        )
        self._embedder = Embedder(model_name=embed_model)
        self._store = VectorStore(index_dir=index_dir, embedder=self._embedder)

    # ── Public API ─────────────────────────────────────────────────────────────

    def add_paper(self, title: str, content: str, metadata: dict | None = None) -> dict:
        if metadata is None:
            metadata = {}
        paper_id = str(uuid.uuid4())
        chunks = self._chunker.chunk(content, paper_id=paper_id, title=title, metadata=metadata)
        if not chunks:
            return {"success": False, "error": "未能從文件中提取內容"}

        self._store.add(chunks)
        self._store.register_paper(paper_id, {"paper_id": paper_id, "title": title, **metadata})

        logger.info("add_paper: %s (%d chunks)", title, len(chunks))
        return {
            "success": True,
            "paper_id": paper_id,
            "title": title,
            "chunks_added": len(chunks),
        }

    def search(self, query: str, top_k: int = 5, use_rerank: bool = True) -> List[SearchResult]:
        raw = self._store.search(query, top_k=top_k)
        return [SearchResult(chunk=c, score=s) for c, s in raw]

    def generate_citation(self, query: str, top_k: int = 3, citation_style: str = "apa") -> dict:
        results = self.search(query, top_k=top_k)
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
            search_results = self.search(query, top_k=top_k)

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
                }

            # 3. Gemini 生成章節
            prompt = self._build_section_prompt(
                section_name, topic, results_text, local_refs, language
            )
            section_text = self._call_gemini(prompt, usage_total)

            # 4. 本地 [n] → 全域 [n]
            section_text_global = self._localref_to_global(section_text, local_refs)
            sections_text[section_name] = section_text_global

            # 5. 建立引用地圖（逐段）
            self._build_citation_map(
                section_name, section_text_global, local_refs, global_ref_list, citation_map
            )

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

    def classify_topic(self, mining_results: dict) -> dict:
        """讀 mining_results 摘要，用 Gemini 產生研究主題與 arXiv 查詢字串。"""
        results_text = self._format_datamind_output(mining_results)
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

    def search_arxiv_candidates(self, mining_results: dict) -> dict:
        """分類 mining_results 產生查詢字，查詢 arXiv 取得候選論文清單（不寫入向量庫）。"""
        classification = self.classify_topic(mining_results)
        candidates = arxiv_source.search_arxiv(classification["arxiv_query"])
        return {
            "topic": classification["topic"],
            "arxiv_query": classification["arxiv_query"],
            "candidates": candidates,
        }

    def ingest_arxiv_selection(self, candidates: List[dict]) -> dict:
        """清空向量庫，下載選中的 arXiv 論文全文並加入索引。

        單篇下載/解析失敗時跳過並記錄，不中斷整體流程；若全部失敗則回傳錯誤。
        """
        self.clear()

        ingested: List[str] = []
        failed: List[str] = []

        for candidate in candidates:
            title = candidate.get("title", "")
            pdf_url = candidate.get("pdf_url", "")
            try:
                content = arxiv_source.fetch_pdf_text(pdf_url)
                if not content.strip():
                    raise ValueError("PDF 未解析出任何文字")
            except Exception as e:
                logger.warning("下載/解析 arXiv PDF 失敗：%s (%s)", title, e)
                failed.append(title)
                continue

            result = self.add_paper(
                title=title,
                content=content,
                metadata={
                    "author": candidate.get("authors", ""),
                    "year": candidate.get("year", ""),
                    "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
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
                    max_output_tokens=2048,
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
        for part in resp.parts:
            if part.function_call and part.function_call.name:
                function_call = part.function_call
                break

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

        return {"reply": (getattr(resp, "text", "") or "").strip(), "papers": papers}

    def get_status(self) -> dict:
        return self._store.get_status()

    def delete_paper(self, paper_id: str) -> dict:
        ok = self._store.delete_paper(paper_id)
        if ok:
            return {"success": True, "message": f"已刪除論文 {paper_id}"}
        return {"success": False, "message": f"找不到論文 {paper_id}"}

    def clear(self) -> dict:
        self._store.clear()
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
            f"- 引用規則：陳述現有方法、背景、比較結果時，須於句末加入 [n] 引用標記；"
            f"如需引用多篇文獻，請以相鄰獨立括號表示（如 [1][2]），"
            f"禁止在同一括號內以逗號列出多個編號（如 [1, 2] 為不允許的格式）\n"
            f"- 僅輸出「{section_name}」的段落內文，不需要章節標題\n"
            f"- 段落間以空行分隔\n\n"
            f"請直接輸出文章內容："
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

        text = re.sub(r"\[(\d+(?:\s*,\s*\d+)*)\]", replace, text)
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

        citation_map 的每一筆結構：
        {
            section        : 章節名稱
            paragraph_index: 該段在章節中的位置（0-indexed）
            text           : 段落文字（含 [n] 標記）
            cited_ref_ids  : 該段引用的全域 ref_id 列表
            sources        : 每個引用的詳細資訊（供前端展示）
        }
        """
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]
        for para_idx, para in enumerate(paragraphs):
            cited_gids = sorted({int(m) for m in re.findall(r"\[(\d+)\]", para)})
            if not cited_gids:
                continue

            sources: List[dict] = []
            for gid in cited_gids:
                # 找對應的 local_ref（可能多個 local_id → 同一 global_id）
                chunk_info = next(
                    (info for info in local_refs.values() if info["global_ref_id"] == gid),
                    None,
                )
                ref_meta = next(
                    (r for r in global_ref_list if r["ref_id"] == gid), {}
                )
                sources.append({
                    "ref_id": gid,
                    "paper_id": chunk_info["chunk"].paper_id if chunk_info else "",
                    "title": ref_meta.get("title", ""),
                    "author": ref_meta.get("author", ""),
                    "year": ref_meta.get("year", ""),
                    # 提供被引用的原始 chunk 內容，方便前端顯示引用依據
                    "relevant_chunk": chunk_info["chunk"].content[:400] if chunk_info else "",
                    "similarity_score": round(chunk_info["score"], 4) if chunk_info else None,
                })

            citation_map.append({
                "section": section_name,
                "paragraph_index": para_idx,
                "text": para,
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
