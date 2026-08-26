export async function fetchResultInsight (miningResults: Record<string, unknown>): Promise<string> {
  const response = await fetch('/api/rag/insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}

export async function fetchTabInsight (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-insight', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.insight ?? '')
}

export interface TabChatMessage {
  role: 'user' | 'model'
  text: string
}

export async function fetchTabChatReply (
  miningResults: Record<string, unknown>,
  tab: string,
  modelName: string,
  splitName: string,
  history: TabChatMessage[],
  message: string,
): Promise<string> {
  const response = await fetch('/api/rag/tab-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mining_results: miningResults,
      tab,
      model_name: modelName,
      split_name: splitName,
      history,
      message,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return String(result.reply ?? '')
}
