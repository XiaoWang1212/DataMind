import { ref } from 'vue'
import type { Ref } from 'vue'
import { Position } from '@vue-flow/core'
import { analyzeWorkflowFromPdf } from '@/api/gemini'
import { INITIAL_NODES } from '@/constants/workflowData'
import type { EdgeBase, FlowNode } from '@/types/workflow'
import { saveWorkflowJsonFileToStorage } from './useWorkflowStorage'
import { MODEL_Y_GAP } from './useWorkflowNodes'


const N8N_PAPER_WEBHOOK_URL
  = (import.meta.env.VITE_N8N_PAPER_WEBHOOK_URL as string | undefined)
    ?? 'https://ideally-strewn-papyrus.ngrok-free.dev/webhook-test/analyze-paper'

const VALID_PREPROCESS_TYPES = new Set([
  'fill_na', 'knn_impute', 'iterative_impute', 'normalize', 'standardize',
  'one_hot', 'label_encode', 'drop_columns', 'remove_outliers_iqr', 'remove_outliers_zscore',
])
const VALID_FE_TYPES = new Set([
  'select_relevant_features', 'pca', 'discretize_continuous', 'continuize_discrete',
  'normalize_features', 'remove_sparse_features',
])

export function useWorkflowImport (
  nodes: Ref<FlowNode[]>,
  edges: Ref<EdgeBase[]>,
  syncComputeCiNode: () => void,
  saveState: () => void,
  fileInputRefs: {
    jsonFileInput: Ref<HTMLInputElement | null>
    paperFileInput: Ref<HTMLInputElement | null>
    geminiFileInput: Ref<HTMLInputElement | null>
  },
) {
  const { jsonFileInput, paperFileInput, geminiFileInput } = fileInputRefs
  const paperUploading = ref(false)
  const geminiUploading = ref(false)
  const selectedJsonFile = ref<File | null>(null)
  const workflowError = ref<string | null>(null)

  async function loadJsonModels(file: File): Promise<void> {
    if (!file.name.toLowerCase().endsWith('.json')) return

    const rawText = await file.text()
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(rawText) as Record<string, unknown>
    } catch (error) {
      console.error('Invalid JSON file', error)
      return
    }

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
        config: {
          preprocessing,
          featureEngineering,
          models,
          compute_ci: Boolean(parsed.compute_ci ?? false),
        },
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

    const preDynDefs = [
      ...(preprocessing.length > 0
        ? [{ id: 'preprocessor', icon: 'mdi-filter-cog-outline', label: 'Preprocessor', desc: '資料前處理', pipeline: preprocessing }]
        : []),
      ...(featureEngineering.length > 0
        ? [{ id: 'featureEngineering', icon: 'mdi-chart-scatter-plot', label: 'Feature\nEngineering', desc: '特徵工程', pipeline: featureEngineering }]
        : []),
    ]
    const preDynNodes: FlowNode[] = preDynDefs.map((def, i) => ({
      id: def.id,
      type: 'iconNode',
      position: { x: 460 + i * 200, y: 290 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: { icon: def.icon, label: def.label, colorClass: 'node-pending', description: def.desc, fields: [], config: { pipeline: def.pipeline } },
    }))

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

    syncComputeCiNode()
    selectedJsonFile.value = file
    await saveWorkflowJsonFileToStorage(file)
    saveState()
  }

  function triggerJsonUpload(): void {
    jsonFileInput.value?.click()
  }

  function handleJsonFileChange(event: Event): void {
    const target = event.target as HTMLInputElement
    selectedJsonFile.value = target.files?.[0] ?? null
    target.value = ''
    if (selectedJsonFile.value) loadJsonModels(selectedJsonFile.value)
  }

  function triggerPaperUpload(): void {
    paperFileInput.value?.click()
  }

  async function handlePaperFileChange(event: Event): Promise<void> {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0] ?? null
    target.value = ''
    if (!file) return

    paperUploading.value = true
    workflowError.value = null

    try {
      const formData = new FormData()
      formData.append('data', file, file.name)
      const response = await fetch(N8N_PAPER_WEBHOOK_URL, { method: 'POST', body: formData })

      if (!response.ok) {
        const errorText = await response.text().catch(() => '')
        throw new Error(`n8n webhook 回應錯誤：${response.status} ${errorText}`)
      }

      const contentType = response.headers.get('content-type') ?? ''
      const result = contentType.includes('application/json') ? await response.json() : await response.text()
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

  function triggerGeminiUpload(): void {
    geminiFileInput.value?.click()
  }

  async function handleGeminiFileChange(event: Event): Promise<void> {
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
      workflowError.value = error instanceof Error ? error.message : '論文 AI 分析失敗，請確認 PDF 是否正確'
      console.error('[gemini] analyze-paper error:', error)
    } finally {
      geminiUploading.value = false
    }
  }

  return {
    paperUploading,
    geminiUploading,
    selectedJsonFile,
    workflowError,
    loadJsonModels,
    triggerJsonUpload,
    handleJsonFileChange,
    triggerPaperUpload,
    handlePaperFileChange,
    triggerGeminiUpload,
    handleGeminiFileChange,
  }
}
