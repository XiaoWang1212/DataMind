import { FEATURE_LABELS, PREPROCESS_LABELS, RESAMPLING_LABELS, VALIDATION_LABELS } from '@/constants/workflowLabels'

export interface PipelineSummary {
  preprocess: string[]
  featureEngineering: string[]
  resampling: string | null
  validation: string | null
  models: string[]
}

const EMPTY: PipelineSummary = {
  preprocess: [],
  featureEngineering: [],
  resampling: null,
  validation: null,
  models: [],
}

interface StoredNode {
  id?: unknown
  data?: { config?: Record<string, unknown>, label?: unknown }
}

function asRecord (value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

// pipeline 步驟的形狀是 { type, ...參數 }，只取 type 去查中文標籤；
// 查不到就原樣顯示，讓未知步驟至少看得見而不是憑空消失
function stepLabels (pipeline: unknown, labels: Record<string, string>): string[] {
  if (!Array.isArray(pipeline)) {
    return []
  }
  return pipeline
    .map(step => String(asRecord(step).type ?? ''))
    .filter(Boolean)
    .map(type => labels[type] ?? type)
}

export function summarizeWorkflowPipeline (nodes: unknown): PipelineSummary {
  if (!Array.isArray(nodes)) {
    return EMPTY
  }

  const list = nodes as StoredNode[]
  const byId = (id: string) => list.find(n => String(n.id ?? '') === id)

  const preprocessorConfig = asRecord(byId('preprocessor')?.data?.config)
  const featureConfig = asRecord(byId('featureEngineering')?.data?.config)
  const testScoreConfig = asRecord(byId('testScore')?.data?.config)

  const validationMethod = String(asRecord(testScoreConfig.validation).method ?? '')
  const resamplingMethod = String(testScoreConfig.resampling_method ?? 'none')

  return {
    preprocess: stepLabels(preprocessorConfig.pipeline, PREPROCESS_LABELS),
    featureEngineering: stepLabels(featureConfig.pipeline, FEATURE_LABELS),
    resampling: resamplingMethod && resamplingMethod !== 'none' ? (RESAMPLING_LABELS[resamplingMethod] ?? resamplingMethod) : null,
    validation: validationMethod ? (VALIDATION_LABELS[validationMethod] ?? validationMethod) : null,
    models: list
      .filter(n => String(n.id ?? '').startsWith('model-'))
      .map(n => String(asRecord(n.data?.config).modelName ?? n.data?.label ?? ''))
      .filter(Boolean),
  }
}
