import type { EdgeBase, FlowNode } from '@/types/workflow'

export const WORKFLOW_DATA_FILE_STORAGE_KEY = 'workflowDataFile'
export const WORKFLOW_JSON_FILE_STORAGE_KEY = 'workflowJsonFile'
export const WORKFLOW_STATE_STORAGE_KEY = 'workflowState'

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = ''
  const bytes = new Uint8Array(buffer)
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCodePoint(bytes[i]!)
  }
  return btoa(binary)
}

function base64ToUint8Array(base64: string): Uint8Array {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.codePointAt(i) ?? 0
  }
  return bytes
}

export async function saveWorkflowDataFileToStorage(file: File | null): Promise<void> {
  if (!file) {
    localStorage.removeItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
    return
  }
  try {
    const buffer = await file.arrayBuffer()
    const payload = {
      name: file.name,
      type: file.type || 'text/csv',
      contentBase64: arrayBufferToBase64(buffer),
    }
    localStorage.setItem(WORKFLOW_DATA_FILE_STORAGE_KEY, JSON.stringify(payload))
  } catch (error) {
    console.warn('Unable to persist workflow file to localStorage', error)
  }
}

export async function loadWorkflowDataFileFromStorage(): Promise<File | null> {
  const raw = localStorage.getItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as { name: string; type: string; contentBase64: string }
    const bytes = base64ToUint8Array(parsed.contentBase64)
    return new File([bytes.buffer as ArrayBuffer], parsed.name, { type: parsed.type })
  } catch (error) {
    console.warn('Unable to restore workflow file from localStorage', error)
    localStorage.removeItem(WORKFLOW_DATA_FILE_STORAGE_KEY)
    return null
  }
}

export async function saveWorkflowJsonFileToStorage(file: File | null): Promise<void> {
  if (!file) {
    localStorage.removeItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
    return
  }
  try {
    const text = await file.text()
    const payload = { name: file.name, type: file.type || 'application/json', text }
    localStorage.setItem(WORKFLOW_JSON_FILE_STORAGE_KEY, JSON.stringify(payload))
  } catch (error) {
    console.warn('Unable to persist workflow JSON to localStorage', error)
  }
}

export async function loadWorkflowJsonFileFromStorage(): Promise<File | null> {
  const raw = localStorage.getItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as { name: string; type: string; text: string }
    return new File([parsed.text], parsed.name, { type: parsed.type })
  } catch (error) {
    console.warn('Unable to restore workflow JSON from localStorage', error)
    localStorage.removeItem(WORKFLOW_JSON_FILE_STORAGE_KEY)
    return null
  }
}

export function saveWorkflowStateToStorage(nodes: FlowNode[], edges: EdgeBase[]): void {
  try {
    const payload = JSON.stringify({ nodes, edges })
    localStorage.setItem(WORKFLOW_STATE_STORAGE_KEY, payload)
    console.log('[WF-SAVE] saved', nodes.length, 'nodes,', edges.length, 'edges, caller:', new Error('trace').stack?.split('\n')[2]?.trim())
  } catch (error) {
    console.error('[WF-SAVE] FAILED:', error)
  }
}

export function loadWorkflowStateFromStorage(): { nodes: FlowNode[]; edges: EdgeBase[] } | null {
  const raw = localStorage.getItem(WORKFLOW_STATE_STORAGE_KEY)
  console.log('[WF-LOAD] localStorage raw length:', raw?.length ?? 'null (nothing saved)')
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as { nodes: FlowNode[]; edges: EdgeBase[] }
    console.log('[WF-LOAD] parsed', parsed.nodes?.length, 'nodes,', parsed.edges?.length, 'edges')
    return parsed
  } catch (error) {
    console.error('[WF-LOAD] JSON.parse FAILED:', error)
    localStorage.removeItem(WORKFLOW_STATE_STORAGE_KEY)
    return null
  }
}
