export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string, valueRaw: number }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult (
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[] {
  if (!workflowResult) {
    return []
  }
  const results = Array.isArray(workflowResult.results)
    ? workflowResult.results
    : []

  const modelGroups = new Map<string, { count: number, metrics: Record<string, number[]>, errors: Record<string, string> }>()

  for (const result of results.filter((r: any) => r && typeof r === 'object')) {
    const modelName = result.model_name || 'unknown'
    const existing = modelGroups.get(modelName) ?? { count: 0, metrics: {}, errors: {} }

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
    metrics: Object.entries(group.metrics).map(([metric, values]) => {
      const average = values.length > 0 ? values.reduce((s, v) => s + v, 0) / values.length : 0
      return {
        metric,
        valueRaw: average,
        valueFormatted: values.length > 0 ? average.toFixed(4) : 'N/A',
      }
    }),
    errors: group.errors,
  }))
}

// 指標值一律視為越大越好——目前介面暴露的
// 指標（accuracy、auc、f1 等）都符合這個方向
export function findBestModel (
  summary: ModelMetricSummary[],
  metric: string,
): { modelName: string, valueFormatted: string } | null {
  let best: { modelName: string, valueFormatted: string, value: number } | null = null
  for (const row of summary) {
    const entry = row.metrics.find(m => m.metric === metric)
    if (!entry) {
      continue
    }
    if (Number.isNaN(entry.valueRaw)) {
      continue
    }
    if (!best || entry.valueRaw > best.value) {
      best = { modelName: row.model_name, valueFormatted: entry.valueFormatted, value: entry.valueRaw }
    }
  }
  return best ? { modelName: best.modelName, valueFormatted: best.valueFormatted } : null
}

// 排最佳模型要用哪個指標。balanced_accuracy 擺第一是因為資料不平衡時
// 單純的 accuracy 會被多數類灌水
export const RANKING_PRIORITY = ['balanced_accuracy', 'accuracy', 'auc']

// 只有部分模型算得出來的指標拿來比較並不公平，所以候選指標必須每個模型都有
export function pickPrimaryMetricOf (metricNamesPerModel: string[][]): string | null {
  if (metricNamesPerModel.length === 0) {
    return null
  }
  for (const candidate of RANKING_PRIORITY) {
    if (metricNamesPerModel.every(names => names.includes(candidate))) {
      return candidate
    }
  }
  return metricNamesPerModel[0]?.[0] ?? null
}

export function pickPrimaryMetric (summary: ModelMetricSummary[]): string | null {
  return pickPrimaryMetricOf(summary.map(row => row.metrics.map(m => m.metric)))
}
