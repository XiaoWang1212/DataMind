import type { ArxivCandidate } from '@/api/arxiv'

export interface StructuredAnalysis {
  model_comparison: string
  data_insights: string
  risks: string
  recommendations: string
}

export async function fetchStructuredAnalysis (miningResults: Record<string, unknown>): Promise<StructuredAnalysis> {
  const response = await fetch('/api/rag/structured-analysis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  const analysis = (result.analysis ?? {}) as Record<string, unknown>
  return {
    model_comparison: String(analysis.model_comparison ?? ''),
    data_insights: String(analysis.data_insights ?? ''),
    risks: String(analysis.risks ?? ''),
    recommendations: String(analysis.recommendations ?? ''),
  }
}

export interface ChatMessage {
  role: 'user' | 'model'
  text: string
}

export interface ChatReply {
  reply: string
  papers: ArxivCandidate[]
}

export async function sendChatMessage (
  miningResults: Record<string, unknown>,
  history: ChatMessage[],
  message: string,
): Promise<ChatReply> {
  const response = await fetch('/api/rag/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults, history, message }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return {
    reply: String(result.reply ?? ''),
    papers: Array.isArray(result.papers) ? result.papers as ArxivCandidate[] : [],
  }
}
