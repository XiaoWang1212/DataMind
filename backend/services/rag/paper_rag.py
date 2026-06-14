"""RAG 論文生成服務

流程：
  1. add_paper()  ─ 上傳參考論文 → 切塊 → 向量化 → 儲存
  2. generate_paper() ─ 接收 DataMind 輸出 → 逐章節 RAG 檢索 + Gemini 生成
     → 回傳 paper_markdown + citation_map（引用地圖）
"""

import logging
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import google.generativeai as genai

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
          citation_map    - 引用地圖（逐段記錄引用來源，供前端使用）
          references      - 全域引用清單（APA 格式）
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

        # 6. 組合完整論文
        paper_markdown = self._assemble_paper(topic, structure, sections_text, global_ref_list)

        return {
            "paper_markdown": paper_markdown,
            "citation_map": citation_map,
            "references": global_ref_list,
            "sections_generated": [s for s in structure if s in sections_text],
            "usage": usage_total,
        }

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
        for i, pv in enumerate(mining_results.get("preprocess_variants", []), 1):
            pp = "、".join(s.get("type", "") for s in pv.get("preprocess_steps", [])) or "無"
            fe = "、".join(s.get("type", "") for s in pv.get("feature_engineering_steps", [])) or "無"
            parts.append(f"【前處理流程 {i}】\n預處理：{pp}\n特徵工程：{fe}")

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
                    max_output_tokens=4096,
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
            f"- 學術寫作風格，使用正式用語與被動語態\n"
            f"- 引用規則：陳述現有方法、背景、比較結果時必須加 [n] 標記\n"
            f"- 僅輸出「{section_name}」的段落內文，不需要章節標題\n"
            f"- 輸出純文字段落，段落間以空行分隔，禁止使用 Markdown 格式符號\n\n"
            f"請直接輸出文章內容："
        )

    # ── 引用處理 ──────────────────────────────────────────────────────────────

    @staticmethod
    def _localref_to_global(text: str, local_refs: Dict[int, dict]) -> str:
        """將章節內的本地 [n] 替換成全域 [n]。"""
        def replace(m: re.Match) -> str:
            local_id = int(m.group(1))
            info = local_refs.get(local_id)
            if info:
                return f"[{info['global_ref_id']}]"
            return m.group(0)

        return re.sub(r"\[(\d+)\]", replace, text)

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
