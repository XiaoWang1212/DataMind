import { ref } from 'vue'
import type { DemoStep } from '@/constants/workflowData'
import { DEMO_FINISH_LINGER, NODE_RUN_DURATION } from '@/constants/workflowData'
import type { FlowNode } from '@/types/workflow'

const DYNAMIC_NODE_IDS = ['preprocessor', 'featureEngineering'] as const

export function useWorkflowDemo() {
  const nodeStatuses = ref<Map<string, 'running' | 'finished'>>(new Map())
  const isDemoRunning = ref(false)
  const isDemoFinished = ref(false)
  const demoTimers: number[] = []

  function resetDemo(): void {
    nodeStatuses.value = new Map()
    isDemoRunning.value = false
    isDemoFinished.value = false
    for (const timer of demoTimers) clearTimeout(timer)
    demoTimers.length = 0
  }

  function scheduleWorkflowSteps(steps: DemoStep[], baseDelay = 0, skipEndMarker = false): void {
    if (steps.length === 0) return

    for (const { nodeIds, delay, duration } of steps) {
      const offset = delay - baseDelay
      if (offset < 0) continue
      const runDuration = duration ?? NODE_RUN_DURATION

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
        }, offset + runDuration),
      )
    }

    if (!skipEndMarker) {
      const lastStep = steps.at(-1)!
      const lastRunDuration = lastStep.duration ?? NODE_RUN_DURATION
      const endTime = lastStep.delay - baseDelay + lastRunDuration + DEMO_FINISH_LINGER
      demoTimers.push(
        window.setTimeout(() => {
          isDemoRunning.value = false
          isDemoFinished.value = true
        }, endTime),
      )
    }
  }

  /** 只把節點設為 running（不自動 finish），等後端回應後再呼叫 finishGatedSteps */
  function scheduleGatedStart(steps: DemoStep[], baseDelay = 0): void {
    for (const { nodeIds, delay } of steps) {
      const offset = delay - baseDelay
      if (offset < 0) continue
      demoTimers.push(
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'running')
          nodeStatuses.value = next
        }, offset),
      )
    }
  }

  /** 後端回應後，依序讓每組節點跑完 running → finished 動畫，再結束整體流程 */
  function finishGatedSteps(steps: DemoStep[]): void {
    let seqDelay = 0
    for (const { nodeIds } of steps) {
      demoTimers.push(
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'running')
          nodeStatuses.value = next
        }, seqDelay),
        window.setTimeout(() => {
          const next = new Map(nodeStatuses.value)
          for (const id of nodeIds) next.set(id, 'finished')
          nodeStatuses.value = next
        }, seqDelay + NODE_RUN_DURATION),
      )
      seqDelay += NODE_RUN_DURATION + 200
    }
    demoTimers.push(
      window.setTimeout(() => {
        isDemoRunning.value = false
        isDemoFinished.value = true
      }, seqDelay + DEMO_FINISH_LINGER),
    )
  }

  function buildDemoSteps(nodes: FlowNode[]): DemoStep[] {
    const FILE_DURATION = 1000
    const common: DemoStep[] = [
      { nodeIds: ['file'], delay: 0, duration: FILE_DURATION },
      { nodeIds: ['distribution'], delay: FILE_DURATION + 100 },
      { nodeIds: ['dataTable'], delay: FILE_DURATION + 500 },
      { nodeIds: ['settings'], delay: FILE_DURATION + 1500 },
    ]
    const presentPipeline = (DYNAMIC_NODE_IDS as readonly string[]).filter(id =>
      nodes.some(n => n.id === id),
    )
    const modelNodeIds = nodes.filter(n => n.id.startsWith('model-')).map(n => n.id)
    const hasComputeCiNode = nodes.some(n => n.id === 'computeCi')
    const resultNodeIds = [
      'featureImportance',
      'confusionMatrix',
      ...(hasComputeCiNode ? ['computeCi'] : []),
    ]

    const SETTINGS_END = FILE_DURATION + 1500 + NODE_RUN_DURATION
    const PIPELINE_BASE = SETTINGS_END + 200

    if (presentPipeline.length === 0 && modelNodeIds.length === 0) {
      return [
        ...common,
        { nodeIds: ['testScore'], delay: PIPELINE_BASE },
        { nodeIds: resultNodeIds, delay: PIPELINE_BASE + 1200 },
      ]
    }

    let delay = PIPELINE_BASE
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
      { nodeIds: resultNodeIds, delay: delay + 1200 },
    ]
  }

  return {
    nodeStatuses,
    isDemoRunning,
    isDemoFinished,
    demoTimers,
    resetDemo,
    scheduleWorkflowSteps,
    scheduleGatedStart,
    finishGatedSteps,
    buildDemoSteps,
  }
}
