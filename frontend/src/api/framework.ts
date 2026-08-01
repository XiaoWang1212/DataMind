export interface FrameworkDTO {
  id: number
  title: string
  subtitle: string
  tag: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
  date: string
}

export interface CreateFrameworkPayload {
  title: string
  subtitle: string
  tag: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
}

async function parseFrameworkResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

export async function listFrameworks (): Promise<FrameworkDTO[]> {
  const response = await fetch('/api/frameworks', { credentials: 'include' })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO[]
}

export async function createFramework (payload: CreateFrameworkPayload): Promise<FrameworkDTO> {
  const response = await fetch('/api/frameworks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO
}
