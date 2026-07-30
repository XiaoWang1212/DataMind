# Workflow 工作流區色票套用設計

## 背景

第一批（[2026-07-30-hub-shell-color-application-design.md](2026-07-30-hub-shell-color-application-design.md)）套用了 Hub 外殼；第二批（[2026-07-30-paper-editor-color-application-design.md](2026-07-30-paper-editor-color-application-design.md)）套用了論文編輯區；第三批（[2026-07-30-hub-content-color-application-design.md](2026-07-30-hub-content-color-application-design.md)）套用了 Hub 頁面內容區，並在最終審查中建議追蹤「剩餘約 18 個檔案的 Workflow 區」。這是第四批,也是這輪色票套用計畫的最後一批。

盤點範圍為 `frontend/src/views/WorkflowPage.vue`、`frontend/src/views/ResultsPage.vue`、`frontend/src/views/PaperSourcesView.vue`,以及 `frontend/src/components/workflow/` 底下 14 個檔案(`UploadDialog.vue`、`IconNode.vue`、`WorkflowCanvas.vue`、`WorkflowOptionsPanel.vue`、`WorkflowWorkspace.vue`,與 `nodePanel/` 下 9 個節點設定面板),共 17 個檔案。`frontend/src/components/WorkflowBuilder.vue` 經 grep 確認未被任何路由或元件引用(死碼),不列入範圍。

這個區域是 `/workflow → /results → /paper/sources` 這條獨立於 Hub 之外的舊流程(`/workflow` 頁面用 `WorkflowWorkspace` 建構與執行模型訓練流程,完成後導向 `/results` 顯示結果,再導向 `/paper/sources` 選擇文獻生成論文)。盤點發現這 17 個檔案共用同一組尚未套用新色票的舊調色盤,CTA/強調藍分裂成兩個相近色碼 `#005dff`(多數檔案)與 `#2563eb`(部分檔案,含各自的 rgba 半透明變體),文字灰階與前幾批發現的模式相同。

## 目標

- 把全部 17 檔共用的 CTA/強調藍(`#005dff`、`#2563eb` 及其 rgba 變體)改成 `var(--color-accent)`
- 把主要文字色改成 `var(--color-ink)`、次要文字色改成 `var(--color-secondary)`
- 把白/近白底改成 `var(--color-surface)`
- `ResultsPage.vue`、`PaperSourcesView.vue` 補上跟 `PaperPage.vue` 一致的頁面局部變數命名(`--page-bg`/`--card-bg`/`--brand`),外層裝飾性光暈改用 accent 色的 `color-mix` 漸層
- `ResultsPage.vue` 的「AI生成洞察」卡片漸層改用 accent 漸層
- 順手統一成功綠、錯誤紅各自重複的兩個色碼(延續前三批已定案的統一值:成功 `#16a34a`、錯誤 `#ef4444`)

## 非目標

- 不處理中性邊框/分隔線灰階色(`rgba(148,163,184,*)`、`#e2e8f0`、`#cbd5e1`、`#ced3e9`、`#d8dbe3` 等)
- 不處理 `IconNode.vue` 的節點類型色盤(`node-purple`/`node-yellow`/`node-pending`)——性質類似前一批排除在外的圖表分類色盤,用於區分節點種類,非品牌色。`node-purple` 剛好用了跟 CTA 相同的 `#005dff`,但維持不動(理由見段落 C)
- 不處理裝飾性功能圖示色塊:Gemini 上傳按鈕的靛紫色 `#4f46e5`,以及 `FeatureEngineeringPanel.vue`/`PreprocessorPanel.vue` 的靛紫步驟編號徽章(`#e0e7ff`/`#4f46e5`)
- 不處理新增/移除節點的短暫閃色動畫(`#06b6d4`/`#ef4444`)——瞬時動畫回饋,非常駐 UI 色
- 不處理 `ComputeCiPanel.vue` 的警告琥珀色 `#92400e`——狀態色,色相剛好接近 accent 純屬巧合,同前一批 `.badge--running` 的排除邏輯
- 不新增/修改任何功能邏輯,只套用既有 UI 的顏色
- `frontend/src/components/WorkflowBuilder.vue` 不在範圍內(未被引用的死碼)

## 設計

### 段落 A:CTA / 強調色

全部 17 個檔案裡的 `#005dff`、`#2563eb`(含各自不同透明度的 rgba 變體,例如 `rgba(0, 93, 255, 0.1)`、`rgba(59, 130, 246, 0.12)`)→ 改用 `var(--color-accent)` 或其 `color-mix`/透明度變體。適用範圍包含:

- 所有 CTA 按鈕(`.btn-primary`、`.add-btn`、`.btn-continue`、`.upload-modal-button`、`.wizard-tab--active`)
- 頁籤/步驟啟用態(`.wizard-tab--active`、`.wizard-tab__num` 啟用態)
- focus/hover 外框與陰影(`.form-row select:focus`、`.column-name-input`、`.node-highlighted` 預設 `--highlight-color` 回退值)
- 抽屜拖曳把手 `.options-drawer__bar`
- `DistributionPanel.vue` SVG 圖表柱狀 `fill="#2563eb"` 與 `WorkflowFileUploadPanel.vue`/`UploadDialog.vue` 的 `.upload-modal-chart-bar-fill` 背景(注意:SVG `fill` 屬性與 CSS `background` 都要套用,不只 CSS 宣告)
- 連結文字(`.distribution-title-toggle`)
- 選取列淺色底(`.target-row td` 的 `rgba(0, 93, 255, 0.1)`)
- `WorkflowWorkspace.vue` 的懸浮工具按鈕(`.demo-btn`/`.execute-workflow-btn`/`.view-results-btn`/`.json-upload-btn`/`.paper-upload-btn`)文字色與邊框
- `DataTablePanel.vue` 的 `.data-table-guide`(選欄引導文字)、`.data-table-loading-overlay` 文字色
- `SettingsPanel.vue`/`ComputeCiPanel.vue` 的卡片邊框、背景 tint(`rgba(0, 93, 255, 0.03~0.14)`)一律改用對應濃度的 `color-mix(in oklab, var(--color-accent) N%, var(--color-surface))` 或 `color-mix(in oklab, var(--color-accent) N%, transparent)`,N 值比照原 rgba 的透明度百分比換算

### 段落 B:文字色

| 現在 | 改成 |
|---|---|
| `#0f172a`、`#1e293b`、`#1f2937`、`#1c2130`、`#20232a`、`#1f2532`、`#1f2430`、`#192235`、`#15181e`、`#242424` | `var(--color-ink)` |
| `#475569`、`#64748b`、`#94a3b8`、`#6b7280`、`#6f7480`、`#5f6571`、`#3a3f4a` | `var(--color-secondary)` |
| `#334155`(僅作文字色使用時,例如 `ComputeCiPanel.vue` 的 `.ci-table__metric`) | `var(--color-secondary)` |

### 段落 C:白/近白底與頁面局部變數

`#ffffff`、`#fff`、`#f8fafc`、`#f9fbff`、`#f8fbff`、`#f7f9ff`、`#fafbff`、`#f0f2f5` → `var(--color-surface)`。

`ResultsPage.vue`、`PaperSourcesView.vue` 目前各自宣告一套局部 CSS 變數(`--page-bg`、`--card-bg`、`--line`、`--text-main`、`--text-secondary`),比照 `PaperPage.vue` 已套用的模式補齊 `--brand: var(--color-accent)`,並把 `--page-bg`/`--card-bg` 的值改為 `var(--color-primary)`/`var(--color-surface)`。兩檔外層 `background` 目前用純灰階漸層(`linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%)`),改用跟 `PaperPage.vue` 一致的做法疊加 accent 光暈:

```css
/* 改為(比照 PaperPage.vue 已套用的模式) */
background:
  radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
  radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
  var(--color-primary);
```

`ResultsPage.vue` 既有的 `rgba(99, 146, 238, 0.18)`/`rgba(88, 157, 255, 0.16)` 光暈(位置與 `PaperPage.vue` 相同,8%/12% 與 91%/89%)直接視為這個模式的舊版本,一併替換;`PaperSourcesView.vue` 目前沒有光暈只有純灰階漸層,補上相同的兩層光暈。

`.results-main`/`.sources-main` 內層背景(`linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%)`)簡化為 `var(--color-surface)`(單一白底,不強行套用 `PaperPage.vue` 的點狀網格紋理,因為原設計本來就沒有紋理,只是淺灰漸層)。

`IconNode.vue` 未使用 `PaperPage.vue` 的變數模式,不受此段落影響。

### 段落 D:ResultsPage.vue AI 洞察卡片漸層

```css
/* 現在 */
.insight-card {
  color: #f7f9ff;
  background: linear-gradient(102deg, #4f86f0 0%, #4554df 100%);
}
```

```css
/* 改為 */
.insight-card {
  color: var(--color-inverted);
  background: linear-gradient(102deg, var(--color-accent) 0%, color-mix(in oklab, var(--color-accent) 70%, var(--color-ink)) 100%);
}
```

理由:這個漸層是強調型 CTA 卡片(AI 生成的洞察摘要,視覺上要最顯眼),不是用來區分多種卡片類型的裝飾色盤,套用 accent 符合段落 A 的強調色邏輯。卡片內半透明白色圖示底(`rgba(255, 255, 255, 0.2)`)、文字透明度變體(`rgba(248, 251, 255, 0.93)`、`rgba(255, 255, 255, 0.28)`)維持不變,只換底色與主文字色。

### 段落 E:IconNode.vue 節點類型色盤(維持不動)

`IconNode.vue` 的 `.node-purple`(`linear-gradient(165deg, #005dff 0%, #4c8cff 100%)`)、`.node-yellow`(`#f0e274`/`#fdfdfd`)、`.node-pending`(`#ced3e9`)三種節點底色,以及對應的 `LABEL_ACCENTS`(`'node-pending': '#7c88a8'`、`'node-purple': '#005dff'`、`'node-yellow': '#c2a935'`)全部維持原樣。這組色碼的作用是讓使用者從畫布上一眼分辨節點種類(一般節點/待處理/特殊節點),屬於分類色盤而非品牌強調色——即使 `node-purple` 剛好重複使用了跟 CTA 相同的 `#005dff`,套用範圍仍限定在「這是一個節點類型代碼」的語境,不隨 CTA 一起改成 accent(避免把三種節點色盤裡的其中一色換掉,破壞辨識度的一致性)。

`.node-highlighted` 的高亮外框(`box-shadow: 0 0 0 4px var(--highlight-color, #005dff)`)語意不同——`--highlight-color` 是由父層動態傳入的「目前作用中步驟」提示,不是節點類型代碼,其預設回退值改為 `var(--color-accent)`(見段落 A)。

### 段落 F:狀態色色碼統一(不套用品牌色)

| 狀態 | 現在(兩個不同色碼) | 統一為 |
|---|---|---|
| 成功 | `#10b981`(`DataTablePanel.vue` 的 `.data-table-guide--ready`) / `#18a836`(`ResultsPage.vue` 的 `--good`) | `#16a34a`(延續前三批已定案值) |
| 錯誤 | `#ef4444`(多檔) / `#b91c1c`(`PaperSourcesView.vue`、`WorkflowOptionsPanel.vue`、`WorkflowFileUploadPanel.vue`、`WorkflowWorkspace.vue`) | `#ef4444`(延續前三批已定案值) |

## 驗證方式

- `npm run build` 確認無編譯錯誤
- 逐一開啟 `/workflow`、`/results?project=<id>`、`/paper/sources?project=<id>` 三個頁面,用 devtools 抽查幾個 CTA 按鈕與標題文字確認顏色正確解析為新 token
- 在 `/workflow` 頁面實際選取任一節點,展開下方抽屜,確認 `WorkflowOptionsPanel.vue` 與對應 `nodePanel/` 面板的按鈕、文字顏色正確
- 確認 `IconNode.vue` 三種節點類型色盤、裝飾性靛紫色塊、中性邊框、`ComputeCiPanel.vue` 警告色維持原樣未被誤改
- 確認 `ResultsPage.vue`/`PaperSourcesView.vue` 的頁面外層光暈與 `PaperPage.vue` 視覺一致(用同一組 `color-mix` 公式)
