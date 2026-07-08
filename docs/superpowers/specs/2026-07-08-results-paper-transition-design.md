# Result 儀表板 ↔ 論文頁 轉換設計

日期:2026-07-08
狀態:已與使用者確認方向,待實作

## 背景

`/results` 目前是單頁儀表板([ResultsPage.vue](../../../frontend/src/views/ResultsPage.vue)),右上有「報告 / 程式碼」tab,但只切換樣式、沒有實際內容切換。論文頁(文件檢視 + 來源文獻/檢索片段側欄)目前只有 mockup,尚未實作。

本設計定義兩頁的導航關係、元件拆分與假資料模型。引用文獻的真實來源(RAG / LLM 生成)尚未決定,本階段一律使用假資料,但資料結構預留未來接後端。

## 決策摘要

- **本次範圍:先單獨做論文頁。** 使用者的核心目標是論文生成的前端。PaperView 掛在獨立路由 `/paper`,不動現有 ResultsPage 與其他程式碼;與儀表板的串接(巢狀路由重構)列為第二階段。
- **導航架構(第二階段):Tab + 巢狀路由。** Tab 外觀保留,點擊實際做 `router.push`,active 狀態由目前路由推導。
- **假資料先行。** 引用來源之後再定;資料模型設計成後端未來回傳同構 JSON 即可直接接上。
- **不做生成中 skeleton。** 假資料階段直接顯示論文;生成狀態 UX 等接真 API(沿用既有 job 輪詢模式)時再加。

## 1. 路由結構

**第一階段(本次):**

```
/paper            → PaperView(論文 + 引用側欄,含 Sidebar,與現有頁面同佈局)
```

**第二階段(之後):**

```
/results          → ResultsOverview(現有儀表板內容)
/results/report   → PaperView(自 /paper 移入)
/results/code     → CodeView(占位,之後再做)
```

第二階段時外殼元件持有 Sidebar、返回鍵與 toolbar tabs,中間為 `<router-view>`,toolbar 為三個 tab:總覽 / 報告 / 程式碼。

## 2. 元件拆分

**第一階段(本次):**

```
frontend/src/views/PaperPage.vue           論文頁:Sidebar + 論文主體 + 引用側欄
frontend/src/components/paper/
  PaperSection.vue       單一章節渲染,含引用 highlight
  CitationPanel.vue      右側「來源文獻 + 檢索片段」卡片列表
```

**第二階段(之後):** 現有 `views/ResultsPage.vue` 拆為 `ResultsLayout.vue` + `ResultsOverview.vue`,`/results` 改為巢狀定義,PaperPage 移入 `/results/report`。

## 3. 假資料模型

位置:`frontend/src/constants/reportData.ts`

```ts
interface Citation {
  id: string
  title: string
  authors: string
  journal: string
  year: number
  snippet: string          // 檢索片段原文
}

interface PaperSegment {
  text: string
  citationId?: string      // 有值 → 渲染為黃底 highlight,可點擊
}

interface PaperSection {
  heading: string          // 例:「4.1 模型效能評估」
  segments: PaperSegment[]
}

interface PaperReport {
  sections: PaperSection[]
  citations: Citation[]
}
```

假資料內容沿用 mockup:電信客戶流失案例、XGBoost vs 其他模型、SHAP 分析、含 2–3 筆引用。

## 4. 論文頁互動

- 點內文黃底 highlight → 右側面板捲動至對應文獻卡片並高亮該卡。
- 點側欄卡片 → 內文捲動至對應段落。
- 側欄固定寬約 280px;內文維持閱讀行寬。窄螢幕(< ~1100px)側欄收合,點 highlight 以彈出層顯示卡片。

## 5. 轉場

- 路由切換使用 fade + 輕微上移(150–200ms),套在 `<router-view>` 的 `<transition>` 上。
- Tab active 樣式沿用現有 toolbar 設計。

## 未來擴充(不在本次範圍)

- 第二階段:儀表板巢狀路由重構,PaperPage 併入 `/results/report`。
- 論文生成改為後端非同步 job(沿用 `/api/models/workflow/jobs` 的輪詢模式),屆時再加入「生成中」狀態 UI。
- 引用來源接 Hub Framework Library(使用者上傳論文庫)做 RAG,或其他方案。
- `/results/code` 的實際內容。
- 報告匯出(PDF / Word)。
