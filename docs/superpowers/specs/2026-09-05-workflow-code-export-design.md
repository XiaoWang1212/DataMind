# Workflow 程式碼匯出 Design Spec

## 背景

DataMind 的 workflow 畫布讓使用者用節點組出一套完整的 ML 分析流程（欄位設定 → 前處理 → 特徵工程 → 模型 → 驗證方式 → 評估指標 → 信賴區間），但執行完只能在畫布內看結果，沒辦法把整套流程帶出去——例如放進論文的 reproducibility 附錄、交給合作的研究人員在自己電腦上重跑、或單純想知道「這個 workflow 到底實際上做了什麼」。這次要做的是把目前畫布上設定好的流程，一次性匯出成一份帶註解的、可直接執行的 Python 程式碼。

## 範圍

- 後端：新增 `generate_workflow_script()`，把 workflow 的設定（前處理、特徵工程、模型、驗證方式、評估指標、信賴區間）轉成一份完整 Python 原始碼字串
- 後端：新增路由，接收 payload、回傳程式碼字串
- 前端：Workflow 畫布頁面新增「匯出程式碼」按鈕，觸發下載 `.py` 檔
- **範圍限定在「產生程式碼」**，不含在伺服器上真的執行這份匯出的程式碼、不含把程式碼存進資料庫或專案歷史
- 前處理／特徵工程的 20 種 step type，第一階段只手寫其中 10 種範本（見下），其餘用清楚的 TODO 註解取代，不是本次要一次做完的範圍
- **不**動現有的 workflow 執行邏輯（`workflow_service.py`/`test_score_service.py`/`preprocess_service.py`/`feature_engineering_service.py`）本身，這次是在旁邊新增一個「讀取同一份設定、輸出成程式碼」的獨立功能，唯一會共用的是「呼叫真正的 model 物件」這件事

## 架構

### 後端：`backend/services/workflow/code_export_service.py`（新檔案）

**主要介面**：
```python
def generate_workflow_script(payload: dict) -> str
```

`payload` 的形狀直接沿用現有 `/api/models/workflow/execute` 已經在用的請求格式（`backend/routes/model.py` 裡 `score_variants_raw`/`preprocess_pipelines`/`model_names` 那條路徑），這樣前端可以重用 `useWorkflowExecution.ts` 組 payload 的邏輯，不用為了這個新功能另外組一份不同形狀的資料：
- `preprocess_pipelines: List[List[Dict]]`（每個 dict 有 `type` 跟該 step 的參數）
- `feature_engineering_steps`（同上結構，作用在特徵工程階段）
- `model_names: List[str]`
- `score_variants: List[Dict]`（`{"metric": "..."}`，對應使用者勾選的評估指標）
- `validation_config: Dict`（`{"method": "k_fold", "n_splits": 10, ...}`）
- `target_col: str`
- `compute_ci: bool`

**輸出**：一份完整的 Python 原始碼字串，區塊順序固定：
1. 檔頭註解（說明這是 DataMind 匯出的程式碼、產生時間、對應哪個 workflow）
2. import 區塊（依實際用到的 step/model 動態組出需要的 import，不要把用不到的東西也 import 進來）
3. 讀取資料集（`DATA_PATH`/`TARGET_COLUMN` 常數留白讓使用者自己填，見下方「資料集處理」）
4. 前處理（依 `preprocess_pipelines` 逐步生成，每步驟前面一行中文註解說明這步在做什麼）
5. 特徵工程（同上）
6. 切分資料（依 `validation_config.method` 生成對應的 sklearn 切分邏輯）
7. 訓練與評估（對每個選用的模型、每個切分產生的 fold，訓練 + 用 `score_variants` 指定的指標評分，`print()` 出結果）
8. Bootstrap 95% CI（僅當 `compute_ci` 為真時附加）

### 模型程式碼：用 `repr()`，不手寫範本

後端 `backend/services/model/models/*.py` 每個模型類別（`RandomForestModel`、`LogisticRegressionModel`...30 多種）都有 `create_estimator()` 回傳一個真正的 sklearn（或相容套件如 xgboost/lightgbm/catboost/imbalanced-learn）估計器物件。這些物件的 `__repr__` 本身就是合法可執行的建構子語法（sklearn 生態系的通用慣例，例如印出 `RandomForestClassifier(class_weight='balanced', n_jobs=-1, random_state=42)`）。

`generate_workflow_script()` 對每個 `model_names` 裡的名字，找到對應的 `ModelConfig`、呼叫 `create_estimator()`、對回傳物件呼叫 `repr()`，直接把這個字串貼進生成的程式碼裡當作模型建構子呼叫。**不**針對每個模型手寫一份程式碼範本——這樣新增模型時這個功能自動涵蓋，不需要額外維護。

需要額外處理的細節：
- `repr()` 印出的是完整類別路徑還是短名稱，取決於該類別有沒有 override `__repr__`（sklearn 標準物件是短名稱，例如 `RandomForestClassifier(...)`，不含模組路徑）；程式碼的 import 區塊要能對應到這個短名稱，所以 import 陳述式要用 `from sklearn.ensemble import RandomForestClassifier` 這種明確 import，而不是 `import sklearn.ensemble as ...`
- 每個模型類別在原始碼裡（`backend/services/model/models/*.py`）已經記錄了它用到的 import 路徑（檔案開頭的 `from sklearn.xxx import YyyClassifier`），`generate_workflow_script()` 需要一個對照表：模型名稱 → 該用哪一行 import。做法是建立一個手動維護的 `MODEL_IMPORTS: Dict[str, str]` 常數（`code_export_service.py` 內），內容抄自各模型檔案開頭的 import 行——不做「動態讀取/解析模型檔案原始碼」這種更複雜的作法，手動維護的對照表在新增模型時要記得同步更新，但簡單可靠

### 前處理／特徵工程：手寫範本，分階段支援

第一階段（本次要做）支援的 step type 與對應的程式碼產生方式：

**前處理**（`preprocess_service.py` 的 `PREPROCESS_STEP_TYPES` 共 10 種，本次支援其中 6 種）：
- `fill_na`：依 `strategy`（mean/mode/median）跟 `columns` 產生 `df[cols] = df[cols].fillna(df[cols].mean())` 這類程式碼
- `standardize`：`from sklearn.preprocessing import StandardScaler` + fit_transform 對應 columns
- `normalize`：`MinMaxScaler`，同上
- `one_hot`：`pd.get_dummies(df, columns=[...])`
- `label_encode`：`LabelEncoder`，逐欄位處理
- `drop_columns`：`df = df.drop(columns=[...])`

**特徵工程**（`feature_engineering_service.py` 的 `FEATURE_ENGINEERING_STEP_TYPES` 共 10 種，本次支援其中 4 種）：
- `pca`：`from sklearn.decomposition import PCA`
- `select_relevant_features`：`SelectKBest(f_classif, k=...)`
- `normalize_features`：沿用前處理的 `MinMaxScaler`/`StandardScaler` 邏輯（依 step 參數決定用哪個）
- `impute_missing`：沿用 `fill_na` 的邏輯

其餘 14 種 step type（`knn_impute`、`iterative_impute`、`remove_outliers_iqr`、`remove_outliers_zscore`、`discretize_continuous`、`continuize_discrete`、`select_random_features`、`randomize_rows`、`remove_sparse_features`、`cur_decomposition`）：`generate_workflow_script()` 遇到這些 step type 時，在對應位置插入：
```python
# ⚠️ TODO：這個 workflow 用了「{step_type}」步驟，DataMind 程式碼匯出功能目前還不支援自動產生這段邏輯。
# 請參考 backend/services/workflow/{preprocess_service.py 或 feature_engineering_service.py} 裡對應的實作，自行補上。
```
不中斷整體產生流程，其餘支援的 step 照樣正常產生。

### 驗證方式：5 種一次做完

對照 `validation_config.method`：
- `k_fold` → `sklearn.model_selection.StratifiedKFold`（若 `stratified: true`）或 `KFold`
- `group_k_fold` → `GroupKFold`
- `random_sampling` → 迴圈跑 `train_test_split` N 次（`n_repeats`）
- `test_on_train` → 訓練跟測試用同一份資料（純粹用於檢查過擬合，程式碼加註解說明這個用途）
- `test_on_test` → 單次 `train_test_split`

### 評估指標與信賴區間

`score_variants` 裡每個 `{"metric": "..."}` 對應 `sklearn.metrics` 裡的一個函式呼叫（`accuracy_score`、`f1_score` 等，10 種都是標準 sklearn 函式，直接組 import + 呼叫，不需要範本分階段）。`compute_ci` 為真時，額外生成一段 bootstrap resampling 迴圈（重抽樣 1000 次、算每次的指標、取 2.5/97.5 百分位數），邏輯對照 `test_score_service.py` 裡既有的 CI 計算方式。

### 資料集處理

生成的程式碼開頭固定：
```python
# TODO：換成你自己的資料集路徑
DATA_PATH = "your_dataset.csv"
TARGET_COLUMN = "{實際的 target 欄位名稱}"  # 這個直接帶入真實值，不是 placeholder

df = pd.read_csv(DATA_PATH)
```
`DATA_PATH` 用 placeholder（使用者自己電腦的檔案路徑對外部沒有意義），但 `TARGET_COLUMN` 直接帶入這個 workflow 實際設定的目標欄位名稱（這個值是 workflow 設定的一部分，不是使用者環境相關的東西）。

### 路由

新增 `POST /api/models/workflow/export-code`，複用 `/api/models/workflow/execute` 的 payload 驗證邏輯（沒有選模型、沒有 target 欄位等錯誤情況回傳一樣的錯誤訊息格式）。成功回傳：
```json
{ "success": true, "code": "...", "filename": "workflow_export_<project_id>.py" }
```

### 前端

`WorkflowWorkspace.vue`（畫布頁面）現有「查看結果」按鈕（`workflowResult` 存在時顯示）旁邊新增「匯出程式碼」按鈕，不需要等 workflow 執行完成才能按（跟現有查看結果按鈕的顯示條件不同，只要有基本設定就能匯出）。點擊時：
1. 用跟 `useWorkflowExecution.ts` 組執行 payload 一樣的邏輯組出 payload
2. `POST` 到新路由
3. 拿到 `{code, filename}` 後用 `Blob` + 動態 `<a download>` 觸發瀏覽器下載
4. 失敗時（後端回傳驗證錯誤）顯示錯誤訊息，不觸發下載

## 錯誤處理 / 邊界情況

- 沒有選任何模型：後端回傳跟現有 `/execute` 一樣的「請至少選擇一個模型」錯誤，前端顯示提示、不下載
- 沒有設定 target 欄位：同上模式
- 前處理／特徵工程用到不支援的 step type：不擋下整個匯出，該步驟位置插入 TODO 註解，其餘正常生成（見上）
- `repr()` 印出來的模型建構子字串理論上不會失敦（sklearn 生態系的標準行為），但如果未來新增了某個不支援標準 `__repr__` 的模型類別，`generate_workflow_script()` 對單一模型的 `repr()` 呼叫要包一層 try/except，失敗時該模型也用跟不支援 step type 一樣的 TODO 註解取代，不讓一個模型的問題擋掉整份程式碼的產生

## 測試

- 後端新增 `backend/tests/test_code_export_service.py`：組一個涵蓋所有已支援 step type（6 種前處理 + 4 種特徵工程）+ 至少 2 個模型 + 5 種驗證方式各一次 + `compute_ci: true` 的假 payload，呼叫 `generate_workflow_script()`，斷言：
  - 回傳字串通過 `ast.parse()`（保證語法合法，即使不見得每次都能真的跑通）
  - 字串裡包含每個 step/model/validation 對應的關鍵程式碼片段（例如 `StandardScaler`、`RandomForestClassifier`、`StratifiedKFold`）
  - 對一個不支援的 step type（例如 `knn_impute`）斷言輸出裡有對應的 TODO 註解字串
- 前端無 vitest，用 `npm run type-check`
- 人工瀏覽器驗證：
  1. 組一個包含已支援 step type 的簡單 workflow，點「匯出程式碼」，確認下載到 `.py` 檔
  2. 把下載下來的檔案裡 `DATA_PATH` 換成真實資料集路徑，用 `python3 workflow_export_x.py` 實際執行，確認能跑完並印出跟畫布上一致的評估指標數字（在浮點數誤差範圍內）
  3. 組一個用到目前不支援 step type 的 workflow（例如 `knn_impute`），確認匯出的程式碼裡看得到清楚的 TODO 註解，其餘部分仍正常
  4. 沒有選模型/沒有 target 欄位時點擊匯出，確認畫面顯示錯誤訊息、沒有觸發下載
