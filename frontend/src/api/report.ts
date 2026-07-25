import type { JSONContent } from '@tiptap/core'
import type { Citation } from '@/constants/reportData'

export interface SavedReport {
  title: string
  content: JSONContent
  citations: Citation[]
  updated_at: string
}

export async function saveReport (
  projectId: string,
  payload: { title: string, content: JSONContent, citations: Citation[] },
): Promise<SavedReport> {
  const response = await fetch(`/api/report/${encodeURIComponent(projectId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as SavedReport
}

export async function getReport (projectId: string): Promise<SavedReport | null> {
  const response = await fetch(`/api/report/${encodeURIComponent(projectId)}`)

  if (response.status === 404) return null

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as SavedReport
}
