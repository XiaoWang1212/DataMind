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

    <!-- 隱藏 file inputs（由 useWorkflowImport 內部使用） -->
    <input
      ref="jsonFileInput"
      accept=".json,application/json"
      hidden
      type="file"
      @change="handleJsonFileChange"
    >
    <input
      ref="paperFileInput"
      accept=".pdf,.doc,.docx,.txt"
      hidden
      type="file"
      @change="handlePaperFileChange"
    >
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
                :drawer-stage="drawerStage"
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
                @continue-settings="handleContinueSettings"
                @open-upload="uploadDialogVisible = true"
                @remove-model="handleRemoveModel"
                @settings-step-change="step => { settingsStep = step }"
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
  import { useRoute } from 'vue-router'
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
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import IconNode from './IconNode.vue'
  import UploadDialog from './UploadDialog.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'

  const nodeTypes = { iconNode: markRaw(IconNode) }
  const route = useRoute()
  const projectId = computed(() => route.query.project as string | undefined)

  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const isInitializing = ref(true)
  const workflowDataFile = ref<File | null>(null)
  const uploadDialogVisible = ref(false)
  const availableModels = ref<string[]>([])
  const modelOptionsLoading = ref(false)
  const selectedNodeId = ref<string | null>(null)
  const settingsStep = ref(0)
  const nodeFlash = ref<Map<string, 'add' | 'remove'>>(new Map())

  function flashNode (nodeId: string, type: 'add' | 'remove', duration = 1200): void {
    nodeFlash.value = new Map(nodeFlash.value).set(nodeId, type)
    window.setTimeout(() => {
      const next = new Map(nodeFlash.value)
      next.delete(nodeId)
      nodeFlash.value = next
    }, duration)
  }

  // file input refs（需在 component 層宣告才能被 template ref binding 綁定）
  const jsonFileInput = ref<HTMLInputElement | null>(null)
  const paperFileInput = ref<HTMLInputElement | null>(null)
  const geminiFileInput = ref<HTMLInputElement | null>(null)

  // ─── composables ─────────────────────────────────────────────────────────

  const { style: drawerStyle, startDrag, reset: resetDrawer, expand: expandDrawer, stage: drawerStage } = useDrawerDrag()

  const { nodeStatuses, isDemoRunning, isDemoFinished, scheduleWorkflowSteps, finishGatedSteps, buildDemoSteps } = useWorkflowDemo()

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
  } = useWorkflowNodes(nodeStatuses, isDemoFinished, selectedNodeId, settingsStep, nodeFlash)

  function saveState (): void {
    saveWorkflowStateToStorage(toRaw(nodes.value), toRaw(edges.value), projectId.value, {
      nodeStatuses: Object.fromEntries(nodeStatuses.value),
      pausedAtNodeId: pausedAtNodeId.value,
      dataTableApplied: dataTableApplied.value,
      selectedNodeId: selectedNodeId.value,
      isDemoFinished: isDemoFinished.value,
      workflowResult: workflowResult.value,
      activeJobId: activeJobId.value,
    })
  }

  const {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    workflowSummary,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
  } = useWorkflowExecution({
    nodes,
    workflowDataFile,
    selectedTargetColumn,
    nodeStatuses,
    isDemoRunning,
    isDemoFinished,
    buildDemoSteps,
    scheduleWorkflowSteps,
    finishGatedSteps,
    selectedNodeId,
    expandDrawer,
    onProgress: pct => {
      if (projectId.value) projectStore.updateProjectProgress(projectId.value, pct)
    },
    onJobActive: jobId => {
      if (projectId.value) projectStore.pollProjectJob(projectId.value, jobId)
    },
  })

  const {
    workflowError: importError,
    loadJsonModels,
    handleJsonFileChange,
    handlePaperFileChange,
    handleGeminiFileChange,
  } = useWorkflowImport(nodes, edges, syncComputeCiNode, saveState, {
    jsonFileInput,
    paperFileInput,
    geminiFileInput,
  }, () => projectId.value)

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
    if (nodeId.startsWith('model-')) return
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
    saveWorkflowDataFileToStorage(file, projectId.value)
  }

  // 專案狀態：草稿建立後從未變動過，這裡讓它跟著 workflow 實際進度走
  function markProjectRunning (): void {
    if (!projectId.value) return
    const target = projectStore.projects.find(p => p.id === projectId.value)
    if (target && target.status !== 'running') {
      projectStore.updateProjectStatus(projectId.value, 'running')
    }
  }

  function handleApplyColumnConfig (): void {
    if (pausedAtNodeId.value !== 'dataTable') return
    dataTableApplied.value = true
    workflowError.value = null
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleContinueSettings (): void {
    markProjectRunning()
    continueWorkflow()
    closeMenu()
  }

  function handleAddModel (modelName: string): void {
    if (!modelName) return
    if (nodes.value.some(n => n.id.startsWith('model-') && n.data.config.modelName === modelName)) return
    const current = nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => ({ name: String(n.data.config.modelName ?? n.data.label ?? ''), type: 'Classification' }))
    const newModelId = `model-${current.length}`
    syncModelCanvasNodes([...current, { name: modelName, type: 'Classification' }])
    flashNode(newModelId, 'add')
  }

  function handleRemoveModel (modelName: string): void {
    if (!modelName) return
    const allModels = nodes.value.filter(n => n.id.startsWith('model-'))
    const removedNode = allModels.find(n => String(n.data.config.modelName ?? n.data.label ?? '') === modelName)
    const next = allModels
      .map(n => ({ name: String(n.data.config.modelName ?? n.data.label ?? ''), type: 'Classification' }))
      .filter(m => m.name !== modelName)
    if (removedNode) {
      flashNode(removedNode.id, 'remove')
      window.setTimeout(() => syncModelCanvasNodes(next), 450)
    } else {
      syncModelCanvasNodes(next)
    }
  }

  function columnConfigEqual (a: unknown, b: unknown): boolean {
    if (!Array.isArray(a) || !Array.isArray(b)) return a === b
    if (a.length !== b.length) return false
    return a.every((col, i) => {
      const cur = col as { name?: unknown, type?: unknown, role?: unknown }
      const other = b[i] as { name?: unknown, type?: unknown, role?: unknown } | undefined
      return other !== undefined
        && cur.name === other.name
        && cur.type === other.type
        && cur.role === other.role
    })
  }

  function handleUpdateConfig (payload: { nodeId: string, config: Record<string, ConfigValue> }): void {
    if (payload.nodeId === 'settings' && ('preprocessing' in payload.config || 'featureEngineering' in payload.config)) {
      const settingsNode = nodes.value.find(n => n.id === 'settings')

      let prevPreLen = 0
      if (Array.isArray(settingsNode?.data.config.preprocessing)) {
        prevPreLen = (settingsNode.data.config.preprocessing as unknown[]).length
      }
      let newPreLen = prevPreLen
      if (Array.isArray(payload.config.preprocessing)) {
        newPreLen = (payload.config.preprocessing as unknown[]).length
      }
      let prevFeLen = 0
      if (Array.isArray(settingsNode?.data.config.featureEngineering)) {
        prevFeLen = (settingsNode.data.config.featureEngineering as unknown[]).length
      }
      let newFeLen = prevFeLen
      if (Array.isArray(payload.config.featureEngineering)) {
        newFeLen = (payload.config.featureEngineering as unknown[]).length
      }

      let pipelineFlashId: string | null = null
      let pipelineFlashType: 'add' | 'remove' | null = null
      if (newPreLen !== prevPreLen) {
        pipelineFlashId = 'preprocessor'
        pipelineFlashType = newPreLen > prevPreLen ? 'add' : 'remove'
      } else if (newFeLen !== prevFeLen) {
        pipelineFlashId = 'featureEngineering'
        pipelineFlashType = newFeLen > prevFeLen ? 'add' : 'remove'
      }

      let needsDelay = false
      if (pipelineFlashType === 'remove' && nodes.value.some(n => n.id === pipelineFlashId)) {
        needsDelay = pipelineFlashId === 'preprocessor' ? newPreLen === 0 : newFeLen === 0
      }

      nodes.value = nodes.value.map(node => {
        if (node.id !== payload.nodeId) return node
        return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
      })
      if ('compute_ci' in payload.config) {
        syncComputeCiNode()
      }

      if (needsDelay && pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
        window.setTimeout(() => {
          syncPipelineCanvasNodes()
          saveState()
        }, 450)
        return
      }
      syncPipelineCanvasNodes()
      if (pipelineFlashId && pipelineFlashType) {
        flashNode(pipelineFlashId, pipelineFlashType)
      }
      saveState()
      return
    }

    const prevColumnConfig = payload.nodeId === 'dataTable' && 'columnConfig' in payload.config
      ? nodes.value.find(n => n.id === 'dataTable')?.data.config.columnConfig
      : undefined

    nodes.value = nodes.value.map(node => {
      if (node.id !== payload.nodeId) return node
      return { ...node, data: { ...node.data, config: { ...node.data.config, ...payload.config } } }
    })
    if (payload.nodeId === 'settings' && 'compute_ci' in payload.config) {
      syncComputeCiNode()
    }
    if (payload.nodeId === 'dataTable' && 'columnConfig' in payload.config) {
      // 只有真的改了（且原本已 Apply）才翻回旗標；面板重掛 emit 相同設定不算改動
      if (dataTableApplied.value && !columnConfigEqual(prevColumnConfig, payload.config.columnConfig)) {
        dataTableApplied.value = false
      }
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
    [nodes, edges, nodeStatuses, pausedAtNodeId, dataTableApplied, selectedNodeId, isDemoFinished, workflowResult, activeJobId],
    () => {
      if (isInitializing.value) {
        console.log('[WF-SAVE] 正在初始化中，跳過自動儲存，防止覆蓋')
        return
      }
      saveState()
    },
    { deep: true },
  )

  // workflow 真正跑出結果才算「已完成」；調整設定後重新執行會在 markProjectRunning() 退回「進行中」
  watch(workflowResult, val => {
    if (val && projectId.value) {
      projectStore.updateProjectStatus(projectId.value, 'completed')
    }
  })

  onMounted(async () => {
    try {
      if (projectId.value) {
        const target = projectStore.projects.find(p => p.id === projectId.value)
        if (target && target.status !== 'completed') markProjectRunning()
      }

      const ctx = projectStore.activeContext
      if (ctx) {
        projectStore.clearActiveContext()
        if (ctx.datasetFile) handleDataFile(ctx.datasetFile)
        if (ctx.frameworkId !== null) {
          const fw = frameworkStore.frameworks.find(f => f.id === ctx.frameworkId)
          if (fw?.workflowJson) {
            const jsonBlob = new File(
              [JSON.stringify(fw.workflowJson)],
              `${fw.title}.json`,
              { type: 'application/json' },
            )
            await loadJsonModels(jsonBlob)
          }
        }
        await nextTick()
        executeWorkflow()
      } else {
        const restoredState = loadWorkflowStateFromStorage(projectId.value)
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

          if (restoredState.nodeStatuses) {
            nodeStatuses.value = new Map(Object.entries(restoredState.nodeStatuses))
          }
          if (restoredState.pausedAtNodeId !== undefined) pausedAtNodeId.value = restoredState.pausedAtNodeId
          if (restoredState.dataTableApplied !== undefined) dataTableApplied.value = restoredState.dataTableApplied
          if (restoredState.selectedNodeId !== undefined) selectedNodeId.value = restoredState.selectedNodeId
          if (restoredState.isDemoFinished !== undefined) isDemoFinished.value = restoredState.isDemoFinished
          if (restoredState.workflowResult !== undefined) workflowResult.value = restoredState.workflowResult
          if (restoredState.activeJobId !== undefined) activeJobId.value = restoredState.activeJobId

          // model 訓練已經搬到後端背景 job 執行，刷新後用存下來的 job_id 接續輪詢即可恢復；
          // 只有在 job 真的找不到（例如後端重啟）時才退回最近一次「暫停等待使用者」的關卡，
          // 避免畫面卡在某個 model 的 loading 狀態動彈不得
          if (pausedAtNodeId.value === null && !isDemoFinished.value) {
            const resumeOutcome = await resumeJob()

            if (resumeOutcome === 'missing') {
              let checkpoint: 'settings' | 'dataTable' | null = null
              if (nodeStatuses.value.get('settings') === 'finished') checkpoint = 'settings'
              else if (nodeStatuses.value.get('dataTable') === 'finished') checkpoint = 'dataTable'

              if (checkpoint) {
                const keepIds = checkpoint === 'settings'
                  ? ['file', 'distribution', 'dataTable', 'settings']
                  : ['file', 'distribution', 'dataTable']
                const next = new Map(nodeStatuses.value)
                for (const id of next.keys()) {
                  if (!keepIds.includes(id)) next.delete(id)
                }
                nodeStatuses.value = next
                pausedAtNodeId.value = checkpoint
                selectedNodeId.value = checkpoint
                workflowError.value = '偵測到上次的執行因刷新而中斷，請重新按「繼續」。'
              }
            }
          }

          if (selectedNodeId.value) expandDrawer()
          console.log('[WF-INIT] 成功從儲存還原 nodes & edges 與執行狀態')
        } else {
          const restoredJsonFile = await loadWorkflowJsonFileFromStorage(projectId.value)
          if (restoredJsonFile) await loadJsonModels(restoredJsonFile)
        }

        const restoredDataFile = await loadWorkflowDataFileFromStorage(projectId.value)
        if (restoredDataFile) {
          workflowDataFile.value = restoredDataFile
          updateFileNodeConfig(restoredDataFile.name)
        }
      }

      await loadAvailableModels()
      await nextTick()
    } catch (error) {
      console.error('[WF-INIT] 初始化過程出錯:', error)
    } finally {
      isInitializing.value = false
      // 初始化期間的狀態變化（例如新建專案時 executeWorkflow() 設定的暫停狀態）
      // 因為鎖住自動儲存而從未被存下，這裡強制存一次基準狀態，避免之後刷新頁面時無資料可還原
      saveState()
      console.log('[WF-INIT] 初始化完成，自動儲存鎖已解開，並已存下基準狀態')
    }
  })

  // 瀏覽器刷新／關閉頁籤時 Vue 的 onBeforeUnmount 不會被觸發，
  // 必須額外監聽 pagehide 才能確保最新狀態在頁面卸載前被寫入 localStorage
  function handlePageHide (): void {
    saveState()
  }

  window.addEventListener('pagehide', handlePageHide)

  // 離開頁面時不能再呼叫 resetDemo() 清空 nodeStatuses：onBeforeUnmount 執行的當下，
  // 元件的 watch 還沒被 Vue 停掉，清空動作可能被該 watch 偵測到並把「清空後」的狀態存進
  // localStorage，導致下次打開專案時整個 workflow 看起來被清掉
  onBeforeUnmount(() => {
    window.removeEventListener('pagehide', handlePageHide)
    saveState()
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
    /* 安全上限：實際高度由 useDrawerDrag 精確控制各段大小，
       這裡固定用 full 段（90vh）當唯一上限，避免用分段 class
       卡高度時，收合到比自己上限還小的段落會被瞬間夾住而不是平滑動畫 */
    max-height: 90vh;
  }

  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    /* 永遠保留捲軸空間（兩側等寬），避免捲軸出現/消失時內容寬度跳動、且左右留白對稱 */
    scrollbar-gutter: stable both-edges;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .drawer-content-wrapper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
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
