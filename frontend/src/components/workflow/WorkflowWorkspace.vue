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

    <button
      class="demo-btn execute-workflow-btn"
      :disabled="pausedAtNodeId === 'dataTable' && !dataTableCanContinue"
      type="button"
      @click="
        pausedAtNodeId === 'dataTable' ? continueWorkflow() : executeWorkflow()
      "
    >
      {{ pausedAtNodeId === "dataTable" ? "繼續 Workflow" : "執行 Workflow" }}
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
            :file="workflowDataFile"
            :paused-node-id="pausedAtNodeId"
            :selected-node="selectedNode"
            :workflow-file-name="workflowDataFile?.name"
            :workflow-result="workflowResult"
            :workflow-summary="workflowSummary"
            @apply-column-config="handleApplyColumnConfig"
            @open-upload="openUploadDialog"
            @update-config="handleUpdateConfig"
            @update:file="handleDataFile"
          />
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
    watch,
  } from 'vue'
  import { executeWorkflowApi } from '@/api/workflow'
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
  const paperUploading = ref(false)

  // n8n webhook 路徑（analyze-paper workflow）
  const N8N_PAPER_WEBHOOK_URL
    = (import.meta.env.VITE_N8N_PAPER_WEBHOOK_URL as string | undefined)
      ?? 'https://ideally-strewn-papyrus.ngrok-free.dev/webhook-test/analyze-paper'
  const workflowDataFile = ref<File | null>(null)
  const workflowResult = ref<null | Record<string, unknown>>(null)
  const workflowError = ref<string | null>(null)
  const pausedAtNodeId = ref<string | null>(null)
  const dataTableApplied = ref(false)

  const WORKFLOW_DATA_FILE_STORAGE_KEY = 'workflowDataFile'
  const WORKFLOW_JSON_FILE_STORAGE_KEY = 'workflowJsonFile'

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

  onMounted(async () => {
    const restoredDataFile = await loadWorkflowDataFileFromStorage()
    if (restoredDataFile) {
      workflowDataFile.value = restoredDataFile
      updateFileNodeConfig(restoredDataFile.name)
    }

    const restoredJsonFile = await loadWorkflowJsonFileFromStorage()
    if (restoredJsonFile) {
      selectedJsonFile.value = restoredJsonFile
      await loadJsonModels(restoredJsonFile)
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
    if (!dataTableCanContinue.value) {
      workflowError.value = selectedTargetColumn.value
        ? '請先按 Apply，再繼續 Workflow。'
        : '請先選擇 target 欄位，再按 Apply。'
      return
    }

    pausedAtNodeId.value = null
    isDemoRunning.value = true

    const dataTableStep = buildDemoSteps().find(step =>
      step.nodeIds.includes('dataTable'),
    )
    if (!dataTableStep) return

    const current = new Map(nodeStatuses.value)
    current.set('dataTable', 'finished')
    nodeStatuses.value = current

    const remainingSteps = buildDemoSteps().filter(
      step => step.delay > dataTableStep.delay,
    )
    scheduleWorkflowSteps(remainingSteps, dataTableStep.delay)
    runWorkflowRequest()
  }

  type DemoStep = {
    nodeIds: string[]
    delay: number
  }

  function buildDemoSteps (): DemoStep[] {
    let steps = DEMO_STEPS.slice(0, 3) as DemoStep[]

    if (nodes.value.some(node => node.id === 'featureEngineering')) {
      steps = [...steps, { nodeIds: ['featureEngineering'], delay: 2400 }]
    }

    const modelNodes = nodes.value.filter(
      node => node.id.startsWith('model') && node.id !== 'modelMore',
    )

    let nextDelay = (steps.at(-1)?.delay ?? 2400) + 500
    for (const node of modelNodes) {
      steps = [...steps, { nodeIds: [node.id], delay: nextDelay }]
      nextDelay += 500
    }

    return [
      ...steps,
      { nodeIds: ['testScore'], delay: nextDelay + 200 },
      {
        nodeIds: ['featureImportance', 'confusionMatrix'],
        delay: nextDelay + 900,
      },
    ]
  }

  // 節點點擊：更新目前選擇的 node
  function handleSelectNode (nodeId: string): void {
    if (selectedNodeId.value === nodeId) {
      closeMenu()
      return
    }
    selectedNodeId.value = nodeId
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
    let parsed
    try {
      parsed = JSON.parse(rawText) as Record<string, unknown>
    } catch (error) {
      console.error('Invalid JSON file', error)
      return
    }

    const models = Array.isArray(parsed.models) ? parsed.models : []
    const featureEngineering = Array.isArray(parsed.featureEngineering)
      ? (parsed.featureEngineering as Array<Record<string, unknown>>)
      : []
    const preprocessing = Array.isArray(parsed.preprocessing)
      ? (parsed.preprocessing as Array<Record<string, unknown>>)
      : []
    const validation = parsed.validation as Record<string, unknown> | undefined
    const metrics = Array.isArray(parsed.metrics)
      ? (parsed.metrics as Array<Record<string, unknown>>)
      : []

    const modelEntries = models.filter(
      (
        model,
      ): model is {
        name: string
        type?: string
        purpose_zh?: string
        purpose_en?: string
      } =>
        model !== null
        && typeof model === 'object'
        && typeof model.name === 'string'
        && model.name.trim().length > 0,
    )

    if (modelEntries.length === 0) {
      console.warn('JSON does not contain a valid models array')
      return
    }

    const dynamicModelNodes: FlowNode[] = modelEntries.map((model, index) => ({
      id: `modelJson${index}`,
      type: 'iconNode',
      position: { x: 420, y: 120 + index * 110 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        icon: 'mdi-cube-outline',
        label: model.name.trim(),
        colorClass: 'node-pending',
        description: model.purpose_zh || model.purpose_en || 'JSON 匯入模型',
        fields: [],
        config: {
          modelName: model.name.trim(),
          type: model.type || 'classification',
        },
      },
    }))

    const fileNode = INITIAL_NODES.find(node => node.id === 'file')
    const dataTableNode = INITIAL_NODES.find(node => node.id === 'dataTable')
    const distributionNode = INITIAL_NODES.find(
      node => node.id === 'distribution',
    )
    const preprocessorNode = INITIAL_NODES.find(
      node => node.id === 'preprocessor',
    )
    const testScoreNode = INITIAL_NODES.find(node => node.id === 'testScore')
    const featureImportanceNode = INITIAL_NODES.find(
      node => node.id === 'featureImportance',
    )
    const confusionMatrixNode = INITIAL_NODES.find(
      node => node.id === 'confusionMatrix',
    )

    if (
      !fileNode
      || !dataTableNode
      || !distributionNode
      || !preprocessorNode
      || !testScoreNode
      || !featureImportanceNode
      || !confusionMatrixNode
    ) {
      return
    }

    const featureNode: FlowNode | null
      = featureEngineering.length > 0
        ? {
          id: 'featureEngineering',
          type: 'iconNode',
          position: { x: 330, y: 170 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: {
            icon: 'mdi-brain',
            label: 'Feature\nEngineering',
            colorClass: 'node-pending',
            description: '根據論文擷取的特徵工程步驟',
            fields: [],
            config: {
              pipeline: featureEngineering,
            },
          },
        }
        : null

    const preprocessorNodeIncluded = preprocessing.length > 0

    const updatedPreprocessorNode: FlowNode | null = preprocessorNodeIncluded
      ? {
        ...preprocessorNode,
        data: {
          ...preprocessorNode.data,
          description: '從論文擷取的前處理設定',
          fields: [],
          config: {
            pipeline: preprocessing,
          },
        },
      }
      : null

    const updatedTestScoreNode: FlowNode = {
      ...testScoreNode,
      data: {
        ...testScoreNode.data,
        description: '切分資料與評估指標設定',
        fields: [],
        config: {
          targetCol:
            (parsed as any).target_col
            || (parsed as any).targetCol
            || '是否跌倒',
          validation: validation || { method: 'test_on_test', train_size: 0.7 },
          metrics: metrics.length > 0 ? metrics : [{ metric: 'accuracy' }],
        },
      },
    }

    nodes.value = [
      fileNode,
      dataTableNode,
      distributionNode,
      ...(preprocessorNodeIncluded && updatedPreprocessorNode
        ? [updatedPreprocessorNode]
        : []),
      ...(featureNode ? [featureNode] : []),
      ...dynamicModelNodes,
      updatedTestScoreNode,
      featureImportanceNode,
      confusionMatrixNode,
    ]

    await nextTick()

    const modelSourceNode = featureNode
      ? 'featureEngineering'
      : (preprocessorNodeIncluded
        ? 'preprocessor'
        : 'dataTable')

    const modelEdges = dynamicModelNodes.flatMap((node, index) => [
      {
        id: `e_${modelSourceNode}_model_${index}`,
        source: modelSourceNode,
        target: node.id,
        type: 'default',
      },
      {
        id: `e_model_testScore_${index}`,
        source: node.id,
        target: 'testScore',
        type: 'default',
      },
    ])

    edges.value = [
      {
        id: 'e0',
        source: 'file',
        target: 'dataTable',
        type: 'default',
      },
      {
        id: 'e0a',
        source: 'file',
        target: 'distribution',
        type: 'default',
      },
      ...(preprocessorNodeIncluded
        ? [
          {
            id: 'e1',
            source: 'dataTable',
            target: 'preprocessor',
            type: 'default',
          },
        ]
        : []),
      ...(featureNode
        ? [
          {
            id: 'e2_feature',
            source: preprocessorNodeIncluded ? 'preprocessor' : 'dataTable',
            target: 'featureEngineering',
            type: 'default',
          },
        ]
        : []),
      ...modelEdges,
      {
        id: 'e4a',
        source: 'testScore',
        target: 'featureImportance',
        type: 'default',
      },
      {
        id: 'e4',
        source: 'testScore',
        target: 'confusionMatrix',
        type: 'default',
      },
    ]

    selectedJsonFile.value = file
    saveWorkflowJsonFileToStorage(file)
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
    const dataTableNode = nodes.value.find(node => node.id === 'dataTable')
    const preprocessNode = nodes.value.find(
      node => node.id === 'preprocessor',
    )
    const featureNode = nodes.value.find(
      node => node.id === 'featureEngineering',
    )
    const testScoreNode = nodes.value.find(node => node.id === 'testScore')
    const modelNodes = nodes.value.filter(
      node => node.id.startsWith('model') && node.id !== 'modelMore',
    )

    const preprocessPipelines = preprocessNode?.data.config.pipeline ?? []
    const featureEngineeringPipelines = featureNode?.data.config.pipeline ?? []
    const validationConfig = testScoreNode?.data.config.validation ?? {}
    const metrics = testScoreNode?.data.config.metrics ?? []

    return {
      preprocess_pipelines: Array.isArray(preprocessPipelines)
        ? [preprocessPipelines]
        : [],
      feature_engineering_pipelines: Array.isArray(featureEngineeringPipelines)
        ? [featureEngineeringPipelines]
        : [],
      model_names: modelNodes
        .map(
          node =>
            node.data.config.modelName || node.data.label.replace(/\n/g, ' '),
        )
        .filter(Boolean),
      validation_config: validationConfig,
      score_variants: Array.isArray(metrics)
        ? metrics.map(metric =>
          typeof metric === 'string' ? { metric } : metric,
        )
        : [],
      column_config: Array.isArray(dataTableNode?.data.config.columnConfig)
        ? (dataTableNode?.data.config.columnConfig as ColumnConfig[])
        : [],
      target_col:
        selectedTargetColumn.value?.name
        ?? testScoreNode?.data.config.targetCol
        ?? '是否跌倒',
    }
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

  // 上傳論文檔案，呼叫 n8n webhook，並將回傳的 workflow JSON 直接載入畫布
  async function handlePaperFileChange (event: Event): Promise<void> {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0] ?? null
    target.value = ''
    if (!file) return

    paperUploading.value = true
    workflowError.value = null

    try {
      // n8n Extract from File 預設讀取 binary 屬性名稱為 "data"
      const formData = new FormData()
      formData.append('data', file, file.name)

      const response = await fetch(N8N_PAPER_WEBHOOK_URL, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        throw new Error(
          `n8n webhook 回應錯誤：${response.status} ${errorText}`,
        )
      }

      const contentType = response.headers.get('content-type') ?? ''
      const result = contentType.includes('application/json')
        ? await response.json()
        : await response.text()
      console.log('[n8n] analyze-paper response:', result)

      // n8n Respond to Webhook 回傳陣列，取第一筆即為 workflow JSON
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
      workflowError.value
        = error instanceof Error ? error.message : '論文上傳失敗'
      console.error('[n8n] analyze-paper error:', error)
    } finally {
      paperUploading.value = false
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
    overflow-y: auto;
    overflow-x: hidden;
    overscroll-behavior: contain;
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
</style>
