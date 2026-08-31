// 前處理／特徵工程／驗證方法的中文標籤。workflow 設定面板與專案詳情頁共用，
// 兩處顯示的名稱必須一致
export const PREPROCESS_LABELS: Record<string, string> = {
  fill_na: '缺值填補',
  knn_impute: 'KNN 缺值填補',
  iterative_impute: 'MICE 多重插補',
  normalize: 'Min-Max 正規化',
  standardize: 'Z-score 標準化',
  one_hot: 'One-Hot 編碼',
  label_encode: 'Label 編碼',
  drop_columns: '移除欄位',
  remove_outliers_iqr: 'IQR 異常值處理',
  remove_outliers_zscore: 'Z-score 異常值處理',
}

export const FEATURE_LABELS: Record<string, string> = {
  select_relevant_features: '特徵選擇',
  pca: 'PCA 降維',
  discretize_continuous: '連續→離散',
  continuize_discrete: '離散→連續',
  normalize_features: '特徵正規化',
  remove_sparse_features: '移除稀疏特徵',
}

// 對應 backend/docs/workflow/resampling.md 列出的 resampling_method 值（不含 none）
export const RESAMPLING_LABELS: Record<string, string> = {
  smote: 'SMOTE 過採樣',
  adasyn: 'ADASYN 自適應過採樣',
  borderline_smote: 'Borderline-SMOTE 邊界過採樣',
  random_oversample: '隨機過採樣',
  random_undersample: '隨機欠採樣',
  smoteenn: 'SMOTE + ENN 複合採樣',
  smotetomek: 'SMOTE + Tomek 複合採樣',
}

export const VALIDATION_LABELS: Record<string, string> = {
  k_fold: 'Cross validation',
  group_k_fold: 'Cross validation by feature',
  random_sampling: 'Random sampling',
  leave_one_out: 'Leave one out',
  test_on_train: 'Test on train data',
  test_on_test: 'Test on test data',
}

export interface NodeHelpEntry {
  /** 畫布上顯示的節點名稱 */
  label: string
  icon: string
  /** 對應 --color-node-* 的分類，說明面板的圖示底色用它 */
  nodeType: 'source' | 'transform' | 'visualize' | 'model' | 'evaluate'
  text: string
}

// 節點說明，順序照 pipeline 由前到後。模型節點一律用 'model'（實際 id 是 model-0、model-1…）
export const NODE_HELP: Record<string, NodeHelpEntry> = {
  file: {
    label: 'File',
    icon: 'mdi-file-outline',
    nodeType: 'source',
    text: '上傳並選擇要分析的資料集檔案，支援 CSV 與 Excel 格式。後續所有節點皆以此檔案為輸入。',
  },
  dataTable: {
    label: 'Data Table',
    icon: 'mdi-table',
    nodeType: 'source',
    text: '檢視資料集的欄位與內容，並指定各欄位的型別與角色（特徵或預測目標）。',
  },
  distribution: {
    label: 'Distribution',
    icon: 'mdi-chart-histogram',
    nodeType: 'visualize',
    text: '以直方圖呈現各欄位的數值分布，用於檢查資料偏態、離群值與類別是否失衡。',
  },
  preprocessor: {
    label: 'Preprocessor',
    icon: 'mdi-filter-cog-outline',
    nodeType: 'transform',
    text: '依序執行前處理步驟，例如缺值填補、標準化與編碼。所有步驟僅以訓練集擬合後再套用至驗證集，避免資料洩漏。',
  },
  featureEngineering: {
    label: 'Feature Engineering',
    icon: 'mdi-chart-scatter-plot',
    nodeType: 'transform',
    text: '對前處理後的特徵進行轉換與篩選，例如特徵選擇、PCA 降維或連續與離散型別互換。',
  },
  settings: {
    label: 'Settings',
    icon: 'mdi-tune-variant',
    nodeType: 'model',
    text: '設定整條流程的前處理、特徵工程、重抽樣與驗證方式，是此工作流程的主要設定入口。',
  },
  model: {
    label: 'Models',
    icon: 'mdi-brain',
    nodeType: 'model',
    text: '一個待訓練的分類模型。流程會將每個模型與每組前處理組合交叉配對，分別訓練並評估。',
  },
  testScore: {
    label: 'Test & Score',
    icon: 'mdi-test-tube',
    nodeType: 'evaluate',
    text: '依設定的驗證方式訓練所有模型與前處理的組合，並輸出各組的評估指標供比較。',
  },
  featureImportance: {
    label: 'Feature Importance',
    icon: 'mdi-chart-bell-curve',
    nodeType: 'evaluate',
    text: '列出各特徵對模型預測結果的影響程度，用於判斷哪些變數具有解釋力。',
  },
  confusionMatrix: {
    label: 'Classification Evaluation',
    icon: 'mdi-grid',
    nodeType: 'evaluate',
    text: '以混淆矩陣呈現各類別的預測結果，顯示正確分類與各種誤判的數量。',
  },
  computeCi: {
    label: 'Compute CI',
    icon: 'mdi-chart-areaspline-variant',
    nodeType: 'evaluate',
    text: '以重抽樣估計評估指標的信賴區間，用於判斷模型之間的差異是否具有統計意義。',
  },
}
