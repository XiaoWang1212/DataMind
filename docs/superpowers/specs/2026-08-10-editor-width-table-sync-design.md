# 論文編輯區寬度與檢視模式對齊、表格欄寬自動校正 Design

## 背景與根本原因

論文頁面（`PaperPage.vue`）有兩個渲染情境，寬度從來沒有互相對齊過：

- **檢視模式**：A4 頁面是照真實紙張比例寫死的，內容區固定 600px（794px 頁寬 − 96px×2 邊界），不管旁邊有沒有評分面板、`.paper-body` 多寬都不會變。
- **編輯模式**：`.paper-sheet` 目前是 `flex: 1`，寬度跟著 `.paper-body` 這條 flex row 的其餘成員（評分面板 `.paper-citations` 寬度、`.paper-body` 本身的 `max-width`）伸縮，且這個寬度歷史上已經變動過好幾次（例如 `.paper-body` 的 `max-width` 從 1064px 調成 1100px 時，編輯區寬度就從 760px 變成 796px）。

Tiptap 表格的欄寬（`colwidth`）是「量測當下實際渲染寬度」凍結成固定像素值後存進文件內容的（`columnResizeBalance.ts` 的 `seedMissingColumnWidths`），凍結之後不會跟著容器寬度重新計算。由於編輯模式的寬度本身就不穩定、又跟檢視模式的固定 600px 從未對齊過，同一張表格的欄寬總和在「建立當下的編輯區寬度」「之後某次改版的編輯區寬度」「檢視模式固定的 600px」這三者之間可能互不相同——而 `table-layout: fixed` 的表格在欄寬總和小於容器寬度時不會自動撐滿，於是就會出現表格比周圍文字窄一截、右側留白的狀況。

## 目標

1. 讓編輯模式的內容寬度固定等於檢視模式 A4 頁面的內容區寬度（600px），兩邊只有一個大家都認的寬度基準，編輯時看到的排版就是最終檢視/列印出來的樣子（WYSIWYG）。
2. 表格欄寬機制能偵測「目前欄寬總和跟容器實際可用寬度對不上」，自動按原本的相對比例重新縮放去對齊——不管是舊表格因為以前的編輯區寬度不同而不對齊，還是以後版面又改變寬度，都能自動校正，不用手動處理。

## 範圍

- 只動 `PaperPage.vue` 的編輯模式版面 CSS，與 `columnResizeBalance.ts` 的表格欄寬邏輯。
- 不改檢視模式（`PaginatedPaperView.vue`）本身的量測/分頁邏輯——A4 頁面內容區本來就已經是固定 600px，不需要改。
- 不改變表格欄寬「相對比例」在重新縮放時的意義：不管當初是自動平分還是使用者手動拖過的比例，重新縮放時一律維持相對比例不變，只是整張表跟著變寬/變窄。

## 設計一：編輯區固定寬度

`PaperPage.vue` 的 `.paper-sheet`（編輯模式，非 `--paginated` 那個變體）目前：

```css
.paper-sheet {
  flex: 1;
  min-width: 0;
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 28px 34px;
  height: fit-content;
}
```

改成新增一個 `.paper-sheet--editing` 修飾類別（模板上 `<article v-else class="paper-sheet">` 改成 `<article v-else class="paper-sheet paper-sheet--editing">`，比照 `.paper-sheet--paginated` 的既有寫法）：

```css
.paper-sheet--editing {
  flex: none;
  width: 670px;
}
```

`.paper-sheet` 本身的 `padding: 28px 34px`、`border: 1px solid` 不變，`box-sizing: border-box` 下內容區寬度是 `670 − 1×2(border) − 34×2(padding) = 600px`；A4 頁面內容區同理是 `794 − 1×2(border) − 96×2(padding) = 600px`，兩邊剛好都是 600px，跟 A4 頁面內容區一致（實測值見 Task 1 review：600.73px / 600.74px，落差在 subpixel 誤差內）。`PaperEditor.vue` 內部不需要改動——`.editor-content` 本來就沒有自己的寬度限制，會直接填滿父層（`.paper-sheet`）的內容區寬度。

卡片靠左排（跟現在同一邊界，不置中），右側會多出空間。`.paper-citations` 加上 `margin-left: auto`：

```css
.paper-citations {
  width: 280px;
  flex-shrink: 0;
  margin-left: auto;
  /* 其餘現有屬性不變 */
}
```

這樣評分面板永遠貼齊 `.paper-body` 最右緣，不管左邊的卡片（編輯模式固定 670px，檢視模式 `flex: 1` 伸縮）實際多寬，編輯模式與檢視模式下評分面板的位置就會一致，不用分別調整。

## 設計二：表格欄寬自動校正

`columnResizeBalance.ts` 現有的 `Plugin.view()` 更新監聽（`seedMissingColumnWidths` 執行的同一個地方）新增一段邏輯，在每次 view 更新時，對每一張**已經有 `colwidth` 的表格**（跟 `seedMissingColumnWidths` 處理「完全沒有 `colwidth`」的情況互補、不重疊）：

1. 找到表格的 `.tableWrapper` 外層 DOM 節點，量測它的實際渲染寬度（`getBoundingClientRect().width`）——`.tableWrapper` 是一般的 block 層級 `<div>`，沒有被表格內部的 `table-layout: fixed` 限制，會忠實反映「容器實際可用寬度」，不受表格自己目前欄寬總和影響。
2. 算出目前所有欄的 `colwidth` 總和。
3. 兩者相差超過 2px（容忍浮點數/瀏覽器 subpixel 誤差，避免每次量測都因為 0.x px 的差異反覆觸發重新縮放、造成無限循環）時：對每一欄套用同一個縮放比例 `scale = 實際可用寬度 / 目前欄寬總和`，新欄寬 `= 原欄寬 × scale`（四捨五入到整數 px），維持每一欄原本的相對比例不變，一次性 dispatch 一個 transaction 更新所有欄的 `colwidth`。

這段邏輯只在「表格容器的實際寬度」跟「表格自己欄寬總和」對不上時觸發，跟現有的「拖曳欄界」邏輯（`appendTransaction`，拖曳時只調整被拖曳欄與緊鄰欄，欄寬總和刻意維持不變）天然不會互相干擾——拖曳過程中容器寬度沒有變、欄寬總和也沒有變，不會觸發這段新邏輯；只有在容器寬度真的變了（例如今天的 670px 改版、或以後版面再次調整）時才會觸發重新縮放。

設計一上線後，任何在此之前建立、欄寬是照舊的編輯區寬度凍結的表格，只要重新打開編輯模式（觸發一次 view 更新），就會被這段邏輯自動偵測到寬度對不上並校正成新的 600px 基準，不需要額外的資料遷移步驟。

### 例外一：使用者手動調整過的表格（`manuallyResized`）

實作過程中發現：拖曳表格「最後一欄」的右邊界（沒有鄰欄可以補償差值）是使用者刻意改變表格總寬度的唯一手段。若不分青紅皂白地把「總寬對不上容器」都當成需要自動校正，會把這種刻意調整也拉回去貼齊容器，等於使用者拖了也沒用。

因此上面設計二的自動校正只套用在「從頭到尾沒被使用者動過總寬度」的表格。一旦偵測到表格總寬度真的變了（且不是合併/分割儲存格這類結構性變動造成的，也不是內部拖曳補償撞到最小欄寬 40px 下限造成的），就在 Table 節點記一個 `manuallyResized: true`，之後永久跳過自動校正——比照 Word/Excel「調過的表格維持調過的大小」。

但這個例外不是無條件的：使用者調出來的寬度如果超過容器（A4 頁面可印刷範圍，600px），仍會被夾回容器寬度上限（維持調整後的相對比例），避免使用者拖出一張比頁面還寬的表格、列印時被裁掉又無法恢復；調得比容器窄則完全尊重，不會被拉回去填滿。

已知限制：row 0 含合併儲存格（`colspan > 1`）的表格會整張跳出自動校正機制（不參與貼齊、也不受 `manuallyResized` 影響）——這類表格在合併當下本來就是對齊容器的，維持原狀即可；如果日後容器寬度又改變，這類表格不會自動貼齊，需要使用者手動調整。

## 測試

- 手動瀏覽器驗證（本專案沒有自動化測試框架）：
  1. 進入編輯模式，確認 `.paper-sheet` 的內容區寬度精確等於檢視模式 A4 頁面內容區的 600px（DOM 量測比對）。
  2. 評分面板在編輯模式與檢視模式下都貼齊 `.paper-body` 最右緣。
  3. 建立一張新表格，確認欄寬平分填滿 600px 內容區。
  4. 手動拖曳調整某張表格的欄寬比例（例如調成不平均的比例），確認比例被保留；模擬「舊表格欄寬跟新容器寬度對不上」的情境（可用瀏覽器 devtools 直接修改某張表格的 `colwidth` 屬性製造落差），重新整理頁面進入編輯模式，確認欄寬被自動按比例縮放到跟 600px 對齊，且比例跟修改前一致。
  5. 拖曳調整欄界時，確認欄寬總和維持不變（不會被新的自動校正邏輯誤觸發、意外改變總寬度）。
