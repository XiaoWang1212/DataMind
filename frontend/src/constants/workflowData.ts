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
    id: "settings",
    type: "iconNode",
    position: { x: 260, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-tune-variant",
      label: "Settings",
      colorClass: "node-pending",
      description: "設定前處理、特徵工程與模型",
      fields: [],
      config: {
        preprocessing: [],
        featureEngineering: [],
        models: [],
      },
    },
  },
  {
    id: "testScore",
    type: "iconNode",
    position: { x: 460, y: 290 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-test-tube",
      label: "Test &\nScore",
      colorClass: "node-pending",
      description: "切分資料、選擇評估指標",
      fields: [],
      config: {
        split: 0.2,
        metric: "accuracy",
        validation: { method: "k_fold", n_splits: 10, stratified: true, train_size: 0.8 },
        metrics: ["balanced_accuracy", "auc", "auprc", "mcc", "f1"],
      },
    },
  },
  {
    id: "featureImportance",
    type: "iconNode",
    position: { x: 660, y: 200 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-chart-bell-curve",
      label: "Feature\nImportance",
      colorClass: "node-pending",
      description: "顯示特徵重要性，協助找出影響模型的欄位",
      fields: [],
      config: {},
    },
  },
  {
    id: "confusionMatrix",
    type: "iconNode",
    position: { x: 660, y: 380 },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    data: {
      icon: "mdi-grid",
      label: "Confusion\nMatrix",
      colorClass: "node-pending",
      description: "輸出混淆矩陣",
      fields: [],
      config: { normalize: "none" },
    },
  },
];

export const INITIAL_EDGES: Pick<Edge, "id" | "source" | "target" | "type">[] = [
  { id: "e0",  source: "file",      target: "dataTable",         type: "default" },
  { id: "e0a", source: "file",      target: "distribution",      type: "default" },
  { id: "e1",  source: "dataTable", target: "settings",          type: "default" },
  { id: "e2",  source: "settings",  target: "testScore",         type: "default" },
  { id: "e3",  source: "testScore", target: "featureImportance", type: "default" },
  { id: "e4",  source: "testScore", target: "confusionMatrix",   type: "default" },
];

/** Demo 動畫每一步的資料結構；duration 可覆蓋 NODE_RUN_DURATION */
export type DemoStep = { nodeIds: string[]; delay: number; duration?: number };

export const DEMO_STEPS: DemoStep[] = [
  { nodeIds: ["file"],                            delay: 800  },
  { nodeIds: ["distribution"],                    delay: 1400 },
  { nodeIds: ["dataTable"],                       delay: 1800 },
  { nodeIds: ["settings"],                        delay: 2800 },
  { nodeIds: ["testScore"],                       delay: 4200 },
  { nodeIds: ["featureImportance", "confusionMatrix"], delay: 5400 },
];

/** 每個節點顯示 loading spinner 的持續時間（ms） */
export const NODE_RUN_DURATION = 700;

/** 全部節點完成後，再停留 1 秒才結束動畫 */
export const DEMO_FINISH_LINGER = 1000;

/** dataTable 節點使用的假資料預覽 */
export const PREVIEW_HEADERS = ["id", "age", "income", "churn"] as const;

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
