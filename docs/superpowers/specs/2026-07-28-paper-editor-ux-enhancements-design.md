# 論文編輯器互動優化(滑動分段切換／引用彈窗／插入圖表)

## 背景

[[2026-07-25-paper-editor-design]] 已經把 `/paper` 頁面從唯讀改成可編輯(Tiptap),並補上後端持久化。目前 `PaperPage.vue` 的檢視/編輯切換是單一個會變形的按鈕(檢視時顯示「編輯」,點下去直接進入編輯模式並換成「取消」/「儲存」),不是雙態切換控制。引用對照則是一個永遠展開的側邊欄(`CitationPanel.vue`),列出全部參考文獻卡片,點擊正文引用標記只是捲動高亮側欄卡片。插入圖表功能完全不存在。

本次針對這三個互動點做優化:

1. 檢視/編輯切換改成有滑動 pill 動畫的分段式控制
2. 引用對照從「永遠展開的側邊欄」改成「點擊標記才彈出的卡片」
3. 編輯工具列新增「插入圖表」,把工作流程頁的模型比對數值畫成圖插入論文

## 範圍

**做:**
- 新增 `ModeSwitch.vue`,取代 `PaperPage.vue` 現有的單一「編輯」按鈕,提供「檢視」/「編輯」雙態滑動 pill,搭配 `offsetLeft`/`offsetWidth` 讀取 + `cubic-bezier(0.65,0,0.35,1)` 0.4s 動畫
- 移除 `CitationPanel.vue` 側邊欄,新增 `CitationPopover.vue`,點擊正文引用標記時在標記旁彈出完整引用卡片(標題/作者/期刊/年份/檢索片段)
- `PaperEditor.vue` 工具列新增「插入圖表」按鈕與 `InsertChartDialog.vue`,可選模型/指標/圖表類型(長條圖或雷達圖),即時預覽後以靜態圖片插入編輯器
- 新增自製 SVG 長條圖/雷達圖繪圖元件(`components/paper/charts/`)
- `summarizeWorkflowResult.ts` 補上 `valueRaw: number` 欄位供繪圖使用
- 新增 `@tiptap/extension-image` 依賴

**不做(out of scope):**
- 圖表不做成互動式/可重新整理的 Tiptap 節點——只存靜態圖片快照,插入後圖表數據若之後變動,已插入的圖片不會跟著更新
- 不支援匯出 workflow 節點流程圖(vue-flow 畫布)本身,只做模型比對數值圖表
- 引用 popover 不做「編輯引用內容」功能,純顯示
- pill 切換不做鍵盤方向鍵導覽(維持滑鼠/觸控點擊)
- 不新增後端 API——圖表以 base64 圖片存進既有 Tiptap `content` JSON,沿用 [[2026-07-25-paper-editor-design]] 的 `report_bp` 存檔流程

## 架構總覽

三個功能彼此獨立,分別修改/新增以下元件,互不依賴:

```
PaperPage.vue
├─ ModeSwitch.vue (新增)          — 取代現有 toolbar-actions 的「編輯」按鈕
├─ PaperEditor.vue (修改)
│   ├─ 工具列新增「插入圖表」按鈕
│   ├─ InsertChartDialog.vue (新增)
│   │   └─ charts/BarChart.vue, charts/RadarChart.vue (新增,SVG 繪製)
│   └─ citation-click emit payload 擴充 { citationId, target }
└─ CitationPopover.vue (新增,取代 CitationPanel.vue)
```

`CitationPanel.vue` 整個刪除,`PaperPage.vue` 的側欄版面(`.paper-body` 雙欄、`.paper-citations`)一併移除,`paper-sheet` 改回單欄置中。

---

## A. `ModeSwitch.vue` — 滑動 pill 分段切換

**Props/Emits**:`modelValue: 'view' | 'edit'`、`disabled: boolean`(對應現有 `loading` 狀態)、`update:modelValue` emit。

**DOM 結構**:
```html
<div class="mode-switch" ref="trackRef">
  <span class="pill" ref="pillRef" />
  <button ref="viewBtn" :class="{active: modelValue==='view'}" @click="select('view')">檢視</button>
  <button ref="editBtn" :class="{active: modelValue==='edit'}" @click="select('edit')">編輯</button>
</div>
```

**動畫邏輯**:
- `select(target)` 時讀取目標 button 的 `offsetLeft`/`offsetWidth`,寫進 `pillRef.value.style.left/width`
- CSS:`.pill { position: absolute; transition: left 0.4s cubic-bezier(0.65,0,0.35,1), width 0.4s cubic-bezier(0.65,0,0.35,1); }`
- `button` 文字顏色 `transition: color 0.4s cubic-bezier(0.65,0,0.35,1)`,未選中 `var(--text-secondary)`,選中白色(pill 底色用 `var(--brand)`)
- `onMounted` 立即定位一次 pill(用 `nextTick` 確保 DOM 已渲染出正確寬度),避免初始畫面 pill 疊在左上角
- 監聽 `window resize`,重新計算目前 active button 的位置(避免 responsive breakpoint 造成 pill 錯位)

**與 `PaperPage.vue` 整合**:`toolbar-actions` 內的「編輯」按鈕(`PaperPage.vue:16-26`)換成 `<ModeSwitch v-model="mode" :disabled="loading" />`;`mode==='edit'` 時在 `ModeSwitch` 右側額外渲染既有的「取消」/「儲存」`v-btn`(`PaperPage.vue:27-38` 原樣保留,只是從 `v-else` 分支移到並排位置)。

---

## B. `CitationPopover.vue` — 點擊引用標記才顯示資訊

**移除**:`CitationPanel.vue` 檔案刪除;`PaperPage.vue` 移除 `<CitationPanel>`、`.paper-body` 雙欄 CSS、`.paper-citations`、`onPanelSelect` 函式。

**`PaperEditor.vue` 改動**:`handleClick`(現行 `PaperEditor.vue:148-159`)的 `citation-click` emit payload 從單純 `citationId: string` 擴充為 `{ citationId: string, target: HTMLElement }`,把被點擊的 `[data-citation-id]` 元素一併傳出,供 popover 定位用。

**`CitationPopover.vue`**:
- 用 Vuetify `v-menu`,`activator` 綁定 `PaperPage.vue` 收到的 `target` 元素,`location="bottom"`(Vuetify 自動 flip 避免超出視窗)
- 內容照搬 `CitationPanel.vue` 卡片內容(標題/作者/期刊/年份/檢索片段),樣式與配色(`#fffbe8`/`#eadf9e` 黃色系)沿用,只是從側欄卡片改成單張浮動卡片
- `PaperPage.vue` 用 `activeCitationId: Ref<string|null>` + `popoverTarget: Ref<HTMLElement|null>` 控制開關:`onCitationClick({citationId, target})` 時,若點的是同一個 `citationId` 且 popover 已開 → 關閉(toggle);否則設定新的 citationId/target 開啟
- `v-menu` 預設點擊外部即關閉,不用額外處理

---

## C. 插入圖表(工作流程模型比對結果)

**繪圖方式**:自製輕量 SVG 元件,不導入 chart.js 等第三方庫(理由:只需長條圖/雷達圖兩種簡單圖型,靜態快照不需要互動能力,SVG 可直接序列化成 `data:image/svg+xml;base64,...`,不用經過 canvas 截圖處理裝置畫素比等細節)。

- `components/paper/charts/BarChart.vue`:props `{ series: { model: string, metric: string, value: number }[] }`,依 metric 分組、model 為 x 軸類別,SVG `<rect>` 畫長條
- `components/paper/charts/RadarChart.vue`:props 同上,以 metric 為軸、model 為多邊形疊圖,SVG `<polygon>` 畫雷達圖
- 兩者共用一份色階(沿用 App 既有配色 token,如 `--brand` 系列衍生的幾個色階給不同 model 上色)

**資料處理**:`summarizeWorkflowResult.ts` 現有回傳的 `metrics: { metric, valueFormatted }[]` 補上 `valueRaw: number`(取平均值後 `toFixed(4)` 之前的原始 number),`ModelMetricSummary` 型別同步更新。既有呼叫端(`ResultView.vue`)只用 `valueFormatted`,不受影響。

**`InsertChartDialog.vue`**:
1. 開啟時呼叫 `loadWorkflowStateFromStorage(projectId)` 取 `workflowResult`,無資料時顯示「此專案尚無工作流程結果可插入」,停用插入
2. 有資料則呼叫 `summarizeWorkflowResult()` 取得各模型/指標數值,渲染:
   - 圖表類型切換(長條圖/雷達圖,兩個 `v-btn-toggle` 選項)
   - 模型複選(checkbox list,預設全選)
   - 指標複選(checkbox list,預設全選)
   - 即時預覽區(用 `BarChart`/`RadarChart` 依目前選擇渲染)
3. 「插入」按鈕:取預覽區 SVG 的 `outerHTML`,用 `XMLSerializer` 序列化、`btoa` 編碼成 `data:image/svg+xml;base64,...`,呼叫 `editor.chain().focus().setImage({ src, alt: '工作流程模型比對圖表' }).run()`,關閉 dialog

**`PaperEditor.vue` 改動**:
- extensions 陣列新增 `Image`(來自新增依賴 `@tiptap/extension-image`,版號對齊現有 tiptap 系列 `^3.29.0`)
- 工具列(`editable=true` 時顯示的區塊)新增「插入圖表」`v-btn`(`icon="mdi-chart-bar"`),點擊開啟 `InsertChartDialog`,需要能拿到目前 `projectId`(從 `PaperPage.vue` 以 prop 傳入,`PaperEditor` 目前沒有這個 prop,需新增)

---

## 錯誤處理

- **ModeSwitch**:`disabled`(對應 `loading`)時按鈕與 pill 點擊一律無效,沿用現有「載入中禁用編輯」邏輯
- **CitationPopover**:找不到對應 `citationId` 的 citation 資料(理論上不會發生,mark 與 citations 陣列同源)時不彈出、記 console warning
- **InsertChartDialog**:
  - 無 workflow 結果 → dialog 內提示,插入按鈕停用(不擋開啟 dialog 本身)
  - 使用者取消勾選到 0 個模型或 0 個指標 → 預覽區顯示「請至少選擇一項」,插入按鈕停用
  - SVG 序列化/插入失敗(理論上不會,純字串操作)→ 不特別處理,與現有專案「無自動化測試、手動驗證」的錯誤處理水準一致

## 測試

專案目前無自動化測試框架,維持手動驗證慣例:

1. **ModeSwitch**:進入 `/paper`,確認 pill 初始位置對齊「檢視」;點擊「編輯」確認 pill 滑動到「編輯」位置且文字顏色 crossfade、右側同時出現「取消」「儲存」;點「取消」確認 pill 滑回「檢視」;縮放視窗確認 pill 位置仍對齊按鈕
2. **CitationPopover**:檢視模式下點擊正文引用標記,確認標記旁彈出卡片且內容正確(標題/作者/期刊/年份/片段);點擊卡片外部確認關閉;再點同一個標記確認 toggle 關閉;點不同標記確認卡片內容切換
3. **InsertChartDialog**:編輯模式下點「插入圖表」,對一個有 workflow 結果的專案:切換長條圖/雷達圖確認預覽正確;勾選/取消模型與指標確認預覽即時更新;點「插入」確認游標處出現圖片;點「儲存」後重新整理頁面確認圖片仍在;對沒有 workflow 結果的專案開啟 dialog,確認提示訊息與停用狀態
