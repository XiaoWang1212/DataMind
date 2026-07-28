# Journal Scoring Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a manually-triggered scoring agent on the `/paper` page that evaluates the generated paper against 3 fixed medical-informatics journal rubrics and shows per-journal score breakdowns.

**Architecture:** A new `PaperRAGService.score_paper()` method makes one independent single-call Gemini request per journal rubric (JSON response mode), exposed via `POST /api/rag/score-paper`. The frontend reconstructs the paper's plain text from the already-rendered `PaperReport` (no store/schema changes needed), calls the new endpoint from a button on `PaperPage.vue`, and shows results in a new tabbed dialog component. Nothing is persisted.

**Tech Stack:** Flask + `google-generativeai` (backend), Vue 3 `<script setup>` + Vuetify + Pinia (frontend). No new dependencies.

## Global Constraints

- Exactly 3 fixed journals, no user-facing journal selection UI: JAMIA, npj Digital Medicine, BMC Medical Informatics and Decision Making.
- Exactly 6 scoring criteria per journal, identical set across journals: 研究貢獻與新穎性、方法嚴謹性、結果呈現與統計報告完整度、文獻回顧與引用品質、臨床/實務意義與限制討論、寫作結構與期刊格式規範.
- Manual trigger only — do not call scoring automatically after `generate_paper()`.
- No persistence — scoring results live only in frontend component state for the current dialog session.
- Each journal is one independent single-call Gemini request (JSON response mode), matching the existing one-shot pattern in `paper_rag.py` (`classify_topic()`, `generate_insight()`). No shared context between journal calls.
- One journal's scoring failure must not block the others — skip and record in `failed_journals`; only fail the whole call if all 3 journals fail.
- No new test framework. Backend verification uses a manual script under `backend/scripts/` (matching `test_arxiv_pipeline.py` convention, hits the real Gemini API using `backend/.env`'s `GEMINI_API_KEY`). Frontend verification is manual browser testing only.
- Error display follows the existing inline-text + retry-button convention (see `PaperSourcesView.vue`), not a snackbar/toast — this codebase has no snackbar component anywhere.

---

### Task 1: Backend — `score_paper()` service method

**Files:**
- Modify: `backend/services/rag/paper_rag.py`
- Test: `backend/scripts/test_score_paper.py` (new manual verification script)

**Interfaces:**
- Produces: `PaperRAGService.score_paper(paper_text: str) -> dict` with shape:
  ```python
  {
    "success": bool,
    "journal_scores": [
      {
        "journal": str, "journal_full_name": str, "overall_score": int,
        "criteria": [{"name": str, "score": int, "comment": str}, ...],
        "suggestions": [str, ...],
      }, ...
    ],
    "failed_journals": [str, ...],
    "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
  }
  ```
  On total failure: `{"success": False, "error": str, "failed_journals": [str, ...]}`. Consumed by Task 2's route.

- [ ] **Step 1: Write the manual verification script (will fail — method doesn't exist yet)**

Create `backend/scripts/test_score_paper.py`:

```python
"""score_paper() 期刊評分手動驗證腳本

用法（在 backend/ 目錄下執行）：
    python scripts/test_score_paper.py
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

SAMPLE_PAPER_TEXT = """# 糖尿病再入院風險預測研究

## 摘要

本研究使用 XGBoost 模型對糖尿病病患的 30 天再入院風險進行預測，
在測試集上達到 AUC 0.96、F1 0.91，顯示模型具備良好的判別能力。

## 研究方法

資料集包含 12000 筆病患紀錄，類別分布為 9820:2180，使用 SMOTE 重採樣
處理類別不平衡問題，並以 train_test_split（80/20，stratified）進行驗證。

## 討論

本研究的限制在於資料僅來自單一醫院，模型的外推能力仍待更多中心驗證。
"""


def main():
    print("=" * 60)
    print("score_paper() 測試")
    print("=" * 60)

    from services.rag.paper_rag import PaperRAGService

    test_index_dir = BACKEND_DIR / "artifacts" / "test_score_index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    os.environ["RAG_INDEX_DIR"] = str(test_index_dir)

    service = PaperRAGService()

    result = service.score_paper(SAMPLE_PAPER_TEXT)
    print(f"\nsuccess: {result['success']}")
    assert result["success"], f"至少要有一個期刊評分成功：{result}"

    print(f"failed_journals: {result['failed_journals']}")
    assert len(result["journal_scores"]) + len(result["failed_journals"]) == 3, \
        "journal_scores + failed_journals 應等於期刊總數 3"

    for js in result["journal_scores"]:
        print(f"\n▶ {js['journal']}（總分 {js['overall_score']}）")
        assert 0 <= js["overall_score"] <= 100
        assert len(js["criteria"]) == 6, f"應有 6 項準則：{js['criteria']}"
        for c in js["criteria"]:
            assert 0 <= c["score"] <= 100
            print(f"    - {c['name']}: {c['score']} — {c['comment'][:40]}...")
        assert len(js["suggestions"]) >= 1, "至少要有一條修改建議"

    print("\n測試完成！")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script to confirm it fails**

Run (from `backend/` directory): `python scripts/test_score_paper.py`
Expected: `AttributeError: 'PaperRAGService' object has no attribute 'score_paper'`

- [ ] **Step 3: Add `import json` to `paper_rag.py`**

In `backend/services/rag/paper_rag.py`, change the top imports:

```python
import logging
import os
import re
import uuid
from dataclasses import dataclass
```

to:

```python
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass
```

- [ ] **Step 4: Add the journal rubric constants**

In `backend/services/rag/paper_rag.py`, right after the existing `_DEFAULT_STRUCTURE = ["摘要", "前言", "研究方法", "實驗結果", "討論", "結論"]` line (and before `@dataclass\nclass SearchResult:`), insert:

```python
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
```

- [ ] **Step 5: Add `_call_gemini_json` and `_safe_parse_json`**

In `backend/services/rag/paper_rag.py`, find the existing `_call_gemini` method — it ends with:

```python
        except Exception as e:
            logger.error("Gemini 生成失敗：%s", e)
            return f"（生成失敗：{e}）"

    # ── Prompt 建立 ───────────────────────────────────────────────────────────
```

Insert the two new methods between the end of `_call_gemini` and the `# ── Prompt 建立 ──` section header:

```python
        except Exception as e:
            logger.error("Gemini 生成失敗：%s", e)
            return f"（生成失敗：{e}）"

    def _call_gemini_json(self, prompt: str, usage_total: dict) -> str:
        """比照 _call_gemini()，但要求 Gemini 以 JSON 格式回傳，且不吞掉例外——
        由呼叫端（如 score_paper()）自行決定失敗時是否跳過。"""
        resp = self._model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=4096,
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

    # ── Prompt 建立 ───────────────────────────────────────────────────────────
```

- [ ] **Step 6: Add `_build_score_prompt`**

In `backend/services/rag/paper_rag.py`, find the end of `_build_section_prompt`:

```python
            f"- 僅輸出「{section_name}」的段落內文，不需要章節標題\n"
            f"- 段落間以空行分隔\n\n"
            f"請直接輸出文章內容："
        )

    # ── 引用處理 ──────────────────────────────────────────────────────────────
```

Insert `_build_score_prompt` between the closing `)` of `_build_section_prompt` and the `# ── 引用處理 ──` header:

```python
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
            "最後再給一個 0 到 100 的總分，以及 2 到 5 條具體的修改建議。\n\n"
            f"【評分準則】\n{criteria_list}\n\n"
            f"【論文全文】\n{paper_text}\n\n"
            "請「只」輸出以下形狀的 JSON，不要有其他文字或 Markdown 圍欄：\n"
            "{\n"
            '  "overall_score": <0-100 整數>,\n'
            '  "criteria": [\n'
            '    {"name": "<準則名稱，須完全比照上面清單>", "score": <0-100 整數>, "comment": "<中文理由>"},\n'
            "    ...\n"
            "  ],\n"
            '  "suggestions": ["<修改建議1>", "<修改建議2>", ...]\n'
            "}"
        )

    # ── 引用處理 ──────────────────────────────────────────────────────────────
```

- [ ] **Step 7: Add the public `score_paper()` method**

In `backend/services/rag/paper_rag.py`, find `generate_insight()` — it ends with:

```python
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        return text.strip()

    def get_status(self) -> dict:
```

Insert `score_paper()` between `generate_insight()`'s closing `return text.strip()` and `def get_status`:

```python
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        text = self._call_gemini(prompt, usage_total)
        return text.strip()

    def score_paper(self, paper_text: str) -> dict:
        """依 _JOURNAL_RUBRICS 對論文全文逐期刊評分，各期刊各一次獨立的 Gemini JSON 呼叫。

        單一期刊評分失敗（Gemini 例外或 JSON 解析失敗）時跳過並記錄，不中斷整體流程；
        若全部期刊皆失敗則回傳 {"success": False, "error": ...}。
        """
        journal_scores: List[dict] = []
        failed_journals: List[str] = []
        usage_total = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for rubric in _JOURNAL_RUBRICS:
            prompt = self._build_score_prompt(paper_text, rubric)
            try:
                raw = self._call_gemini_json(prompt, usage_total)
                parsed = self._safe_parse_json(raw)
                if parsed is None:
                    raise ValueError("Gemini 回傳非合法 JSON")

                journal_scores.append({
                    "journal": rubric["name"],
                    "journal_full_name": rubric["full_name"],
                    "overall_score": int(parsed["overall_score"]),
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
            except Exception as e:
                logger.warning("期刊評分失敗：%s (%s)", rubric["name"], e)
                failed_journals.append(rubric["name"])
                continue

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

    def get_status(self) -> dict:
```

- [ ] **Step 8: Run the script to confirm it passes**

Run (from `backend/` directory, with `GEMINI_API_KEY` set in `backend/.env`): `python scripts/test_score_paper.py`
Expected: prints `success: True`, 3 journals' scores (or fewer with `failed_journals` populated), all assertions pass, ends with "測試完成！".

- [ ] **Step 9: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/scripts/test_score_paper.py
git commit -m "feat: add score_paper() for per-journal paper scoring"
```

---

### Task 2: Backend — `POST /api/rag/score-paper` route

**Files:**
- Modify: `backend/routes/rag.py`

**Interfaces:**
- Consumes: `PaperRAGService.score_paper(paper_text: str) -> dict` from Task 1.
- Produces: `POST /api/rag/score-paper` endpoint, consumed by Task 3's `scorePaper()` frontend function. Request body `{"paper_text": str}`. Response: same shape as `score_paper()`'s return value, plus HTTP status (200 on success, 422 when all journals failed, 400 on missing `paper_text`, 500 on unexpected exception).

- [ ] **Step 1: Add the route**

Append to the end of `backend/routes/rag.py` (after the existing `generate_insight` route):

```python
@rag_bp.route("/score-paper", methods=["POST"])
def score_paper():
    """對論文全文，依固定的期刊評分準則逐一評分

    JSON body:
        - paper_text : 論文全文純文字（必填）

    回傳：
        - journal_scores  : 各期刊評分結果（journal/journal_full_name/overall_score/criteria/suggestions）
        - failed_journals : 評分失敗的期刊名稱清單
        - usage           : Gemini token 用量
    """
    from services.rag.paper_rag import get_paper_rag_service

    data = request.get_json()
    paper_text = (data or {}).get("paper_text", "").strip()
    if not paper_text:
        return jsonify({"success": False, "error": "paper_text 為必填欄位"}), 400

    service = get_paper_rag_service()

    try:
        result = service.score_paper(paper_text)
        status_code = 200 if result.get("success") else 422
        return jsonify(result), status_code

    except Exception as e:
        logger.exception("期刊評分失敗")
        return jsonify({"success": False, "error": str(e)}), 500
```

- [ ] **Step 2: Start the backend dev server**

Run (from `backend/` directory): `python app.py`
Expected: server starts on `http://localhost:5001` (or `$FLASK_PORT` if set).

- [ ] **Step 3: Manually verify the happy path with curl**

Run:

```bash
curl -s -X POST http://localhost:5001/api/rag/score-paper \
  -H "Content-Type: application/json" \
  -d '{"paper_text": "# 糖尿病再入院風險預測研究\n\n## 摘要\n\n本研究使用 XGBoost 模型對糖尿病病患的 30 天再入院風險進行預測，在測試集上達到 AUC 0.96。\n\n## 討論\n\n本研究的限制在於資料僅來自單一醫院。"}'
```

Expected: HTTP 200, JSON body with `"success": true`, `journal_scores` array (up to 3 entries, each with `journal`, `journal_full_name`, `overall_score`, `criteria` (6 items), `suggestions`).

- [ ] **Step 4: Manually verify the validation error with curl**

Run:

```bash
curl -s -i -X POST http://localhost:5001/api/rag/score-paper \
  -H "Content-Type: application/json" \
  -d '{}'
```

Expected: HTTP 400, body `{"success": false, "error": "paper_text 為必填欄位"}`.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/rag.py
git commit -m "feat: add POST /api/rag/score-paper route"
```

---

### Task 3: Frontend — data layer, dialog component, and `PaperPage.vue` wiring

**Files:**
- Modify: `frontend/src/utils/paperTransform.ts`
- Modify: `frontend/src/api/arxiv.ts`
- Create: `frontend/src/components/paper/JournalScoreDialog.vue`
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes: `PaperReport` type (`frontend/src/constants/reportData.ts`), `POST /api/rag/score-paper` from Task 2.
- Produces: `buildPaperText(report: PaperReport, citationIndex: Record<string, number>): string`; `scorePaper(paperText: string): Promise<{journalScores: JournalScore[], failedJournals: string[]}>`; `JournalScoreDialog.vue` (consumed only by `PaperPage.vue`).

- [ ] **Step 1: Add `buildPaperText()` to `paperTransform.ts`**

Append to the end of `frontend/src/utils/paperTransform.ts` (the file already imports `PaperReport` at the top, no new import needed):

```ts
export function buildPaperText (report: PaperReport, citationIndex: Record<string, number>): string {
  const lines: string[] = [`# ${report.title}`]

  for (const section of report.sections) {
    lines.push(`## ${section.heading}`)

    for (const paragraph of section.paragraphs) {
      const paragraphText = paragraph
        .map(segment => {
          const marks = (segment.citationIds ?? [])
            .map(id => `[${citationIndex[id] ?? id}]`)
            .join('')
          return segment.text + marks
        })
        .join('')
      lines.push(paragraphText)
    }
  }

  return lines.join('\n\n')
}
```

- [ ] **Step 2: Add types and `scorePaper()` to `arxiv.ts`**

Append to the end of `frontend/src/api/arxiv.ts`:

```ts
export interface CriterionScore {
  name: string
  score: number
  comment: string
}

export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  criteria: CriterionScore[]
  suggestions: string[]
}

export interface ScorePaperResult {
  journalScores: JournalScore[]
  failedJournals: string[]
}

export async function scorePaper (paperText: string): Promise<ScorePaperResult> {
  const response = await fetch('/api/rag/score-paper', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_text: paperText }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  const rawScores = Array.isArray(result.journal_scores)
    ? result.journal_scores as Record<string, unknown>[]
    : []

  return {
    journalScores: rawScores.map(js => ({
      journal: String(js.journal ?? ''),
      journalFullName: String(js.journal_full_name ?? ''),
      overallScore: Number(js.overall_score ?? 0),
      criteria: Array.isArray(js.criteria)
        ? (js.criteria as Record<string, unknown>[]).map(c => ({
          name: String(c.name ?? ''),
          score: Number(c.score ?? 0),
          comment: String(c.comment ?? ''),
        }))
        : [],
      suggestions: Array.isArray(js.suggestions) ? (js.suggestions as unknown[]).map(String) : [],
    })),
    failedJournals: Array.isArray(result.failed_journals)
      ? (result.failed_journals as unknown[]).map(String)
      : [],
  }
}
```

- [ ] **Step 3: Create `JournalScoreDialog.vue`**

Create `frontend/src/components/paper/JournalScoreDialog.vue`:

```vue
<template>
  <div
    v-if="visible"
    class="journal-score-backdrop"
    @click.self="emit('close')"
  >
    <div class="journal-score-card">
      <header class="journal-score-header">
        <h3>期刊評分結果</h3>
        <button
          class="journal-score-close"
          type="button"
          @click="emit('close')"
        >
          ×
        </button>
      </header>

      <p v-if="failedJournals.length" class="journal-score-warning">
        <v-icon icon="mdi-alert-outline" size="14" />
        {{ failedJournals.join('、') }} 評分失敗，僅顯示其餘期刊結果
      </p>

      <nav class="journal-score-tabs">
        <button
          v-for="(js, index) in journalScores"
          :key="js.journal"
          class="journal-score-tab"
          :class="{ 'journal-score-tab--active': index === activeIndex }"
          type="button"
          @click="activeIndex = index"
        >
          {{ js.journal }}
        </button>
      </nav>

      <div v-if="activeJournal" class="journal-score-body">
        <div class="journal-score-overall">
          <span class="journal-score-overall__name">{{ activeJournal.journalFullName }}</span>
          <span class="journal-score-overall__value">{{ activeJournal.overallScore }}<small>/100</small></span>
        </div>

        <ul class="journal-score-criteria">
          <li
            v-for="criterion in activeJournal.criteria"
            :key="criterion.name"
            class="journal-score-criterion"
          >
            <div class="journal-score-criterion__head">
              <span class="journal-score-criterion__name">{{ criterion.name }}</span>
              <span class="journal-score-criterion__score">{{ criterion.score }}</span>
            </div>
            <p class="journal-score-criterion__comment">{{ criterion.comment }}</p>
          </li>
        </ul>

        <div class="journal-score-suggestions">
          <p class="journal-score-suggestions__title">修改建議</p>
          <ul>
            <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    visible: boolean
    journalScores: JournalScore[]
    failedJournals: string[]
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const activeIndex = ref(0)

  watch(() => props.visible, visible => {
    if (visible) activeIndex.value = 0
  })

  const activeJournal = computed(() => props.journalScores[activeIndex.value] ?? null)
</script>

<style scoped>
  .journal-score-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(20, 22, 30, 0.45);
    z-index: 1000;
  }

  .journal-score-card {
    width: 640px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
    overflow: hidden;
  }

  .journal-score-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid #e8ebf1;
  }

  .journal-score-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-close {
    border: none;
    background: none;
    font-size: 20px;
    line-height: 1;
    color: #6f7480;
    cursor: pointer;
  }

  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 12px 20px 0;
    padding: 8px 12px;
    border-radius: 8px;
    background: #fff4e5;
    color: #9a5b00;
    font-size: 12px;
  }

  .journal-score-tabs {
    display: flex;
    gap: 6px;
    padding: 14px 20px 0;
    border-bottom: 1px solid #e8ebf1;
  }

  .journal-score-tab {
    border: none;
    background: none;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 600;
    color: #6f7480;
    cursor: pointer;
    border-bottom: 2px solid transparent;
  }

  .journal-score-tab--active {
    color: #1058d6;
    border-bottom-color: #1058d6;
  }

  .journal-score-body {
    padding: 18px 20px 20px;
    overflow-y: auto;
  }

  .journal-score-overall {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .journal-score-overall__name {
    font-size: 12.5px;
    color: #6f7480;
  }

  .journal-score-overall__value {
    font-size: 26px;
    font-weight: 700;
    color: #1058d6;
  }

  .journal-score-overall__value small {
    font-size: 13px;
    font-weight: 500;
    color: #6f7480;
  }

  .journal-score-criteria {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .journal-score-criterion {
    border: 1px solid #e8ebf1;
    border-radius: 10px;
    padding: 10px 12px;
  }

  .journal-score-criterion__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .journal-score-criterion__name {
    font-size: 12.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-criterion__score {
    font-size: 12.5px;
    font-weight: 700;
    color: #1058d6;
  }

  .journal-score-criterion__comment {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }

  .journal-score-suggestions {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid #e8ebf1;
  }

  .journal-score-suggestions__title {
    margin: 0 0 8px;
    font-size: 12.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-suggestions ul {
    margin: 0;
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .journal-score-suggestions li {
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }
</style>
```

- [ ] **Step 4: Wire the button, state, and dialog into `PaperPage.vue`**

Replace the full contents of `frontend/src/views/PaperPage.vue` with:

```vue
<template>
  <section class="paper-page">
    <HubSidebar />

    <main class="paper-main">
      <header class="paper-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.back()"
        />
        <h2 class="paper-title">{{ report.title }}</h2>
        <v-btn
          class="score-btn"
          :loading="scoring"
          prepend-icon="mdi-school-outline"
          size="small"
          variant="tonal"
          @click="handleScorePaper"
        >
          期刊評分
        </v-btn>
      </header>

      <p v-if="scoreError" class="score-error">
        {{ scoreError }}
        <v-btn size="small" variant="text" @click="handleScorePaper">重試</v-btn>
      </p>

      <div class="paper-body">
        <article ref="sheetRef" class="paper-sheet">
          <PaperSection
            v-for="section in report.sections"
            :key="section.heading"
            :active-citation-id="activeCitationId"
            :citation-index="citationIndex"
            :section="section"
            @citation-click="onCitationClick"
          />
        </article>

        <CitationPanel
          :active-citation-id="activeCitationId"
          :citations="report.citations"
          class="paper-citations"
          @select="onPanelSelect"
        />
      </div>
    </main>

    <JournalScoreDialog
      :failed-journals="failedJournals"
      :journal-scores="journalScores"
      :visible="scoreDialogVisible"
      @close="scoreDialogVisible = false"
    />
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { type JournalScore, scorePaper } from '@/api/arxiv'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPanel from '@/components/paper/CitationPanel.vue'
  import JournalScoreDialog from '@/components/paper/JournalScoreDialog.vue'
  import PaperSection from '@/components/paper/PaperSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'
  import { buildPaperText } from '@/utils/paperTransform'

  const router = useRouter()
  const paperStore = usePaperStore()
  const report = paperStore.generatedReport ?? mockPaperReport
  paperStore.clearGeneratedReport()

  const citationIndex = Object.fromEntries(
    report.citations.map((citation, index) => [citation.id, index + 1]),
  )

  const activeCitationId = ref<string | null>(null)
  const sheetRef = ref<HTMLElement | null>(null)

  const scoring = ref(false)
  const scoreError = ref<string | null>(null)
  const scoreDialogVisible = ref(false)
  const journalScores = ref<JournalScore[]>([])
  const failedJournals = ref<string[]>([])

  onMounted(() => {
    document.title = 'DataMind'
  })

  function onCitationClick (citationId: string) {
    activeCitationId.value = citationId
  }

  function onPanelSelect (citationId: string) {
    activeCitationId.value = citationId
    sheetRef.value
      ?.querySelector(`[data-citation-id~="${CSS.escape(citationId)}"]`)
      ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  async function handleScorePaper (): Promise<void> {
    scoring.value = true
    scoreError.value = null
    try {
      const paperText = buildPaperText(report, citationIndex)
      const result = await scorePaper(paperText)
      journalScores.value = result.journalScores
      failedJournals.value = result.failedJournals
      scoreDialogVisible.value = true
    } catch (error) {
      scoreError.value = error instanceof Error ? error.message : String(error)
    } finally {
      scoring.value = false
    }
  }
</script>

<style scoped>
  .paper-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background:
      radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
      linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: hidden;
  }

  .paper-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .paper-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .score-btn {
    margin-left: auto;
  }

  .score-error {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 10px 2px 0;
    font-size: 12px;
    color: #b91c1c;
  }

  .paper-body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 16px;
    margin-top: 14px;
    overflow: auto;
  }

  .paper-sheet {
    flex: 1;
    min-width: 0;
    max-width: 760px;
    margin: 0 auto;
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 28px 34px;
    height: fit-content;
  }

  .paper-citations {
    width: 280px;
    flex-shrink: 0;
    position: sticky;
    top: 0;
    align-self: flex-start;
    max-height: calc(100vh - 150px);
    overflow-y: auto;
  }

  @media (max-width: 1100px) {
    .paper-body {
      flex-direction: column;
    }

    .paper-citations {
      width: 100%;
      position: static;
      max-height: none;
      overflow-y: visible;
    }
  }
</style>
```

- [ ] **Step 5: Manually verify in the browser**

1. Start the backend (from `backend/`): `python app.py`
2. Start the frontend (from `frontend/`): `npm run dev`
3. Open the frontend dev URL and navigate to `/paper` directly (with no prior workflow run, this loads `mockPaperReport` as a fallback — confirms the feature works even without a real generated paper).
4. Click "期刊評分". Confirm: the button shows a loading spinner, then a dialog opens with up to 3 journal tabs.
5. Click through each tab. Confirm: journal full name, overall score, 6 criteria (each with a score and comment), and a suggestions list all render.
6. Close the dialog (× button or click outside the card). Confirm it closes and the paper page is unaffected.
7. Stop the backend process, then click "期刊評分" again. Confirm: no dialog opens, and an inline red error message with a "重試" button appears instead.
8. Restart the backend, click "重試". Confirm the dialog now opens successfully.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/paperTransform.ts frontend/src/api/arxiv.ts frontend/src/components/paper/JournalScoreDialog.vue frontend/src/views/PaperPage.vue
git commit -m "feat: add journal scoring dialog and wire into /paper page"
```
