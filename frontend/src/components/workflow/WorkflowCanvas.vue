<template>
  <!-- 畫布容器：專注顯示 Vue Flow，不承擔狀態管理 -->
  <section class="canvas">
    <!-- 真正的 flow 可視區 -->
    <section class="flow-area" ref="flowAreaRef">
      <VueFlow
        id="main-flow"
        :nodes="nodes"
        :edges="edges"
        :node-types="nodeTypes"
        :fit-view-on-init-options="{ padding: isMobile ? 0.18 : 0.3 }"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :elements-selectable="false"
        :pan-on-drag="true"
        :zoom-on-scroll="true"
        :zoom-on-double-click="false"
        :min-zoom="isMobile ? 0.6 : 0.75"
        :max-zoom="isMobile ? 1.5 : 1.6"
        :translate-extent="[[-280, -150], [1240, 900]]"
        fit-view-on-init
        @node-click="onNodeClick"
        @pane-click="onPaneClick"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type { Component } from 'vue'
import { VueFlow, useVueFlow, type Edge } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import type { FlowNode } from '@/types/workflow'

// 由父層 Workspace 傳入資料
defineProps<{
  nodes: FlowNode[]
  edges: Edge[]
  nodeTypes: Record<string, Component>
}>()

// 這個元件只往外通知事件，不直接改資料
const emit = defineEmits<{
  (e: 'select-node', nodeId: string): void
  (e: 'pane-click'): void
}>()

// 手機模式旗標：根據視窗寬度判斷
const isMobile = ref(false)

// 畫布容器 ref：用於監聽容器尺寸變化（支援 sidebar 伸縮）
const flowAreaRef = ref<HTMLElement | null>(null)

// 取得 VueFlow 操作函式（fitView 在容器 resize 時重新對齊）
const { fitView, getViewport } = useVueFlow('main-flow')

// 視窗尺寸改變時重新判斷是否手機模式
function updateViewportMode() {
  isMobile.value = window.innerWidth < 768
}

// 容器 ResizeObserver：當畫布容器寬/高改變時（例如 sidebar 展開）自動重新 fitView
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  // 初次掛載先判斷一次
  updateViewportMode()
  // 監聽 resize，持續保持 RWD 狀態
  window.addEventListener('resize', updateViewportMode)

  // 監聽畫布容器大小變動，確保節點始終置中
  if (flowAreaRef.value) {
    resizeObserver = new ResizeObserver(() => {
      fitView({ padding: isMobile.value ? 0.18 : 0.3 })
    })
    resizeObserver.observe(flowAreaRef.value)
  }
})

onBeforeUnmount(() => {
  // 清理監聽，避免 memory leak
  window.removeEventListener('resize', updateViewportMode)
  resizeObserver?.disconnect()
})

// 計算底部節點（flowY）有沒有被 options panel 遮住，回傳需要往上抬幾 px
function computeRequiredRaise(flowY: number): number {
  const { y: viewportY, zoom } = getViewport()
  const canvasRect = flowAreaRef.value?.getBoundingClientRect()
  if (!canvasRect) return 0
  const panelHeight = Math.min(window.innerHeight * 0.46, 360)
  const panelTop = window.innerHeight - panelHeight
  const margin = 16
  // 節點底部的螢幕 Y（節點高度約 100px）
  const screenBottom = canvasRect.top + (flowY + 100) * zoom + viewportY
  const needed = screenBottom - (panelTop - margin)
  return Math.max(0, needed)
}
defineExpose({ computeRequiredRaise })

// 將點擊節點 id 傳回父層
function onNodeClick(event: { node: { id: string } }) {
  emit('select-node', event.node.id)
}

// 點擊空白區通知父層（通常用來關閉抽屜）
function onPaneClick() {
  emit('pane-click')
}
</script>

<style scoped>
.canvas {
  background: transparent;
  border: none;
  border-radius: 12px;
  padding-top: 6px;
  min-height: 0;
  height: 100%;
  box-sizing: border-box;

  display: flex;
  flex-direction: column;
  gap: 12px;
}

.flow-area {
  flex: 1;
  min-height: 300px;
  border: none;
  border-radius: 12px;
  background-color: #f8fbff;
  background-image: radial-gradient(rgba(0, 93, 255, 0.08) 0.9px, transparent 0.9px);
  background-size: 14px 14px;
  overflow: hidden;
  padding-top: 6px;
}

/* 拖曳時顯示手掌游標 */
:deep(.vue-flow__pane) {
  cursor: grab;
}

:deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

:deep(.vue-flow__edge-path) {
  stroke: #005DFF;
  stroke-width: 2.4;
}

@media (max-width: 1024px) {
  /* 平板：畫布高度加高，避免節點擠在一起 */
  .flow-area {
    min-height: 360px;
  }
}

@media (max-width: 768px) {
  /* 手機：外層邊距縮小、圓角縮小、高度再拉高 */
  .canvas {
    padding: 2px 0;
  }

  .flow-area {
    min-height: 420px;
    border-radius: 10px;
  }
}
</style>
