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

    <div v-if="workflowError" class="workflow-result">
      <div class="workflow-error">{{ workflowError }}</div>
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
                @open-upload="openUploadDialog"
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
  import type {
    ConfigValue,
    EdgeBase,
    FlowNode,
    SimpleNode,
  } from '@/types/workflow'
  import { type Edge, Position } from '@vue-flow/core'
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
  import { analyzeWorkflowFromPdf } from '@/api/gemini'
  import { executeWorkflowApi, fetchAvailableModels } from '@/api/workflow'
  import { useDrawerDrag } from '@/composables/useDrawerDrag'
  import {
    DEMO_FINISH_LINGER,
    INITIAL_EDGES,
    INITIAL_NODES,
    NODE_RUN_DURATION,
  } from '@/constants/workflowData'
  import IconNode from './IconNode.vue'
  import WorkflowCanvas from './WorkflowCanvas.vue'
  import WorkflowOptionsPanel from './WorkflowOptionsPanel.vue'

  type ColumnType = 'numeric' | 'categorial' | 'text' | 'datetime'
  type ColumnRole = 'feature' | 'target' | 'meta' | 'skip'

  interface ColumnConfig {
    name: string
    type: ColumnType
    role: ColumnRole
  }

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
  const jsonFileInput = ref<HTMLInputElement | null>(null)
  const selectedJsonFile = ref<File | null>(null)
  const paperFileInput = ref<HTMLInputElement | null>(null)
  const geminiFileInput = ref<HTMLInputElement | null>(null)
  const paperUploading = ref(false)
  const geminiUploading = ref(false)
  const availableModels = ref<string[]>([])
  const modelOptionsLoading = ref(false)

  // n8n webhook 路徑（analyze-paper workflow）
  const N8N_PAPER_WEBHOOK_URL
    = (import.meta.env.VITE_N8N_PAPER_WEBHOOK_URL as string | undefined)
      ?? 'https://ideally-strewn-papyrus.ngrok-free.dev/webhook-test/analyze-paper'

  const workflowDataFile = ref<File | null>(null)
  const workflowResult = ref<null | Record<string, unknown>>(null)
  const workflowError = ref<string | null>(null)
  const pausedAtNodeId = ref<string | null>(null)
  const dataTableApplied = ref(false)
  const isInitializing = ref(true)

  const WORKFLOW_DATA_FILE_STORAGE_KEY = 'workflowDataFile'
  const WORKFLOW_JSON_FILE_STORAGE_KEY = 'workflowJsonFile'
  const WORKFLOW_STATE_STORAGE_KEY = 'workflowState'

  function arrayBufferToBase64 (buffer: ArrayBuffer): string {
    let binary = ''
    const bytes = new Uint8Array(buffer)
    for (let i = 0; i < bytes.byteLength; i += 1) {
      const byte = bytes[i]!
      binary += String.fromCodePoint(byte)
    }
    return btoa(binary)
  }

  function base64ToUint8Array (base64: string): Uint8Array {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.codePointAt(i) ?? 0
    }
    return bytes
  }

  async function saveWorkflowDataFileToStorage (
    file: File | null,
  ): Promise<void> {
    if (!file) {
      localStorage.removeItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
      return
    }

    try {
      const buffer = await file.arrayBuffer()
      const payload = {
        name: file.name,
        type: file.type || 'text/csv',
        contentBase64: arrayBufferToBase64(buffer),
      }
      localStorage.setItem(
        WORKFLOW_DATA_FILE_STORAGE_KEY,
        JSON.stringify(payload),
      )
    } catch (error) {
      console.warn('Unable to persist workflow file to localStorage', error)
    }
  }

  async function loadWorkflowDataFileFromStorage (): Promise<File | null> {
    const raw = localStorage.getItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
    if (!raw) return null

    try {
      const parsed = JSON.parse(raw) as {
        name: string
        type: string
        contentBase64: string
      }
      const bytes = base64ToUint8Array(parsed.contentBase64)
      return new File([bytes.buffer as ArrayBuffer], parsed.name, {
        type: parsed.type,
      })
    } catch (error) {
      console.warn('Unable to restore workflow file from localStorage', error)
      localStorage.removeItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
      return null
    }
  }

  async function saveWorkflowJsonFileToStorage (
    file: File | null,
  ): Promise<void> {
    if (!file) {
      localStorage.removeItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
      return
    }

    try {
      const text = await file.text()
      const payload = {
        name: file.name,
        type: file.type || 'application/json',
        text,
      }
      localStorage.setItem(
        WORKFLOW_JSON_FILE_STORAGE_KEY,
        JSON.stringify(payload),
      )
    } catch (error) {
      console.warn('Unable to persist workflow JSON to localStorage', error)
    }
  }

  async function loadWorkflowJsonFileFromStorage (): Promise<File | null> {
    const raw = localStorage.getItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
    if (!raw) return null

    try {
      const parsed = JSON.parse(raw) as {
        name: string
        type: string
        text: string
      }
      return new File([parsed.text], parsed.name, { type: parsed.type })
    } catch (error) {
      console.warn('Unable to restore workflow JSON from localStorage', error)
      localStorage.removeItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
      return null
    }
  }

  function saveWorkflowStateToStorage (): void {
    try {
      const rawNodes = toRaw(nodes.value)
      const rawEdges = toRaw(edges.value)
      const payload = JSON.stringify({ nodes: rawNodes, edges: rawEdges })
      localStorage.setItem(WORKFLOW_STATE_STORAGE_KEY, payload)
      console.log('[WF-SAVE] saved', rawNodes.length, 'nodes,', rawEdges.length, 'edges, caller:', new Error('trace').stack?.split('\n')[2]?.trim())
    } catch (error) {
      console.error('[WF-SAVE] FAILED:', error)
    }
  }

  function loadWorkflowStateFromStorage (): {
    nodes: FlowNode[]
    edges: EdgeBase[]
  } | null {
    const raw = localStorage.getItem(WORKFLOW_STATE_STORAGE_KEY)
    console.log('[WF-LOAD] localStorage raw length:', raw?.length ?? 'null (nothing saved)')
    if (!raw) return null

    try {
      const parsed = JSON.parse(raw) as {
        nodes: FlowNode[]
        edges: EdgeBase[]
      }
      console.log('[WF-LOAD] parsed', parsed.nodes?.length, 'nodes,', parsed.edges?.length, 'edges')
      return parsed
    } catch (error) {
      console.error('[WF-LOAD] JSON.parse FAILED:', error)
      localStorage.removeItem(WORKFLOW_STATE_STORAGE_KEY)
      return null
    }
  }

  function updateFileNodeConfig (fileName: string | null): void {
    nodes.value = nodes.value.map(node => {
      if (node.id !== 'file') return node
      return {
        ...node,
        data: {
          ...node.data,
          config: {
            ...node.data.config,
            fileName,
          },
        },
      }
    })
  }

  const dataTableColumnConfig = computed(() => {
    const node = nodes.value.find(node => node.id === 'dataTable')
    if (!node) return [] as Array<{ name: string, type: string, role: string }>
    const config = node.data.config.columnConfig
    return Array.isArray(config)
      ? (config as Array<{ name: string, type: string, role: string }>)
      : []
  })

  const selectedTargetColumn = computed(() =>
    dataTableColumnConfig.value.find(column => column.role === 'target'),
  )

  const dataTableCanContinue = computed(
    () =>
      pausedAtNodeId.value === 'dataTable'
      && dataTableApplied.value
      && selectedTargetColumn.value !== undefined,
  )

  const settingsCanContinue = computed(
    () =>
      pausedAtNodeId.value === 'settings'
      && nodes.value.some(n => n.id.startsWith('model-')),
  )

  async function loadAvailableModels (): Promise<void> {
    modelOptionsLoading.value = true
    try {
      availableModels.value = await fetchAvailableModels()
    } catch (error) {
      console.warn('Unable to load available models', error)
      availableModels.value = []
    } finally {
      modelOptionsLoading.value = false
    }
  }

  watch(
    [nodes, edges],
    () => {
      if (isInitializing.value) {
        console.log('[WF-SAVE] 正在初始化中，跳過自動儲存，防止覆蓋')
        return
      }
      saveWorkflowStateToStorage()
    },
    { deep: true },
  )

  const DYNAMIC_NODE_IDS = ['preprocessor', 'featureEngineering'] as const
  const RESULT_NODE_IDS = ['featureImportance', 'confusionMatrix', 'computeCi'] as const
  const MODEL_Y_GAP = 110

  // 回傳 model 節點前最後一個節點的 id（featureEngineering → preprocessor → settings）
  function getLastPreModelNodeId (): string {
    if (nodes.value.some(n => n.id === 'featureEngineering')) return 'featureEngineering'
    if (nodes.value.some(n => n.id === 'preprocessor')) return 'preprocessor'
    return 'settings'
  }

  // 以 modelList 為準重建畫布上的 model 節點與相關 edges
  function syncModelCanvasNodes (modelList: Array<unknown>): void {
    const preDynCount = (DYNAMIC_NODE_IDS as readonly string[]).filter(id =>
      nodes.value.some(n => n.id === id),
    ).length
    const modelX = 460 + preDynCount * 200
    const testScoreX = modelX + 200
    const resultX = testScoreX + 200

    const newModelNodes: FlowNode[] = modelList.map((m, i) => {
      const name = typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? '')
      const purposeZh = typeof m === 'object' && m !== null
        ? String((m as Record<string, unknown>).purpose_zh ?? '')
        : ''
      const startY = 290 - ((modelList.length - 1) * MODEL_Y_GAP) / 2
      return {
        id: `model-${i}`,
        type: 'iconNode',
        position: { x: modelX, y: startY + i * MODEL_Y_GAP },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          icon: 'mdi-brain',
          label: name,
          colorClass: 'node-pending',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
      }
    })

    const lastPreId = getLastPreModelNodeId()
    const nonModelNodes = nodes.value
      .filter(n => !n.id.startsWith('model-'))
      .map(n => {
        if (n.id === 'testScore') return { ...n, position: { ...n.position, x: testScoreX } }
        if ((RESULT_NODE_IDS as readonly string[]).includes(n.id)) return { ...n, position: { ...n.position, x: resultX } }
        return n
      })

    const insertAfterIdx = nonModelNodes.findIndex(n => n.id === lastPreId)
    const rebuilt = [...nonModelNodes]
    rebuilt.splice(insertAfterIdx + 1, 0, ...newModelNodes)
    nodes.value = rebuilt

    // 過濾 model-related edges 與 lastPreId→testScore；e5 依 computeCi 節點是否存在決定
    const nonModelEdges = edges.value.filter(e =>
      !e.id.startsWith('etm') && !e.id.startsWith('emts')
      && !e.source.startsWith('model-') && !e.target.startsWith('model-')
      && !(e.source === lastPreId && e.target === 'testScore')
      && e.id !== 'e5',
    )
    const hasComputeCi = nodes.value.some(n => n.id === 'computeCi')
    const e5Edges: EdgeBase[] = hasComputeCi
      ? [{ id: 'e5', source: 'testScore', target: 'computeCi', type: 'default' }]
      : []

    if (newModelNodes.length === 0) {
      const noModelEdgeId = preDynCount === 0 ? 'e2' : `e2${String.fromCodePoint(96 + preDynCount)}`
      edges.value = [
        ...nonModelEdges,
        { id: noModelEdgeId, source: lastPreId, target: 'testScore', type: 'default' },
        ...e5Edges,
      ]
      return
    }

    edges.value = [
      ...nonModelEdges,
      ...newModelNodes.map((m, i) => ({ id: `etm${i}`, source: lastPreId, target: m.id, type: 'default' })),
      ...newModelNodes.map((m, i) => ({ id: `emts${i}`, source: m.id, target: 'testScore', type: 'default' })),
      ...e5Edges,
    ]
  }

  // 還原舊 workflowState 後，補上因 code 更新而缺少的動態節點
  function ensureDynamicNodes (): void {
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    if (!settingsNode) return

    const preprocessing = Array.isArray(settingsNode.data.config.preprocessing)
      ? (settingsNode.data.config.preprocessing as Array<Record<string, unknown>>)
      : []
    const featureEng = Array.isArray(settingsNode.data.config.featureEngineering)
      ? (settingsNode.data.config.featureEngineering as Array<Record<string, unknown>>)
      : []

    // ── 1. 補上缺少的 pipeline 節點（preprocessor / featureEngineering）──
    const expectedPipelineIds: string[] = [
      ...(preprocessing.length > 0 ? ['preprocessor'] : []),
      ...(featureEng.length > 0 ? ['featureEngineering'] : []),
    ]
    const currentPipelineIds = nodes.value
      .filter(n => (DYNAMIC_NODE_IDS as readonly string[]).includes(n.id))
      .map(n => n.id)

    const pipelineNeedsRebuild = !(
      expectedPipelineIds.length === currentPipelineIds.length
      && expectedPipelineIds.every((id, i) => id === currentPipelineIds[i])
    )

    if (pipelineNeedsRebuild) {
      const xShift = expectedPipelineIds.length * 200
      const pipelineNodes: FlowNode[] = expectedPipelineIds.map((id, index) => ({
        id,
        type: 'iconNode',
        position: { x: 460 + index * 200, y: 290 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: id === 'preprocessor'
          ? { icon: 'mdi-filter-cog-outline', label: 'Preprocessor', colorClass: 'node-pending', description: '資料前處理', fields: [], config: { pipeline: preprocessing } }
          : { icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', colorClass: 'node-pending', description: '特徵工程', fields: [], config: { pipeline: featureEng } },
      }))

      const base = nodes.value.filter(n =>
        !(DYNAMIC_NODE_IDS as readonly string[]).includes(n.id) && !n.id.startsWith('model-'),
      )
      const settingsIdx = base.findIndex(n => n.id === 'settings')
      const rebuilt = base.map(n => {
        const orig = INITIAL_NODES.find(b => b.id === n.id)
        return orig && (['testScore', ...(RESULT_NODE_IDS as readonly string[])] as string[]).includes(n.id)
          ? { ...n, position: { ...n.position, x: orig.position.x + xShift } }
          : n
      })
      rebuilt.splice(settingsIdx + 1, 0, ...pipelineNodes)
      nodes.value = rebuilt

      edges.value = edges.value.filter(e => ['e0', 'e0a', 'e1', 'e3', 'e4'].includes(e.id))
    }

    // ── 2. 補上缺少的 model 節點 ──
    const settingsModels = Array.isArray(settingsNode.data.config.models)
      ? settingsNode.data.config.models as Array<unknown>
      : []
    const currentModelCount = nodes.value.filter(n => n.id.startsWith('model-')).length
    if (settingsModels.length > 0 && currentModelCount !== settingsModels.length) {
      syncModelCanvasNodes(settingsModels)
    } else if (settingsModels.length === 0 && currentModelCount === 0) {
      // 沒有 model 也要確保 settings/pipeline → testScore 的 edge 存在
      const lastPreId = getLastPreModelNodeId()
      if (!edges.value.some(e => e.source === lastPreId && e.target === 'testScore')) {
        const preDynCount = (DYNAMIC_NODE_IDS as readonly string[]).filter(id =>
          nodes.value.some(n => n.id === id),
        ).length
        const edgeId = preDynCount === 0 ? 'e2' : `e2${String.fromCodePoint(96 + preDynCount)}`
        edges.value = [...edges.value, { id: edgeId, source: lastPreId, target: 'testScore', type: 'default' }]
      }
    }
  }

  // 重建 preprocessor / featureEngineering canvas 節點（由 settings.config 驅動）
  function syncPipelineCanvasNodes (): void {
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    if (!settingsNode) return

    const preprocessing = Array.isArray(settingsNode.data.config.preprocessing)
      ? (settingsNode.data.config.preprocessing as Array<Record<string, unknown>>)
      : []
    const featureEng = Array.isArray(settingsNode.data.config.featureEngineering)
      ? (settingsNode.data.config.featureEngineering as Array<Record<string, unknown>>)
      : []

    const preDynDefs = [
      ...(preprocessing.length > 0
        ? [{ id: 'preprocessor', icon: 'mdi-filter-cog-outline', label: 'Preprocessor', desc: '資料前處理', pipeline: preprocessing }]
        : []),
      ...(featureEng.length > 0
        ? [{ id: 'featureEngineering', icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', desc: '特徵工程', pipeline: featureEng }]
        : []),
    ]

    const pipelineNodes: FlowNode[] = preDynDefs.map((def, i) => {
      const existing = nodes.value.find(n => n.id === def.id)
      return {
        id: def.id,
        type: 'iconNode',
        position: { x: 460 + i * 200, y: 290 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          icon: def.icon,
          label: def.label,
          colorClass: existing?.data.colorClass ?? 'node-pending',
          description: def.desc,
          fields: [],
          config: { pipeline: def.pipeline },
        },
      }
    })

    const modelNodes = nodes.value.filter(n => n.id.startsWith('model-'))
    const modelX = 460 + preDynDefs.length * 200
    const testScoreX = modelX + 200
    const resultX = testScoreX + 200

    const updatedModelNodes = modelNodes.map((n, i) => {
      const startY = 290 - ((modelNodes.length - 1) * MODEL_Y_GAP) / 2
      return { ...n, position: { x: modelX, y: startY + i * MODEL_Y_GAP } }
    })

    const baseNodes = nodes.value
      .filter(n => !(DYNAMIC_NODE_IDS as readonly string[]).includes(n.id) && !n.id.startsWith('model-'))
      .map(n => {
        if (n.id === 'testScore') return { ...n, position: { ...n.position, x: testScoreX } }
        if ((RESULT_NODE_IDS as readonly string[]).includes(n.id)) return { ...n, position: { ...n.position, x: resultX } }
        return n
      })

    nodes.value = [...baseNodes, ...pipelineNodes, ...updatedModelNodes]

    const lastPreId = preDynDefs.length > 0 ? preDynDefs.at(-1)!.id : 'settings'
    const fullPreChain = ['settings', ...preDynDefs.map(d => d.id)]
    const innerChainEdges: EdgeBase[] = fullPreChain.slice(0, -1).map((src, i) => ({
      id: i === 0 ? 'e2' : `e2${String.fromCodePoint(96 + i)}`,
      source: src,
      target: fullPreChain[i + 1]!,
      type: 'default',
    }))

    const midEdges: EdgeBase[] = updatedModelNodes.length > 0
      ? [
        ...updatedModelNodes.map((m, i) => ({ id: `etm${i}`, source: lastPreId, target: m.id, type: 'default' })),
        ...updatedModelNodes.map((m, i) => ({ id: `emts${i}`, source: m.id, target: 'testScore', type: 'default' })),
      ]
      : [{ id: preDynDefs.length === 0 ? 'e2' : `e2${String.fromCodePoint(96 + preDynDefs.length)}`, source: lastPreId, target: 'testScore', type: 'default' }]

    const e5Edges: EdgeBase[] = nodes.value.some(n => n.id === 'computeCi')
      ? [{ id: 'e5', source: 'testScore', target: 'computeCi', type: 'default' }]
      : []

    edges.value = [
      { id: 'e0', source: 'file', target: 'dataTable', type: 'default' },
      { id: 'e0a', source: 'file', target: 'distribution', type: 'default' },
      { id: 'e1', source: 'dataTable', target: 'settings', type: 'default' },
      ...innerChainEdges,
      ...midEdges,
      { id: 'e3', source: 'testScore', target: 'featureImportance', type: 'default' },
      { id: 'e4', source: 'testScore', target: 'confusionMatrix', type: 'default' },
      ...e5Edges,
    ]
  }

  // 依 settings.compute_ci 新增或移除 computeCi 動態節點與 e5 edge
  function syncComputeCiNode (): void {
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    const enabled = Boolean(settingsNode?.data.config.compute_ci)
    const hasComputeCi = nodes.value.some(n => n.id === 'computeCi')

    if (enabled === hasComputeCi) return

    if (enabled) {
      const resultX = nodes.value.find(n => n.id === 'featureImportance')?.position.x
        ?? nodes.value.find(n => n.id === 'confusionMatrix')?.position.x
        ?? ((nodes.value.find(n => n.id === 'testScore')?.position.x ?? 460) + 200)
      nodes.value = [...nodes.value, {
        id: 'computeCi',
        type: 'iconNode',
        position: { x: resultX, y: 560 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          icon: 'mdi-chart-areaspline-variant',
          label: 'Compute\nCI',
          colorClass: 'node-pending',
          description: 'Bootstrap 信賴區間',
          fields: [],
          config: {},
        },
      }]
      edges.value = [...edges.value, { id: 'e5', source: 'testScore', target: 'computeCi', type: 'default' }]
    } else {
      nodes.value = nodes.value.filter(n => n.id !== 'computeCi')
      edges.value = edges.value.filter(e => e.id !== 'e5')
    }
  }

  onMounted(async () => {
    try {
      // 3. 優先還原工作流狀態
      const restoredState = loadWorkflowStateFromStorage()
      if (restoredState && restoredState.nodes?.length > 0) {
        nodes.value = restoredState.nodes
        edges.value = restoredState.edges
        // 補齊缺少的靜態節點
        for (const initNode of INITIAL_NODES) {
          if (!nodes.value.some(n => n.id === initNode.id)) {
            nodes.value = [...nodes.value, initNode]
          }
        }
        for (const initEdge of INITIAL_EDGES) {
          if (!edges.value.some(e => e.id === initEdge.id)) {
            edges.value = [...edges.value, initEdge]
          }
        }
        ensureDynamicNodes()
        // 確保 computeCi 動態節點與 settings.compute_ci 一致
        syncComputeCiNode()
        console.log('[WF-INIT] 成功從儲存還原 nodes & edges')
      } else {
        // 如果沒有整體狀態，再嘗試還原 JSON
        const restoredJsonFile = await loadWorkflowJsonFileFromStorage()
        if (restoredJsonFile) {
          selectedJsonFile.value = restoredJsonFile
          await loadJsonModels(restoredJsonFile)
        }
      }

      // 4. 還原實體 CSV 檔案狀態
      const restoredDataFile = await loadWorkflowDataFileFromStorage()
      if (restoredDataFile) {
        workflowDataFile.value = restoredDataFile
        updateFileNodeConfig(restoredDataFile.name)
      }

      // 5. 載入外部模型選項
      await loadAvailableModels()

      // 6. 確保 DOM 與畫布元件都跟上最新資料
      await nextTick()
    } catch (error) {
      console.error('[WF-INIT] 初始化過程出錯:', error)
    } finally {
      // 7. 解開鎖定！從現在開始，使用者的任何改動才會被存入 localStorage
      isInitializing.value = false
      console.log('[WF-INIT] 初始化完成，自動儲存鎖已解開')
    }
  })

  const workflowSummary = computed(() => {
    if (!workflowResult.value) return []

    const results = Array.isArray(workflowResult.value.results)
      ? workflowResult.value.results
      : []

    const modelGroups = new Map<
      string,
      {
        count: number
        metrics: Record<string, number[]>
        errors: Record<string, string[]>
      }
    >()

    for (const result of results.filter(
      (result: any) => result && typeof result === 'object',
    )) {
      const modelName = result.model_name || 'unknown'
      const existing = modelGroups.get(modelName) ?? {
        count: 0,
        metrics: {},
        errors: {},
      }

      if (Array.isArray(result.metrics)) {
        for (const metric of result.metrics) {
          const name = metric.metric || 'unknown'
          if (metric?.error) {
            existing.errors[name] = metric.error
            continue
          }
          const value = Number(metric.value)
          if (!Number.isNaN(value)) {
            existing.metrics[name] = existing.metrics[name] ?? []
            existing.metrics[name].push(value)
          }
        }
      }

      existing.count += 1
      modelGroups.set(modelName, existing)
    }

    return Array.from(modelGroups.entries()).map(([modelName, group]) => ({
      model_name: modelName,
      split_name: `${group.count} splits`,
      metrics: Object.entries(group.metrics).map(([metric, values]) => ({
        metric,
        valueFormatted:
          values.length > 0
            ? (
              values.reduce((sum, current) => sum + current, 0)
              / values.length
            ).toFixed(4)
            : 'N/A',
      })),
      errors: group.errors,
    }))
  })

  // 預設不選任何節點，點擊後才顯示下方 options
  const selectedNodeId = ref<string | null>(null)

  // 抽屜拖曳邏輯（封裝在 composable）
  const {
    isExpanded,
    style: drawerStyle,
    startDrag,
    reset: resetDrawer,
    expand: expandDrawer,
  } = useDrawerDrag()

  // 目前被選取的節點（傳給 OptionsPanel）
  const selectedNode = computed<SimpleNode | null>(() => {
    if (!selectedNodeId.value) return null
    const node = nodes.value.find(item => item.id === selectedNodeId.value)
    return node ? { id: node.id, data: node.data } : null
  })

  // 讀取畫布上的 model 節點名稱（canvas nodes 是唯一 source of truth）
  const usedModelNames = computed<string[]>(() =>
    nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => String(n.data.config.modelName ?? n.data.label ?? ''))
      .filter(Boolean),
  )

  const availableModelOptions = computed<string[]>(() =>
    availableModels.value.filter(name => !usedModelNames.value.includes(name)),
  )

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

  const canvasMinHeight = computed<number>(() => {
    if (canvasNodes.value.length === 0) return 520
    const maxBottom = Math.max(
      ...canvasNodes.value.map(node => node.position.y + 140),
    )
    return Math.max(520, maxBottom + 120)
  })

  const canvasMinWidth = computed<number>(() => {
    if (canvasNodes.value.length === 0) return 860
    const maxRight = Math.max(
      ...canvasNodes.value.map(node => node.position.x + 180),
    )
    return Math.max(860, maxRight + 160)
  })

  // 重置 demo 全部狀態並清除所有計時器
  function resetDemo (): void {
    nodeStatuses.value = new Map()
    isDemoRunning.value = false
    isDemoFinished.value = false
    pausedAtNodeId.value = null
    for (const timer of demoTimers) {
      clearTimeout(timer)
    }
    demoTimers.length = 0
  }

  function scheduleWorkflowSteps (steps: DemoStep[], baseDelay = 0): void {
    if (steps.length === 0) {
      return
    }

    for (const { nodeIds, delay } of steps) {
      const offset = delay - baseDelay
      if (offset < 0) continue

      demoTimers.push(
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'running')
          nodeStatuses.value = next
        }, offset),
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'finished')
          nodeStatuses.value = next
        }, offset + NODE_RUN_DURATION),
      )
    }

    const lastDelay = steps.at(-1)!.delay
    const endTime
      = lastDelay - baseDelay + NODE_RUN_DURATION + DEMO_FINISH_LINGER
    demoTimers.push(
      window.setTimeout(() => {
        isDemoRunning.value = false
        isDemoFinished.value = true
      }, endTime),
    )
  }

  function continueWorkflow (): void {
    if (pausedAtNodeId.value === 'dataTable') {
      if (!dataTableCanContinue.value) {
        workflowError.value = selectedTargetColumn.value
          ? '請先按 Apply，再繼續 Workflow。'
          : '請先選擇 target 欄位，再按 Apply。'
        return
      }

      pausedAtNodeId.value = null
      isDemoRunning.value = true

      const steps = buildDemoSteps()
      const dataTableStep = steps.find(step => step.nodeIds.includes('dataTable'))
      const settingsStep = steps.find(step => step.nodeIds.includes('settings'))
      if (!dataTableStep || !settingsStep) return

      const current = new Map(nodeStatuses.value)
      current.set('dataTable', 'finished')
      nodeStatuses.value = current

      // 動畫跑到 settings 後暫停，自動開啟 settings panel
      const runAt = settingsStep.delay - dataTableStep.delay
      demoTimers.push(
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          next.set('settings', 'running')
          nodeStatuses.value = next
        }, runAt),
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          next.set('settings', 'finished')
          nodeStatuses.value = next
          isDemoRunning.value = false
          pausedAtNodeId.value = 'settings'
          selectedNodeId.value = 'settings'
          expandDrawer()
        }, runAt + NODE_RUN_DURATION),
      )
      return
    }

    if (pausedAtNodeId.value === 'settings') {
      if (!settingsCanContinue.value) {
        workflowError.value = '請至少新增一個模型，再繼續 Workflow。'
        return
      }

      pausedAtNodeId.value = null
      isDemoRunning.value = true

      const steps = buildDemoSteps()
      const settingsStep = steps.find(step => step.nodeIds.includes('settings'))
      if (!settingsStep) return

      const remainingSteps = steps.filter(step => step.delay > settingsStep.delay)
      scheduleWorkflowSteps(remainingSteps, settingsStep.delay)
      runWorkflowRequest()
    }
  }

  type DemoStep = {
    nodeIds: string[]
    delay: number
  }

  function buildDemoSteps (): DemoStep[] {
    const common: DemoStep[] = [
      { nodeIds: ['file'], delay: 800 },
      { nodeIds: ['distribution'], delay: 1400 },
      { nodeIds: ['dataTable'], delay: 1800 },
      { nodeIds: ['settings'], delay: 2800 },
    ]
    const presentPipeline = (DYNAMIC_NODE_IDS as readonly string[]).filter(id =>
      nodes.value.some(n => n.id === id),
    )
    const modelNodeIds = nodes.value.filter(n => n.id.startsWith('model-')).map(n => n.id)

    if (presentPipeline.length === 0 && modelNodeIds.length === 0) {
      return [
        ...common,
        { nodeIds: ['testScore'], delay: 4200 },
        { nodeIds: ['featureImportance', 'confusionMatrix'], delay: 5400 },
      ]
    }

    let delay = 3600
    const pipelineSteps: DemoStep[] = presentPipeline.map(id => {
      const step: DemoStep = { nodeIds: [id], delay }
      delay += 1400
      return step
    })
    const modelStep: DemoStep[] = modelNodeIds.length > 0
      ? [{ nodeIds: modelNodeIds, delay }, { nodeIds: ['testScore'], delay: (delay += 1400) }]
      : [{ nodeIds: ['testScore'], delay }]
    return [
      ...common,
      ...pipelineSteps,
      ...modelStep,
      { nodeIds: ['featureImportance', 'confusionMatrix'], delay: delay + 1200 },
    ]
  }

  // 節點點擊：更新目前選擇的 node
  function handleSelectNode (nodeId: string): void {
    if (selectedNodeId.value === nodeId) {
      closeMenu()
      return
    }
    selectedNodeId.value = nodeId
    expandDrawer()
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

  function triggerJsonUpload (): void {
    jsonFileInput.value?.click()
  }

  function handleJsonFileChange (event: Event): void {
    const target = event.target as HTMLInputElement
    selectedJsonFile.value = target.files?.[0] ?? null
    target.value = ''
    if (selectedJsonFile.value) {
      loadJsonModels(selectedJsonFile.value)
    }
  }

  async function loadJsonModels (file: File): Promise<void> {
    if (!file.name.toLowerCase().endsWith('.json')) return

    const rawText = await file.text()
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(rawText) as Record<string, unknown>
    } catch (error) {
      console.error('Invalid JSON file', error)
      return
    }

    const VALID_PREPROCESS_TYPES = new Set([
      'fill_na', 'knn_impute', 'iterative_impute', 'normalize', 'standardize',
      'one_hot', 'label_encode', 'drop_columns', 'remove_outliers_iqr', 'remove_outliers_zscore',
    ])
    const VALID_FE_TYPES = new Set([
      'select_relevant_features', 'pca', 'discretize_continuous', 'continuize_discrete',
      'normalize_features', 'remove_sparse_features',
    ])

    const models = Array.isArray(parsed.models) ? parsed.models : []
    const featureEngineering = (Array.isArray(parsed.featureEngineering)
      ? (parsed.featureEngineering as Array<Record<string, unknown>>)
      : []
    ).filter(s => typeof s.type === 'string' && VALID_FE_TYPES.has(s.type as string))
    const preprocessing = (Array.isArray(parsed.preprocessing)
      ? (parsed.preprocessing as Array<Record<string, unknown>>)
      : []
    ).filter(s => typeof s.type === 'string' && VALID_PREPROCESS_TYPES.has(s.type as string))
    const validation = parsed.validation as Record<string, unknown> | undefined
    const metrics = Array.isArray(parsed.metrics) ? parsed.metrics : []

    const fileNode = INITIAL_NODES.find(n => n.id === 'file')!
    const dataTableNode = INITIAL_NODES.find(n => n.id === 'dataTable')!
    const distributionNode = INITIAL_NODES.find(n => n.id === 'distribution')!
    const settingsNode = INITIAL_NODES.find(n => n.id === 'settings')!
    const testScoreNode = INITIAL_NODES.find(n => n.id === 'testScore')!
    const featureImportanceNode = INITIAL_NODES.find(n => n.id === 'featureImportance')!
    const confusionMatrixNode = INITIAL_NODES.find(n => n.id === 'confusionMatrix')!

    const updatedSettingsNode: FlowNode = {
      ...settingsNode,
      data: {
        ...settingsNode.data,
        config: { preprocessing, featureEngineering, models, compute_ci: Boolean(parsed.compute_ci ?? false) },
      },
    }

    const updatedTestScoreNode: FlowNode = {
      ...testScoreNode,
      data: {
        ...testScoreNode.data,
        config: {
          ...testScoreNode.data.config,
          targetCol: (parsed.target_col ?? parsed.targetCol ?? '是否跌倒') as string,
          validation: validation ?? { method: 'k_fold', n_splits: 10, stratified: true, train_size: 0.8 },
          metrics: metrics.length > 0 ? metrics : ['balanced_accuracy', 'auc', 'auprc', 'mcc', 'f1'],
          resampling_method: (() => {
            const r = parsed.resampling as any
            return typeof r === 'string' ? r : (r?.method ?? 'none')
          })(),
          resampling_config: (() => {
            const r = parsed.resampling as any
            return (typeof r === 'object' && r !== null) ? (r.config ?? {}) : {}
          })(),
          tuning_method: (() => {
            const t = parsed.tuning as any
            return typeof t === 'string' ? t : (t?.method ?? 'none')
          })(),
          tuning_cv: (parsed.tuning as any)?.cv ?? 3,
          tuning_n_iter: (parsed.tuning as any)?.n_iter ?? 20,
          tuning_scoring: (parsed.tuning as any)?.scoring ?? 'roc_auc',
          compute_ci: Boolean(parsed.compute_ci ?? false),
        },
      },
    }

    // ── pipeline 節點（preprocessor / featureEngineering）──
    const preDynDefs = [
      ...(preprocessing.length > 0 ? [{ id: 'preprocessor', icon: 'mdi-filter-cog-outline', label: 'Preprocessor', desc: '資料前處理', pipeline: preprocessing }] : []),
      ...(featureEngineering.length > 0 ? [{ id: 'featureEngineering', icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', desc: '特徵工程', pipeline: featureEngineering }] : []),
    ]
    const preDynNodes: FlowNode[] = preDynDefs.map((def, i) => ({
      id: def.id,
      type: 'iconNode',
      position: { x: 460 + i * 200, y: 290 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: { icon: def.icon, label: def.label, colorClass: 'node-pending', description: def.desc, fields: [], config: { pipeline: def.pipeline } },
    }))

    // ── model 節點（垂直排列）──
    const modelX = 460 + preDynDefs.length * 200
    const modelStartY = 290 - ((models.length - 1) * MODEL_Y_GAP) / 2
    const modelNodes: FlowNode[] = (models as Array<unknown>).map((m, i) => {
      const name = typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? '')
      const purposeZh = typeof m === 'object' && m !== null
        ? String((m as Record<string, unknown>).purpose_zh ?? '')
        : ''
      return {
        id: `model-${i}`,
        type: 'iconNode',
        position: { x: modelX, y: modelStartY + i * MODEL_Y_GAP },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          icon: 'mdi-brain',
          label: name,
          colorClass: 'node-pending',
          description: purposeZh || name,
          fields: [],
          config: { modelName: name },
        },
      }
    })

    const testScoreX = modelX + 200
    const resultX = testScoreX + 200

    nodes.value = [
      fileNode, dataTableNode, distributionNode, updatedSettingsNode,
      ...preDynNodes, ...modelNodes,
      { ...updatedTestScoreNode, position: { ...testScoreNode.position, x: testScoreX } },
      { ...featureImportanceNode, position: { ...featureImportanceNode.position, x: resultX } },
      { ...confusionMatrixNode, position: { ...confusionMatrixNode.position, x: resultX } },
    ]

    // ── edges ──
    const fullPreChain = ['settings', ...preDynDefs.map(d => d.id)]
    const lastPreId = fullPreChain.at(-1)!
    const innerChainEdges: EdgeBase[] = fullPreChain.slice(0, -1).map((src, i) => ({
      id: i === 0 ? 'e2' : `e2${String.fromCodePoint(96 + i)}`,
      source: src,
      target: fullPreChain[i + 1]!,
      type: 'default',
    }))

    const midEdges: EdgeBase[] = modelNodes.length > 0
      ? [
        ...modelNodes.map((m, i) => ({ id: `etm${i}`, source: lastPreId, target: m.id, type: 'default' })),
        ...modelNodes.map((m, i) => ({ id: `emts${i}`, source: m.id, target: 'testScore', type: 'default' })),
      ]
      : [{ id: preDynDefs.length === 0 ? 'e2' : `e2${String.fromCodePoint(96 + preDynDefs.length)}`, source: lastPreId, target: 'testScore', type: 'default' }]

    edges.value = [
      { id: 'e0', source: 'file', target: 'dataTable', type: 'default' },
      { id: 'e0a', source: 'file', target: 'distribution', type: 'default' },
      { id: 'e1', source: 'dataTable', target: 'settings', type: 'default' },
      ...innerChainEdges, ...midEdges,
      { id: 'e3', source: 'testScore', target: 'featureImportance', type: 'default' },
      { id: 'e4', source: 'testScore', target: 'confusionMatrix', type: 'default' },
    ]

    // 依 compute_ci 決定是否顯示 computeCi 動態節點
    syncComputeCiNode()

    selectedJsonFile.value = file
    saveWorkflowJsonFileToStorage(file)
    saveWorkflowStateToStorage()
  }

  function handleDataFile (file: File): void {
    workflowDataFile.value = file
    workflowError.value = null
    updateFileNodeConfig(file.name)
    saveWorkflowDataFileToStorage(file)
  }

  async function ensureWorkflowDataFile (): Promise<void> {
    if (workflowDataFile.value) return

    const restoredFile = await loadWorkflowDataFileFromStorage()
    if (restoredFile) {
      workflowDataFile.value = restoredFile
      updateFileNodeConfig(restoredFile.name)
    }
  }

  function buildWorkflowPayload (): Record<string, unknown> {
    const dataTableNode = nodes.value.find(n => n.id === 'dataTable')
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    const testScoreNode = nodes.value.find(n => n.id === 'testScore')

    const preprocessing = settingsNode?.data.config.preprocessing ?? []
    const featureEngineering = settingsNode?.data.config.featureEngineering ?? []
    const modelNames = nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => String(n.data.config.modelName ?? n.data.label ?? ''))
      .filter(Boolean)

    const validationConfig = testScoreNode?.data.config.validation ?? {}
    const metrics = testScoreNode?.data.config.metrics ?? []

    return {
      preprocess_pipelines: Array.isArray(preprocessing) ? [preprocessing] : [],
      feature_engineering_pipelines: Array.isArray(featureEngineering) ? [featureEngineering] : [],
      model_names: modelNames,
      validation_config: validationConfig,
      score_variants: Array.isArray(metrics)
        ? metrics.map(m => typeof m === 'string' ? { metric: m } : m)
        : [],
      column_config: Array.isArray(dataTableNode?.data.config.columnConfig)
        ? (dataTableNode?.data.config.columnConfig as ColumnConfig[])
        : [],
      target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '是否跌倒',
      resampling_method: String(testScoreNode?.data.config.resampling_method ?? 'none'),
      resampling_config: (testScoreNode?.data.config.resampling_config ?? {}) as Record<string, unknown>,
      tuning_method: String(testScoreNode?.data.config.tuning_method ?? 'none'),
      tuning_cv: Number(testScoreNode?.data.config.tuning_cv ?? 3),
      tuning_n_iter: Number(testScoreNode?.data.config.tuning_n_iter ?? 20),
      tuning_scoring: String(testScoreNode?.data.config.tuning_scoring ?? 'roc_auc'),
      compute_ci: Boolean(nodes.value.find(n => n.id === 'computeCi')?.data.config.enabled ?? settingsNode?.data.config.compute_ci ?? false),
    }
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

  async function runWorkflowRequest (): Promise<void> {
    if (!workflowDataFile.value) {
      workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
      return
    }

    workflowError.value = null
    workflowResult.value = null

    try {
      const payload = buildWorkflowPayload()
      workflowResult.value = await executeWorkflowApi({
        file: workflowDataFile.value,
        workflowPayload: payload,
      })
    } catch (error) {
      workflowError.value
        = error instanceof Error ? error.message : 'Workflow 執行失敗'
      resetDemo()
    }
  }

  async function executeWorkflow (): Promise<void> {
    await ensureWorkflowDataFile()
    if (!workflowDataFile.value) {
      workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
      return
    }

    resetDemo()
    isDemoRunning.value = true
    pausedAtNodeId.value = 'dataTable'
    workflowError.value = null
    workflowResult.value = null

    const nextStatuses = new Map<string, 'running' | 'finished'>([
      ['file', 'finished'],
      ['distribution', 'finished'],
      ['dataTable', 'running'],
    ])
    nodeStatuses.value = nextStatuses
    selectedNodeId.value = 'dataTable'
  }

  function triggerPaperUpload (): void {
    paperFileInput.value?.click()
  }

  function triggerGeminiUpload (): void {
    geminiFileInput.value?.click()
  }

  // 上傳論文檔案，呼叫 n8n webhook，並將回傳的 workflow JSON 直接載入畫布
  async function handlePaperFileChange (event: Event): Promise<void> {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0] ?? null
    target.value = ''
    if (!file) return

    paperUploading.value = true
    workflowError.value = null

    try {
      const formData = new FormData()
      formData.append('data', file, file.name)

      const response = await fetch(N8N_PAPER_WEBHOOK_URL, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        throw new Error(`n8n webhook 回應錯誤：${response.status} ${errorText}`)
      }

      const contentType = response.headers.get('content-type') ?? ''
      const result = contentType.includes('application/json')
        ? await response.json()
        : await response.text()

      const payload = Array.isArray(result) ? result[0] : result
      if (payload && typeof payload === 'object') {
        const jsonBlob = new File(
          [JSON.stringify(payload)],
          `${file.name.replace(/\.[^.]+$/, '')}.json`,
          { type: 'application/json' },
        )
        await loadJsonModels(jsonBlob)
      }
    } catch (error) {
      workflowError.value = error instanceof Error ? error.message : '論文上傳失敗'
      console.error('[n8n] analyze-paper error:', error)
    } finally {
      paperUploading.value = false
    }
  }

  // 上傳論文 PDF → 呼叫 Gemini AI 分析 → 將回傳的 workflow JSON 載入畫布
  async function handleGeminiFileChange (event: Event): Promise<void> {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0] ?? null
    target.value = ''
    if (!file) return

    geminiUploading.value = true
    workflowError.value = null

    try {
      const workflowJson = await analyzeWorkflowFromPdf({
        file,
        title: file.name.replace(/\.[^.]+$/, ''),
      })

      const jsonBlob = new File(
        [JSON.stringify(workflowJson)],
        `${file.name.replace(/\.[^.]+$/, '')}.json`,
        { type: 'application/json' },
      )
      await loadJsonModels(jsonBlob)
    } catch (error) {
      workflowError.value
        = error instanceof Error ? error.message : '論文 AI 分析失敗，請確認 PDF 是否正確'
      console.error('[gemini] analyze-paper error:', error)
    } finally {
      geminiUploading.value = false
    }
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

  function handleApplyColumnConfig (): void {
    dataTableApplied.value = true
    workflowError.value = null
  }

  // 點空白區可收起 menu
  function closeMenu (): void {
    selectedNodeId.value = null
    resetDrawer()
  }

  // 面板儲存：更新對應 node 的 config，若是 settings 的 pipeline 欄位則同步畫布
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

    if (payload.nodeId === 'settings') {
      if ('preprocessing' in payload.config || 'featureEngineering' in payload.config) {
        syncPipelineCanvasNodes()
      }
      if ('compute_ci' in payload.config) {
        syncComputeCiNode()
      }
    }

    saveWorkflowStateToStorage()
  }

  // 元件卸載時確保儲存狀態並清除 demo 計時器
  onBeforeUnmount(() => {
    saveWorkflowStateToStorage()
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
    background-image: radial-gradient(
      rgba(0, 93, 255, 0.035) 0.8px,
      transparent 0.8px
    );
    background-size: 16px 16px;
  }

  .workspace-canvas {
    flex: 1;
    min-height: 520px;
    width: 100%;
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
    transition:
      background 0.15s,
      opacity 0.15s;
    user-select: none;
    padding: 0 14px;
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
    transition:
      background 0.15s,
      opacity 0.15s;
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
    transition:
      background 0.15s,
      opacity 0.15s;
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
    transition:
      background 0.15s,
      opacity 0.15s;
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
    bottom: 18px;
    left: 18px;
    right: 18px;
    z-index: 5;
    padding: 18px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid rgba(0, 93, 255, 0.12);
    box-shadow: 0 20px 40px rgba(17, 24, 39, 0.08);
    color: #102a43;
    max-height: 320px;
    overflow: auto;
  }

  .workflow-summary {
    margin-bottom: 12px;
  }

  .summary-list {
    display: grid;
    gap: 12px;
  }

  .summary-item {
    display: grid;
    gap: 8px;
    padding: 12px;
    border-radius: 12px;
    background: #f6fbff;
    border: 1px solid rgba(0, 93, 255, 0.12);
  }

  .summary-item__header {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    font-weight: 700;
    color: #022d65;
  }

  .summary-item__metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    color: #16325c;
  }

  .summary-metric {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(0, 93, 255, 0.08);
    color: #103d82;
    font-size: 12px;
  }

  .workflow-result pre {
    margin: 0;
    padding: 14px;
    background: #f1f7ff;
    border-radius: 12px;
    color: #0f172a;
    overflow-x: auto;
  }

  .workflow-error {
    margin-bottom: 12px;
    padding: 12px;
    background: rgba(255, 235, 238, 0.9);
    border: 1px solid rgba(244, 67, 54, 0.18);
    border-radius: 12px;
    color: #b00020;
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
    will-change: height, transform;
    transition: height 260ms cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
  }

  /* 抽屜內部可滾動區區：拖曳區固定頂部，內容區独立滾動 */
  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
    padding-bottom: 16px;
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

  .options-drawer__scroll {
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .options-drawer--expanded {
    max-height: 54vh;
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

  .workflow-summary {
    margin-bottom: 12px;
  }

  .workflow-summary h4 {
    margin: 0 0 10px;
    font-size: 14px;
    color: #0f172a;
    letter-spacing: 0.02em;
  }

  .summary-list {
    display: grid;
    gap: 10px;
  }

  .summary-item {
    padding: 10px 12px;
    background: rgba(0, 93, 255, 0.05);
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
  }

  .summary-item__header {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #0f172a;
  }

  .summary-item__metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .summary-metric {
    font-size: 12px;
    color: #334155;
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 999px;
    padding: 4px 8px;
  }

  .summary-empty {
    font-size: 12px;
    color: #475569;
  }

  .workflow-result pre {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 12px;
    line-height: 1.45;
    color: #0f172a;
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

  .drawer-panel-enter-active,
  .drawer-panel-leave-active {
    transition:
      opacity 180ms ease,
      transform 180ms ease;
  }

  .drawer-panel-enter-from,
  .drawer-panel-leave-to {
    opacity: 0;
    transform: translateY(8px);
  }

  .drawer-panel-enter-to,
  .drawer-panel-leave-from {
    opacity: 1;
    transform: translateY(0);
  }

  .drawer-content-enter-active,
  .drawer-content-leave-active {
    transition:
      opacity 180ms ease,
      transform 180ms ease;
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
