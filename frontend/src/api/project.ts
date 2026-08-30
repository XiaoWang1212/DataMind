export interface VariableMapping {
  column: string
  type: string
}

export interface ProjectDTO {
  id: number
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  status: 'draft' | 'running' | 'completed'
  progress: number
  accuracy?: string
  keyFinding?: string
  variables: number
  columnMapping?: Record<string, VariableMapping> | null
  date: string
}

export interface CreateProjectPayload {
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  variables: number
}

export interface UpdateProjectPatch {
  status?: string
  progress?: number
  datasetName?: string
  accuracy?: string
  keyFinding?: string
  columnMapping?: Record<string, VariableMapping>
  variables?: number
}

async function parseProjectResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

export async function listProjects (): Promise<ProjectDTO[]> {
  const response = await fetch('/api/projects', { credentials: 'include' })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO[]
}

export async function createProject (payload: CreateProjectPayload): Promise<ProjectDTO> {
  const response = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}

export async function updateProject (id: number, patch: UpdateProjectPatch): Promise<ProjectDTO> {
  const response = await fetch(`/api/projects/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}

export async function getProject (id: number): Promise<ProjectDTO> {
  const response = await fetch(`/api/projects/${id}`, { credentials: 'include' })
  const result = await parseProjectResponse(response)
  return result.result as ProjectDTO
}

export async function deleteProject (id: number): Promise<void> {
  const response = await fetch(`/api/projects/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  await parseProjectResponse(response)
}
