import type { ComputedRef, Ref } from 'vue'
import { computed, ref } from 'vue'
import { executeWorkflowApi, fetchWorkflowJob, startWorkflowJob } from '@/api/workflow'
import type { DemoStep } from '@/constants/workflowData'
import type { FlowNode } from '@/types/workflow'
import { summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'

type ColumnConfig = { name: string; type: string; role: string }

const JOB_POLL_INTERVAL_MS = 1500

export function useWorkflowExecution(deps: {
  nodes: Ref<FlowNode[]>
  workflowDataFile: Ref<File | null>
  selectedTargetColumn: ComputedRef<ColumnConfig | undefined>
  nodeStatuses: Ref<Map<string, 'running' | 'finished'>>
  isDemoRunning: Ref<boolean>
  isDemoFinished: Ref<boolean>
  buildDemoSteps: (nodes: FlowNode[]) => DemoStep[]
  scheduleWorkflowSteps: (steps: DemoStep[], baseDelay?: number, skipEndMarker?: boolean) => void
  finishGatedSteps: (steps: DemoStep[]) => void
  selectedNodeId: Ref<string | null>
  expandDrawer: () => void
  onProgress?: (pct: number) => void
  onJobActive?: (jobId: string) => void
}) {
  const {
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
    onProgress,
    onJobActive,
  } = deps

  const workflowResult = ref<null | Record<string, unknown>>(null)
  const workflowError = ref<string | null>(null)
  const pausedAtNodeId = ref<string | null>(null)
  const dataTableApplied = ref(false)
  const activeJobId = ref<string | null>(null)
  const pollIntervalId = ref<number | null>(null)

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

  const workflowSummary = computed(() => summarizeWorkflowResult(workflowResult.value))

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
      target_col: selectedTargetColumn.value?.name ?? testScoreNode?.data.config.targetCol ?? '',
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

  /** 從目前的 nodes 推算 model 節點順序與「所有 model 跑完後」要播放的後續步驟 */
  function getModelPhaseInfo (): { modelNodeIdsOrdered: string[], postModelSteps: DemoStep[] } {
    const steps = buildDemoSteps(nodes.value)
    const modelGatedStep = steps.find(s => s.nodeIds.some(id => id.startsWith('model-')))
    const modelNodeIdsOrdered = modelGatedStep ? modelGatedStep.nodeIds : []
    const apiGatedSteps = modelGatedStep ? steps.filter(s => s.delay >= modelGatedStep.delay) : []
    const postModelSteps = modelGatedStep ? apiGatedSteps.filter(s => s !== modelGatedStep) : apiGatedSteps
    return { modelNodeIdsOrdered, postModelSteps }
  }

  /** 立即把後置步驟標記為完成，不經過動畫；用於重新打開頁面或輪詢時才發現 job 早已跑完／出錯的情境，
   * 避免動畫用的 setTimeout 鏈被使用者離開頁面打斷，導致 isDemoFinished 永遠卡在 false，
   * 進而讓下次打開頁面時誤判成「需要退回 checkpoint」而把已完成的節點狀態清空 */
  function finishStepsImmediately (steps: DemoStep[]): void {
    const next = new Map(nodeStatuses.value)
    for (const step of steps) {
      for (const id of step.nodeIds) {
        next.set(id, 'finished')
      }
    }
    nodeStatuses.value = next
    isDemoRunning.value = false
    isDemoFinished.value = true
  }

  /** 輪詢後端背景 job：依真實完成數推進節點動畫與專案進度，刷新後也能用同一個 job_id 接續呼叫 */
  function pollJob (
    jobId: string,
    modelNodeIdsOrdered: string[],
    postModelSteps: DemoStep[],
    seenInit = 0,
  ): void {
    let seen = seenInit
    pollIntervalId.value = window.setInterval(() => {
      ;(async () => {
        try {
          const job = await fetchWorkflowJob(jobId)

          if (job.completedModels.length > seen) {
            const next = new Map(nodeStatuses.value)
            for (let i = seen; i < job.completedModels.length; i += 1) {
              next.set(modelNodeIdsOrdered[i]!, 'finished')
              const nextNodeId = modelNodeIdsOrdered[i + 1]
              if (nextNodeId) {
                next.set(nextNodeId, 'running')
              }
            }
            nodeStatuses.value = next
            seen = job.completedModels.length
          }

          if (modelNodeIdsOrdered.length > 0) {
            onProgress?.(Math.round((seen / modelNodeIdsOrdered.length) * 100))
          }

          if (job.status === 'done') {
            if (pollIntervalId.value !== null) window.clearInterval(pollIntervalId.value)
            pollIntervalId.value = null
            activeJobId.value = null
            workflowResult.value = job.result
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          } else if (job.status === 'error') {
            if (pollIntervalId.value !== null) window.clearInterval(pollIntervalId.value)
            pollIntervalId.value = null
            activeJobId.value = null
            workflowError.value = job.error ?? 'Workflow 執行失敗'
            window.setTimeout(() => finishGatedSteps(postModelSteps), 200)
          }
        } catch {
          // 輪詢暫時失敗（網路抖動等），下一輪再試，不中斷整個流程
        }
      })()
    }, JOB_POLL_INTERVAL_MS)
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
        next.set('settings', 'running')
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
      if (!workflowDataFile.value) {
        workflowError.value = '請先在 File 節點上傳 CSV 資料檔案。'
        return
      }

      pausedAtNodeId.value = null
      isDemoRunning.value = true
      workflowError.value = null
      workflowResult.value = null

      const next = new Map(nodeStatuses.value)
      next.set('settings', 'finished')
      nodeStatuses.value = next

      const steps = buildDemoSteps(nodes.value)
      const settingsStep = steps.find(s => s.nodeIds.includes('settings'))
      if (!settingsStep) return

      const remainingSteps = steps.filter(s => s.delay > settingsStep.delay)

      // model 步驟：等後端逐一回傳才 finish；其餘前置 pipeline 用固定時長
      const modelGatedStep = remainingSteps.find(s => s.nodeIds.some(id => id.startsWith('model-')))
      const apiGatedSteps = modelGatedStep
        ? remainingSteps.filter(s => s.delay >= modelGatedStep.delay)
        : []
      const postModelSteps = modelGatedStep
        ? apiGatedSteps.filter(s => s !== modelGatedStep)
        : apiGatedSteps
      const preModelSteps = remainingSteps.filter(s => !apiGatedSteps.includes(s))

      // 依序播放前處理動畫（緊接，每步 1s）
      const PIPELINE_STEP_MS = 1000
      let seqOffset = 0
      for (const step of preModelSteps) {
        const start = seqOffset
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of step.nodeIds) {
            next.set(id, 'running')
          }
          nodeStatuses.value = next
        }, start)
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of step.nodeIds) {
            next.set(id, 'finished')
          }
          nodeStatuses.value = next
        }, start + PIPELINE_STEP_MS)
        seqOffset += PIPELINE_STEP_MS + 100
      }

      // 前處理全部完成後才啟動 model loading 和 API 呼叫
      const postPipelineDelay = seqOffset

      // 依序執行：一次只讓一個 model 進入 running，該 model API 回傳後才讓下一個開始
      const modelNodeIdsOrdered = modelGatedStep ? modelGatedStep.nodeIds : []
      if (modelNodeIdsOrdered.length > 0) {
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          next.set(modelNodeIdsOrdered[0]!, 'running')
          nodeStatuses.value = next
        }, postPipelineDelay)
      }

      const payload = buildWorkflowPayload()
      const file = workflowDataFile.value

      window.setTimeout(() => {
        ;(async () => {
          try {
            const { jobId } = await startWorkflowJob({ file, workflowPayload: payload })
            activeJobId.value = jobId
            onJobActive?.(jobId)
            pollJob(jobId, modelNodeIdsOrdered, postModelSteps)
          } catch (error) {
            workflowError.value = error instanceof Error ? error.message : 'Workflow 執行失敗'
            window.setTimeout(() => {
              finishGatedSteps(postModelSteps)
            }, 200)
          }
        })()
      }, postPipelineDelay)
    }
  }

  /** 刷新後若有上次留下的 job_id，先確認後端 job 的真實狀態再決定怎麼接續 */
  async function resumeJob (): Promise<'resumed' | 'completed' | 'missing'> {
    if (!activeJobId.value) {
      // activeJobId 可能在「結尾動畫」播完前就被清空了（例如即時輪詢時 job 一跑完就立刻
      // 清空 activeJobId，但動畫還要再跑個 1~2 秒才會把 isDemoFinished 設成 true；如果使用者
      // 這時候離開頁面，動畫就會被中斷）。只要 workflowResult 已經拿到，就代表 job 真的跑完了，
      // 直接補上完成狀態即可，不能誤判成「job 找不到」而退回 checkpoint 把已完成的節點清空
      if (workflowResult.value) {
        const { postModelSteps } = getModelPhaseInfo()
        finishStepsImmediately(postModelSteps)
        return 'completed'
      }
      return 'missing'
    }
    const jobId = activeJobId.value

    try {
      const job = await fetchWorkflowJob(jobId)
      const { modelNodeIdsOrdered, postModelSteps } = getModelPhaseInfo()

      if (job.status === 'error') {
        activeJobId.value = null
        return 'missing'
      }

      if (job.status === 'done') {
        activeJobId.value = null
        workflowResult.value = job.result
        const next = new Map(nodeStatuses.value)
        for (const id of modelNodeIdsOrdered) {
          next.set(id, 'finished')
        }
        nodeStatuses.value = next
        onProgress?.(100)
        finishStepsImmediately(postModelSteps)
        return 'completed'
      }

      const next = new Map(nodeStatuses.value)
      for (let i = 0; i < job.completedModels.length; i += 1) {
        const id = modelNodeIdsOrdered[i]
        if (id) {
          next.set(id, 'finished')
        }
      }
      const runningId = modelNodeIdsOrdered[job.completedModels.length]
      if (runningId) {
        next.set(runningId, 'running')
      }
      nodeStatuses.value = next
      isDemoRunning.value = true
      onJobActive?.(jobId)
      pollJob(jobId, modelNodeIdsOrdered, postModelSteps, job.completedModels.length)
      return 'resumed'
    } catch {
      activeJobId.value = null
      return 'missing'
    }
  }

  /** 前端放棄目前正在追蹤的 job：停止輪詢、清空 activeJobId。
   * 後端的模型訓練執行緒可能還在跑，但前端從此不再理會其結果。 */
  function abandonActiveJob (): void {
    if (pollIntervalId.value !== null) {
      window.clearInterval(pollIntervalId.value)
      pollIntervalId.value = null
    }
    activeJobId.value = null
  }

  return {
    workflowResult,
    workflowError,
    pausedAtNodeId,
    dataTableApplied,
    activeJobId,
    dataTableCanContinue,
    settingsCanContinue,
    workflowSummary,
    buildWorkflowPayload,
    runWorkflowRequest,
    executeWorkflow,
    continueWorkflow,
    resumeJob,
    abandonActiveJob,
  }
}
