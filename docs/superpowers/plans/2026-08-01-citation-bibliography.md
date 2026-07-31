# Paper Editor Reference List / Citation Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-generate a formatted reference list (APA/IEEE/MLA) at the end of the paper editor, using genuinely correct arXiv-preprint citation templates for arXiv-sourced references (by threading `arxiv_id` through from the backend), and a best-effort fallback for references without one.

**Architecture:** A small backend change makes `arxiv_id` available on generated references. The frontend gains a pure formatting module (`formatCitation.ts`), a read-only display component (`ReferencesSection.vue`), and a style selector wired into `PaperPage.vue`'s existing save/load flow. The reference list is never written into the editable Tiptap document — it's computed and rendered independently every time from `report.citations` + `report.citationStyle`.

**Tech Stack:** Vue 3, Vuetify 4, TypeScript, Flask (Python), Tailwind CSS v4 tokens.

## Global Constraints

- No unit test framework is configured in `frontend/` or `backend/` — verification is `npm run build` / `npm run lint` (from `frontend/`), targeted standalone Python scripts run directly with `python` (from `backend/`), and live browser/API checks
- `backend/services/report/report_store.py` stores `citations`/other report fields as schema-less JSON — new fields do not need a migration
- `CitationStyle` values are exactly `'apa' | 'ieee' | 'mla'`, default `'apa'`
- Do NOT reformat author names (e.g. to "Last, F." form) — `authors` is an opaque source string; keep it as-is in every template
- Do NOT implement: manual citation add/edit UI, manual inline-citation insertion, alphabetical sorting of the reference list, volume/issue/pages/DOI handling for non-arXiv sources, "et al." truncation
- The citation style `<v-select>` in `PaperPage.vue` must be disabled while `mode === 'edit'` — style changes are only allowed (and only auto-saved) in view mode
- `formatCitation`'s template strings (Task 3) must be implemented verbatim as specified — they are the spec's literal output contract, not just an example

---

### Task 1: Backend — `arxiv_id` passthrough and `citationStyle` persistence

**Files:**
- Modify: `backend/services/rag/paper_rag.py:328-336`
- Modify: `backend/services/report/report_store.py`
- Modify: `backend/routes/report.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: `references[].arxiv_id` (string, may be empty) in the JSON returned by `POST /api/rag/arxiv/generate` (via `PaperRAGService.generate_paper`'s existing `**sr.chunk.metadata` spread — unchanged, just gets one more key); `ReportStore.save(project_id, title, content, citations, citation_style="apa")` (new 5th parameter, defaults `"apa"`); the JSON record returned by both `GET /api/report/<id>` and `POST /api/report/<id>` now includes a `"citationStyle"` key — later frontend tasks (2, 6) rely on this exact key name

- [ ] **Step 1: Add `arxiv_id` to the arXiv paper metadata**

Replace (`backend/services/rag/paper_rag.py`, inside the arXiv-ingestion loop, around line 328-336):

```python
            result = self.add_paper(
                title=title,
                content=content,
                metadata={
                    "author": candidate.get("authors", ""),
                    "year": candidate.get("year", ""),
                    "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
                },
            )
```

With:

```python
            result = self.add_paper(
                title=title,
                content=content,
                metadata={
                    "author": candidate.get("authors", ""),
                    "year": candidate.get("year", ""),
                    "journal": f"arXiv:{candidate.get('arxiv_id', '')}",
                    "arxiv_id": candidate.get("arxiv_id", ""),
                },
            )
```

- [ ] **Step 2: Verify `arxiv_id` flows into chunk metadata**

Create `backend/verify_arxiv_id_temp.py`:

```python
from services.rag.paper_rag import PaperRAGService
import os

os.environ["RAG_INDEX_DIR"] = "artifacts/test_arxiv_id_verify"

service = PaperRAGService()
service.clear()
service.add_paper(
    title="Test Paper for arxiv_id passthrough",
    content="This paper discusses machine learning methods for classification tasks in clinical datasets, covering feature selection, model training, and evaluation metrics in detail.",
    metadata={
        "author": "Test Author",
        "year": "2024",
        "journal": "arXiv:1234.5678",
        "arxiv_id": "1234.5678",
    },
)
results = service.search("machine learning classification methods", top_k=1)
assert len(results) == 1, f"expected 1 search result, got {len(results)}"
assert results[0].chunk.metadata.get("arxiv_id") == "1234.5678", f"arxiv_id missing: {results[0].chunk.metadata}"
print("PASS: arxiv_id correctly stored in chunk metadata:", results[0].chunk.metadata["arxiv_id"])
```

Run (from `backend/`): `python verify_arxiv_id_temp.py`
Expected: `PASS: arxiv_id correctly stored in chunk metadata: 1234.5678`

Delete the temp script: `rm backend/verify_arxiv_id_temp.py` (do not commit it).

- [ ] **Step 3: Add `citation_style` to `ReportStore.save`**

Replace (`backend/services/report/report_store.py`):

```python
    def save(self, project_id: str, title: str, content: dict, citations: list) -> dict:
        record = {
            "title": title,
            "content": content,
            "citations": citations,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path_for(project_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record
```

With:

```python
    def save(self, project_id: str, title: str, content: dict, citations: list, citation_style: str = "apa") -> dict:
        record = {
            "title": title,
            "content": content,
            "citations": citations,
            "citationStyle": citation_style,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path_for(project_id).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return record
```

- [ ] **Step 4: Read `citationStyle` from the save request**

Replace (`backend/routes/report.py`):

```python
    title = data.get("title")
    content = data.get("content")
    citations = data.get("citations", [])

    if not title or content is None:
        return jsonify({"success": False, "error": "title 和 content 為必填欄位"}), 400

    store = get_report_store()

    try:
        result = store.save(project_id, title, content, citations)
        return jsonify({"success": True, "result": result})
```

With:

```python
    title = data.get("title")
    content = data.get("content")
    citations = data.get("citations", [])
    citation_style = data.get("citationStyle", "apa")

    if not title or content is None:
        return jsonify({"success": False, "error": "title 和 content 為必填欄位"}), 400

    store = get_report_store()

    try:
        result = store.save(project_id, title, content, citations, citation_style)
        return jsonify({"success": True, "result": result})
```

Also update the docstring immediately above (lines 14-20) to mention the new field — replace:

```python
    """儲存論文編輯內容

    JSON body:
        - title    : 論文標題（必填）
        - content  : Tiptap JSON 文件內容（必填）
        - citations: 參考文獻清單（選填，預設空陣列）
    """
```

With:

```python
    """儲存論文編輯內容

    JSON body:
        - title        : 論文標題（必填）
        - content      : Tiptap JSON 文件內容（必填）
        - citations    : 參考文獻清單（選填，預設空陣列）
        - citationStyle: 參考文獻格式，'apa'/'ieee'/'mla'（選填，預設 'apa'）
    """
```

- [ ] **Step 5: Verify `citationStyle` round-trips through `ReportStore`**

Create `backend/verify_citation_style_temp.py`:

```python
from services.report.report_store import ReportStore
import tempfile

store = ReportStore(index_dir=tempfile.mkdtemp())
record = store.save("test-project", "Test Title", {"type": "doc", "content": []}, [], "ieee")
assert record["citationStyle"] == "ieee", f"citationStyle missing from save result: {record}"

loaded = store.load("test-project")
assert loaded["citationStyle"] == "ieee", f"citationStyle missing from load result: {loaded}"

record_default = store.save("test-project-2", "Test Title 2", {"type": "doc", "content": []}, [])
assert record_default["citationStyle"] == "apa", f"default citationStyle wrong: {record_default}"

print("PASS: citationStyle correctly persisted, loaded, and defaults to apa:", loaded["citationStyle"])
```

Run (from `backend/`): `python verify_citation_style_temp.py`
Expected: `PASS: citationStyle correctly persisted, loaded, and defaults to apa: ieee`

Delete the temp script: `rm backend/verify_citation_style_temp.py` (do not commit it).

- [ ] **Step 6: Commit**

```bash
git add backend/services/rag/paper_rag.py backend/services/report/report_store.py backend/routes/report.py
git commit -m "feat: pass arxiv_id through citation pipeline and persist citationStyle"
```

---

### Task 2: Frontend data model — `CitationStyle`, `Citation.arxivId`, `PaperReport.citationStyle`

**Files:**
- Modify: `frontend/src/api/arxiv.ts`
- Modify: `frontend/src/constants/reportData.ts`
- Modify: `frontend/src/api/report.ts`

**Interfaces:**
- Consumes: Task 1's backend response shape (`references[].arxiv_id`, `citationStyle` key on save/load responses)
- Produces: `CitationStyle` type (`'apa' | 'ieee' | 'mla'`), exported from `frontend/src/constants/reportData.ts` — Task 3 (`formatCitation.ts`), Task 4 (`paperTransform.ts`), Task 5 (`ReferencesSection.vue`), and Task 6 (`PaperPage.vue`) all import it from there. `Citation.arxivId?: string`. `PaperReport.citationStyle: CitationStyle` (required field on the interface, always populated by the code that constructs a `PaperReport`).

- [ ] **Step 1: Add `arxiv_id` to `ArxivReference`**

Replace (`frontend/src/api/arxiv.ts`):

```ts
export interface ArxivReference {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  journal?: string
}
```

With:

```ts
export interface ArxivReference {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  journal?: string
  arxiv_id?: string
}
```

- [ ] **Step 2: Add `CitationStyle`, `Citation.arxivId`, `PaperReport.citationStyle`**

Replace (`frontend/src/constants/reportData.ts`, top of file):

```ts
import type { JSONContent } from '@tiptap/core'

export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
}

export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
}
```

With:

```ts
import type { JSONContent } from '@tiptap/core'

export type CitationStyle = 'apa' | 'ieee' | 'mla'

export interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string
  arxivId?: string
}

export interface PaperReport {
  title: string
  content: JSONContent
  citations: Citation[]
  citationStyle: CitationStyle
}
```

- [ ] **Step 3: Add `citationStyle` to `mockPaperReport`**

Replace:

```ts
export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citations: [
```

With:

```ts
export const mockPaperReport: PaperReport = {
  title: '基於機器學習之電信客戶流失預測研究',
  citationStyle: 'apa',
  citations: [
```

- [ ] **Step 4: Add `citationStyle` to `SavedReport` and `saveReport`'s payload type**

Replace (`frontend/src/api/report.ts`):

```ts
import type { JSONContent } from '@tiptap/core'
import type { Citation } from '@/constants/reportData'

export interface SavedReport {
  title: string
  content: JSONContent
  citations: Citation[]
  updated_at: string
}

export async function saveReport (
  projectId: string,
  payload: { title: string, content: JSONContent, citations: Citation[] },
): Promise<SavedReport> {
```

With:

```ts
import type { JSONContent } from '@tiptap/core'
import type { Citation, CitationStyle } from '@/constants/reportData'

export interface SavedReport {
  title: string
  content: JSONContent
  citations: Citation[]
  citationStyle: CitationStyle
  updated_at: string
}

export async function saveReport (
  projectId: string,
  payload: { title: string, content: JSONContent, citations: Citation[], citationStyle: CitationStyle },
): Promise<SavedReport> {
```

- [ ] **Step 5: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits non-zero with type errors — this is expected at this point. `PaperPage.vue` (not yet updated) constructs `PaperReport`-shaped objects without `citationStyle` (lines 108 and 143) and calls `saveReport` without the new field (line 138-142); `paperTransform.ts` (not yet updated) returns a `PaperReport` without `citationStyle`. Confirm the errors are exactly these two files/call sites and nothing else — Tasks 4 and 6 fix them.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/arxiv.ts frontend/src/constants/reportData.ts frontend/src/api/report.ts
git commit -m "feat: add CitationStyle type and arxivId/citationStyle fields to paper data model"
```

---

### Task 3: `formatCitation.ts`

**Files:**
- Create: `frontend/src/utils/paper/formatCitation.ts`

**Interfaces:**
- Consumes: `Citation`, `CitationStyle` from `@/constants/reportData` (Task 2)
- Produces: `formatCitation(citation: Citation, style: CitationStyle, index: number): string`, `citationStyleLabels: Record<CitationStyle, string>` — Task 5 (`ReferencesSection.vue`) and Task 6 (`PaperPage.vue`) both import from this file

- [ ] **Step 1: Create the formatting module**

Create `frontend/src/utils/paper/formatCitation.ts`:

```ts
import type { Citation, CitationStyle } from '@/constants/reportData'

export const citationStyleLabels: Record<CitationStyle, string> = {
  apa: 'APA',
  ieee: 'IEEE',
  mla: 'MLA',
}

function formatArxiv (citation: Citation, style: CitationStyle, index: number): string {
  const { authors, title, year, arxivId } = citation

  switch (style) {
    case 'apa': {
      return `${authors} (${year}). ${title}. arXiv. https://arxiv.org/abs/${arxivId}`
    }
    case 'mla': {
      return `${authors}. "${title}." arXiv, ${year}, arxiv.org/abs/${arxivId}.`
    }
    case 'ieee': {
      return `[${index}] ${authors}, "${title}," arXiv:${arxivId}, ${year}.`
    }
  }
}

function formatFallback (citation: Citation, style: CitationStyle, index: number): string {
  const { authors, title, year, journal } = citation

  switch (style) {
    case 'apa': {
      const journalSegment = journal ? ` ${journal}.` : ''
      return `${authors} (${year}). ${title}.${journalSegment}`
    }
    case 'mla': {
      const journalPart = journal ? ` ${journal}, ${year}.` : ` ${year}.`
      return `${authors}. "${title}."${journalPart}`
    }
    case 'ieee': {
      const journalPart = journal ? ` ${journal}, ${year}.` : ` ${year}.`
      return `[${index}] ${authors}, "${title}",${journalPart}`
    }
  }
}

export function formatCitation (citation: Citation, style: CitationStyle, index: number): string {
  return citation.arxivId
    ? formatArxiv(citation, style, index)
    : formatFallback(citation, style, index)
}
```

- [ ] **Step 2: Verify the formatting output manually**

Run (from `frontend/`): `npx tsx -e "
import { formatCitation } from './src/utils/paper/formatCitation'
const arxivCitation = { id: 'c1', title: 'A Study of Things', authors: 'John Smith, Jane Doe', journal: 'arXiv:2301.12345', year: 2023, snippet: '', arxivId: '2301.12345' }
const fallbackCitation = { id: 'c2', title: 'Another Study', authors: 'A. Author', journal: 'Journal of Examples', year: 2022, snippet: '' }
console.log(formatCitation(arxivCitation, 'apa', 1))
console.log(formatCitation(arxivCitation, 'ieee', 1))
console.log(formatCitation(arxivCitation, 'mla', 1))
console.log(formatCitation(fallbackCitation, 'apa', 2))
console.log(formatCitation(fallbackCitation, 'ieee', 2))
console.log(formatCitation(fallbackCitation, 'mla', 2))
"`

If `tsx` is not available (check with `npx tsx --version` first; install with `npm install --no-save tsx` if missing, from `frontend/`), run the equivalent via `node --experimental-strip-types` is not needed — `tsx` handles the `@/` path alias via the project's existing `vite-tsconfig-paths`-equivalent resolution is NOT guaranteed outside Vite, so if the `@/` import fails to resolve, temporarily change the import in the command to a relative path (`./src/constants/reportData`) for this one-off check only — do not change the actual file's import style.

Expected output (six lines):
```
John Smith, Jane Doe (2023). A Study of Things. arXiv. https://arxiv.org/abs/2301.12345
[1] John Smith, Jane Doe, "A Study of Things," arXiv:2301.12345, 2023.
John Smith, Jane Doe. "A Study of Things." arXiv, 2023, arxiv.org/abs/2301.12345.
A. Author (2022). Another Study. Journal of Examples.
[2] A. Author, "Another Study", Journal of Examples, 2022.
A. Author. "Another Study." Journal of Examples, 2022.
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: same two pre-existing errors as Task 2 Step 5 (this task adds a new, unreferenced file — no new errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/paper/formatCitation.ts
git commit -m "feat: add formatCitation module for APA/IEEE/MLA reference formatting"
```

---

### Task 4: `paperTransform.ts` — wire `arxivId` and `citationStyle` through

**Files:**
- Modify: `frontend/src/utils/paperTransform.ts`

**Interfaces:**
- Consumes: `ArxivReference.arxiv_id` (Task 2), `Citation.arxivId`/`PaperReport.citationStyle` (Task 2)
- Produces: `transformArxivResultToPaperReport` now returns a `PaperReport` with `citationStyle: 'apa'` populated — Task 6 (`PaperPage.vue`) relies on this being present when a freshly-generated report is loaded via `paperStore.generatedReport`

- [ ] **Step 1: Map `arxiv_id` into `Citation.arxivId`**

Replace (`frontend/src/utils/paperTransform.ts`):

```ts
function buildCitations (result: ArxivGenerateResult): Citation[] {
  return result.references
    .toSorted((a, b) => a.ref_id - b.ref_id)
    .map(ref => {
      const snippetEntry = result.citation_map
        .flatMap(entry => entry.sources)
        .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)

      return {
        id: `cite-${ref.ref_id}`,
        title: ref.title,
        authors: String(ref.author ?? ''),
        journal: String(ref.journal ?? 'arXiv'),
        year: Number(ref.year) || 0,
        snippet: snippetEntry?.relevant_chunk ?? '',
      }
    })
}
```

With:

```ts
function buildCitations (result: ArxivGenerateResult): Citation[] {
  return result.references
    .toSorted((a, b) => a.ref_id - b.ref_id)
    .map(ref => {
      const snippetEntry = result.citation_map
        .flatMap(entry => entry.sources)
        .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)

      return {
        id: `cite-${ref.ref_id}`,
        title: ref.title,
        authors: String(ref.author ?? ''),
        journal: String(ref.journal ?? 'arXiv'),
        year: Number(ref.year) || 0,
        snippet: snippetEntry?.relevant_chunk ?? '',
        arxivId: ref.arxiv_id || undefined,
      }
    })
}
```

- [ ] **Step 2: Add `citationStyle` to the returned `PaperReport`**

Replace:

```ts
  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
  }
}
```

With:

```ts
  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
    citationStyle: 'apa',
  }
}
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits non-zero with one remaining type error — `PaperPage.vue` (lines 108, 138-143) still doesn't handle `citationStyle`. This is fixed in Task 6.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/paperTransform.ts
git commit -m "feat: propagate arxivId and default citationStyle through paper transform"
```

---

### Task 5: `ReferencesSection.vue`

**Files:**
- Create: `frontend/src/components/paper/ReferencesSection.vue`

**Interfaces:**
- Consumes: `formatCitation`, `CitationStyle` (Task 3); `Citation` (Task 2)
- Produces: `<ReferencesSection :citations="..." :style="..." />` — Task 6 (`PaperPage.vue`) renders this component with props `citations: Citation[]` and `style: CitationStyle`

- [ ] **Step 1: Create the component**

Create `frontend/src/components/paper/ReferencesSection.vue`:

```vue
<template>
  <section v-if="citations.length > 0" class="references-section">
    <h3 class="references-title">參考文獻</h3>
    <ol v-if="style === 'ieee'" class="references-list references-list--numbered">
      <li v-for="(citation, index) in citations" :key="citation.id">
        {{ formatCitation(citation, style, index + 1) }}
      </li>
    </ol>
    <ul v-else class="references-list">
      <li v-for="(citation, index) in citations" :key="citation.id">
        {{ formatCitation(citation, style, index + 1) }}
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
  import type { Citation, CitationStyle } from '@/constants/reportData'
  import { formatCitation } from '@/utils/paper/formatCitation'

  defineProps<{
    citations: Citation[]
    style: CitationStyle
  }>()
</script>

<style scoped>
  .references-section {
    margin-top: 28px;
    padding-top: 18px;
    border-top: 1px solid #d8dbe3;
  }

  .references-title {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .references-list {
    margin: 0;
    padding-left: 22px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .references-list li {
    font-size: 12.5px;
    line-height: 1.7;
    color: var(--color-ink);
  }

  .references-list:not(.references-list--numbered) {
    list-style: none;
    padding-left: 0;
  }
</style>
```

- [ ] **Step 2: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: same single remaining error as Task 4 Step 3 (this task adds a new, unreferenced-by-anything-yet component — no new errors).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/paper/ReferencesSection.vue
git commit -m "feat: add ReferencesSection component for formatted citation lists"
```

---

### Task 6: `PaperPage.vue` integration

**Files:**
- Modify: `frontend/src/views/PaperPage.vue`

**Interfaces:**
- Consumes: `ReferencesSection` (Task 5), `citationStyleLabels` (Task 3), `CitationStyle` (Task 2), `saveReport`/`SavedReport` (Task 2)
- Produces: nothing consumed by later tasks (final integration point)

- [ ] **Step 1: Import the new pieces**

Replace:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { getReport, saveReport } from '@/api/report'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { usePaperStore } from '@/store/paperStore'
```

With:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { getReport, saveReport } from '@/api/report'
  import CitationPopover from '@/components/paper/CitationPopover.vue'
  import HubSidebar from '@/components/hub/HubSidebar.vue'
  import ModeSwitch from '@/components/paper/ModeSwitch.vue'
  import PaperEditor from '@/components/paper/PaperEditor.vue'
  import ReferencesSection from '@/components/paper/ReferencesSection.vue'
  import { mockPaperReport } from '@/constants/reportData'
  import { citationStyleLabels } from '@/utils/paper/formatCitation'
  import { usePaperStore } from '@/store/paperStore'
```

(`HubSidebar` moved up one line to keep the `@/components/...` group alphabetically sorted case-insensitively with the newly-added `ReferencesSection` entry: `CitationPopover` < `HubSidebar` < `ModeSwitch` < `PaperEditor` < `ReferencesSection`.)

- [ ] **Step 2: Add `citationStyleItems` and `onCitationStyleChange`**

Replace:

```ts
  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
  }
```

With:

```ts
  const citationStyleItems = Object.entries(citationStyleLabels).map(([value, title]) => ({ value, title }))

  function cancelEdit () {
    report.value = structuredClone(savedSnapshot)
    mode.value = 'view'
  }

  async function onCitationStyleChange () {
    if (!projectId.value) return
    try {
      await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
        citationStyle: report.value.citationStyle,
      })
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    }
  }
```

- [ ] **Step 3: Fix `onMounted`'s hydration to include `citationStyle`**

Replace:

```ts
    } else if (projectId.value) {
      try {
        const saved = await getReport(projectId.value)
        if (saved) {
          report.value = { title: saved.title, content: saved.content, citations: saved.citations }
        }
      } catch (error) {
        saveError.value = error instanceof Error ? error.message : String(error)
      }
    }
```

With:

```ts
    } else if (projectId.value) {
      try {
        const saved = await getReport(projectId.value)
        if (saved) {
          report.value = {
            title: saved.title,
            content: saved.content,
            citations: saved.citations,
            citationStyle: saved.citationStyle ?? 'apa',
          }
        }
      } catch (error) {
        saveError.value = error instanceof Error ? error.message : String(error)
      }
    }
```

- [ ] **Step 4: Fix `save()` to include `citationStyle`**

Replace:

```ts
  async function save () {
    if (!projectId.value) return
    saving.value = true
    saveError.value = null
    try {
      const result = await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
      })
      report.value = { title: result.title, content: result.content, citations: result.citations }
      savedSnapshot = structuredClone(toRaw(report.value))
      mode.value = 'view'
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    } finally {
      saving.value = false
    }
  }
```

With:

```ts
  async function save () {
    if (!projectId.value) return
    saving.value = true
    saveError.value = null
    try {
      const result = await saveReport(projectId.value, {
        title: report.value.title,
        content: report.value.content,
        citations: report.value.citations,
        citationStyle: report.value.citationStyle,
      })
      report.value = {
        title: result.title,
        content: result.content,
        citations: result.citations,
        citationStyle: result.citationStyle,
      }
      savedSnapshot = structuredClone(toRaw(report.value))
      mode.value = 'view'
    } catch (error) {
      saveError.value = error instanceof Error ? error.message : String(error)
    } finally {
      saving.value = false
    }
  }
```

- [ ] **Step 5: Add the style selector to the toolbar**

Replace:

```html
        <div class="toolbar-actions">
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <div class="edit-actions" :class="{ 'edit-actions--hidden': mode !== 'edit' }">
```

With:

```html
        <div class="toolbar-actions">
          <v-select
            v-model="report.citationStyle"
            class="citation-style-select"
            density="compact"
            :disabled="loading || mode === 'edit'"
            hide-details
            :items="citationStyleItems"
            variant="outlined"
            @update:model-value="onCitationStyleChange"
          />
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <div class="edit-actions" :class="{ 'edit-actions--hidden': mode !== 'edit' }">
```

- [ ] **Step 6: Render `ReferencesSection` after `PaperEditor`**

Replace:

```html
        <article class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
        </article>
```

With:

```html
        <article class="paper-sheet">
          <PaperEditor
            v-model="report.content"
            :citations="report.citations"
            :editable="mode === 'edit'"
            :project-id="projectId"
            @citation-click="onCitationClick"
          />
          <ReferencesSection :citations="report.citations" :style="report.citationStyle" />
        </article>
```

- [ ] **Step 7: Add CSS for the style selector**

Add to the `<style scoped>` block, after `.toolbar-actions`:

```css
  .citation-style-select {
    width: 92px;
  }

  .citation-style-select :deep(.v-field) {
    font-size: 12px;
  }
```

- [ ] **Step 8: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors — this fixes the last remaining type error from Tasks 2/4/5.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: integrate citation style selector and reference list into paper page"
```

---

### Task 7: Full verification pass

**Files:**
- No file modifications — this task only verifies the combined state of Tasks 1–6.

**Interfaces:**
- Consumes: the completed state of Tasks 1–6
- Produces: nothing (terminal task)

- [ ] **Step 1: Verify the build and lint both succeed**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

Run (from `frontend/`): `npm run lint`
Expected: no new errors introduced by this plan's files (`reportData.ts`, `arxiv.ts`, `report.ts`, `formatCitation.ts`, `paperTransform.ts`, `ReferencesSection.vue`, `PaperPage.vue`) — pre-existing project-wide lint debt in unrelated files is expected and not a failure.

- [ ] **Step 2: Live browser walkthrough**

Run (from `frontend/`): `npm run dev`. Open the paper editor for a project that has a saved report with citations (or generate a fresh one via the arXiv paper-generation flow so it has real `arxivId` values), then:

1. Confirm a "參考文獻" section appears below the paper content, in view mode, formatted per the current style (default APA).
2. Confirm the citation style `<v-select>` appears in the toolbar next to the view/edit switch, showing APA/IEEE/MLA options.
3. Switch to IEEE — confirm the reference list re-renders as a numbered list matching the `[n] Authors, "Title," arXiv:ID, Year.` template for arXiv-sourced entries.
4. Switch to MLA — confirm it re-renders as an unnumbered list matching the MLA template.
5. Reload the page — confirm the style selection persisted (still IEEE/MLA, not reset to APA), confirming the `onCitationStyleChange` auto-save round-tripped through the backend.
6. Click 編輯 (edit mode) — confirm the style `<v-select>` becomes disabled (grayed out, not interactive) while editing.
7. Click 取消 (cancel) to return to view mode — confirm the style selector becomes interactive again and the reference list is unaffected.
8. If a project with zero citations is available, confirm the reference section doesn't render at all; if not available, read `ReferencesSection.vue`'s `v-if="citations.length > 0"` in the diff and confirm it's present and correctly placed.

Expected: all of the above work with no console errors.

- [ ] **Step 3: Stop the dev server after checking**

Stop the `npm run dev` process started in Step 2.

---

## Plan Self-Review

**Spec coverage:** 段落 A (`arxiv_id`) → Task 1 Step 1-2. 段落 B (前端型別) → Task 2, Task 4 Step 1. 段落 C (格式化邏輯) → Task 3. 段落 D (`ReferencesSection.vue`) → Task 5. 段落 E (後端/API `citationStyle` 傳遞) → Task 1 Step 3-5, Task 2 Step 4. 段落 F (`PaperPage.vue` 整合) → Task 6. 段落 G (邊界情況) → covered inline: empty citations (Task 5 Step 1's `v-if`), missing `citationStyle` on old records (Task 6 Step 3's `?? 'apa'`), missing `arxivId` (Task 3's `formatCitation` branch), empty `journal` (Task 3's `formatFallback`).

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" — every step shows complete before/after code, exact commands, and exact expected output. Task 3 Step 2's manual verification includes a fallback instruction (relative-import workaround) because `tsx`'s path-alias resolution outside Vite is a genuine environmental uncertainty, not a placeholder — the primary path and expected output are both fully specified.

**Type consistency:** `CitationStyle` is defined once (Task 2, `reportData.ts`) and imported by name (never redefined) in Task 3, Task 5, Task 6, and `api/report.ts`. `Citation.arxivId` (Task 2) is the exact property name used in Task 3's `formatArxiv`/`formatFallback` and Task 4's `buildCitations`. `formatCitation(citation, style, index)`'s signature (Task 3) matches every call site in Task 5. `PaperReport.citationStyle` (Task 2) is populated at all three construction sites: `mockPaperReport` (Task 2 Step 3), `transformArxivResultToPaperReport` (Task 4 Step 2), and both `onMounted`/`save()` in `PaperPage.vue` (Task 6 Steps 3-4) — no code path can produce a `PaperReport` missing this now-required field.
