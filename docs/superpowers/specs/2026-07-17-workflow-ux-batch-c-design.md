# Workflow UX 批次 C 設計：自製下拉元件 + 結果面板重做

> 三塊相關的 workflow 面板改動，共用一個新的下拉元件。實作順序：**元件先行** → 換各處 select → 重做結果面板。
> 範圍限 workflow 面板（Settings / DataTable / Feature Importance / Feature Engineering）；Hub 設定頁不在此批。

## 整體

一個可重用的 `CustomSelect` 取代原生 `<select>`（Windows 上原生下拉很醜、且展開清單樣式改不動），先用在 workflow 的幾個面板；同時把 Feature Importance 與 Feature Engineering 兩個唯讀面板重做。

實作依賴：`CustomSelect`（無依賴）→ 換 Settings / DataTable 的 select（依賴 CustomSelect）→ Feature Importance 重做（依賴 CustomSelect）；Feature Engineering 面板重做（獨立、不用下拉）。

## 1. `CustomSelect` 元件

**檔案**：`frontend/src/components/common/CustomSelect.vue`（若無 `common/` 目錄則新建）

**用途**：取代原生 `<select>` 的單選下拉，外觀可控、跨平台一致。

**Props / Emits**
```ts
props: {
  modelValue: string                                    // v-model
  options: { value: string; label: string; disabled?: boolean }[]
  placeholder?: string                                  // 未選（modelValue 不在 options 內）時顯示，不可被選為值
  disabled?: boolean                                    // 整個控件停用
  highlight?: boolean                                   // 注意態邊框（DataTable Role 未選 target 用）
}
emits: {
  'update:modelValue': (value: string)
  'change': (value: string)                             // 選定後觸發（供 Role demote 等）
}
```

**結構與行為**
- **Trigger**：一顆按鈕，顯示目前選項的 `label`（找不到對應 option 時顯示 `placeholder`）＋ 右側 chevron（沿用專案現有的藍色 chevron SVG）。`disabled` 時樣式淡化、不可開。
- **浮層（popup）**：點 trigger 開啟，`<Teleport to="body">` 渲染一個 `listbox`，用 trigger 的 `getBoundingClientRect()` 以 `position: fixed` 定位在 trigger 正下方、寬度對齊 trigger。**必須 teleport**——Settings step-body 是捲動區、DataTable Role select 在有 `overflow` 的表格內，inline 浮層會被裁掉。清單過長時浮層內自己捲（`max-height` + `overflow-y:auto`）。
- **關閉**：點選項、點外部、按 Esc、trigger 捲出視窗；視窗 `scroll`（capture）/`resize` 時重新定位（trigger 離開視窗就關）。
- **鍵盤**：Trigger focus 時 Enter/Space/↓ 開啟；開啟後 ↑↓ 移動 highlight、Enter 選定、Esc 關、Tab 關。
- **Type-ahead**：清單開啟時打字累積到一個 buffer（約 500ms 無輸入就清空），highlight 跳到第一個 `label` 以 buffer 開頭（不分大小寫）的選項。
- **a11y**：trigger `role="combobox"` + `aria-haspopup="listbox"` + `aria-expanded` + `aria-activedescendant`（指向目前 highlight 選項的 id，虛擬焦點模式，焦點留在 trigger）；浮層 `role="listbox"`；每項 `role="option"` + `aria-selected` + 唯一 `id`；停用項 `aria-disabled`。
- **開啟中被 disable**：`disabled` 若在浮層開啟時翻成 `true`，watch 立即關閉浮層（避免卡在停用卻可互動的狀態）。
- **展開/收合動畫**：仿 jQuery `slideToggle` 的高度滑動——用 `<Transition :css="false">` 的 JS hook + Web Animations 滑動浮層高度（`0 ↔ min(內容高, 240)`）＋淡入淡出。開 ~100ms `ease-out`、關 ~90ms `ease-in`；快速連點以 `getAnimations().cancel()` 防打架；`prefers-reduced-motion` 直接跳過動畫。（高度不定，故用 JS 量測而非純 CSS transition。）
- **樣式**：對齊現有輸入元件（白底、`#005dff` 藍、圓角 8px、border `rgba(0,93,255,.18)`）；選定項與 hover 項高亮；`disabled` 選項不可點、淡化。chevron 展開時轉 180°。

## 2. 換掉 6 個原生 select

改用 `<CustomSelect>`，把原本 `<option>` 陣列改成 `options` 陣列（`{ value, label }`），原生 disabled 首項改成 `placeholder`。

- **SettingsPanel.vue**：
  - 前處理 add-bar type select（`newPreprocessType`，`placeholder="選擇步驟類型"`，options 來自 `PREPROCESS_LABELS`）。
  - 特徵工程 add-bar type select（`newFEType`，options 來自 `FEATURE_LABELS`）。
  - 模型 add-bar select（`selectedModel`，options 為可用模型；`placeholder` 依狀態顯示「載入中…／已全部加入／選擇模型」，`disabled` 綁 `modelOptionsLoading || availableModels.length === 0`）。
  - `fill_na` 的 strategy 參數 select（options 均值/中位數/眾數 → 值 mean/median/mode）。
- **DataTablePanel.vue**：
  - Type select（`column.type`，options 為 `typeOptions` + `typeLabels`）。
  - Role select（`column.role`，options 為 `roleOptions` + `roleLabels`）：
    - 保留外層 `.role-select-wrap` 與 tap-hint 漣漪提示（它定位在 wrapper，不受浮層 teleport 影響）。
    - 注意態邊框改用 `:highlight="props.loading && !hasTarget && !roleSelectTouched"`。
    - `@change="onRoleChange(index)"` 照舊（重選 target 時 demote 舊 target）。

## 3. Feature Importance 面板重做

**現況**：一次把**每個模型 × 每一折**全部傾印成巢狀卡片（10 折冗餘、難讀）；面板內還有一個跟 panel header 重複的 `<h4>Feature Importance</h4>`。

**改法**（`FeatureImportancePanel.vue`）：
- **移除**面板內重複的 `<h4>Feature Importance</h4>`（panel header 已有標題）。
- 頂部控制列**兩組並排**，每組是 `label ｜ CustomSelect` 的**行內橫向**排法（label 在下拉左邊，不是上下堆疊）：「模型 [下拉]」「fold [下拉]」，下拉固定寬 ~160px。用 `<div>` 包（不是 `<label>`——`<label>` 包自製 combobox 會讓點文字也觸發展開）。
  - 模型 options＝各 `model_name`；fold options＝**目前選定模型**的 `splits` 的 `split_name`。
  - 預設：第一個模型 + 它的第一個 fold。切換模型時 fold **一律**重置為該模型的第一個（`watch(currentModel)` 無條件設；因各模型 split 名稱相同，不能只在「舊 fold 不存在」時才重置）。
- 下方只顯示 **(選定模型, 選定 fold)** 那一組的 feature/importance 表，**沿用 Test & Score 的共用 result-table 樣式**（圓角外框卡片、`#f8fafc` 表頭、列間分隔線、Importance 欄 `tabular-nums` 右對齊、hover 高亮），維持結果面板視覺一致。
- 面板頂部不留多餘上方留白（`padding: 0`），下拉貼近上緣。
- **不做跨折平均**——逐折檢視（組員拍板）。
- 空狀態（無結果）：「尚未有特徵重要性結果，請執行 Workflow 後再查看。」；選定 fold 無資料時：「該抽樣沒有可用的特徵重要性資訊。」

## 4. Feature Engineering 面板重做

**現況**：唯讀面板把每個步驟 `JSON.stringify` 傾印，空曠難讀。

**改法**（`FeatureEngineeringPanel.vue`）：比照隔壁 **PreprocessorPanel** 的唯讀卡片樣式（同一套設計語言）：
- 頂部「共 N 個特徵工程步驟」。
- 卡片 grid（`repeat(auto-fill, minmax(180px, 1fr))`），每張卡：step index 圓圈 + 中文 label（用 `FEATURE_LABELS`：特徵選擇 / PCA 降維 / 連續→離散 …）+ 參數列 `key: val`。
- 參數標籤沿用**原始英文 key**（`k`、`n_components` …），跟 Preprocessor 面板與 Settings 的參數顯示一致。
- 空狀態：「尚未設定特徵工程步驟。」
- 移除 `formatStep` / `<pre>` JSON 傾印。

## 測試

無自動測試。`npm run dev` 手動驗：
1. CustomSelect：Settings 三個 type/模型下拉、strategy、DataTable Type/Role 都能展開/選取；浮層**不被面板捲動區或表格裁掉**；鍵盤 ↑↓/Enter/Esc、打字 type-ahead 可用；disabled/placeholder 正確。
2. DataTable Role：未選 target 的注意態邊框 + tap-hint 漣漪還在；重選 target 仍會 demote 舊 target。
3. Feature Importance：兩顆下拉並排；選模型→fold→只顯示那折的表；換模型 fold 重置；面板內不再有重複標題。
4. Feature Engineering：卡片式顯示（label + 參數），不再是 JSON。

收尾：`npm run build`（vue-tsc）。`npm run lint` 為既有壞基線，本批照現有檔案風格撰寫、不引入新種類問題。
