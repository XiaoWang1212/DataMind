import type { ArxivGenerateResult } from '@/api/arxiv'
import type { Citation, PaperReport, PaperSection, PaperSegment } from '@/constants/reportData'

function parseParagraph (paragraphText: string): PaperSegment[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const segments: PaperSegment[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const ids = Array.from(token.matchAll(/\d+/g)).map(match => `cite-${match[0]}`)
      const prev = segments.at(-1)
      if (prev && !prev.citationIds) {
        prev.citationIds = ids
      } else {
        segments.push({ text: '', citationIds: ids })
      }
    } else {
      segments.push({ text: token })
    }
  }

  return segments
}

function buildCitations (result: ArxivGenerateResult): Citation[] {
  return result.references
    .toSorted((a, b) => a.ref_id - b.ref_id)
    .map(ref => {
      const snippetEntry = result.citation_map
        .flatMap(entry => entry.sources)
        .find(source => source.ref_id === ref.ref_id && source.relevant_chunk)

      return {
        id: `cite-${ref.ref_id}`,
        title: ref.title,
        authors: String(ref.author ?? ''),
        journal: String(ref.journal ?? 'arXiv'),
        year: Number(ref.year) || 0,
        snippet: snippetEntry?.relevant_chunk ?? '',
      }
    })
}

export function transformArxivResultToPaperReport (result: ArxivGenerateResult, topic: string): PaperReport {
  const blocks = result.paper_markdown.split('\n\n---\n\n')
  const sections: PaperSection[] = []

  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ') || trimmed.startsWith('## 參考文獻')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)
      .map(p => parseParagraph(p))

    sections.push({ heading, paragraphs })
  }

  return {
    title: topic,
    sections,
    citations: buildCitations(result),
  }
}
