<template>
  <!-- Workflow 主容器：上方畫布 + 下方可滑出的設定抽屜 -->
  <section class="workspace">
    <!-- 畫布區：顯示節點與連線 -->
    <WorkflowCanvas
      class="workspace-canvas"
      :nodes="canvasNodes"
      :edges="canvasEdges"
      :node-types="nodeTypes"
      @select-node="handleSelectNode"
      @pane-click="closeMenu"
    />

    <!-- Demo 執行按鈕 -->
    <button
      class="demo-btn"
      :class="{ 'demo-btn--running': isDemoRunning }"
      :disabled="isDemoRunning"
      @click="startDemo"
    >
      {{ isDemoRunning ? '⏳' : '▶' }}
    </button>

    <!-- 下方抽屜：只有選到節點時才出現 -->
    <Transition name="slide-up">
      <div v-if="selectedNode" class="options-drawer" :class="{ 'options-drawer--expanded': isExpanded }" :style="drawerStyle">
        <!-- 拖曳區：上拉展開、下拉三段式操作 -->
        <div
          class="options-drawer__drag-zone"
          aria-hidden="true"
          @mousedown.prevent="startDrag"
          @touchstart.prevent="startDrag"
        >
          <div class="options-drawer__bar" />
        </div>

        <!-- 設定內容區（可滾動） -->
        <div class="options-drawer__scroll">
          <WorkflowOptionsPanel
            :selected-node="selectedNode"
            @update-config="handleUpdateConfig"
          />
        </div>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed, markRaw, onBeforeUnmount, ref } from 'vue'
import { type Edge } from '@vue-flow/core'
import IconNode from './IconNode.vue'
import WorkflowCanvas from './WorkflowCanvas.vue'
import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'
import { useDrawerDrag } from '@/composables/useDrawerDrag'
import { DEMO_FINISH_LINGER, DEMO_STEPS, INITIAL_EDGES, INITIAL_NODES, NODE_RUN_DURATION } from '@/constants/workflowData'
import type { ConfigValue, EdgeBase, FlowNode, SimpleNode } from '@/types/workflow'

// demo 動畫狀態：Map<nodeId, 'running' | 'finished'>
const nodeStatuses = ref<Map<string, 'running' | 'finished'>>(new Map())

// demo 是否正在執行中
const isDemoRunning = ref(false)

// demo 全部動畫是否已結束（結束後邊線保持黃色但停止動畫）
const isDemoFinished = ref(false)

// 存放 demo 計時器 id，元件卸載時用來清除
const demoTimers: number[] = []

// 註冊自訂節點元件：iconNode 對應 IconNode.vue
const nodeTypes = {
  iconNode: markRaw(IconNode),
}

// 核心節點與連線資料
const nodes = ref<FlowNode[]>(INITIAL_NODES)
const edges = ref<EdgeBase[]>(INITIAL_EDGES)

// 預設不選任何節點，點擊後才顯示下方 options
const selectedNodeId = ref<string | null>(null)

// 抽屜拖曳邏輯（封裝在 composable）
const { isExpanded, style: drawerStyle, startDrag, reset: resetDrawer } = useDrawerDrag()

// 目前被選取的節點（傳給 OptionsPanel）
const selectedNode = computed<SimpleNode | null>(() => {
  if (!selectedNodeId.value) return null
  const node = nodes.value.find((item) => item.id === selectedNodeId.value)
  return node ? { id: node.id, data: node.data } : null
})

// 節點顏色：完成的節點改成黃色，其餘依 data.colorClass
const canvasNodes = computed<FlowNode[]>(() =>
  nodes.value.map((node) => {
    const status = nodeStatuses.value.get(node.id) ?? null
    return {
      ...node,
      class: '',
      data: {
        ...node.data,
        status,
        // 只有 finished 才變黃，running 保持原色（只顯示 spinner）
        colorClass: status === 'finished' ? 'node-yellow' : node.data.colorClass,
      },
    }
  }),
)

// flow 連線：每次 nodeStatuses 變動都產生全新物件，確保 Vue Flow 偵測到變化並更新 SVG marker
const canvasEdges = computed<Edge[]>(() =>
  edges.value.map((edge): Edge => {
    const done = nodeStatuses.value.get(String(edge.source)) === 'finished'
    return {
      ...edge,
      animated: done && !isDemoFinished.value,
      style: done ? { stroke: '#F0E274', strokeWidth: 2 } : { stroke: '#d9d9d9', strokeWidth: 1.5 },
    }
  }),
)

// 重置 demo 全部狀態並清除所有計時器
function resetDemo(): void {
  nodeStatuses.value = new Map()
  isDemoRunning.value = false
  isDemoFinished.value = false
  demoTimers.forEach(clearTimeout)
  demoTimers.splice(0)
}

// 演示執行：依照 workflow 順序逐步點亮節點
function startDemo(): void {
  if (isDemoRunning.value) return

  resetDemo()
  isDemoRunning.value = true

  for (const { nodeIds, delay } of DEMO_STEPS) {
    // 先設為 running：顯示 spinner
    demoTimers.push(
      setTimeout(() => {
        const next = new Map(nodeStatuses.value)
        nodeIds.forEach((id) => next.set(id, 'running'))
        nodeStatuses.value = next
      }, delay),
    )
    // NODE_RUN_DURATION 後設為 finished：顏色變黃、spinner 消失
    demoTimers.push(
      setTimeout(() => {
        const next = new Map(nodeStatuses.value)
        nodeIds.forEach((id) => next.set(id, 'finished'))
        nodeStatuses.value = next
      }, delay + NODE_RUN_DURATION),
    )
  }

  // 全部節點完成後再等 DEMO_FINISH_LINGER，才停止動畫
  const lastStepDelay = Math.max(...DEMO_STEPS.map((s) => s.delay))
  const endTime = lastStepDelay + NODE_RUN_DURATION + DEMO_FINISH_LINGER
  demoTimers.push(
    setTimeout(() => {
      isDemoRunning.value = false
      isDemoFinished.value = true
    }, endTime),
  )
}

// 節點點擊：更新目前選擇的 node
function handleSelectNode(nodeId: string): void {
  if (selectedNodeId.value === nodeId) {
    closeMenu()
    return
  }
  selectedNodeId.value = nodeId
  resetDrawer()
}

// 點空白區可收起 menu
function closeMenu(): void {
  selectedNodeId.value = null
  resetDrawer()
}

// 面板儲存：只更新對應 node 的 config
function handleUpdateConfig(payload: { nodeId: string; config: Record<string, ConfigValue> }): void {
  nodes.value = nodes.value.map((node) => {
    if (node.id !== payload.nodeId) return node
    return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
  })
}

// 元件卸載時確保清除 demo 計時器
onBeforeUnmount(resetDemo)
</script>

<style scoped>
.workspace {
  position: relative;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  border-radius: 16px 16px 0 0;
  background-color: #f9fbff;
  background-image: radial-gradient(rgba(0, 93, 255, 0.035) 0.8px, transparent 0.8px);
  background-size: 16px 16px;
}

.workspace-canvas {
  height: 100%;
}

/* Demo 執行按鈕：浮在畫布右上角 */
.demo-btn {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1.5px solid rgba(0, 93, 255, 0.18);
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  font-size: 13px;
  color: #005DFF;
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
  user-select: none;
  padding: 0;
}

.demo-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.92);
}

.demo-btn--running,
.demo-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.options-drawer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 10;
  /* max-height 由 useDrawerDrag composable 的 inline style 控制 */
  border-top-left-radius: 14px;
  border-top-right-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.45);
  background: rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(16px);
  box-shadow: 0 -8px 18px rgba(15, 23, 42, 0.05);
  will-change: transform;
  display: flex;
  flex-direction: column;
}

/* 抽屜內部可滾動區區：拖曳區固定頂部，內容區独立滾動 */
.options-drawer__scroll {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.options-drawer__bar {
  width: 52px;
  height: 5px;
  border-radius: 999px;
  background: rgba(0, 93, 255, 0.26);
  margin: 0 auto;
  cursor: grab;
}

.options-drawer__drag-zone {
  padding: 12px 0 0px;
  cursor: grab;
  touch-action: none;
}

.options-drawer__bar:active {
  cursor: grabbing;
}

.options-drawer__drag-zone:active {
  cursor: grabbing;
}

@media (max-width: 1024px) {
  /* max-height 由 composable 失管，依届域地小，在這裡不覆寫 */
}

@media (max-width: 768px) {
  .workspace {
    border-radius: 12px;
  }

  .options-drawer {
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
  }

  .options-drawer__drag-zone {
    padding: 14px 0 8px;
  }
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.22s ease, opacity 0.22s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.slide-up-enter-to,
.slide-up-leave-from {
  transform: translateY(0);
  opacity: 1;
}
</style>
