import type { EdgeBase, FlowNode } from '@/types/workflow'

const WORKFLOW_DATA_FILE_KEY = 'workflowDataFile'
const WORKFLOW_JSON_FILE_KEY = 'workflowJsonFile'
const WORKFLOW_STATE_KEY = 'workflowState'

const DB_NAME = 'datamindWorkflowFiles'
const DB_STORE = 'files'

function k (base: string, projectId?: string): string {
  return projectId ? `${base}_${projectId}` : base
}

// 一次性清掉舊版（base64 存 localStorage）留下的資料檔案，
// 這些殘留可能就是當初把 localStorage 配額塞滿、導致存檔靜默失敗的原因
function purgeLegacyDataFileEntries (): void {
  const staleKeys: string[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (key && (key === WORKFLOW_DATA_FILE_KEY || key.startsWith(`${WORKFLOW_DATA_FILE_KEY}_`))) {
      staleKeys.push(key)
    }
  }
  for (const key of staleKeys) {
    localStorage.removeItem(key)
  }
}

purgeLegacyDataFileEntries()

// CSV 資料檔案改用 IndexedDB 儲存：localStorage 容量通常只有 5~10MB，
// 累積多個專案的資料檔很容易超過上限導致 setItem 靜默失敗，造成刷新後資料消失
function openFileDb (): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(DB_STORE)) {
        request.result.createObjectStore(DB_STORE)
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.addEventListener('error', () => reject(request.error))
  })
}

export async function saveWorkflowDataFileToStorage (file: File | null, projectId?: string): Promise<void> {
  const key = k(WORKFLOW_DATA_FILE_KEY, projectId)
  try {
    const db = await openFileDb()
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(DB_STORE, 'readwrite')
      if (file) {
        tx.objectStore(DB_STORE).put({ name: file.name, type: file.type || 'text/csv', blob: file }, key)
      } else {
        tx.objectStore(DB_STORE).delete(key)
      }
      tx.oncomplete = () => resolve()
      tx.addEventListener('error', () => reject(tx.error))
    })
    db.close()
  } catch (error) {
    console.error('[WF-SAVE] 無法將資料檔案存入 IndexedDB:', error)
  }
}

export async function loadWorkflowDataFileFromStorage (projectId?: string): Promise<File | null> {
  const key = k(WORKFLOW_DATA_FILE_KEY, projectId)
  try {
    const db = await openFileDb()
    const record = await new Promise<{ name: string, type: string, blob: Blob } | undefined>((resolve, reject) => {
      const tx = db.transaction(DB_STORE, 'readonly')
      const req = tx.objectStore(DB_STORE).get(key)
      req.onsuccess = () => resolve(req.result)
      req.addEventListener('error', () => reject(req.error))
    })
    db.close()
    if (!record) {
      return null
    }
    return new File([record.blob], record.name, { type: record.type })
  } catch (error) {
    console.error('[WF-LOAD] 無法從 IndexedDB 還原資料檔案:', error)
    return null
  }
}

export async function saveWorkflowJsonFileToStorage (file: File | null, projectId?: string): Promise<void> {
  const key = k(WORKFLOW_JSON_FILE_KEY, projectId)
  if (!file) {
    localStorage.removeItem(key)
    return
  }
  try {
    const text = await file.text()
    const payload = { name: file.name, type: file.type || 'application/json', text }
    localStorage.setItem(key, JSON.stringify(payload))
  } catch (error) {
    console.warn('Unable to persist workflow JSON to localStorage', error)
  }
}

export async function loadWorkflowJsonFileFromStorage (projectId?: string): Promise<File | null> {
  const key = k(WORKFLOW_JSON_FILE_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return null
  }
  try {
    const parsed = JSON.parse(raw) as { name: string, type: string, text: string }
    return new File([parsed.text], parsed.name, { type: parsed.type })
  } catch (error) {
    console.warn('Unable to restore workflow JSON from localStorage', error)
    localStorage.removeItem(key)
    return null
  }
}

export interface WorkflowExecutionState {
  nodeStatuses?: Record<string, 'running' | 'finished'>
  pausedAtNodeId?: string | null
  dataTableApplied?: boolean
  selectedNodeId?: string | null
  isDemoFinished?: boolean
  workflowResult?: Record<string, unknown> | null
  activeJobId?: string | null
}

export function saveWorkflowStateToStorage (
  nodes: FlowNode[],
  edges: EdgeBase[],
  projectId?: string,
  execution?: WorkflowExecutionState,
): void {
  const key = k(WORKFLOW_STATE_KEY, projectId)
  try {
    localStorage.setItem(key, JSON.stringify({ nodes, edges, ...execution }))
  } catch (error) {
    console.error('[WF-SAVE] FAILED:', error)
  }
}

export function loadWorkflowStateFromStorage (
  projectId?: string,
): ({ nodes: FlowNode[], edges: EdgeBase[] } & WorkflowExecutionState) | null {
  const key = k(WORKFLOW_STATE_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as { nodes: FlowNode[], edges: EdgeBase[] } & WorkflowExecutionState
  } catch (error) {
    console.error('[WF-LOAD] JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return null
  }
}
