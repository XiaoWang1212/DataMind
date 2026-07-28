# Data Table Panel 改動設計

日期：2026-07-09
範圍：`frontend/src/components/workflow/nodePanel/DataTablePanel.vue`、`frontend/src/composables/useDrawerDrag.ts`

## 背景

Data Table 節點面板目前有四個待改進的地方：

1. 面板內部標題「Data Table」跟外層 `WorkflowOptionsPanel.vue` 的 `panel-header`（`<h3>{{ selectedNode.data.label }}</h3>`）重複顯示了兩次。
2. 引導使用者選擇 Target 欄位的提示文字，目前獨立佔一整行、有色塊底框，希望搬到跟「已選檔案」同一行。
3. 引導使用者點擊 Role 欄下拉選單的動畫圈圈（tap-hint），目前只在使用者選定 Target 後才消失；希望改成使用者只要點開過 Role 下拉選單就消失，不必真的選定 Target。
4. Drawer 面板的展開三段式（peeked / collapsed / expanded）中，expanded 高度目前是視窗高度的 54vh，希望改成 90vh，開到接近整頁。

## 改動 1：移除重複標題

刪除 `DataTablePanel.vue` 中的 `.data-table-title`（"Data Table" 文字）區塊與對應 CSS class。外層 `panel-header` 已顯示節點名稱，不需要面板內部再顯示一次。

## 改動 2：引導提示文字搬到與檔名同一行

現況：

```
[Data Table 標題]                    [已選檔案：xxx]
────────────────────────────────
│ 請將要預測的欄位在下方「Role」欄選為 Target，再按右下角「繼續」。 │  ← 獨立一行，色塊底框
```

改為：

```
[引導文字（依 hasTarget 切換文案）]       [已選檔案：xxx]
```

- 顯示邏輯不變：只在 `props.loading`（等待使用者設定欄位）且已解析出欄位（`previewColumns.length > 0`）時，才顯示左側引導文字；沒有欄位或非 loading 狀態時，該行只顯示檔名。
- 文案切換邏輯不變：未選 Target 時顯示「請選擇 Target」提示；已選 Target 時顯示「已選定目標變數...」提示。只要沒選 Target 就會持續顯示提示（不會因為其他互動而提早消失）。
- 樣式從獨立色塊底框，改成一般行內文字（用文字顏色區分未選/已選兩種狀態，不用背景色塊）。

## 改動 3：Tap-hint 圈圈點開任一列 Role 選單即消失

新增一個布林狀態（例如 `roleSelectTouched`），初始為 `false`。

- 任一列的 Role `<select>` 取得 focus（點擊或鍵盤切換皆會觸發 focus）時，將其設為 `true`。
- Tap-hint 的顯示條件從 `props.loading && !hasTarget && index === 0` 改為 `props.loading && !roleSelectTouched && index === 0`。
- 不需要處理「重新上傳新檔案後重置」的情境，因為此面板不支援換檔案（同一個工作流程只會處理同一份已上傳的資料）。

## 改動 4：Drawer expanded 高度 54vh → 90vh

`useDrawerDrag.ts` 的 `getExpandedPx()`：

```ts
function getExpandedPx(): number {
  return Math.round(window.innerHeight * 0.9); // 原本 0.54
}
```

其餘拖曳、吸附、速度判斷邏輯不變。

## 驗證方式

- 手動在瀏覽器開啟 workflow 畫面、上傳 CSV，確認：
  - 面板只顯示一次「Data Table」/節點標題
  - 引導文字與「已選檔案」同一行，未選 Target 時文字持續顯示，選定後文案切換
  - 點開任一列 Role 下拉選單後，tap-hint 圈圈消失且不再出現
  - 拖曳/點擊 drawer handle 展開到第三段時，高度接近整頁（約 90vh）
