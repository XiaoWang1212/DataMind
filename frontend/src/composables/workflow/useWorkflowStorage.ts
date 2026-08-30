import type { EdgeBase, FlowNode } from '@/types/workflow'
import type { TabChatMessage } from '@/api/insight'
import type { ChatMessage, StructuredAnalysis } from '@/api/resultAnalysis'

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

const RESULT_INSIGHT_KEY = 'resultInsight'

export function saveResultInsightToStorage (projectId: string, insight: string): void {
  const key = k(RESULT_INSIGHT_KEY, projectId)
  try {
    localStorage.setItem(key, insight)
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存洞察文字:', error)
  }
}

export function loadResultInsightFromStorage (projectId: string): string | null {
  const key = k(RESULT_INSIGHT_KEY, projectId)
  return localStorage.getItem(key)
}

export function clearResultInsightFromStorage (projectId: string): void {
  const key = k(RESULT_INSIGHT_KEY, projectId)
  localStorage.removeItem(key)
}

const TAB_INSIGHT_KEY = 'tabInsight'

function tabInsightStorageKey (
  projectId: string, modelName: string, splitName: string, tab: string,
): string {
  return k(`${TAB_INSIGHT_KEY}_${tab}_${modelName}_${splitName}`, projectId)
}

export function saveTabInsightToStorage (
  projectId: string, modelName: string, splitName: string, tab: string, insight: string,
): void {
  const key = tabInsightStorageKey(projectId, modelName, splitName, tab)
  try {
    localStorage.setItem(key, insight)
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存分頁解讀文字:', error)
  }
}

export function loadTabInsightFromStorage (
  projectId: string, modelName: string, splitName: string, tab: string,
): string | null {
  const key = tabInsightStorageKey(projectId, modelName, splitName, tab)
  return localStorage.getItem(key)
}

// 分頁解讀是組合鍵（tab/model/fold 各自獨立一個 key），沒辦法像單一 key 那樣直接刪，
// 要掃描 localStorage 找出屬於這個 projectId 的全部分頁解讀 key 再逐一移除
export function clearAllTabInsightsFromStorage (projectId: string): void {
  const prefix = `${TAB_INSIGHT_KEY}_`
  const suffix = `_${projectId}`
  const staleKeys: string[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (key && key.startsWith(prefix) && key.endsWith(suffix)) {
      staleKeys.push(key)
    }
  }
  for (const key of staleKeys) {
    localStorage.removeItem(key)
  }
}

const TAB_CHAT_KEY = 'tabChat'

function tabChatStorageKey (
  projectId: string, modelName: string, splitName: string, tab: string,
): string {
  return k(`${TAB_CHAT_KEY}_${tab}_${modelName}_${splitName}`, projectId)
}

export function saveTabChatToStorage (
  projectId: string, modelName: string, splitName: string, tab: string, messages: TabChatMessage[],
): void {
  const key = tabChatStorageKey(projectId, modelName, splitName, tab)
  try {
    localStorage.setItem(key, JSON.stringify(messages))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存分頁問答紀錄:', error)
  }
}

export function loadTabChatFromStorage (
  projectId: string, modelName: string, splitName: string, tab: string,
): TabChatMessage[] {
  const key = tabChatStorageKey(projectId, modelName, splitName, tab)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return []
  }
  try {
    return JSON.parse(raw) as TabChatMessage[]
  } catch (error) {
    console.error('[WF-LOAD] 分頁問答紀錄 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return []
  }
}

// 分頁問答是組合鍵（tab/model/fold 各自獨立一個 key），沒辦法像單一 key 那樣直接刪，
// 要掃描 localStorage 找出屬於這個 projectId 的全部分頁問答 key 再逐一移除
export function clearAllTabChatsFromStorage (projectId: string): void {
  const prefix = `${TAB_CHAT_KEY}_`
  const suffix = `_${projectId}`
  const staleKeys: string[] = []
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i)
    if (key && key.startsWith(prefix) && key.endsWith(suffix)) {
      staleKeys.push(key)
    }
  }
  for (const key of staleKeys) {
    localStorage.removeItem(key)
  }
}

// job 在後端已經永久查不到時（重啟、超過 TTL）呼叫，避免下次重新整理又試著輪詢同一個死掉的 job_id
export function clearActiveJobIdFromStorage (projectId?: string): void {
  const key = k(WORKFLOW_STATE_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return
  }
  try {
    const state = JSON.parse(raw) as Record<string, unknown>
    state.activeJobId = null
    localStorage.setItem(key, JSON.stringify(state))
  } catch (error) {
    console.error('[WF-SAVE] 無法清除過期的 activeJobId:', error)
  }
}

const STRUCTURED_ANALYSIS_KEY = 'structuredAnalysis'

export function saveStructuredAnalysisToStorage (projectId: string, analysis: StructuredAnalysis): void {
  const key = k(STRUCTURED_ANALYSIS_KEY, projectId)
  try {
    localStorage.setItem(key, JSON.stringify(analysis))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存結構化分析:', error)
  }
}

export function loadStructuredAnalysisFromStorage (projectId: string): StructuredAnalysis | null {
  const key = k(STRUCTURED_ANALYSIS_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return null
  }
  try {
    return JSON.parse(raw) as StructuredAnalysis
  } catch (error) {
    console.error('[WF-LOAD] 結構化分析 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return null
  }
}

const CHAT_HISTORY_KEY = 'chatHistory'

export function saveChatHistoryToStorage (projectId: string, history: ChatMessage[]): void {
  const key = k(CHAT_HISTORY_KEY, projectId)
  try {
    localStorage.setItem(key, JSON.stringify(history))
  } catch (error) {
    console.error('[WF-SAVE] 無法儲存對話紀錄:', error)
  }
}

export function loadChatHistoryFromStorage (projectId: string): ChatMessage[] {
  const key = k(CHAT_HISTORY_KEY, projectId)
  const raw = localStorage.getItem(key)
  if (!raw) {
    return []
  }
  try {
    return JSON.parse(raw) as ChatMessage[]
  } catch (error) {
    console.error('[WF-LOAD] 對話紀錄 JSON.parse FAILED:', error)
    localStorage.removeItem(key)
    return []
  }
}
