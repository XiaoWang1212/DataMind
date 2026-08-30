<template>
  <!-- 畫布容器：專注顯示 Vue Flow，不承擔狀態管理 -->
  <section class="canvas">
    <!-- 真正的 flow 可視區 -->
    <section
      ref="flowAreaRef"
      class="flow-area"
      :style="{
        minHeight: canvasMinHeight ? `${canvasMinHeight}px` : undefined,
        minWidth: canvasMinWidth ? `${canvasMinWidth}px` : undefined,
      }"
      @mousedown="userHasPanned = true"
      @touchstart.passive="userHasPanned = true"
      @wheel.passive="userHasPanned = true"
    >
      <VueFlow
        id="main-flow"
        :edges="edges"
        :elements-selectable="false"
        fit-view-on-init
        :fit-view-on-init-options="{ padding: isMobile ? 0.18 : 0.3 }"
        :max-zoom="isMobile ? 1.5 : 1.6"
        :min-zoom="minZoom"
        :node-types="nodeTypes"
        :nodes="nodes"
        :nodes-connectable="false"
        :nodes-draggable="false"
        :pan-on-drag="true"
        :style="{ width: '100%', height: '100%' }"
        :translate-extent="translateExtent"
        :zoom-on-double-click="false"
        :zoom-on-scroll="true"
        @node-click="onNodeClick"
        @pane-click="onPaneClick"
      />
    </section>
  </section>
</template>

<script setup lang="ts">
  import type { Component } from 'vue'
  import type { FlowNode } from '@/types/workflow'
  import { type Edge, useVueFlow, VueFlow } from '@vue-flow/core'
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import '@vue-flow/core/dist/style.css'
  import '@vue-flow/core/dist/theme-default.css'

  // 由父層 Workspace 傳入資料
  const props = defineProps<{
    nodes: FlowNode[]
    edges: Edge[]
    nodeTypes: Record<string, Component>
    canvasMinHeight?: number
    canvasMinWidth?: number
  }>()

  // 這個元件只往外通知事件，不直接改資料
  const emit = defineEmits<{
    (e: 'select-node', nodeId: string): void
    (e: 'pane-click'): void
  }>()

  // 手機模式旗標：根據視窗寬度判斷
  const isMobile = ref(false)

  // min-zoom 和 translate-extent 根據畫布大小動態調整
  const minZoom = computed(() => {
    const ref = 860
    const w = props.canvasMinWidth ?? ref
    const suggested = Math.max(0.2, 0.75 * (ref / w))
    return isMobile.value ? Math.max(0.15, suggested * 0.8) : suggested
  })

  const translateExtent = computed<[[number, number], [number, number]]>(() => {
    const w = Math.max(2400, (props.canvasMinWidth ?? 860) + 1200)
    const h = Math.max(2400, (props.canvasMinHeight ?? 520) + 1200)
    return [[-800, -600], [w, h]]
  })

  // 畫布容器 ref：用於監聽容器尺寸變化（支援 sidebar 伸縮）
  const flowAreaRef = ref<HTMLElement | null>(null)

  // 取得 VueFlow 操作函式（fitView 在容器 resize 時重新對齊）
  const { fitView, getViewport, setNodes, setEdges } = useVueFlow('main-flow')

  // 使用者手動移動過視角後，不再自動 fitView（避免打斷操作）
  const userHasPanned = ref(false)

  // 視窗尺寸改變時重新判斷是否手機模式
  function updateViewportMode () {
    isMobile.value = window.innerWidth < 768
  }

  function refreshFitView (force = false): void {
    if (!force && userHasPanned.value) return
    nextTick(() => {
      fitView({ padding: isMobile.value ? 0.18 : 0.3 })
    })
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
        refreshFitView()
      })
      resizeObserver.observe(flowAreaRef.value)
    }
  })

  // 初始對齊完成後鎖定視角，之後新增/刪除節點不會因為 canvasMinWidth 改變而重置。
  // 計時從「第一次真的對齊過」起算而不是從掛載起算：節點可能是從 localStorage 還原、
  // 或等執行結果回來才有，掛載時 nodes 還是空的，那時候 fitView 沒有東西可以對
  const VIEWPORT_LOCK_DELAY_MS = 800
  let hasFitted = false

  function fitOnce (): void {
    if (hasFitted) return
    hasFitted = true
    refreshFitView(true)
    window.setTimeout(() => {
      userHasPanned.value = true
    }, VIEWPORT_LOCK_DELAY_MS)
  }

  onBeforeUnmount(() => {
    // 清理監聽，避免 memory leak
    window.removeEventListener('resize', updateViewportMode)
    resizeObserver?.disconnect()
  })

  // 只記錄節點的結構特徵（id + position），nodeType 變動不算結構改變
  function nodeStructureKey (nodes: typeof props.nodes): string {
    return nodes.map(n => `${n.id}:${n.position.x},${n.position.y}`).join('|')
  }

  let prevStructureKey = ''

  watch(
    () => props.nodes,
    newNodes => {
      setNodes(newNodes)
      const key = nodeStructureKey(newNodes)
      if (key !== prevStructureKey) {
        prevStructureKey = key
        nextTick(() => {
          setEdges(props.edges)
          // 只有第一次拿到節點才 fitView；後續新增/刪除不重置視角
          if (newNodes.length > 0) fitOnce()
        })
      }
    },
    { deep: true, immediate: true },
  )

  watch(
    () => props.edges,
    newEdges => {
      setEdges(newEdges)
    },
    { deep: true },
  )

  // 計算底部節點（flowY）有沒有被 options panel 遮住，回傳需要往上抬幾 px
  function computeRequiredRaise (flowY: number): number {
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

  // 將點擊節點 id 傳回父層（同時視為使用者已確立視角，不再自動 fitView）
  function onNodeClick (event: { node: { id: string } }) {
    userHasPanned.value = true
    emit('select-node', event.node.id)
  }

  // 點擊空白區通知父層（通常用來關閉抽屜）
  function onPaneClick () {
    emit('pane-click')
  }
</script>

<style scoped>
  .canvas {
    /* 不鋪底色也不套玻璃：直接讓頁面漸層透上來，畫布跟背景連成一片，
       只疊一層點狀紋理標示可操作區域。圓角交給外層 .workspace 統一裁 */
    background: radial-gradient(var(--color-border-strong) 0.9px, transparent 0.9px) 0 0 / 14px 14px;
    padding-top: 6px;
    min-height: 0;
    min-width: 0;
    box-sizing: border-box;

    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .flow-area {
    flex: 1;
    min-height: 300px;
    min-width: 0;
    overflow: auto;
    padding-top: 6px;
    background: transparent;
  }

  /* 拖曳時顯示手掌游標 */
  :deep(.vue-flow__pane) {
    cursor: grab;
  }

  :deep(.vue-flow__pane.dragging) {
    cursor: grabbing;
  }

  /* 可點的節點顯示手指；模型節點停用互動、顯示預設箭頭 */
  :deep(.vue-flow__node) {
    cursor: pointer;
  }

  :deep(.vue-flow__node.node-non-interactive) {
    cursor: default;
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--color-accent);
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
    }
  }
</style>
