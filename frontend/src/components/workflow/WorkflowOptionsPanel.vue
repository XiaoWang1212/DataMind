<template>
  <!-- 抽屜內容容器：由 Workspace 控制顯示/隱藏 -->
  <section class="setting-area">
    <!-- 有選到節點時才渲染內容 -->
    <div v-if="selectedNode" class="panel">
      <!-- 標題區：顯示目前節點名稱與說明，色點對應節點分類色（見 §2.3） -->
      <div
        class="panel-header"
        :style="{ '--panel-color': `var(--color-node-${selectedNode.data.nodeType})` }"
      >
        <h3><span class="panel-header__dot" />{{ selectedNode.data.label.replace(/\n/g, " ") }}</h3>
        <p>{{ selectedNode.data.description }}</p>
      </div>

      <div class="panel-body">
        <template v-if="selectedNode.id === 'dataTable'">
          <DataTablePanel
            :column-config="localConfig.columnConfig as ColumnConfig[]"
            :file="props.file"
            :file-name="fileName"
            :loading="props.pausedNodeId === 'dataTable'"
            @apply-column-config="handleApplyColumnConfig"
            @update-column-config="handleColumnConfigChange"
          />
        </template>

        <!-- Distribution 節點：顯示當前資料視覺化 -->
        <template v-if="selectedNode.id === 'distribution'">
          <DistributionPanel
            :drawer-stage="props.drawerStage"
            :file="props.file"
            :file-name="fileName"
          />
        </template>

        <template v-else-if="selectedNode.id === 'featureImportance'">
          <FeatureImportancePanel
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>

        <template v-else-if="selectedNode.id === 'confusionMatrix'">
          <ConfusionMatrixPanel
            :project-id="props.projectId"
            :workflow-result="props.workflowResult ?? undefined"
          />
        </template>

        <!-- Preprocessor 節點：顯示前處理步驟 -->
        <template v-else-if="selectedNode.id === 'preprocessor'">
          <PreprocessorPanel
            v-if="preprocessorPipeline.length > 0"
            :pipeline="preprocessorPipeline"
          />
          <template v-else>
            <div
              v-for="field in selectedNode.data.fields"
              :key="field.key"
              class="form-row"
            >
              <label :for="field.key">{{ field.label }}</label>
              <select :id="field.key" v-model="localConfig[field.key]">
                <option
                  v-for="option in field.options ?? []"
                  :key="option"
                  :value="option"
                >
                  {{ option }}
                </option>
              </select>
            </div>
            <div
              v-if="selectedNode.data.fields.length === 0"
              class="info-text"
            >
              尚未設定前處理步驟。
            </div>
          </template>
        </template>

        <!-- Settings 節點：前處理 + 特徵工程 + 模型 -->
        <template v-else-if="selectedNode.id === 'settings'">
          <SettingsPanel
            :available-models="availableModels"
            :compute-ci="settingsComputeCi"
            :dataset-columns="settingsDatasetColumns"
            :feature-engineering="settingsFeatureEngineering"
            :model-options-loading="props.modelOptionsLoading"
            :models="settingsModels"
            :preprocessing="settingsPreprocessing"
            :used-model-names="(props.usedModelNames ?? [])"
            :validation="settingsValidation"
            @add-model="name => emit('add-model', name)"
            @back-node="emit('back-node')"
            @continue="emit('continue-settings')"
            @remove-model="name => emit('remove-model', name)"
            @step-change="step => emit('settings-step-change', step)"
            @update-compute-ci="handleSettingsComputeCiUpdate"
            @update-feature-engineering="handleSettingsFEUpdate"
            @update-preprocessing="handleSettingsPreprocessingUpdate"
            @update-validation="handleSettingsValidationUpdate"
          />
        </template>

        <!-- Feature Engineering 節點：顯示特徵工程設定 -->
        <template v-else-if="selectedNode.id === 'featureEngineering'">
          <FeatureEngineeringPanel :pipeline="featureEngineeringPipeline" />
        </template>

        <!-- Compute CI 節點：唯讀介紹面板 -->
        <template v-else-if="selectedNode.id === 'computeCi'">
          <ComputeCiPanel :workflow-result="props.workflowResult ?? undefined" />
        </template>

        <!-- Test & Score 節點：顯示評分摘要 -->
        <template v-else-if="selectedNode.id === 'testScore'">
          <TestScorePanel :summary="workflowSummary" />
        </template>

        <template v-else-if="selectedNode.id === 'modelMore'">
          <div class="form-row">
            <label for="available-models">可用模型</label>
            <select
              id="available-models"
              v-model="selectedModel"
              :disabled="modelOptionsLoading || availableModels.length === 0"
            >
              <option disabled value="">
                {{ modelOptionsLoading ? "載入中..." : "請選擇模型" }}
              </option>
              <option
                v-for="model in availableModels"
                :key="model"
                :value="model"
              >
                {{ model }}
              </option>
            </select>
          </div>
          <div class="form-row">
            <AppButton
              :disabled="!selectedModel || modelOptionsLoading"
              variant="primary"
              @click="handleAddModel"
            >
              新增模型
            </AppButton>
          </div>
          <div v-if="availableModels.length === 0" class="info-text">
            目前沒有可用模型，請稍後再試。
          </div>
        </template>

        <template v-else-if="isModelNode">
          <div class="form-row">
            <label>Model</label>
            <div>
              {{
                selectedNode.data.config.modelName ||
                  selectedNode.data.label.replace(/\n/g, " ")
              }}
            </div>
          </div>
          <div v-if="selectedNode.data.fields.length === 0" class="info-text">
            此模型目前沒有額外設定。
          </div>
          <div v-else-if="selectedNode.data.fields.length > 0">
            <div
              v-for="field in selectedNode.data.fields"
              :key="field.key"
              class="form-row"
            >
              <label :for="field.key">{{ field.label }}</label>

              <input
                v-if="field.type === 'text'"
                :id="field.key"
                v-model="localConfig[field.key]"
                type="text"
              >

              <input
                v-else-if="field.type === 'number'"
                :id="field.key"
                v-model.number="localConfig[field.key]"
                min="0"
                type="number"
              >

              <select v-else :id="field.key" v-model="localConfig[field.key]">
                <option
                  v-for="option in field.options ?? []"
                  :key="option"
                  :value="option"
                >
                  {{ option }}
                </option>
              </select>
            </div>
          </div>
        </template>

        <!-- 非 Data Table / File / Distribution / Feature Engineering / Test & Score 節點：依 fields 動態渲染一般表單 -->
        <template v-else-if="!isModelNode">
          <div
            v-for="field in selectedNode.data.fields"
            :key="field.key"
            class="form-row"
          >
            <label :for="field.key">{{ field.label }}</label>

            <input
              v-if="field.type === 'text'"
              :id="field.key"
              v-model="localConfig[field.key]"
              type="text"
            >

            <input
              v-else-if="field.type === 'number'"
              :id="field.key"
              v-model.number="localConfig[field.key]"
              min="0"
              type="number"
            >

            <select v-else :id="field.key" v-model="localConfig[field.key]">
              <option
                v-for="option in field.options ?? []"
                :key="option"
                :value="option"
              >
                {{ option }}
              </option>
            </select>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { ConfigValue, SimpleNode } from '@/types/workflow'
  import type { Stage } from '@/composables/useDrawerDrag'
  import { computed, reactive, ref, watch } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import ComputeCiPanel from './nodePanel/ComputeCiPanel.vue'
  import ConfusionMatrixPanel from './nodePanel/ConfusionMatrixPanel.vue'
  import DataTablePanel from './nodePanel/DataTablePanel.vue'
  import DistributionPanel from './nodePanel/DistributionPanel.vue'
  import FeatureEngineeringPanel from './nodePanel/FeatureEngineeringPanel.vue'
  import FeatureImportancePanel from './nodePanel/FeatureImportancePanel.vue'
  import PreprocessorPanel from './nodePanel/PreprocessorPanel.vue'
  import SettingsPanel from './nodePanel/SettingsPanel.vue'
  import TestScorePanel from './nodePanel/TestScorePanel.vue'

  type ColumnType = 'numeric' | 'categorial' | 'text' | 'datetime'
  type ColumnRole = 'feature' | 'target' | 'meta' | 'skip'

  interface ColumnConfig {
    name: string
    type: ColumnType
    role: ColumnRole
  }

  type TestScoreSummary = {
    model_name: string
    split_name: string
    metrics: Array<{ metric: string, valueFormatted: string }>
  }

  const props = defineProps<{
    selectedNode: SimpleNode | null
    file?: File | null
    workflowFileName?: string | null
    workflowSummary?: TestScoreSummary[]
    workflowResult?: Record<string, unknown> | null
    pausedNodeId?: string | null
    drawerStage?: Stage
    availableModels?: string[]
    usedModelNames?: string[]
    modelOptionsLoading?: boolean
    validationConfig?: Record<string, unknown>
    datasetColumns?: Array<{ name: string, type: string, role: string }>
    projectId?: string
  }>()

  // 將設定變更回傳給父層
  const emit = defineEmits<{
    (
      e: 'update-config',
      payload: { nodeId: string, config: Record<string, ConfigValue> },
    ): void
    (e: 'open-upload' | 'apply-column-config' | 'continue-settings' | 'back-node'): void
    (e: 'update:file', file: File): void
    (e: 'add-model' | 'remove-model', modelName: string): void
    (e: 'settings-step-change', step: number): void
  }>()

  // localConfig：面板內可編輯的暫存設定，按下「儲存設定」才同步給父層
  const localConfig = reactive<Record<string, ConfigValue>>({})
  const selectedModel = ref<string>('')

  const isModelNode = computed(() =>
    props.selectedNode?.id.startsWith('model'),
  )

  const fileName = computed(() => {
    if (typeof localConfig.fileName === 'string' && localConfig.fileName) {
      return localConfig.fileName
    }
    return props.workflowFileName ?? ''
  })

  const availableModels = computed(() => props.availableModels ?? [])
  const workflowSummary = computed(() => props.workflowSummary ?? [])

  watch(
    () => availableModels.value,
    models => {
      selectedModel.value = models.length > 0 ? models[0]! : ''
    },
    { immediate: true },
  )

  watch(
    () => props.selectedNode?.id,
    () => {
      selectedModel.value
        = availableModels.value.length > 0 ? availableModels.value[0]! : ''
    },
  )

  function handleAddModel (): void {
    if (!selectedModel.value) return
    emit('add-model', selectedModel.value)
  }

  function handleColumnConfigChange (value: ColumnConfig[]): void {
    localConfig.columnConfig = value
    if (!props.selectedNode) return
    emit('update-config', {
      nodeId: props.selectedNode.id,
      config: { columnConfig: value },
    })
  }

  function handleApplyColumnConfig (): void {
    emit('apply-column-config')
  }

  const featureEngineeringPipeline = computed(() => {
    const pipelineValue = localConfig.pipeline
    return Array.isArray(pipelineValue)
      ? (pipelineValue as Array<Record<string, unknown>>)
      : []
  })

  const preprocessorPipeline = computed(() => {
    const pipelineValue = localConfig.pipeline
    return Array.isArray(pipelineValue)
      ? (pipelineValue as Array<Record<string, unknown>>)
      : []
  })

  const settingsPreprocessing = computed(() => {
    const v = localConfig.preprocessing
    return Array.isArray(v) ? (v as Array<Record<string, unknown>>) : []
  })

  const settingsFeatureEngineering = computed(() => {
    const v = localConfig.featureEngineering
    return Array.isArray(v) ? (v as Array<Record<string, unknown>>) : []
  })

  const settingsModels = computed(() => {
    const used = props.usedModelNames ?? []
    return used.map(name => ({ name, type: 'Classification' }))
  })

  const settingsComputeCi = computed(() => Boolean(localConfig.compute_ci ?? false))

  const settingsValidation = computed(() => props.validationConfig ?? {})
  const settingsDatasetColumns = computed(() => props.datasetColumns ?? [])

  function handleSettingsPreprocessingUpdate (steps: Array<Record<string, unknown>>): void {
    localConfig.preprocessing = steps
    if (!props.selectedNode) return
    emit('update-config', { nodeId: props.selectedNode.id, config: { preprocessing: steps } })
  }

  function handleSettingsFEUpdate (steps: Array<Record<string, unknown>>): void {
    localConfig.featureEngineering = steps
    if (!props.selectedNode) return
    emit('update-config', { nodeId: props.selectedNode.id, config: { featureEngineering: steps } })
  }

  function handleSettingsComputeCiUpdate (value: boolean): void {
    localConfig.compute_ci = value
    if (!props.selectedNode) return
    emit('update-config', { nodeId: props.selectedNode.id, config: { compute_ci: value } })
  }

  function handleSettingsValidationUpdate (value: Record<string, unknown>): void {
    emit('update-config', { nodeId: 'testScore', config: { validation: value } })
  }

  // 當切換節點時，把該節點 config 複製到本地表單狀態
  watch(
    () => props.selectedNode,
    node => {
      // 先清空舊資料，避免欄位殘留
      for (const key of Object.keys(localConfig)) delete localConfig[key]
      if (!node) {
        return
      }
      Object.assign(localConfig, node.data.config)
    },
    { immediate: true },
  )
</script>

<style scoped>
  .setting-area {
    flex: 1;
    border: none;
    border-radius: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: transparent;
  }

  .panel-header {
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    background: transparent;
  }

  .panel-header h3 {
    margin: 0 0 2px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    color: var(--color-text);
  }

  .panel-header__dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--panel-color, var(--color-accent));
  }

  .panel-header p {
    margin: 0;
    font-size: 13px;
    color: var(--color-secondary);
  }

  .panel-body {
    flex: 1;
    min-height: 0;
    overflow: visible;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 4px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 10px;
  }

  .form-row label {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-secondary);
  }

  .form-row input,
  .form-row select {
    border: 1px solid color-mix(in oklab, var(--color-accent) 20%, transparent);
    border-radius: var(--radius-sm);
    padding: 7px 10px;
    font-size: 13px;
    outline: none;
    background: rgba(255, 255, 255, 0.5);
  }

  /* 隱藏原生 select 箭頭，換成自訂 chevron */
  .form-row select {
    appearance: none;
    -webkit-appearance: none;
    padding-right: 32px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23E8A33D' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    cursor: pointer;
  }

  @media (max-width: 768px) {
    /* 手機：改為單欄表單，避免標籤與輸入框擠壓 */
    .setting-area {
      padding: 12px 14px 16px;
    }

    .panel-header h3 {
      font-size: 15px;
    }

    .panel-header p {
      font-size: 12px;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 6px;
    }

    .form-row label {
      font-size: 12px;
    }

    .form-row input,
    .form-row select {
      font-size: 12px;
      padding: 8px 9px;
    }

  }

</style>
