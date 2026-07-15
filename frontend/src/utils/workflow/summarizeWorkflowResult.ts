export interface ModelMetricSummary {
  model_name: string
  split_name: string
  metrics: { metric: string, valueFormatted: string }[]
  errors: Record<string, string>
}

export function summarizeWorkflowResult (
  workflowResult: Record<string, unknown> | null,
): ModelMetricSummary[] {
  if (!workflowResult) return []
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
}
