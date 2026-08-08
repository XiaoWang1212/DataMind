# 論文編輯器參考文獻列表

## 背景

先前設計論文編輯器工具列增強時，使用者提出「文獻管理，最好可設定 APA、IEEE 或 MLA 格式」，但因為屬於獨立子系統，明確延後為未來session的獨立主題（另一項延後項目是 Word 風格自動分頁，尚未排入）。這次針對文獻管理討論後，範圍收斂為：只做「論文結尾自動產生格式化的參考文獻列表」，不做手動新增/編輯文獻條目，也不做編輯器內手動插入行內引用的 UI（行內引用目前只能靠 AI 生成論文內容時自動帶入，這次不擴充）。

探索既有程式碼後確認：
- `Citation`（`frontend/src/constants/reportData.ts`）目前只有 `title`/`authors`/`journal`/`year`/`snippet`，`authors` 是預先組好的完整姓名字串（例如 arXiv API 回傳的 "John Smith, Jane Doe"），不是拆開的姓/名結構。
- 論文的參考文獻資料幾乎全部來自 arXiv 探勘生成流程（`frontend/src/utils/paperTransform.ts` 的 `buildCitations`，資料源頭是 `backend/services/rag/paper_rag.py` 的 `generate_paper`）。後端收錄 arXiv 論文時已經抓得到 `arxiv_id`（`paper_rag.py:334`），但目前只把它塞進 `journal` 字串（`f"arXiv:{arxiv_id}"`）裡，沒有獨立傳給前端。
- 另有一條手動上傳論文的路徑（`backend/routes/rag.py`），只收集 `author`/`year`，連 `journal` 都沒有。
- 後端 `report_store.py` 把 `citations` 當任意 JSON 存檔，不做 schema 驗證，新增欄位不需要 migration。
- 有一個 `/api/rag/cite` 端點做過陽春的 APA/MLA 字串拼接，但前端完全沒有呼叫它，是死路，這次不沿用。

第一輪設計時使用者直接反對「格式不完全正確這功能就沒用了」——調查後確認：arXiv 預印本本來就不該套用期刊論文的引用格式（不需要 volume/issue/pages，那些是期刊才有的欄位），只要把 `arxiv_id` 傳出來，就能用真正符合各格式規範的 arXiv 預印本引用寫法。這是這次設計能做到「真正正確」的關鍵，而不是像原本那樣不管來源都硬套同一種期刊格式模板。

## 目標

1. 後端收錄 arXiv 論文時，把 `arxiv_id` 當成獨立的 metadata 欄位傳出來（原本只塞在 `journal` 字串裡）
2. 前端 `Citation`／`ArxivReference` 型別新增可選的 `arxivId` 欄位，`buildCitations` 接起來
3. 新增 `formatCitation(citation, style, index)` 純函式，依「有無 `arxivId`」分兩種樣板：有 `arxivId` 用正確的 arXiv 預印本格式；沒有的話用既有欄位盡力排版（省略缺欄位）
4. 新增 `ReferencesSection.vue`，顯示在論文內容下方（`.paper-sheet` 內、`<PaperEditor>` 之後），依 `report.citationStyle` 即時算出格式化列表
5. 新增格式選擇器（`v-select`，APA/IEEE/MLA），放在 `PaperPage.vue` 工具列跟 ModeSwitch 並列，選擇結果存進 `report.citationStyle` 並跟論文一起存檔

## 非目標

- 不做手動新增/編輯/刪除文獻條目的 UI——文獻資料完全來自既有的 AI 生成/RAG 探勘流程
- 不做編輯器內「插入行內引用」的工具列按鈕——行內引用只能靠 AI 生成內容時自動帶入 `citation` mark，這次不擴充
- 不重新排版作者姓名成學術格式要求的「姓在前、名字縮寫」寫法（例如 APA 的 `Smith, J.`）——來源資料是不透明的完整姓名字串，無法可靠拆解重組，這次只保證「來源類型判斷正確、欄位順序與標點正確」，作者姓名維持原始字串
- 不做長作者清單的 "et al." 縮寫截斷——同樣因為 `authors` 是不透明字串，沒有可靠的截斷依據
- 不處理手動上傳論文（無 `arxiv_id`、甚至無 `journal`）的完整期刊格式化——這類來源缺乏 volume/issue/pages/DOI，做不到真正正確，維持「盡力排版、省略缺欄位」的備援邏輯，不假裝是完整期刊引用
- 不做參考文獻列表依姓氏字母排序（APA/MLA 標準做法）——維持 `citations` 陣列原本順序（文中第一次出現的順序），因為姓名字串不透明、無法可靠取姓氏排序
- 不把參考文獻列表寫進 Tiptap 的可編輯文件內容（`content` JSON）——維持獨立的唯讀 Vue 元件呈現，不與可編輯文件內容混合，避免同步/覆寫使用者手動編輯的風險

## 設計

### 段落 A：後端傳出 `arxiv_id`

`backend/services/rag/paper_rag.py` 的 `generate_paper` 收錄候選論文時：

```python
# 現在（第 328-336 行附近）
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

```python
# 改為
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

這個 metadata 字典會透過 `generate_paper` 既有邏輯（`global_ref_list.append({..., **sr.chunk.metadata})`，`paper_rag.py:211-216`）自動展開進 `references` 陣列的每個項目，不需要再改其他後端程式碼。`journal` 欄位維持不動（給沒有走新格式化邏輯的舊資料相容用）。

### 段落 B：前端型別與資料轉換

`frontend/src/api/arxiv.ts` 的 `ArxivReference`：

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

`frontend/src/constants/reportData.ts` 的 `Citation`：

```ts
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

（`CitationStyle` 型別定義在段落 C。）

`frontend/src/utils/paperTransform.ts` 的 `buildCitations`：

```ts
return result.references
  .toSorted((a, b) => a.ref_id - b.ref_id)
  .map(ref => ({
    id: `cite-${ref.ref_id}`,
    title: ref.title,
    authors: String(ref.author ?? ''),
    journal: String(ref.journal ?? 'arXiv'),
    year: Number(ref.year) || 0,
    snippet: snippetEntry?.relevant_chunk ?? '',
    arxivId: ref.arxiv_id || undefined,
  }))
```

（`snippetEntry` 邏輯不變，只是額外帶出 `arxivId`。）

`transformArxivResultToPaperReport` 回傳值新增 `citationStyle: 'apa'`（預設值）。

`mockPaperReport`（`reportData.ts`）也要補上 `citationStyle: 'apa'`，維持型別一致；它的兩筆範例文獻沒有 `arxivId`，會走備援格式，這是預期行為（示範資料本來就不是真的 arXiv 論文）。

### 段落 C：格式化邏輯

新檔案 `frontend/src/utils/paper/formatCitation.ts`：

```ts
import type { Citation } from '@/constants/reportData'

export type CitationStyle = 'apa' | 'ieee' | 'mla'

export const citationStyleLabels: Record<CitationStyle, string> = {
  apa: 'APA',
  ieee: 'IEEE',
  mla: 'MLA',
}

function formatArxiv (citation: Citation, style: CitationStyle, index: number): string {
  const { authors, title, year, arxivId } = citation
  const url = `https://arxiv.org/abs/${arxivId}`

  switch (style) {
    case 'apa': {
      return `${authors} (${year}). ${title}. arXiv. ${url}`
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
  const journalSegment = journal ? ` ${journal}.` : ''

  switch (style) {
    case 'apa': {
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

`index` 是 1-based，對應該篇文獻在 `report.citations` 陣列中的位置（也就是文中第一次被引用的順序，跟 `PaperEditor.vue` 現有的 `citationIndex[citation.id] = index + 1` 用同一套順序）——只有 IEEE 樣板實際顯示編號，APA/MLA 忽略這個參數但仍保留一致的函式簽章。

### 段落 D：`ReferencesSection.vue`

新檔案 `frontend/src/components/paper/ReferencesSection.vue`：

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
  import type { Citation } from '@/constants/reportData'
  import type { CitationStyle } from '@/utils/paper/formatCitation'
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

沒有 IEEE 編號的樣式（APA/MLA）不用項目符號，直接條列（`list-style: none`），符合這兩種格式常見的排版慣例。

### 段落 E：後端/API 的 `citationStyle` 傳遞

`backend/routes/report.py` 的 `save_report`：

```python
title = data.get("title")
content = data.get("content")
citations = data.get("citations", [])
citation_style = data.get("citationStyle", "apa")
...
result = store.save(project_id, title, content, citations, citation_style)
```

`backend/services/report/report_store.py` 的 `save`：

```python
def save(self, project_id: str, title: str, content: dict, citations: list, citation_style: str = "apa") -> dict:
    record = {
        "title": title,
        "content": content,
        "citations": citations,
        "citationStyle": citation_style,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    ...
```

`GET` 端不用改——`load()` 直接把整包 JSON 記錄讀回來，`citationStyle` 會自然包含在裡面。

`frontend/src/api/report.ts` 的 `SavedReport`／`saveReport`：

```ts
import type { CitationStyle } from '@/utils/paper/formatCitation'

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
): Promise<SavedReport> { /* 函式主體不變，只是 payload 型別多一個欄位 */ }
```

### 段落 F：`PaperPage.vue` 整合

在 `.paper-sheet` 內、`<PaperEditor>` 之後加入：

```html
<ReferencesSection :citations="report.citations" :style="report.citationStyle" />
```

工具列（`.toolbar-actions`，跟 `<ModeSwitch>` 同一列）新增格式選擇器：

```html
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
```

```ts
import { citationStyleLabels } from '@/utils/paper/formatCitation'
import { saveReport } from '@/api/report'

const citationStyleItems = Object.entries(citationStyleLabels).map(([value, title]) => ({ value, title }))

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

選擇器在編輯模式下停用（`mode === 'edit'` 時 `disabled`），只能在檢視模式切換格式。這是刻意的限制：檢視模式下 `report.value.content`／`title`／`citations` 保證跟後端最後一次存檔的狀態一致（`cancelEdit`／`save` 都會在離開編輯模式前把狀態收斂成一致），所以格式切換時直接呼叫 `saveReport` 是安全的，不會把使用者編輯中、還沒點「儲存」的暫存內容意外存進去。`onCitationStyleChange` 是獨立的輕量存檔路徑，不重用既有的 `save()`（`PaperPage.vue:133-151`）——`save()` 是編輯流程專用的，儲存成功後會把 `mode` 切回 `'view'`、更新 `savedSnapshot`，這些副作用跟純粹切換文獻格式無關，混用會讓語意變得混亂。

既有的 `save()` 函式（`PaperPage.vue:133-151`，使用者在編輯模式點「儲存」時呼叫）也要補上 `citationStyle: report.value.citationStyle`：

```ts
const result = await saveReport(projectId.value, {
  title: report.value.title,
  content: report.value.content,
  citations: report.value.citations,
  citationStyle: report.value.citationStyle,
})
report.value = { title: result.title, content: result.content, citations: result.citations, citationStyle: result.citationStyle }
```

這是必要的修改，不是選配：後端 `save_report` 路由用 `data.get("citationStyle", "apa")` 取值，如果編輯流程存檔時沒有帶這個欄位，每次一般的內容編輯存檔都會把使用者選好的格式悄悄重設回 APA。

### 段落 G：邊界情況

- `citations.length === 0`：`ReferencesSection` 整段不渲染（`v-if="citations.length > 0"`）
- 舊的已存檔論文（存檔時還沒有 `citationStyle` 欄位）：`getReport` 讀回來時，`report.value = { ..., citationStyle: saved.citationStyle ?? 'apa' }`，預設 APA
- 舊的已存檔文獻（沒有 `arxivId`）：`formatCitation` 自動走備援樣板，不會因為缺欄位而壞掉
- `journal` 為空字串（備援樣板）：省略整段 journal 文字，不留多餘標點

## 驗證方式

- `npm run build`、`npm run lint` 皆無錯誤（`frontend/` 目錄下執行）
- 後端：跑一次 arXiv 論文生成流程，確認 `/api/rag/arxiv/generate` 回傳的 `references` 陣列每筆都帶有 `arxiv_id`
- 前端：載入一篇有 arXiv 來源文獻的論文，切換 APA/IEEE/MLA 三種格式，確認參考文獻列表照段落 C 的樣板正確顯示（含 `https://arxiv.org/abs/...` 連結文字、IEEE 編號）
- 載入 `mockPaperReport`（無 `arxivId`），確認走備援樣板，三種格式都能正常顯示且無多餘標點
- 切換格式後重新整理頁面，確認格式選擇維持（已存檔）
- 清空一篇論文的文獻（或用沒有文獻的論文測試），確認參考文獻區塊整段不顯示
- 參考文獻區塊在檢視與編輯模式都會顯示；格式選擇器在編輯模式下應為停用狀態（看得到但不能點），只有在檢視模式才能切換格式
