<template>
  <!-- Workflow 主容器：上方畫布 + 下方可滑出的設定抽屜 -->
  <section class="workspace">
    <!-- 畫布區：顯示節點與連線 -->
    <WorkflowCanvas
      class="workspace-canvas"
      :edges="canvasEdges"
      :node-types="nodeTypes"
      :nodes="canvasNodes"
      @pane-click="closeMenu"
      @select-node="handleSelectNode"
    />

    <div
      v-if="uploadDialogVisible"
      class="upload-dialog-backdrop"
      @click.self="closeUploadDialog"
    >
      <div class="upload-dialog-card">
        <div class="upload-dialog-header">
          <div>
            <button
              class="upload-dialog-close"
              type="button"
              @click="closeUploadDialog"
            >
              ×
            </button>
            <h3>上傳模型檔案</h3>
            <p>將檔案拖曳到此處，或點擊瀏覽選擇模型檔案。</p>
          </div>
        </div>

        <div
          class="upload-dropzone"
          :class="{ 'upload-dropzone--active': dragActive }"
          @dragenter.prevent="handleDragEnter"
          @dragleave.prevent="handleDragLeave"
          @dragover.prevent
          @drop.prevent="handleDrop"
        >
          <div class="upload-dropzone__icon">⇪</div>
          <div class="upload-dropzone__text">Drop files here!</div>
          <label class="upload-dropzone__browse">
            瀏覽
            <input
              accept=".csv,.xlsx,.model"
              hidden
              type="file"
              @change="handleFileChange"
            >
          </label>
          <div v-if="selectedUploadFile" class="upload-dropzone__file">
            已選檔案：{{ selectedUploadFile.name }}
          </div>
        </div>

        <div class="upload-dialog-actions">
          <button
            class="btn btn-secondary"
            type="button"
            @click="closeUploadDialog"
          >
            取消
          </button>
          <button
            class="btn btn-primary"
            :disabled="!selectedUploadFile"
            type="button"
            @click="confirmUpload"
          >
            上傳
          </button>
        </div>
      </div>
    </div>

    <!-- Demo 執行按鈕 -->
    <button
      class="demo-btn"
      :class="{ 'demo-btn--running': isDemoRunning }"
      :disabled="isDemoRunning"
      @click="startDemo"
    >
      {{ isDemoRunning ? "⏳" : "▶" }}
    </button>

    <!-- 下方抽屜：只有選到節點時才出現 -->
    <Transition name="slide-up">
      <div
        v-if="selectedNode"
        class="options-drawer"
        :class="{ 'options-drawer--expanded': isExpanded }"
        :style="drawerStyle"
      >
        <!-- 拖曳區：上拉展開、下拉三段式操作 -->
        <div
          aria-hidden="true"
          class="options-drawer__drag-zone"
          @mousedown.prevent="startDrag"
          @touchstart.prevent="startDrag"
        >
          <div class="options-drawer__bar" />
        </div>

        <!-- 設定內容區（可滾動） -->
        <div class="options-drawer__scroll">
          <WorkflowOptionsPanel
            :selected-node="selectedNode"
            @open-upload="openUploadDialog"
            @update-config="handleUpdateConfig"
          />
        </div>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
  import type { Edge } from '@vue-flow/core'
  import type {
    ConfigValue,
    EdgeBase,
    FlowNode,
    SimpleNode,
  } from '@/types/workflow'
  import { computed, markRaw, onBeforeUnmount, ref } from 'vue'
  import { useDrawerDrag } from '@/composables/useDrawerDrag'
  import {
    DEMO_FINISH_LINGER,
    DEMO_STEPS,
    INITIAL_EDGES,
    INITIAL_NODES,
    NODE_RUN_DURATION,
  } from '@/constants/workflowData'
  import IconNode from './IconNode.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'

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

  const uploadDialogVisible = ref(false)
  const selectedUploadFile = ref<File | null>(null)
  const dragActive = ref(false)

  // 預設不選任何節點，點擊後才顯示下方 options
  const selectedNodeId = ref<string | null>(null)

  // 抽屜拖曳邏輯（封裝在 composable）
  const {
    isExpanded,
    style: drawerStyle,
    startDrag,
    reset: resetDrawer,
  } = useDrawerDrag()

  // 目前被選取的節點（傳給 OptionsPanel）
  const selectedNode = computed<SimpleNode | null>(() => {
    if (!selectedNodeId.value) return null
    const node = nodes.value.find(item => item.id === selectedNodeId.value)
    return node ? { id: node.id, data: node.data } : null
  })

  // 節點顏色：完成的節點改成黃色，其餘依 data.colorClass
  const canvasNodes = computed<FlowNode[]>(() =>
    nodes.value.map(node => {
      const status = nodeStatuses.value.get(node.id) ?? null
      return {
        ...node,
        class: '',
        data: {
          ...node.data,
          status,
          // 只有 finished 才變黃，running 保持原色（只顯示 spinner）
          colorClass:
            status === 'finished' ? 'node-yellow' : node.data.colorClass,
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
        style: done
          ? { stroke: '#F0E274', strokeWidth: 2 }
          : { stroke: '#d9d9d9', strokeWidth: 1.5 },
      }
    }),
  )

  // 重置 demo 全部狀態並清除所有計時器
  function resetDemo (): void {
    nodeStatuses.value = new Map()
    isDemoRunning.value = false
    isDemoFinished.value = false
    for (const timer of demoTimers) {
      clearTimeout(timer)
    }
    demoTimers.length = 0
  }

  // 演示執行：依照 workflow 順序逐步點亮節點
  function startDemo (): void {
    if (isDemoRunning.value) return

    resetDemo()
    isDemoRunning.value = true

    for (const { nodeIds, delay } of DEMO_STEPS) {
      // 先設為 running：顯示 spinner
      demoTimers.push(
        setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'running')
          nodeStatuses.value = next
        }, delay),
        setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'finished')
          nodeStatuses.value = next
        }, delay + NODE_RUN_DURATION),
      )
    }

    // 全部節點完成後再等 DEMO_FINISH_LINGER，才停止動畫
    const lastStepDelay = Math.max(...DEMO_STEPS.map(s => s.delay))
    const endTime = lastStepDelay + NODE_RUN_DURATION + DEMO_FINISH_LINGER
    demoTimers.push(
      setTimeout(() => {
        isDemoRunning.value = false
        isDemoFinished.value = true
      }, endTime),
    )
  }

  // 節點點擊：更新目前選擇的 node
  function handleSelectNode (nodeId: string): void {
    if (selectedNodeId.value === nodeId) {
      closeMenu()
      return
    }
    selectedNodeId.value = nodeId
    resetDrawer()

    if (nodeId.startsWith('model')) {
      openUploadDialog()
    }
  }

  function openUploadDialog (): void {
    uploadDialogVisible.value = true
    selectedUploadFile.value = null
    dragActive.value = false
  }

  function closeUploadDialog (): void {
    uploadDialogVisible.value = false
    selectedUploadFile.value = null
    dragActive.value = false
  }

  function handleFileChange (event: Event): void {
    const target = event.target as HTMLInputElement
    selectedUploadFile.value = target.files?.[0] ?? null
  }

  function handleDrop (event: DragEvent): void {
    event.preventDefault()
    dragActive.value = false
    const files = event.dataTransfer?.files
    if (files && files.length > 0) {
      selectedUploadFile.value = files.item(0) ?? null
    }
  }

  function handleDragEnter (): void {
    dragActive.value = true
  }

  function handleDragLeave (): void {
    dragActive.value = false
  }

  function confirmUpload (): void {
    if (!selectedNodeId.value || !selectedUploadFile.value) return
    nodes.value = nodes.value.map(node => {
      if (node.id !== selectedNodeId.value) return node
      return {
        ...node,
        data: {
          ...node.data,
          config: {
            ...node.data.config,
            fileName: selectedUploadFile.value!.name,
          },
        },
      }
    })
    closeUploadDialog()
  }

  // 點空白區可收起 menu
  function closeMenu (): void {
    selectedNodeId.value = null
    resetDrawer()
  }

  // 面板儲存：只更新對應 node 的 config
  function handleUpdateConfig (payload: {
    nodeId: string
    config: Record<string, ConfigValue>
  }): void {
    nodes.value = nodes.value.map(node => {
      if (node.id !== payload.nodeId) return node
      return {
        ...node,
        data: {
          ...node.data,
          config: { ...node.data.config, ...payload.config },
        },
      }
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
    background-image: radial-gradient(
      rgba(0, 93, 255, 0.035) 0.8px,
      transparent 0.8px
    );
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
    color: #005dff;
    cursor: pointer;
    transition:
      background 0.15s,
      opacity 0.15s;
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

  .upload-dialog-backdrop {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(8px);
  }

  .upload-dialog-card {
    width: min(560px, calc(100% - 32px));
    border-radius: 20px;
    background: #ffffff;
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .upload-dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .upload-dialog-close {
    border: none;
    background: rgba(243, 244, 246, 0.9);
    width: 36px;
    height: 36px;
    border-radius: 999px;
    color: #1f2937;
    font-size: 18px;
    cursor: pointer;
  }

  .upload-dialog-card h3 {
    margin: 0;
    font-size: 20px;
  }

  .upload-dialog-card p {
    margin: 6px 0 0;
    color: #475569;
    font-size: 14px;
    line-height: 1.6;
  }

  .upload-dropzone {
    min-height: 210px;
    padding: 28px 20px;
    border: 2px dashed rgba(148, 163, 184, 0.8);
    border-radius: 18px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: rgba(236, 246, 255, 0.68);
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.12);
  }

  .upload-dropzone__icon {
    font-size: 28px;
    color: #2563eb;
  }

  .upload-dropzone__text {
    font-size: 18px;
    color: #1f2937;
    font-weight: 600;
  }

  .upload-dropzone__browse {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 22px;
    border-radius: 999px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-dropzone__file {
    font-size: 13px;
    color: #475569;
  }

  .upload-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
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
    transition:
      transform 0.22s ease,
      opacity 0.22s ease;
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
