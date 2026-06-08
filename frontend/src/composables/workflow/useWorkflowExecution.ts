import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { executeWorkflowApi } from '@/api/workflow'
import type { DemoStep } from '@/constants/workflowData'
import type { FlowNode } from '@/types/workflow'

type ColumnConfig = { name: string; type: string; role: string }

export function useWorkflowExecution(deps: {
  nodes: Ref<FlowNode[]>
  workflowDataFile: Ref<File | null>
  selectedTargetColumn: ComputedRef<ColumnConfig | undefined>
  nodeStatuses: Ref<Map<string, 'running' | 'finished'>>
  isDemoRunning: Ref<boolean>
  buildDemoSteps: (nodes: FlowNode[]) => DemoStep[]
  scheduleWorkflowSteps: (steps: DemoStep[], baseDelay?: number) => void
  selectedNodeId: Ref<string | null>
  expandDrawer: () => void
}) {
  const {
    nodes,
    workflowDataFile,
    selectedTargetColumn,
    nodeStatuses,
    isDemoRunning,
    buildDemoSteps,
    scheduleWorkflowSteps,
    selectedNodeId,
    expandDrawer,
  } = deps

  const workflowResult = ref<null | Record<string, unknown>>(null)
  const workflowError = ref<string | null>(null)
  const pausedAtNodeId = ref<string | null>(null)
  const dataTableApplied = ref(false)

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

  const workflowSummary = computed(() => {
    if (!workflowResult.value) return []
    const results = Array.isArray(workflowResult.value.results)
      ? workflowResult.value.results
      : []

    const modelGroups = new Map<string, { count: number; metrics: Record<string, number[]>; errors: Record<string, string[]> }>()

    for (const result of results.filter((r: any) => r && typeof r === 'object')) {
      const modelName = result.model_name || 'unknown'
      const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

      if (Array.isArray(result.metrics)) {
        for (const metric of result.metrics) {
          const name = metric.metric || 'unknown'
          if (metric?.error) { existing.errors[name] = metric.error; continue }
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
        valueFormatted: values.length > 0
          ? (values.reduce((s, v) => s + v, 0) / values.length).toFixed(4)
          : 'N/A',
      })),
      errors: group.errors,
    }))
  })

  function buildWorkflowPayload(): Record<string, unknown> {
    const dataTableNode = nodes.value.find(n => n.id === 'dataTable')
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    const testScoreNode = nodes.value.find(n => n.id === 'testScore')

    const preprocessing = settingsNode?.data.config.preprocessing ?? []
    const featureEngineering = settingsNode?.data.config.featureEngineering ?? []
    const modelNames = nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => String(n.data.config.modelName ?? n.data.label ?? ''))
      .filter(Boolean)

    return {
      preprocess_pipelines: Array.isArray(preprocessing) ? [preprocessing] : [],
      feature_engineering_pipelines: Array.isArray(featureEngineering) ? [featureEngineering] : [],
      model_names: modelNames,
      validation_config: testScoreNode?.data.config.validation ?? {},
      score_variants: Array.isArray(testScoreNode?.data.config.metrics)
        ? (testScoreNode.data.config.metrics as any[]).map(m => typeof m === 'string' ? { metric: m } : m)
        : [],
      column_config: Array.isArray(dataTableNode?.data.config.columnConfig)
        ? dataTableNode?.data.config.columnConfig
        : [],
      target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '是否跌倒',
      resampling_method: String(testScoreNode?.data.config.resampling_method ?? 'none'),
      resampling_config: (testScoreNode?.data.config.resampling_config ?? {}) as Record<string, unknown>,
      tuning_method: String(testScoreNode?.data.config.tuning_method ?? 'none'),
      tuning_cv: Number(testScoreNode?.data.config.tuning_cv ?? 3),
      tuning_n_iter: Number(testScoreNode?.data.config.tuning_n_iter ?? 20),
      tuning_scoring: String(testScoreNode?.data.config.tuning_scoring ?? 'roc_auc'),
      compute_ci: Boolean(
        nodes.value.find(n => n.id === 'computeCi')?.data.config.enabled
        ?? settingsNode?.data.config.compute_ci
        ?? false,
      ),
    }
  }

  async function runWorkflowRequest(): Promise<void> {
    if (!workflowDataFile.value) {
      workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
      return
    }
    workflowError.value = null
    workflowResult.value = null
    try {
      const payload = buildWorkflowPayload()
      workflowResult.value = await executeWorkflowApi({ file: workflowDataFile.value, workflowPayload: payload })
    } catch (error) {
      workflowError.value = error instanceof Error ? error.message : 'Workflow 執行失敗'
    }
  }

  async function executeWorkflow(): Promise<void> {
    if (!workflowDataFile.value) {
      workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
      return
    }

    nodeStatuses.value = new Map()
    isDemoRunning.value = true
    pausedAtNodeId.value = 'dataTable'
    workflowError.value = null
    workflowResult.value = null
    dataTableApplied.value = false

    nodeStatuses.value = new Map<string, 'running' | 'finished'>([
      ['file', 'finished'],
      ['distribution', 'finished'],
      ['dataTable', 'running'],
    ])
    selectedNodeId.value = 'dataTable'
  }

  function continueWorkflow(): void {
    if (pausedAtNodeId.value === 'dataTable') {
      if (!dataTableCanContinue.value) {
        workflowError.value = selectedTargetColumn.value
          ? '請先按 Apply，再繼續 Workflow。'
          : '請先選擇 target 欄位，再按 Apply。'
        return
      }

      pausedAtNodeId.value = null
      isDemoRunning.value = true

      const steps = buildDemoSteps(nodes.value)
      const dataTableStep = steps.find(s => s.nodeIds.includes('dataTable'))
      const settingsStep = steps.find(s => s.nodeIds.includes('settings'))
      if (!dataTableStep || !settingsStep) return

      const current = new Map(nodeStatuses.value)
      current.set('dataTable', 'finished')
      nodeStatuses.value = current

      const runAt = settingsStep.delay - dataTableStep.delay
      setTimeout(() => {
        const next = new Map(nodeStatuses.value)
        next.set('settings', 'running')
        nodeStatuses.value = next
      }, runAt)
      setTimeout(() => {
        const next = new Map(nodeStatuses.value)
        next.set('settings', 'finished')
        nodeStatuses.value = next
        isDemoRunning.value = false
        pausedAtNodeId.value = 'settings'
        selectedNodeId.value = 'settings'
        expandDrawer()
      }, runAt + 700)
      return
    }

    if (pausedAtNodeId.value === 'settings') {
      if (!settingsCanContinue.value) {
        workflowError.value = '請至少新增一個模型，再繼續 Workflow。'
        return
      }

      pausedAtNodeId.value = null
      isDemoRunning.value = true

      const steps = buildDemoSteps(nodes.value)
      const settingsStep = steps.find(s => s.nodeIds.includes('settings'))
      if (!settingsStep) return

      const remainingSteps = steps.filter(s => s.delay > settingsStep.delay)
      scheduleWorkflowSteps(remainingSteps, settingsStep.delay)
      runWorkflowRequest()
    }
  }

  return {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    dataTableCanContinue,
    settingsCanContinue,
    workflowSummary,
    buildWorkflowPayload,
    runWorkflowRequest,
    executeWorkflow,
    continueWorkflow,
  }
}
