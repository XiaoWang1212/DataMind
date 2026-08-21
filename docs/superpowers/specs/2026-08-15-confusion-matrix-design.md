# 混淆矩陣節點補完 Design Spec

## 背景

Workflow 畫布上有一個「Confusion Matrix」節點（`frontend/src/constants/workflowData.ts:105-119`），但它是死節點：沒有對應的面板元件（`FeatureImportancePanel.vue`、`ComputeCiPanel.vue` 都有對應面板，這個沒有）、後端從來沒有把真正的混淆矩陣資料算出來回傳過（`test_score_service.py` 的 `_specificity()` 內部有算，但算完就丟，只拿來導出 specificity 這個數值）、`config: { normalize: "none" }` 沒有任何地方讀寫。點下去只會看到空白面板。

混淆矩陣在醫學分類論文裡很常見（尤其二元分類任務，sensitivity/specificity 這些指標的原始拆解），現在有骨架但沒有內容，應該補完而不是刪除。

## 範圍

- 後端：`execute_workflow`/`execute_workflow_stream`（`backend/services/workflow/workflow_service.py`）在組每筆結果時，額外算出並回傳混淆矩陣
- 前端：新增 `ConfusionMatrixPanel.vue`，接上 `confusionMatrix` 節點，樣式與互動模式比照既有的 `FeatureImportancePanel.vue`（模型 + fold 雙下拉切換）
- **不**動現有的 `metrics`/`evaluate_metrics()` 邏輯、**不**動 `_specificity()` 的既有計算方式（它有自己的用途，繼續保留）
- **不**動節點的 id、既有的邊（edge）連接、`useWorkflowNodes.ts`/`useWorkflowDemo.ts`/`useWorkflowImport.ts` 對 `confusionMatrix` id 的既有引用（這些只是版面/流程管理用，不需要改）

## 後端設計

`y_test`（實際值）跟 `y_pred`（預測值）在 `results.append(...)` 之前已經算好（`workflow_service.py:441` 非串流版、`:644` 串流版），在該處新增混淆矩陣計算：

```python
from sklearn.metrics import confusion_matrix as sk_confusion_matrix

cm_labels = sorted(pd.unique(pd.concat([y_test, y_pred]).dropna()), key=str)
cm = sk_confusion_matrix(y_test, y_pred, labels=cm_labels)
confusion_matrix_data = {"labels": [str(l) for l in cm_labels], "matrix": cm.tolist()}
```

`{labels: string[], matrix: number[][]}` 是 NxN 的通用形狀，不寫死二分類（雖然本專案其他 metrics 如 AUC/specificity 目前確實只支援二分類，但混淆矩陣本身用 sklearn 算，天生支援任意類別數，沒有理由特地限縮）。新增的欄位 `confusion_matrix` 加進 `results.append({...})`／`model_results.append({...})` 那個 dict 裡，跟既有的 `metrics`/`feature_importance` 同一層。非串流（`execute_workflow`）跟串流（`execute_workflow_stream`）兩處都要加，兩邊程式碼結構完全對稱，各自獨立加。

## 前端設計

**`ConfusionMatrixPanel.vue`**（新檔案，比照 `FeatureImportancePanel.vue` 的結構）：

- Props：`workflowResult?: Record<string, unknown> | null`（跟 `FeatureImportancePanel` 一樣直接吃整包結果）
- 從 `workflowResult.results[]` 依 `model_name` 分組、每組底下依 `split_name` 再分組（複用 `FeatureImportancePanel.vue` 現有的 `groupedResults`/`currentModel`/`currentImportance` computed 邏輯的寫法模式，換成讀 `confusion_matrix` 欄位）
- 控制列：模型下拉 + fold 下拉，跟 `FeatureImportancePanel.vue` 的 `.fi-controls` 一致（換模型時 fold 重置為第一筆，邏輯完全比照）
- 內容區：NxN 網格表格，橫軸表頭是「預測：{label}」、縱軸是「實際：{label}」，格子顯示數字；對角線（預測正確的格子）用淡色底色標出來，方便一眼看出模型答對/答錯的分布
- 沒有結果時顯示「尚未有混淆矩陣結果，請執行 Workflow 後再查看」（文字比照 `FeatureImportancePanel.vue` 既有的空狀態寫法）

**`WorkflowOptionsPanel.vue`**：新增 `v-else-if="selectedNode.id === 'confusionMatrix'"` 分支，比照 `featureImportance` 分支的寫法（`<ConfusionMatrixPanel :workflow-result="props.workflowResult ?? undefined" />`）。

**`workflowData.ts`**：`confusionMatrix` 節點的 `description`（目前寫「輸出混淆矩陣」）維持不變即可，本來就是對的描述，只是現在終於有東西可以輸出了。

## 錯誤處理 / 相容性

- 舊的 workflow 執行結果（在這次改動之前跑的）沒有 `confusion_matrix` 欄位，`ConfusionMatrixPanel.vue` 讀取時用 `Array.isArray`/型別檢查防禦，缺欄位時該筆結果視為「沒有混淆矩陣資料」，不會整個面板報錯崩潰（比照 `FeatureImportancePanel.vue` 現有的防禦寫法）
- 混淆矩陣計算基於 `y_test`/`y_pred`，這兩個值執行時一定存在（不像 `feature_importance` 需要模型支援 `feature_importances_` 屬性才有值），所以正常執行完的新結果一定會有這個欄位，不需要額外的「模型不支援」空狀態

## 測試

- 後端無 pytest，前端無 vitest。用 `docker exec datamind-backend .venv/bin/python -m py_compile` 做語法檢查，前端用 `npm run type-check`
- 人工瀏覽器驗證：執行一次 workflow，點 `confusionMatrix` 節點，確認：
  - 顯示模型 + fold 下拉，切換後表格內容跟著變
  - NxN 表格的數字加總起來等於該 fold 的測試集筆數（sanity check：混淆矩陣所有格子總和應該等於 `y_test` 的樣本數）
  - 對角線格子有底色標示
