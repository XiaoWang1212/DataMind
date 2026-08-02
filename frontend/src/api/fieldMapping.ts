import type {
  ChatMessage,
  MappingAction,
  MappingState,
  PaperVariable,
  UserColumn,
} from '@/types/fieldMapping'

const BASE = '/api/field-mapping'

interface InitResponse {
  success: boolean
  result: MappingState
  ai_available: boolean
  error?: string
}

interface ChatResponse {
  success: boolean
  result: { actions: MappingAction[]; reply: string }
  error?: string
}

/** 初始化對映：演算法自動配對 + Gemini 語意補完。 */
export async function initFieldMapping (payload: {
  paperVariables: PaperVariable[]
  userColumns: UserColumn[]
}): Promise<{ state: MappingState; aiAvailable: boolean }> {
  const response = await fetch(`${BASE}/init`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      paper_variables: payload.paperVariables,
      user_columns: payload.userColumns,
    }),
  })

  const body = await response.json() as InitResponse
  if (!response.ok || !body.success) {
    throw new Error(body.error || '欄位對齊初始化失敗')
  }
  return { state: body.result, aiAvailable: body.ai_available }
}

/** 對話式修正：只回這一輪的變更，套用由呼叫端負責。 */
export async function refineFieldMapping (payload: {
  mappingState: MappingState
  userColumns: UserColumn[]
  userMessage: string
  chatHistory: ChatMessage[]
}): Promise<{ actions: MappingAction[]; reply: string }> {
  const response = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({
      current_mapping_state: {
        mapping_status: payload.mappingState.mapping_status,
        user_columns: payload.userColumns,
      },
      user_message: payload.userMessage,
      chat_history: payload.chatHistory,
    }),
  })

  const body = await response.json() as ChatResponse
  if (!response.ok || !body.success) {
    throw new Error(body.error || 'AI 目前無法回應')
  }
  return body.result
}
