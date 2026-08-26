export interface DatasetColumn {
  name: string
  type: string
  role: string
}

export type FillNaColumnKind = 'numeric' | 'nominal' | 'mixed'

/** 把「沒有指定 columns 的 fill_na 步驟」拆成兩筆具體步驟：
 * 數值型欄位補均值、其餘型別（categorial/text/datetime）補眾數。
 * 已經有 columns 的步驟（使用者/其他流程已經明確範圍過）原樣跳過，回傳 null。
 */
export function splitAutoFillNaStep (
  step: Record<string, unknown>,
  datasetColumns: DatasetColumn[],
): Array<Record<string, unknown>> | null {
  if (step.type !== 'fill_na' || step.columns !== undefined || datasetColumns.length === 0) {
    return null
  }

  const numericCols = datasetColumns.filter(c => c.type === 'numeric').map(c => c.name)
  const nominalCols = datasetColumns.filter(c => c.type !== 'numeric').map(c => c.name)

  const steps: Array<Record<string, unknown>> = []
  if (numericCols.length > 0) {
    steps.push({ type: 'fill_na', strategy: 'mean', columns: numericCols })
  }
  if (nominalCols.length > 0) {
    steps.push({ type: 'fill_na', strategy: 'mode', columns: nominalCols })
  }

  return steps.length > 0 ? steps : null
}

/** 展開 pipeline 裡所有可拆分的 fill_na 步驟；冪等（已拆過的步驟因為已有 columns 不會再變動）。 */
export function expandAutoFillNaSteps (
  steps: Array<Record<string, unknown>>,
  datasetColumns: DatasetColumn[],
): Array<Record<string, unknown>> {
  return steps.flatMap(step => splitAutoFillNaStep(step, datasetColumns) ?? [step])
}

/** 判斷某個 fill_na 步驟目前的 columns 是純數值、純類別，還是混合／未指定。 */
export function fillNaColumnKind (
  step: Record<string, unknown>,
  datasetColumns: DatasetColumn[],
): FillNaColumnKind {
  const columns = Array.isArray(step.columns) ? step.columns as string[] : null
  if (!columns || columns.length === 0) {
    return 'mixed'
  }

  const types = columns.map(name => datasetColumns.find(c => c.name === name)?.type)
  if (types.every(t => t === 'numeric')) {
    return 'numeric'
  }
  if (types.every(t => t !== undefined && t !== 'numeric')) {
    return 'nominal'
  }
  return 'mixed'
}
