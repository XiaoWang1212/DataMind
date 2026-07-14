# Test & Score 與 Feature Importance 表格樣式統一 設計

日期：2026-07-14
範圍：`frontend/src/components/workflow/nodePanel/TestScorePanel.vue`、`frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue`

要解決的問題：**兩個結果表格長得不一樣**。使用者希望節點 panel 的表格看起來像同一套設計。

## 背景

畫布上的 panel 目前有**四套各自為政的表格實作**：

| Panel | 實作 | 長相 |
|---|---|---|
| `TestScorePanel` | div grid | 20px 圓角、藍色 header `#e7f0ff`、全部置中、斑馬紋、13px |
| `FeatureImportancePanel` | div grid + 外層卡片 | 18px 圓角卡、灰 header `#f8fafc`、無列分隔線、無斑馬紋 |
| `ComputeCiPanel` | div grid | 6px 圓角、11px 小字、緊湊 padding（4px/8px）、斑馬紋 |
| `DataTablePanel` | 真 `<table>` | sticky thead、border-bottom 分隔線、格內有 input/select |

Preprocessor / Settings 則不是表格，是卡片式 item-list（key/value chips），屬另一種元件語言。

**這次只處理 Test & Score 與 Feature Importance 兩個**：它們是使用者最常對照著看的一組（同一批執行結果的兩個切面），差異也最刺眼。ComputeCi 的表格要 Settings 開啟 Compute CI、且執行結果裡真的有 `ci_lower`/`ci_upper` 才會出現（`ComputeCiPanel.vue:118-157` 的 `ciGroups`），平常畫面上看到的是靜態介紹文，先不動。

### 為什麼不抽共用樣式

原始問題記錄裡的建議是抽一套共用的表格樣式（`.wf-table` 之類）給所有 panel 共用。**這次刻意不那樣做**：使用者預期這兩個表格之後會分開演化（各自長出不同的欄位、互動），提早抽共用層會讓之後的分歧變成「要不要破壞共用元件」的兩難。

代價講明：**兩份樣式各寫各的**，日後改配色要改兩處，也有再度分歧的風險。這是拿「維護成本」換「各自演化的彈性」，是使用者明確要的取捨。真的要收斂時（例如把 ComputeCi、Data Table 一起收進來），再從兩份長得一樣的 CSS 抽共用層，成本不會比現在高。

## 目標樣式

兩個表格都改成同一套視覺語言（下稱「資料表風」），刻意往 `DataTablePanel` 的方向靠——它是使用者停留最久的表格，讓結果表格跟它同語言，整體才算收斂：

- 白底 + 1px 淺灰外框 `rgba(148, 163, 184, 0.22)` + 12px 圓角
- Header 列灰底 `#f8fafc`、12px、`#475569`、`font-weight: 600`
- 列與列之間 1px 分隔線 `rgba(148, 163, 184, 0.16)`；**不用斑馬紋**
- 非 header 列 hover 淡藍底 `rgba(0, 93, 255, 0.035)`
- 左欄（Metric / Feature）文字左對齊、加粗 `#1e293b`
- 數字欄右對齊 + `font-variant-numeric: tabular-nums`（多個模型的分數逐位對齊，比置中好比較）
- 儲存格 padding `11px 14px`、13px

## 改動 1：`TestScorePanel.vue`

表格是 metric（列）× model（欄）的矩陣，`grid-template-columns: 160px repeat(auto-fit, minmax(120px, 1fr))` 不變。

**Template**：數值格加上 `table-cell--num`，讓數字右對齊：

```diff
       <div class="table-row" v-for="row in matrixRows" :key="row.metric">
         <div class="table-cell table-cell--metric">{{ row.metric }}</div>
         <div
           v-for="(value, index) in row.values"
           :key="`${row.metric}-${modelNames[index]}`"
-          class="table-cell"
+          class="table-cell table-cell--num"
         >
           {{ value }}
         </div>
       </div>
```

Header 的 Metric 那格不動；`table-cell--model`（模型名 + split 名的兩行堆疊）不動 class，只改樣式。

**Style**（scoped）：

```diff
   .summary-table {
     display: flex;
     flex-direction: column;
-    border-radius: 20px;
+    border: 1px solid rgba(148, 163, 184, 0.22);
+    border-radius: 12px;
     overflow: hidden;
     background: #ffffff;
   }

   .table-row {
     display: grid;
     grid-template-columns: 160px repeat(auto-fit, minmax(120px, 1fr));
     gap: 0;
     align-items: center;
   }

-  .table-row:not(.table-row--header) {
-    background: #ffffff;
-  }
-
-  .table-row:nth-child(even):not(.table-row--header) {
-    background: #f8fafc;
-  }
+  .table-row:not(:last-child) {
+    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
+  }
+
+  .table-row:not(.table-row--header):hover {
+    background: rgba(0, 93, 255, 0.035);
+  }

   .table-row--header {
-    font-weight: 700;
-    color: #0f172a;
-    background: #e7f0ff;
+    font-weight: 600;
+    font-size: 12px;
+    color: #475569;
+    background: #f8fafc;
   }

   .table-cell {
-    padding: 14px 16px;
+    padding: 11px 14px;
     color: #0f172a;
     font-size: 13px;
     min-width: 0;
     word-break: break-word;
     background: transparent;
-    text-align: center;
+    text-align: left;
   }

-  .table-row:last-child .table-cell {
-    border-bottom: none;
-  }
-
   .table-cell--metric {
-    background: rgba(226, 232, 240, 0.25);
-    font-weight: 700;
-    color: #0f172a;
+    font-weight: 600;
+    color: #1e293b;
   }
+
+  .table-cell--num {
+    text-align: right;
+    font-variant-numeric: tabular-nums;
+  }

   .table-cell--model {
     display: flex;
     flex-direction: column;
     gap: 3px;
+    align-items: flex-end;
     background: transparent;
   }

   .model-name {
     font-weight: 700;
     color: #1f2937;
-    font-size: 13px;
+    font-size: 12px;
   }

   .model-split {
-    font-size: 12px;
-    color: #475569;
+    font-size: 11px;
+    color: #94a3b8;
+    font-weight: 400;
   }
```

**幾個決定**：

- **斑馬紋整個拿掉、換成 hover**。斑馬紋是在沒有分隔線時幫助橫向掃視的手段；有了列分隔線就是重複的視覺噪音。而且原本的 `nth-child(even)` 規則依賴 header 是第一個子元素，脆弱。
- **`.table-cell--metric` 的淺灰底拿掉**。左欄靠字重（600 + `#1e293b`）就足以跟數字區分，多一塊底色會讓表格看起來被切成兩半。
- **`.table-row:last-child .table-cell { border-bottom: none }` 刪掉**：cell 本來就沒有 `border-bottom`，這是條沒有作用的死規則。分隔線改掛在 row 上，`:not(:last-child)` 自然處理最後一列。
- **model 表頭改右對齊**：模型名/split 名要跟它底下那一整欄的數字對齊，不然數字靠右、標題靠左會看起來錯開。

## 改動 2：`FeatureImportancePanel.vue`

結構是「模型卡片 → 每個 split → 一張兩欄表（Feature / Importance）」。卡片與表格的巢狀結構不動，`grid-template-columns: 1fr 120px` 不變。

**Template**：不動。現有的 class（`importance-cell--feature` / `importance-cell--value`）已經夠掛樣式。

**Style**（scoped）：

```diff
+  .importance-list {
+    display: flex;
+    flex-direction: column;
+    gap: 14px;
+  }
+
   .importance-card {
-    border-radius: 18px;
+    border-radius: 12px;
     overflow: hidden;
     background: #ffffff;
     border: 1px solid rgba(148, 163, 184, 0.16);
   }

   .importance-card__header {
     padding: 14px 16px;
     background: #f8fafc;
+    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
     display: flex;
     justify-content: space-between;
     gap: 16px;
     flex-wrap: wrap;
   }
+
+  .importance-split-list {
+    display: flex;
+    flex-direction: column;
+    gap: 14px;
+    padding: 14px 16px;
+  }
+
+  .importance-split {
+    display: flex;
+    flex-direction: column;
+    gap: 6px;
+  }
+
+  .importance-split__title {
+    font-size: 12px;
+    color: #94a3b8;
+  }

   .importance-table {
     display: flex;
     flex-direction: column;
+    border: 1px solid rgba(148, 163, 184, 0.22);
+    border-radius: 12px;
+    overflow: hidden;
   }

   .importance-row {
     display: grid;
     grid-template-columns: 1fr 120px;
     gap: 0;
     align-items: center;
-    padding: 12px 16px;
   }
+
+  .importance-row:not(:last-child) {
+    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
+  }
+
+  .importance-row:not(.importance-row--header):hover {
+    background: rgba(0, 93, 255, 0.035);
+  }

   .importance-row--header {
-    font-weight: 700;
-    background: #f1f5f9;
-    color: #0f172a;
+    font-weight: 600;
+    font-size: 12px;
+    background: #f8fafc;
+    color: #475569;
   }

   .importance-cell {
+    padding: 11px 14px;
     color: #0f172a;
     font-size: 13px;
     word-break: break-word;
   }

   .importance-cell--feature {
-    color: #1f2937;
+    font-weight: 600;
+    color: #1e293b;
   }

   .importance-cell--value {
     text-align: right;
+    font-variant-numeric: tabular-nums;
   }
```

**幾個決定**：

- **padding 從 row 移到 cell**。原本 `padding` 掛在 `.importance-row` 上，加了外框後底色/hover 會在 padding 之外露出一圈白邊；掛在 cell 上，整列的底色才會鋪滿。
- **`.importance-list` 是新規則**：包住多張模型卡片的容器目前在 CSS 裡沒有任何對應規則，所以模型超過一個時卡片會直接黏在一起（`.feature-importance-panel` 的 `gap: 16px` 只作用在它的直接子元素上，管不到 `.importance-list` 內部）。補上 `flex` + `gap`。
- **`.importance-split-list` / `.importance-split` / `.importance-split__title` 是新規則**——這三個 class 目前在 template 裡有、CSS 裡完全沒有對應規則（split 名稱現在是無樣式的預設文字）。表格加了外框後必須有 padding 把它跟卡片邊緣隔開，順手把 split 標題也降成 12px 灰字，讓它讀起來像表格的標籤而不是另一個標題。
- **卡片 header 補一條底線**：卡片 header 與表格 header 現在都是 `#f8fafc`，中間隔著 split 標題；補一條 `border-bottom` 讓「卡片標頭」與「內容區」的界線明確，不會看成兩條連在一起的灰帶。
- **表格 header 的 `#f1f5f9` 統一成 `#f8fafc`**：跟 Test & Score 用同一個灰。

## 不做的事

- 不動 `ComputeCiPanel`、`DataTablePanel`、`PreprocessorPanel`、`SettingsPanel`、`FeatureEngineeringPanel`。
- 不抽共用 CSS／共用元件（理由見上）。
- 不改任何 `<script>`、不改文案、不改 i18n、不改資料計算。兩個檔案的改動限於 `<template>` 的 class 與 `<style scoped>`。

## 驗收

這兩個 panel 都要有 `workflowResult` 才會顯示表格（沒有時各自顯示「尚未有…結果」的空狀態）。`workflowResult` 會存進 localStorage（`WorkflowWorkspace.vue:489` 還原），所以**用一個已經跑完 workflow 的既有專案**即可，不必重跑。若手上沒有，就上傳 CSV、在 Settings 加 2 個以上模型跑完一次。

`npm run dev` 後：

1. **Test & Score**：header 是灰底、不是藍底；沒有斑馬紋；每一列之間有細分隔線；分數靠右且逐位對齊（`0.8421` 和 `0.9013` 的小數點在同一條垂直線上）；滑鼠移到某一列，整列（含左欄）淡藍高亮。
2. **Feature Importance**：每張模型卡片內，表格有自己的外框與 12px 圓角、跟卡片邊緣有間距；列之間有分隔線；hover 會高亮；Feature 名稱比 Importance 數值粗；數值靠右對齊。
3. **兩者並排看像同一套設計**：切換這兩個節點，外框粗細/圓角、header 灰、字級、列高應該一致。
4. **模型多時不爆版**：跑 4 個以上模型 → Test & Score 表頭的模型名與 split 名（兩行堆疊）不溢出格子、不把欄寬撐爆；長模型名（如 `RandomForestClassifier`）會換行而不是撐開表格。
5. **空狀態沒壞**：開一個沒跑過的新專案 → 兩個 panel 各自顯示「尚未有測試評分結果…」「尚未有特徵重要性結果…」，沒有殘留的空表格外框。
6. `npm run build` 通過。（`npm run lint` 在本專案 baseline 就是紅的，不能當閘門；只需確認這兩個檔案沒有新增 lint 錯誤。）
