# Journal Scoring 顏色收斂

日期：2026-08-16

## 背景

`JournalScoreDialog.vue` / `JournalScorePanel.vue` / `ScoreRing.vue` 這組期刊評分報告元件，目前有兩套顏色系統疊在一起，造成畫面雜、不協調：

1. **分數色**（`utils/scoreColor.ts`）：≥80 分綠色、其餘一律 `--color-warning`（金黃色）。因為分數多數落在 80 以下，金黃色會大量出現在 ScoreRing、進度條、分數數字上。
2. **期刊識別色**（`utils/journalTheme.ts`）：JAMIA / npj Digital Medicine / BMC MIDM 三個期刊各自借用一個 workflow 節點分類色（`--color-node-visualize` / `--color-node-model` / `--color-node-source`），套在分頁籤選中狀態、eyebrow 文字、section title、建議編號上。

這個借用是 2026-08-15 workflow 設計系統批次最後整體審查時記錄的已知問題（節點色跟期刊評分色相衝突），當時的決定是「另開任務」，這份 spec 就是那個任務。

另外三個獨立問題：
- 「評分失敗，僅顯示其餘期刊結果」警告用整塊 `--color-warning-bg` 黃底，太搶眼。
- 彈窗套 `.glass-panel`，但背後是深藍半透明遮罩，`backdrop-filter` 會把遮罩的深色一起模糊進來，讓白色看起來偏濁——跟 2026-08-15 workflow canvas 玻璃問題同一個成因。
- 「修改建議」每條都有一個很淡的邊框，幾乎看不出來，變成沒意義的裝飾。

## 設計

### 1. 分數色：統一成品牌藍，不分高低

`utils/scoreColor.ts` 的 `getScoreColor(score)` 不再按 80 分門檻回傳綠色/金黃色，固定回傳 `var(--color-accent)`。函式簽名維持吃 `score` 參數（呼叫端不用改），只是內部不再依分數分支——如果之後真的要恢復分級，改動只留在這一個檔案。

`SCORE_THRESHOLD` / `SCORE_COLOR_HIGH` / `SCORE_COLOR_LOW` 這三個 export 一併移除，改成單一 `SCORE_COLOR = 'var(--color-accent)'`。

受影響的呼叫端（不用改邏輯，顏色會自動跟著變）：
- `ScoreRing.vue` 的 `ringColor`
- `JournalScorePanel.vue` 的 `.score-panel-summary__row-score` 文字色、`.score-panel-summary__bar-fill` 底色
- `JournalScoreDialog.vue` 的 `.journal-score-criterion__bar-fill` 底色、`.journal-score-criterion__score` 文字色

### 2. 期刊識別色：整個拿掉

`utils/journalTheme.ts` 刪除（`getJournalAccent` 在拿掉後沒有其他呼叫端，全站搜尋確認過）。

`JournalScoreDialog.vue` 改動：
- 移除 `import { getJournalAccent } from '@/utils/journalTheme'`
- 移除 `activeAccent` computed
- 分頁籤選中狀態（`.journal-score-tab--active` 的 inline style）：從 `{ color: getJournalAccent(js.journal).text, borderBottomColor: getJournalAccent(js.journal).main }` 改成純 CSS class，`.journal-score-tab--active { color: var(--color-accent); border-bottom-color: var(--color-accent); }`（拿掉 inline style 綁定，因為現在是固定值不用算）
- `.journal-score-eyebrow`、兩個 `.journal-score-section-title`、`.journal-score-suggestion__index` 的 inline `:style="{ color: activeAccent.text }"` 全部拿掉，色值收進對應的 scoped CSS 規則裡，固定寫 `color: var(--color-accent)`

三個期刊分頁籤外觀完全平等，只有文字（期刊名稱）不同。

### 3. 彈窗底色：拿掉玻璃，改實色白

`.journal-score-card` 移除 `glass-panel` class，改成 scoped CSS 自己給底色/邊框/圓角/陰影：

```css
.journal-score-card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  /* 其餘 width/max-width/max-height/overflow/flex 維持原樣 */
}
```

跟 2026-08-15 workflow canvas 同一個判斷：backdrop-filter 疊在深色遮罩（`.journal-score-backdrop` 的 `rgba(18, 30, 58, 0.45)`）前面，模糊效果會把遮罩的深色一起帶進來，實色白底更乾淨、也不會有色偏。

### 4. 「評分失敗」警告：拿掉黃底

`.journal-score-warning` 移除 `background: var(--color-warning-bg)`、`border-radius`、`padding` 的區塊感，改成純文字＋icon：

```css
.journal-score-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 14px 24px 0;
  color: var(--color-warning-text);
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}
```

文字色維持 `--color-warning-text`（這是真的警告事件，語意保留），只是不再整塊上色。跟這次 workflow 那邊「必填」標籤拿掉紅底、只留紅字的處理方式一致。

### 5. 「修改建議」框框：拿掉，改間距

`.journal-score-suggestion` 移除 `border` 與大 `padding`，改成用 `gap` 做視覺分隔：

```css
.journal-score-suggestions {
  /* gap 從 10px 加大到 16px，扛起原本靠邊框分隔的視覺責任 */
  gap: 16px;
}

.journal-score-suggestion {
  display: flex;
  gap: 10px;
  /* 不再有 border / border-radius / padding */
}
```

跟上面「逐項評分準則」區塊排版風格一致（那區本來就沒有框，純靠間距分隔）。

### 6. 順手修正：兩處誤用 warning 色的裝飾

審查現有程式碼時發現的既有問題，跟本次「warning 色被挪用」主題相同，一併處理：

- `JournalScorePanel.vue` 的 `.score-panel-summary__title`（「評分摘要」標題文字）目前是 `color: var(--color-warning-text)`，這裡不是警告語意，改成 `var(--color-text)`。
- `JournalScorePanel.vue` 的 `.score-panel-empty__icon`（空狀態星星 icon 的底色）目前是 `background: var(--color-warning-bg)`，改成 `var(--color-surface-alt)`；icon 本身的 `color="var(--color-warning-text)"` 也一併改成 `var(--color-ink-soft)`。

## 範圍外

- `chartColors.ts` / 論文結構化圖表的顏色（bar chart / radar chart）不在這次範圍內，那是另一個獨立的顯示脈絡，使用者沒有提出要動。
- 分數門檻/評分邏輯本身（後端算分方式）不動，只動顏色呈現。

## 驗收

- `npm run build`（含 vue-tsc）過。
- 瀏覽器實際打開期刊評分報告，確認：分數相關顏色統一是品牌藍、三個期刊分頁籤外觀一致、彈窗底色是不透明白、失敗警告沒有黃底色塊、修改建議沒有邊框。
