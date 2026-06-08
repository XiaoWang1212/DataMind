<template>
  <!-- Workflow 主容器：上方畫布 + 下方可滑出的設定抽屜 -->
  <section class="workspace">
    <!-- 畫布區：顯示節點與連線 -->
    <WorkflowCanvas
      :canvas-min-height="canvasMinHeight"
      :canvas-min-width="canvasMinWidth"
      class="workspace-canvas"
      :edges="canvasEdges"
      :node-types="nodeTypes"
      :nodes="canvasNodes"
      @pane-click="closeMenu"
      @select-node="handleSelectNode"
    />

    <!-- 上傳 model 檔案 dialog -->
    <UploadDialog
      :visible="uploadDialogVisible"
      @close="uploadDialogVisible = false"
      @confirm="confirmUpload"
    />

    <!-- 工具列按鈕 -->
    <button
      class="demo-btn execute-workflow-btn"
      :disabled="
        (pausedAtNodeId === 'dataTable' && !dataTableCanContinue)
          || (pausedAtNodeId === 'settings' && !settingsCanContinue)
      "
      type="button"
      @click="
        pausedAtNodeId === 'dataTable' || pausedAtNodeId === 'settings'
          ? continueWorkflow()
          : executeWorkflow()
      "
    >
      {{ pausedAtNodeId === "dataTable" || pausedAtNodeId === "settings" ? "繼續 Workflow" : "執行 Workflow" }}
    </button>

    <button
      class="demo-btn json-upload-btn"
      type="button"
      @click="triggerJsonUpload"
    >
      上傳 JSON
    </button>
    <input
      ref="jsonFileInput"
      accept=".json,application/json"
      hidden
      type="file"
      @change="handleJsonFileChange"
    >

    <button
      class="demo-btn paper-upload-btn"
      :disabled="paperUploading"
      type="button"
      @click="triggerPaperUpload"
    >
      {{ paperUploading ? "上傳中..." : "上傳論文" }}
    </button>
    <input
      ref="paperFileInput"
      accept=".pdf,.doc,.docx,.txt"
      hidden
      type="file"
      @change="handlePaperFileChange"
    >

    <button
      class="demo-btn gemini-upload-btn"
      :disabled="geminiUploading"
      type="button"
      @click="triggerGeminiUpload"
    >
      {{ geminiUploading ? "AI 分析中..." : "AI 生成 Workflow" }}
    </button>
    <input
      ref="geminiFileInput"
      accept=".pdf,application/pdf"
      hidden
      type="file"
      @change="handleGeminiFileChange"
    >

    <div v-if="workflowError || importError" class="workflow-result">
      <div class="workflow-error">{{ workflowError || importError }}</div>
    </div>

    <!-- 下方抽屜：只有選到節點時才出現 -->
    <Transition name="slide-up">
      <div
        v-if="selectedNode"
        class="options-drawer"
        :class="{ 'options-drawer--expanded': isExpanded }"
        :style="drawerStyle"
        @wheel.stop
      >
        <div
          aria-hidden="true"
          class="options-drawer__drag-zone"
          @mousedown.prevent="startDrag"
          @touchstart.prevent="startDrag"
        >
          <div class="options-drawer__bar" />
        </div>

        <div class="options-drawer__scroll">
          <Transition mode="out-in" name="drawer-content">
            <div
              :key="selectedNode?.id ?? 'no-node'"
              class="drawer-content-wrapper"
            >
              <WorkflowOptionsPanel
                :available-models="availableModelOptions"
                :file="workflowDataFile"
                :model-options-loading="modelOptionsLoading"
                :paused-node-id="pausedAtNodeId"
                :selected-node="selectedNode"
                :used-model-names="usedModelNames"
                :workflow-file-name="workflowDataFile?.name"
                :workflow-result="workflowResult"
                :workflow-summary="workflowSummary"
                @add-model="handleAddModel"
                @apply-column-config="handleApplyColumnConfig"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @update-config="handleUpdateConfig"
                @update:file="handleDataFile"
              />
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </section>
</template>

<script setup lang="ts">
  import type { ConfigValue } from '@/types/workflow'
  import {
    computed,
    markRaw,
    nextTick,
    onBeforeUnmount,
    onMounted,
    ref,
    toRaw,
    watch,
  } from 'vue'
  import { fetchAvailableModels } from '@/api/workflow'
  import { useDrawerDrag } from '@/composables/useDrawerDrag'
  import { useWorkflowDemo } from '@/composables/workflow/useWorkflowDemo.ts'
  import { useWorkflowExecution } from '@/composables/workflow/useWorkflowExecution.ts'
  import { useWorkflowImport } from '@/composables/workflow/useWorkflowImport.ts'
  import { useWorkflowNodes } from '@/composables/workflow/useWorkflowNodes.ts'
  import {
    loadWorkflowDataFileFromStorage,
    loadWorkflowJsonFileFromStorage,
    loadWorkflowStateFromStorage,
    saveWorkflowDataFileToStorage,
    saveWorkflowStateToStorage,
  } from '@/composables/workflow/useWorkflowStorage.ts'
  import { INITIAL_EDGES, INITIAL_NODES } from '@/constants/workflowData'
  import IconNode from './IconNode.vue'
  import UploadDialog from './UploadDialog.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'

  const nodeTypes = { iconNode: markRaw(IconNode) }

  const isInitializing = ref(true)
  const workflowDataFile = ref<File | null>(null)
  const uploadDialogVisible = ref(false)
  const availableModels = ref<string[]>([])
  const modelOptionsLoading = ref(false)
  const selectedNodeId = ref<string | null>(null)

  // file input refs（需在 component 層宣告才能被 template ref binding 綁定）
  const jsonFileInput = ref<HTMLInputElement | null>(null)
  const paperFileInput = ref<HTMLInputElement | null>(null)
  const geminiFileInput = ref<HTMLInputElement | null>(null)

  // ─── composables ─────────────────────────────────────────────────────────

  const { isExpanded, style: drawerStyle, startDrag, reset: resetDrawer, expand: expandDrawer } = useDrawerDrag()

  const { nodeStatuses, isDemoRunning, isDemoFinished, resetDemo, scheduleWorkflowSteps, scheduleGatedStart, finishGatedSteps, buildDemoSteps } = useWorkflowDemo()

  const {
    nodes,
    edges,
    canvasNodes,
    canvasEdges,
    canvasMinHeight,
    canvasMinWidth,
    selectedTargetColumn,
    usedModelNames,
    updateFileNodeConfig,
    syncModelCanvasNodes,
    syncPipelineCanvasNodes,
    syncComputeCiNode,
    ensureDynamicNodes,
  } = useWorkflowNodes(nodeStatuses, isDemoFinished)

  function saveState (): void {
    saveWorkflowStateToStorage(toRaw(nodes.value), toRaw(edges.value))
  }

  const {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    dataTableCanContinue,
    settingsCanContinue,
    workflowSummary,
    executeWorkflow,
    continueWorkflow,
  } = useWorkflowExecution({
    nodes,
    workflowDataFile,
    selectedTargetColumn,
    nodeStatuses,
    isDemoRunning,
    buildDemoSteps,
    scheduleWorkflowSteps,
    scheduleGatedStart,
    finishGatedSteps,
    selectedNodeId,
    expandDrawer,
  })

  const {
    paperUploading,
    geminiUploading,
    workflowError: importError,
    loadJsonModels,
    triggerJsonUpload,
    handleJsonFileChange,
    triggerPaperUpload,
    handlePaperFileChange,
    triggerGeminiUpload,
    handleGeminiFileChange,
  } = useWorkflowImport(nodes, edges, syncComputeCiNode, saveState, {
    jsonFileInput,
    paperFileInput,
    geminiFileInput,
  })

  // ─── computed ─────────────────────────────────────────────────────────────

  const selectedNode = computed(() => {
    if (!selectedNodeId.value) return null
    const node = nodes.value.find(n => n.id === selectedNodeId.value)
    return node ? { id: node.id, data: node.data } : null
  })

  const availableModelOptions = computed<string[]>(() =>
    availableModels.value.filter(name => !usedModelNames.value.includes(name)),
  )

  // ─── handlers ────────────────────────────────────────────────────────────

  function handleSelectNode (nodeId: string): void {
    if (selectedNodeId.value === nodeId) {
      closeMenu()
      return
    }
    selectedNodeId.value = nodeId
    expandDrawer()
  }

  function closeMenu (): void {
    selectedNodeId.value = null
    resetDrawer()
  }

  function handleDataFile (file: File): void {
    workflowDataFile.value = file
    workflowError.value = null
    updateFileNodeConfig(file.name)
    saveWorkflowDataFileToStorage(file)
  }

  function handleApplyColumnConfig (): void {
    dataTableApplied.value = true
    workflowError.value = null
  }

  function handleAddModel (modelName: string): void {
    if (!modelName) return
    if (nodes.value.some(n => n.id.startsWith('model-') && n.data.config.modelName === modelName)) return
    const current = nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => ({ name: String(n.data.config.modelName ?? n.data.label ?? ''), type: 'Classification' }))
    syncModelCanvasNodes([...current, { name: modelName, type: 'Classification' }])
  }

  function handleRemoveModel (modelName: string): void {
    if (!modelName) return
    const current = nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => ({ name: String(n.data.config.modelName ?? n.data.label ?? ''), type: 'Classification' }))
      .filter(m => m.name !== modelName)
    syncModelCanvasNodes(current)
  }

  function handleUpdateConfig (payload: { nodeId: string, config: Record<string, ConfigValue> }): void {
    nodes.value = nodes.value.map(node => {
      if (node.id !== payload.nodeId) return node
      return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
    })

    if (payload.nodeId === 'settings') {
      if ('preprocessing' in payload.config || 'featureEngineering' in payload.config) syncPipelineCanvasNodes()
      if ('compute_ci' in payload.config) syncComputeCiNode()
    }

    saveState()
  }

  function confirmUpload (file: File): void {
    if (!selectedNodeId.value) return
    nodes.value = nodes.value.map(node => {
      if (node.id !== selectedNodeId.value) return node
      return { ...node, data: { ...node.data, config: { ...node.data.config, fileName: file.name } } }
    })
    uploadDialogVisible.value = false
  }

  async function loadAvailableModels (): Promise<void> {
    modelOptionsLoading.value = true
    try {
      availableModels.value = await fetchAvailableModels()
    } catch {
      availableModels.value = []
    } finally {
      modelOptionsLoading.value = false
    }
  }

  // ─── lifecycle ───────────────────────────────────────────────────────────

  watch(
    [nodes, edges],
    () => {
      if (isInitializing.value) {
        console.log('[WF-SAVE] 正在初始化中，跳過自動儲存，防止覆蓋')
        return
      }
      saveState()
    },
    { deep: true },
  )

  onMounted(async () => {
    try {
      const restoredState = loadWorkflowStateFromStorage()
      if (restoredState && restoredState.nodes?.length > 0) {
        nodes.value = restoredState.nodes
        edges.value = restoredState.edges
        for (const initNode of INITIAL_NODES) {
          if (!nodes.value.some(n => n.id === initNode.id)) nodes.value = [...nodes.value, initNode]
        }
        for (const initEdge of INITIAL_EDGES) {
          if (!edges.value.some(e => e.id === initEdge.id)) edges.value = [...edges.value, initEdge]
        }
        ensureDynamicNodes()
        syncComputeCiNode()
        console.log('[WF-INIT] 成功從儲存還原 nodes & edges')
      } else {
        const restoredJsonFile = await loadWorkflowJsonFileFromStorage()
        if (restoredJsonFile) await loadJsonModels(restoredJsonFile)
      }

      const restoredDataFile = await loadWorkflowDataFileFromStorage()
      if (restoredDataFile) {
        workflowDataFile.value = restoredDataFile
        updateFileNodeConfig(restoredDataFile.name)
      }

      await loadAvailableModels()
      await nextTick()
    } catch (error) {
      console.error('[WF-INIT] 初始化過程出錯:', error)
    } finally {
      isInitializing.value = false
      console.log('[WF-INIT] 初始化完成，自動儲存鎖已解開')
    }
  })

  onBeforeUnmount(() => {
    saveState()
    resetDemo()
  })
</script>

<style scoped>
  .workspace {
    position: relative;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: auto;
    border-radius: 16px 16px 0 0;
    background-color: #f9fbff;
    background-image: radial-gradient(rgba(0, 93, 255, 0.035) 0.8px, transparent 0.8px);
    background-size: 16px 16px;
  }

  .workspace-canvas {
    flex: 1;
    min-height: 520px;
    width: 100%;
  }

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
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0;
  }

  .demo-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .demo-btn:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .execute-workflow-btn {
    position: absolute;
    top: 14px;
    right: 120px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .json-upload-btn {
    position: absolute;
    top: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .json-upload-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }

  .paper-upload-btn {
    position: absolute;
    top: 14px;
    right: 230px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .paper-upload-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .gemini-upload-btn {
    position: absolute;
    top: 14px;
    right: 340px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 130px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(99, 102, 241, 0.3);
    background: rgba(238, 242, 255, 0.85);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #4f46e5;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .gemini-upload-btn:hover:not(:disabled) {
    background: rgba(224, 231, 255, 0.95);
  }

  .gemini-upload-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .workflow-result {
    position: absolute;
    top: 62px;
    right: 14px;
    z-index: 5;
    width: min(430px, calc(100% - 32px));
    max-height: 500px;
    overflow: auto;
    padding: 16px;
    background: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.32);
    border-radius: 16px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
    color: #0f172a;
  }

  .workflow-error {
    margin-bottom: 10px;
    color: #b91c1c;
    font-size: 13px;
    font-weight: 600;
  }

  .options-drawer {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.45);
    background: rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(16px);
    box-shadow: 0 -8px 18px rgba(15, 23, 42, 0.05);
    will-change: height, transform;
    transition: height 260ms cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
  }

  .options-drawer--expanded {
    max-height: 54vh;
  }

  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar {
    width: 8px;
    height: 8px;
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.72);
    border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(6px);
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.85);
  }

  .options-drawer__bar {
    width: 52px;
    height: 5px;
    border-radius: 999px;
    background: rgba(0, 93, 255, 0.26);
    margin: 0 auto;
    cursor: grab;
  }

  .options-drawer__bar:active {
    cursor: grabbing;
  }

  .options-drawer__drag-zone {
    padding: 12px 0 0;
    cursor: grab;
    touch-action: none;
  }

  .options-drawer__drag-zone:active {
    cursor: grabbing;
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

  .drawer-content-enter-active,
  .drawer-content-leave-active {
    transition: opacity 180ms ease, transform 180ms ease;
  }

  .drawer-content-enter-from,
  .drawer-content-leave-to {
    opacity: 0;
    transform: translateY(8px);
  }

  .drawer-content-enter-to,
  .drawer-content-leave-from {
    opacity: 1;
    transform: translateY(0);
  }
</style>
