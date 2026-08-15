import type { Position } from "@vue-flow/core";

export interface NodeField {
  key: string;
  label: string;
  type: "text" | "number" | "select";
  options?: string[];
}

export type ConfigValue =
  | string
  | number
  | boolean
  | null
  | unknown[]
  | Record<string, unknown>;

export type NodeType = "source" | "transform" | "visualize" | "model" | "evaluate";

export interface NodeData {
  icon: string;
  label: string;
  /** 節點分類，決定底色（docs/DESIGN_SYSTEM.md §2.3），建立節點時指定、不隨執行狀態改變 */
  nodeType: NodeType;
  description: string;
  fields: NodeField[];
  config: Record<string, unknown>;
  /** demo 動畫狀態，由 canvasNodes computed 動態註入 */
  status?: "running" | "finished" | null;
  /** 是否為目前點選中的節點，由 canvasNodes computed 依 selectedNodeId 動態註入 */
  isSelected?: boolean;
}

export interface FlowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  sourcePosition?: Position;
  targetPosition?: Position;
  data: NodeData;
  class?: string;
}

/** 傳給 OptionsPanel 的精簡節點型別（不含 VueFlow 佈局資訊） */
export interface SimpleNode {
  id: string;
  data: NodeData;
}

/** edges ref 的核心型別（不含樣式） */
export type EdgeBase = Pick<
  import("@vue-flow/core").Edge,
  "id" | "source" | "target" | "type"
>;
