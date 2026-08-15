# Workflow 頁面套用設計系統（Batch 3）設計文件

## 背景

`docs/DESIGN_SYSTEM.md` 的改版已完成側邊欄（Batch 1）與 Hub 頁面（Batch 2），`workflow/` 相關的 15 個檔案（`components/workflow/` 14 個 + `views/WorkflowPage.vue`）從頭到尾沒有套用過設計系統，累積了大量殘留樣式：硬寫 hex 色值、原生 `<button>`、超出規範的字重/圓角/動畫時長。

更關鍵的問題在節點配色：`docs/DESIGN_SYSTEM.md` §2.3 定義的五個節點分類色 token（`--color-node-source/inspect/transform/model/evaluate`）從未被實際使用；畫布上真正在跑的是 `IconNode.vue` 裡一套跟分類無關的舊機制——`colorClass` 只有三個值（`node-pending`/`node-purple`/`node-yellow`），而且 `node-yellow` 實際代表的是「執行完成」，不是分類。也就是說現在的顏色把「這是什麼類型的節點」和「這個節點跑到哪一步」兩種語意混在同一個欄位裡。

`components/WorkflowBuilder.vue`（669 行）經確認沒有任何地方 import，是死代碼，內含一整套跟目前實際渲染節點不同的舊節點定義（Intent & Target、Predictions 等）。**本次範圍不動它**，維持現狀。

## 目標

1. 把「節點分類」和「執行狀態」拆成兩個獨立欄位，分類決定底色、狀態決定右下角徽章
2. 節點分類改用 Orange Data Mining 的五類分法（Data / Transform / Visualize / Model / Evaluate），色票另外設計（不直接沿用 Orange 原色，見下）
3. 清理 15 個檔案裡違反設計系統規範的殘留樣式：硬寫 hex、原生 button、字重、圓角、動畫時長

## 節點分類色

### 為什麼不能直接照 Orange 的顏色

Orange 六類色系（黃橘=Data、綠=Model、紅粉=Evaluate…）中有三類正面撞上本專案既有的狀態色語意（success 綠、warning 琥珀、error 紅，§2.2）。同色系會讓「這是 Model 節點」跟「這個節點跑完了」在色相上分不出來——這不是美感問題，是色相距離的客觀衝突，經算圖驗證：直接沿用 Orange 色相時，Data 對 warning 只差 3°、Evaluate 對 error 只差 10°、Model 對 success 只差 21°，全部落在容易混淆的範圍內。

### 配色方法

節點構造採 Orange 原本的做法——**淺底 + 深色 icon**（`--color-ink-strong`），而非目前 `IconNode.vue` 的飽和底 + 白色 icon。這個構造下，「五色之間要和諧」不是靠固定色相間距，而是靠 OKLCH 色彩空間裡明度（L）與彩度（C）維持一致：色相可以自由選，只要每個顏色的「感知重量」相同，整組看起來就不會有誰特別跳出來搶戲。

經過與使用者來回試色（依序嘗試冷色安全區、Orange 直接飽和度版、彩虹漸層版，最終定案於低飽和大地色系），確認以下最終色票：

| 分類 | 色值 | OKLCH | 對應節點 |
|---|---|---|---|
| Data | `#CFA3B6` | H=350° L=0.76 C=0.058 | File、Data Table |
| Transform | `#D2A596` | H=40° L=0.76 C=0.058 | Preprocessor、Feature Engineering |
| Visualize | `#CEC068` | H=100° L=0.80 C=0.11（手動微調，見下） | Distribution |
| Model | `#85BDBC` | H=195° L=0.76 C=0.058 | Settings、Models |
| Evaluate | `#A9AED6` | H=280° L=0.76 C=0.058 | Test & Score、Feature Importance、Confusion Matrix、Compute CI |

**Visualize 是手動調整過的例外**，不與其他四色共用 L/C：黃綠色相（100°附近）在同樣的低彩度下比其他色相更容易讀成「濁」，所以彩度單獨拉高到 0.11 才不顯髒；明度只能到 0.80，不能再往上調——會跟畫布底色太接近而消失，這正是原始參考色票（低飽和大地色系）踩到的同一個陷阱。

**分類跟舊分法的差異**：Data Table 原本歸在（已廢棄的）inspect 類，現在併入 Data（跟 File 同類，比照 Orange 的分法）；Distribution 獨立成 Visualize 一類。

### 邊框：所有分類色統一加

淺色底在本專案偏冷灰藍的畫布底色（`--color-page` `#E4E9ED`）上普遍存在對比不足的問題——量出來大多落在 1.4～1.8 之間（1.0 代表完全無法區分）。所有分類色統一加一圈 `1.5px solid rgba(18, 36, 74, 0.16)` 邊框，這是不管色票怎麼調都通用的保險，不必為了拉開對比而犧牲色彩本身的淡雅調性。

### 完成徽章

執行狀態不再改變節點底色（`useWorkflowNodes.ts:67` 目前 `finished` 會把 `colorClass` 換成 `node-yellow`，這行要移除）。完成狀態改成節點右下角一個重疊的圓形徽章：`--color-success` 底、白色勾勾（`mdi-check`），外圈套一圈畫布底色的描邊把它跟節點分開。進行中維持現有的 spinner（節點中央 icon 換成旋轉動畫），不受這次調整影響。

## 資料結構變更

`types/workflow.ts` 的 `NodeData`：

```ts
export type NodeCategory = 'source' | 'transform' | 'visualize' | 'model' | 'evaluate'

export interface NodeData {
  category: NodeCategory   // 取代 colorClass，決定底色，不隨執行變化
  status?: 'running' | 'finished' | null   // 不變，決定 spinner / 完成徽章
  // …其餘欄位不變
}
```

> 分類命名沿用內部既有的 `source`（非 Orange 的 `data`），因為第一顆節點是「資料來源」而不是「資料本身」，跟 §2.3 原文一致；模板顯示文字用 `Data` 等 Orange 慣用講法，不影響 code 內部命名。

**為什麼是新增欄位而不是從 label 推導**：模型節點的 label 直接來自後端（`m.name`，論文寫什麼就是什麼），是任意字串，無法用字串比對推分類。而且既有 label 本身就不一致（`"Data\nTable"` vs `'Data Table'`），不能作為穩定的分類依據。

需要更新的節點建立點（分類依上表映射）：

- `constants/workflowData.ts` — demo 節點的固定分類
- `composables/workflow/useWorkflowNodes.ts` — 動態產生的 Preprocessor / Feature Engineering / Compute CI 節點；同時移除 `colorClass: status === 'finished' ? 'node-yellow' : …` 這行
- `composables/workflow/useWorkflowImport.ts` — 從 Gemini 解析結果建立的 Preprocessor / Feature Engineering / 模型節點

`vuetify.ts` 的 `--color-node-*` token 需要跟分類欄位對齊，除了改色值，`node-inspect` 這個 key 已無對應分類（Data Table 併入 Data、Distribution 獨立成 Visualize），改名為 `node-visualize`；`node-source` 沿用既有 key 名但改用上表 Data 分類的新色值：

```
node-source     #CFA3B6   (Data)
node-transform  #D2A596   (Transform)
node-visualize  #CEC068   (Visualize，取代舊的 node-inspect)
node-model      #85BDBC   (Model)
node-evaluate   #A9AED6   (Evaluate)
```

`IconNode.vue` 渲染調整：

- 底色改用 `.node-source` / `.node-transform` / `.node-visualize` / `.node-model` / `.node-evaluate` 五個 class，直接吃上面對應的 token；舊的 `.node-pending`、`.node-purple`、`.node-yellow` 三個 class 整段刪除（不再是任何節點會用到的 class，因為底色不再隨執行狀態切換）
- `LABEL_ACCENTS` 這個 JS hex 對照表整段刪除——選中底線的顏色改用 CSS 繼承同一個分類色變數，不需要 JS 再算一次
- icon 顏色從白色改為 `var(--color-ink-strong)`
- 新增右下角完成徽章
- `flash-add` / `flash-remove` 的 `#06b6d4` / `#ef4444` 改用狀態色 `--color-success` / `--color-error`（新增/移除是真的狀態變化，用狀態色語意正確）

## 樣式清理範圍

以下四類問題掃描 15 個檔案（`components/workflow/*.vue`、`components/workflow/nodePanel/*.vue`、`views/WorkflowPage.vue`）得出，逐一列出範圍與處理方式：

### 1. 原生 `<button>` → `AppButton`（15 處）

已存在 `components/ui/AppButton.vue`（`variant: primary/secondary/ghost/danger`、`iconOnly`、`loading`、`disabled`），全站其他已改版頁面用它。以下 15 處換成 `AppButton`：

- `UploadDialog.vue`：關閉（iconOnly ghost）、取消（secondary）、上傳（primary）
- `WorkflowWorkspace.vue`：查看結果（primary）
- `WorkflowOptionsPanel.vue`：新增模型（primary）
- `DistributionPanel.vue`：更多/收起 toggle（ghost）
- `DataTablePanel.vue`：Reset（secondary）、Apply（primary）
- `WorkflowFileUploadPanel.vue`：瀏覽檔案（secondary）
- `SettingsPanel.vue`：新增前處理/新增特徵工程/新增模型 3 處（secondary）、移除 3 處（iconOnly ghost/danger）、回 Data Table（secondary）、上一步（secondary）、主要動作按鈕（primary）

**明確排除**：`SettingsPanel.vue` 的 `wizard-tab`（步驟頁籤，導覽語意）與 `ci-toggle`（開關語意）不是按鈕，維持原樣，不套用 `AppButton`。

### 2. `font-weight: 600/700` → `500`（42 處）

§3 只允許 400/500 兩種字重，13 個檔案共 42 處直接改成 500，沒有例外或模糊地帶。

### 3. 硬寫圓角 → `var(--radius-*)`（69 處）

- 20 處 `999px`（pill）：本來就對，只需確認語意上是膠囊按鈕/徽章/輸入框
- 28 處數值本身合規（8/12/16px）：補上對應的 `var(--radius-sm/md/lg)`
- 21 處規範外數值，改成最接近的合法值：
  - `18px → 16px`、`20px → 16px`（明確更接近 lg）
  - `10px`：卡片/容器類（`WorkflowCanvas .flow-area`、`SettingsPanel .ci-card`、兩處 `.upload-modal-preview-table`）→ `12px`；輸入類（`FeatureEngineeringPanel`/`PreprocessorPanel` 選項列）→ `8px`；按鈕上的 2 處（`WorkflowOptionsPanel .btn`、`SettingsPanel .btn-continue/.btn-back`）隨第 1 類按鈕遷移直接消失，不需另外處理
  - `14px`：2 處皆為表格容器（`.upload-modal-preview-table`）→ `12px`
  - `6px → 8px`（無比 8px 更小的 token）
  - `3px`、`2px`：維持不變，屬於圖表刻度線等極小視覺細節，不在圓角規範管轄範圍內

### 4. 硬寫動畫時長 → `var(--dur-*)`（32 處互動 transition）

只處理互動用途的 `transition`，不動 keyframe `animation`（spinner 轉 0.75s、pulse 閃 1.4s、flash 1.2s 等效果型動畫本身就該有自己的物理時長，硬套三檔 token 會破壞效果，維持原樣）：

| 現值 | 次數 | 映射 |
|---|---|---|
| `0.12s` | 5 | `--dur-fast`（120ms，精確符合） |
| `0.15s` | 17 | `--dur-fast`（較接近） |
| `0.2s` | 4 | `--dur-base`（200ms，精確符合） |
| `180ms` | 2 | `--dur-base`（較接近） |
| `0.22s` | 2 | `--dur-base`（較接近） |
| `260ms` | 1 | `--dur-slow`（跟 base/slow 等距，因為是面板 `height` 展開、動作幅度較大，歸慢檔） |
| `0.3s` | 1 | `--dur-slow`（較接近） |

### 5. 殘留 hex 色值

除節點分類色（已在上面處理）外，15 個檔案裡其餘硬寫 hex（灰階邊框、狀態色等）比照既有 token 表（`--color-border`、`--color-border-strong`、`--color-success` 等）逐一替換，沒有需要新增 token 的情況。

## 明確排除（本次不動）

- `components/WorkflowBuilder.vue`（死代碼，未被任何地方 import）
- Workflow 畫布本身的縮放/拖拉/連線邏輯
- `@vue-flow/core` 套件層級的行為
- `SettingsPanel.vue` 的 `wizard-tab` 與 `ci-toggle` 元件重新設計（維持現有樣式，只在圓角/時長清理範圍內順手套 token，不改變其視覺呈現方式）

## 驗證方式

- `npx eslint`、`npm run build` 確認無型別或 lint 錯誤（專案無自動化視覺測試）
- 手動在瀏覽器檢查：
  - 五種節點分類色在畫布上彼此可辨識，且與 success/warning/error 三個狀態色不混淆
  - 完成徽章在各分類色底上都清晰可讀（尤其 Model 的 `#85BDBC` 偏綠，需確認徽章的 `--color-success` 綠不會糊在一起）
  - 進行中 spinner 動畫正常
  - 各 nodePanel 的按鈕遷移後行為（disabled/loading 狀態）與遷移前一致
  - `wizard-tab`、`ci-toggle` 未被誤套用 `AppButton` 樣式
