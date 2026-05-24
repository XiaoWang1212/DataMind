import { Position } from "@vue-flow/core";
import type { Edge } from "@vue-flow/core";
import type { FlowNode } from "@/types/workflow";

export const INITIAL_NODES: FlowNode[] = [
  {
    id: "file",
    type: "iconNode",
    position: { x: -120, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-file-outline",
      label: "File",
      colorClass: "node-pending",
      description: "上傳資料檔案",
      fields: [],
      config: { fileName: "" },
    },
  },
  {
    id: "dataTable",
    type: "iconNode",
    position: { x: 60, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-table",
      label: "Data\nTable",
      colorClass: "node-pending",
      description: "上傳資料預覽",
      fields: [],
      config: {},
    },
  },
  {
    id: "distribution",
    type: "iconNode",
    position: { x: 60, y: 170 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-chart-histogram",
      label: "Distribution",
      colorClass: "node-pending",
      description: "資料分布視覺化",
      fields: [],
      config: {},
    },
  },
  {
    id: "preprocessor",
    type: "iconNode",
    position: { x: 240, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-tune-variant",
      label: "Preprocessor",
      colorClass: "node-pending",
      description: "前處理（缺值、標準化、編碼）",
      fields: [
        {
          key: "missing",
          label: "缺值處理",
          type: "select",
          options: ["drop", "mean", "median"],
        },
        {
          key: "scale",
          label: "標準化",
          type: "select",
          options: ["none", "standard", "minmax"],
        },
      ],
      config: { missing: "mean", scale: "standard" },
    },
  },
  {
    id: "modelLinear",
    type: "iconNode",
    position: { x: 420, y: 110 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-chart-line",
      label: "Linear\nRegression",
      colorClass: "node-pending",
      description: "線性回歸模型設定",
      fields: [
        {
          key: "fitIntercept",
          label: "Fit Intercept",
          type: "select",
          options: ["true", "false"],
        },
      ],
      config: { fitIntercept: "true" },
    },
  },
  {
    id: "modelRandomForest",
    type: "iconNode",
    position: { x: 420, y: 230 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-forest",
      label: "Random\nForest",
      colorClass: "node-pending",
      description: "隨機森林模型設定",
      fields: [{ key: "nEstimators", label: "n_estimators", type: "number" }],
      config: { nEstimators: 200 },
    },
  },
  {
    id: "modelXgboost",
    type: "iconNode",
    position: { x: 420, y: 350 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-flash",
      label: "XGBoost",
      colorClass: "node-pending",
      description: "XGBoost 模型設定",
      fields: [{ key: "maxDepth", label: "max_depth", type: "number" }],
      config: { maxDepth: 6 },
    },
  },
  {
    id: "modelMore",
    type: "iconNode",
    position: { x: 420, y: 470 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-dots-horizontal-circle-outline",
      label: "More\nModels",
      colorClass: "node-pending",
      description: "其餘模型收合在此（SVM / Naive Bayes / KNN ...）",
      fields: [],
      config: {},
    },
  },
  {
    id: "testScore",
    type: "iconNode",
    position: { x: 600, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-test-tube",
      label: "Test &\nScore",
      colorClass: "node-pending",
      description: "切分資料、選擇評估指標",
      fields: [
        { key: "split", label: "Test Split", type: "number" },
        {
          key: "metric",
          label: "Metric",
          type: "select",
          options: ["accuracy", "f1", "auc", "precision", "recall"],
        },
      ],
      config: { split: 0.2, metric: "accuracy" },
    },
  },
  {
    id: "confusionMatrix",
    type: "iconNode",
    position: { x: 780, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-grid",
      label: "Confusion\nMatrix",
      colorClass: "node-pending",
      description: "輸出混淆矩陣（顯示方式）",
      fields: [
        {
          key: "normalize",
          label: "Normalize",
          type: "select",
          options: ["none", "true", "pred"],
        },
      ],
      config: { normalize: "none" },
    },
  },
];

/** 核心連線資料，不含樣式（樣式由 canvasEdges computed 動態產生） */
export const INITIAL_EDGES: Pick<Edge, "id" | "source" | "target" | "type">[] =
  [
    { id: "e0", source: "file", target: "dataTable", type: "default" },
    { id: "e0a", source: "file", target: "distribution", type: "default" },
    { id: "e1", source: "dataTable", target: "preprocessor", type: "default" },
    {
      id: "e2a",
      source: "preprocessor",
      target: "modelLinear",
      type: "default",
    },
    {
      id: "e2b",
      source: "preprocessor",
      target: "modelRandomForest",
      type: "default",
    },
    {
      id: "e2c",
      source: "preprocessor",
      target: "modelXgboost",
      type: "default",
    },
    { id: "e2d", source: "preprocessor", target: "modelMore", type: "default" },
    { id: "e3a", source: "modelLinear", target: "testScore", type: "default" },
    {
      id: "e3b",
      source: "modelRandomForest",
      target: "testScore",
      type: "default",
    },
    { id: "e3c", source: "modelXgboost", target: "testScore", type: "default" },
    { id: "e3d", source: "modelMore", target: "testScore", type: "default" },
    {
      id: "e4",
      source: "testScore",
      target: "confusionMatrix",
      type: "default",
    },
  ];

/** Demo 動畫每一步的資料結構 */
export type DemoStep = { nodeIds: string[]; delay: number };

/** Demo 動畫：依序點亮的節點 id 與觸發時間（ms） */
export const DEMO_STEPS: DemoStep[] = [
  { nodeIds: ["file"], delay: 800 },
  { nodeIds: ["distribution"], delay: 1400 },
  { nodeIds: ["dataTable"], delay: 1800 },
  { nodeIds: ["preprocessor"], delay: 2600 },
  { nodeIds: ["modelLinear"], delay: 3100 },
  { nodeIds: ["modelRandomForest"], delay: 3600 },
  { nodeIds: ["modelXgboost"], delay: 4100 },
  { nodeIds: ["modelMore"], delay: 4600 },
  { nodeIds: ["testScore"], delay: 5800 },
  { nodeIds: ["confusionMatrix"], delay: 7000 },
];

/** 每個節點顯示 loading spinner 的持續時間（ms） */
export const NODE_RUN_DURATION = 700;

/** 全部節點完成後，再停留 1 秒才結束動畫 */
export const DEMO_FINISH_LINGER = 1000;

/** dataTable 節點使用的假資料預覽 */
export const PREVIEW_HEADERS = ["id", "age", "income", "churn"] as const;

/** 每一筆資料的欄數必須與 PREVIEW_HEADERS 一致 */
type PreviewRow = [string, string, string, string];

export const PREVIEW_SOURCE_ROWS: PreviewRow[] = [
  ["1001", "34", "52000", "0"],
  ["1002", "41", "67000", "1"],
  ["1003", "29", "43000", "0"],
  ["1004", "37", "59000", "1"],
  ["1005", "45", "71000", "0"],
  ["1006", "31", "48000", "0"],
  ["1007", "52", "86000", "1"],
  ["1008", "27", "39000", "0"],
  ["1009", "39", "61000", "1"],
  ["1010", "33", "50000", "0"],
  ["1011", "46", "76000", "1"],
];
