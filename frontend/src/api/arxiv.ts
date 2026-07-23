export interface ArxivCandidate {
  arxiv_id: string
  title: string
  authors: string
  year: number | null
  abstract: string
  pdf_url: string
}

export interface ArxivSearchResult {
  topic: string
  arxiv_query: string
  candidates: ArxivCandidate[]
}

export async function searchArxivCandidates (miningResults: Record<string, unknown>): Promise<ArxivSearchResult> {
  const response = await fetch('/api/rag/arxiv/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mining_results: miningResults }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return {
    topic: String(result.topic ?? ''),
    arxiv_query: String(result.arxiv_query ?? ''),
    candidates: Array.isArray(result.candidates) ? result.candidates as ArxivCandidate[] : [],
  }
}

export interface ArxivCitationSource {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  relevant_chunk?: string
  similarity_score?: number | null
}

export interface ArxivCitationMapEntry {
  section: string
  paragraph_index: number
  text: string
  cited_ref_ids: number[]
  sources: ArxivCitationSource[]
}

export interface ArxivReference {
  ref_id: number
  paper_id: string
  title: string
  author?: string
  year?: string | number
  journal?: string
}

export interface ArxivGenerateResult {
  paper_markdown: string
  citation_map: ArxivCitationMapEntry[]
  references: ArxivReference[]
  citation_report: string
  sections_generated: string[]
  usage: Record<string, number | null>
}

export async function generateFromArxiv (params: {
  topic: string
  miningResults: Record<string, unknown>
  selectedCandidates: ArxivCandidate[]
}): Promise<ArxivGenerateResult> {
  const response = await fetch('/api/rag/arxiv/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic: params.topic,
      mining_results: params.miningResults,
      selected_candidates: params.selectedCandidates,
    }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  return result.result as ArxivGenerateResult
}
