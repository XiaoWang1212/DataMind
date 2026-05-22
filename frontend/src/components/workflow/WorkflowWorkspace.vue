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
      type="button"
      @click="startDemo"
    >
      {{ isDemoRunning ? "⏳" : "▶" }}
    </button>
    <button
      class="demo-btn execute-workflow-btn"
      type="button"
      @click="executeWorkflow"
    >
      執行 Workflow
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

    <div v-if="workflowResult || workflowError" class="workflow-result">
      <div v-if="workflowError" class="workflow-error">{{ workflowError }}</div>
      <div v-if="workflowResult" class="workflow-summary">
        <h4>Score Summary</h4>
        <div v-if="workflowSummary.length > 0" class="summary-list">
          <div
            v-for="(item, index) in workflowSummary"
            :key="`${item.model_name}-${item.split_name}-${index}`"
            class="summary-item"
          >
            <div class="summary-item__header">
              <span>{{ item.model_name }}</span>
              <span>{{ item.split_name }}</span>
            </div>
            <div class="summary-item__metrics">
              <span
                v-for="metric in item.metrics"
                :key="metric.metric"
                class="summary-metric"
              >
                {{ metric.metric }}:
                <strong>{{ metric.valueFormatted }}</strong>
              </span>
            </div>
          </div>
        </div>
        <div v-else class="summary-empty">No summary metrics available.</div>
      </div>
      <pre v-if="workflowResult">{{
        JSON.stringify(workflowResult, null, 2)
      }}</pre>
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
            :selected-node="selectedNode"
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
  import { computed, markRaw, nextTick, onBeforeUnmount, ref } from 'vue'
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
  const jsonFileInput = ref<HTMLInputElement | null>(null)
  const selectedJsonFile = ref<File | null>(null)
  const workflowDataFile = ref<File | null>(null)
  const workflowResult = ref<null | Record<string, unknown>>(null)
  const workflowError = ref<string | null>(null)

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

    results
      .filter((result: any) => result && typeof result === 'object')
      .forEach((result: any) => {
        const modelName = result.model_name || 'unknown'
        const existing = modelGroups.get(modelName) ?? {
          count: 0,
          metrics: {},
          errors: {},
        }

        if (Array.isArray(result.metrics)) {
          result.metrics.forEach((metric: any) => {
            const name = metric.metric || 'unknown'
            if (metric?.error) {
              existing.errors[name] = metric.error
              return
            }
            const value = Number(metric.value)
            if (!Number.isNaN(value)) {
              existing.metrics[name] = existing.metrics[name] ?? []
              existing.metrics[name].push(value)
            }
          })
        }

        existing.count += 1
        modelGroups.set(modelName, existing)
      })

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
    const preprocessorNode = INITIAL_NODES.find(
      node => node.id === 'preprocessor',
    )
    const testScoreNode = INITIAL_NODES.find(node => node.id === 'testScore')
    const confusionMatrixNode = INITIAL_NODES.find(
      node => node.id === 'confusionMatrix',
    )

    if (
      !fileNode
      || !dataTableNode
      || !preprocessorNode
      || !testScoreNode
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

    const updatedPreprocessorNode: FlowNode = {
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
      updatedPreprocessorNode,
      ...(featureNode ? [featureNode] : []),
      ...dynamicModelNodes,
      updatedTestScoreNode,
      confusionMatrixNode,
    ]

    await nextTick()

    const modelEdges = dynamicModelNodes.flatMap((node, index) => [
      {
        id: `e_preprocessor_model_${index}`,
        source: featureNode ? 'featureEngineering' : 'preprocessor',
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
        id: 'e1',
        source: 'dataTable',
        target: 'preprocessor',
        type: 'default',
      },
      ...(featureNode
        ? [
          {
            id: 'e2_feature',
            source: 'preprocessor',
            target: 'featureEngineering',
            type: 'default',
          },
        ]
        : []),
      ...modelEdges,
      {
        id: 'e4',
        source: 'testScore',
        target: 'confusionMatrix',
        type: 'default',
      },
    ]
  }

  function handleDataFile (file: File): void {
    workflowDataFile.value = file
    workflowError.value = null
  }

  function buildWorkflowPayload (): Record<string, unknown> {
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
      target_col: testScoreNode?.data.config.targetCol ?? '是否跌倒',
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
    }
  }

  async function executeWorkflow (): Promise<void> {
    if (!workflowDataFile.value) {
      workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
      return
    }

    const payload = buildWorkflowPayload()
    const formData = new FormData()
    formData.append('file', workflowDataFile.value)
    formData.append('workflow_payload', JSON.stringify(payload))

    workflowError.value = null
    workflowResult.value = null

    try {
      const response = await fetch('/api/models/workflow/execute', {
        method: 'POST',
        body: formData,
      })
      const result = await response.json()
      if (!response.ok) {
        workflowError.value = result.error || `HTTP ${response.status}`
        return
      }
      workflowResult.value = result
    } catch (error) {
      workflowError.value
        = error instanceof Error ? error.message : 'Workflow 執行失敗'
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
    right: 64px;
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
    right: 170px;
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
    overflow-y: auto;
    overflow-x: hidden;
    flex-direction: column;
    overflow: hidden;
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
