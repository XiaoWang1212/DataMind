import type { Ref } from 'vue'
import { computed, ref } from 'vue'
import { type Edge, Position } from '@vue-flow/core'
import { INITIAL_EDGES, INITIAL_NODES } from '@/constants/workflowData'
import type { EdgeBase, FlowNode } from '@/types/workflow'

export const DYNAMIC_NODE_IDS = ['preprocessor', 'featureEngineering'] as const
export const RESULT_NODE_IDS = ['featureImportance', 'confusionMatrix', 'computeCi'] as const
export const MODEL_Y_GAP = 110

const STEP_HIGHLIGHT_COLORS = ['#f0e274', '#f0e274', '#f0e274', '#f0e274'] as const

export function useWorkflowNodes(
  nodeStatuses: Ref<Map<string, 'running' | 'finished'>>,
  isDemoFinished: Ref<boolean>,
  selectedNodeId: Ref<string | null>,
  settingsStep: Ref<number>,
  nodeFlash: Ref<Map<string, 'add' | 'remove'>>,
) {
  const nodes = ref<FlowNode[]>(INITIAL_NODES)
  const edges = ref<EdgeBase[]>(INITIAL_EDGES)

  // ─── computed ────────────────────────────────────────────────────────────

  const dataTableColumnConfig = computed(() => {
    const node = nodes.value.find(n => n.id === 'dataTable')
    if (!node) return [] as Array<{ name: string; type: string; role: string }>
    const config = node.data.config.columnConfig
    return Array.isArray(config)
      ? (config as Array<{ name: string; type: string; role: string }>)
      : []
  })

  const selectedTargetColumn = computed(() =>
    dataTableColumnConfig.value.find(col => col.role === 'target'),
  )

  const usedModelNames = computed<string[]>(() =>
    nodes.value
      .filter(n => n.id.startsWith('model-'))
      .map(n => String(n.data.config.modelName ?? n.data.label ?? ''))
      .filter(Boolean),
  )

  function getHighlightedIds(): Set<string> {
    if (selectedNodeId.value !== 'settings') return new Set()
    const step = settingsStep.value
    if (step === 0) return new Set(['preprocessor'])
    if (step === 1) return new Set(['featureEngineering'])
    if (step === 2) return new Set(nodes.value.filter(n => n.id.startsWith('model-')).map(n => n.id))
    if (step === 3) return new Set(['computeCi'])
    return new Set()
  }

  const canvasNodes = computed<FlowNode[]>(() => {
    const highlightedIds = getHighlightedIds()
    const color: string | null = STEP_HIGHLIGHT_COLORS[settingsStep.value] ?? null
    return nodes.value.map(node => {
      const status = nodeStatuses.value.get(node.id) ?? null
      const highlighted = highlightedIds.has(node.id)
      return {
        ...node,
        class: node.id.startsWith('model-') ? 'node-non-interactive' : '',
        data: {
          ...node.data,
          status,
          highlighted,
          highlightColor: highlighted ? color : null,
          isSelected: node.id === selectedNodeId.value,
          flashType: nodeFlash.value.get(node.id) ?? null,
        },
      }
    })
  })

  const canvasEdges = computed<Edge[]>(() =>
    edges.value.map((edge): Edge => {
      const id = String(edge.id)
      let done: boolean
      if (id.startsWith('etm')) {
        // pipeline → model：該 model 開始 running 才連線（逐一連接）
        done = nodeStatuses.value.has(String(edge.target))
      } else if (id.startsWith('emts')) {
        // model → testScore：等全部 model 完成、testScore 開始才一起連線
        done = nodeStatuses.value.has(String(edge.target))
      } else {
        done = nodeStatuses.value.get(String(edge.source)) === 'finished'
      }
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
    const maxBottom = Math.max(...canvasNodes.value.map(n => n.position.y + 140))
    return Math.max(520, maxBottom + 120)
  })

  const canvasMinWidth = computed<number>(() => {
    if (canvasNodes.value.length === 0) return 860
    const maxRight = Math.max(...canvasNodes.value.map(n => n.position.x + 180))
    return Math.max(860, maxRight + 160)
  })

  // ─── node sync helpers ───────────────────────────────────────────────────

  function getLastPreModelNodeId(): string {
    if (nodes.value.some(n => n.id === 'featureEngineering')) return 'featureEngineering'
    if (nodes.value.some(n => n.id === 'preprocessor')) return 'preprocessor'
    return 'settings'
  }

  function updateFileNodeConfig(fileName: string | null): void {
    nodes.value = nodes.value.map(node => {
      if (node.id !== 'file') return node
      return {
        ...node,
        data: { ...node.data, config: { ...node.data.config, fileName } },
      }
    })
  }

  function syncModelCanvasNodes(modelList: Array<unknown>): void {
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
          nodeType: 'model',
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

  function syncPipelineCanvasNodes(): void {
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
          nodeType: 'transform',
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

  function syncComputeCiNode(): void {
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
          nodeType: 'evaluate',
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

  function ensureDynamicNodes(): void {
    const settingsNode = nodes.value.find(n => n.id === 'settings')
    if (!settingsNode) return

    const preprocessing = Array.isArray(settingsNode.data.config.preprocessing)
      ? (settingsNode.data.config.preprocessing as Array<Record<string, unknown>>)
      : []
    const featureEng = Array.isArray(settingsNode.data.config.featureEngineering)
      ? (settingsNode.data.config.featureEngineering as Array<Record<string, unknown>>)
      : []

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
          ? { icon: 'mdi-filter-cog-outline', label: 'Preprocessor', nodeType: 'transform', description: '資料前處理', fields: [], config: { pipeline: preprocessing } }
          : { icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', nodeType: 'transform', description: '特徵工程', fields: [], config: { pipeline: featureEng } },
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

    const settingsModels = Array.isArray(settingsNode.data.config.models)
      ? settingsNode.data.config.models as Array<unknown>
      : []
    const currentModelCount = nodes.value.filter(n => n.id.startsWith('model-')).length
    // 只有在畫布上完全沒有 model 節點時才從 settings 補齊（例如首次從框架 JSON 建立）；
    // 若 model 節點已存在（由 localStorage 還原），就以它們為準，不用 settings 舊清單覆寫，
    // 否則使用者透過 UI 增刪的模型會在重新整理後被還原成框架預設清單
    if (settingsModels.length > 0 && currentModelCount === 0) {
      syncModelCanvasNodes(settingsModels)
    } else if (settingsModels.length === 0 && currentModelCount === 0) {
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

  return {
    nodes,
    edges,
    canvasNodes,
    canvasEdges,
    canvasMinHeight,
    canvasMinWidth,
    dataTableColumnConfig,
    selectedTargetColumn,
    usedModelNames,
    updateFileNodeConfig,
    syncModelCanvasNodes,
    syncPipelineCanvasNodes,
    syncComputeCiNode,
    ensureDynamicNodes,
  }
}
