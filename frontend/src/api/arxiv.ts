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
  arxiv_id?: string
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

export interface CriterionScore {
  name: string
  score: number
  comment: string
}

export interface JournalScore {
  journal: string
  journalFullName: string
  overallScore: number
  overallComment: string
  criteria: CriterionScore[]
  suggestions: string[]
}

export interface ScorePaperResult {
  journalScores: JournalScore[]
  failedJournals: string[]
}

export async function scorePaper (paperText: string): Promise<ScorePaperResult> {
  const response = await fetch('/api/rag/score-paper', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ paper_text: paperText }),
  })

  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }

  const rawScores = Array.isArray(result.journal_scores)
    ? result.journal_scores as Record<string, unknown>[]
    : []

  return {
    journalScores: rawScores.map(js => ({
      journal: String(js.journal ?? ''),
      journalFullName: String(js.journal_full_name ?? ''),
      overallScore: Number(js.overall_score ?? 0),
      overallComment: String(js.overall_comment ?? ''),
      criteria: Array.isArray(js.criteria)
        ? (js.criteria as Record<string, unknown>[]).map(c => ({
            name: String(c.name ?? ''),
            score: Number(c.score ?? 0),
            comment: String(c.comment ?? ''),
          }))
        : [],
      suggestions: Array.isArray(js.suggestions) ? (js.suggestions as unknown[]).map(String) : [],
    })),
    failedJournals: Array.isArray(result.failed_journals)
      ? (result.failed_journals as unknown[]).map(String)
      : [],
  }
}
