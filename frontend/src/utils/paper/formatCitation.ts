import type { Citation, CitationStyle } from '@/constants/reportData'

export const citationStyleLabels: Record<CitationStyle, string> = {
  apa: 'APA',
  ieee: 'IEEE',
  mla: 'MLA',
}

function formatArxiv (citation: Citation, style: CitationStyle, index: number): string {
  const { authors, title, year, arxivId } = citation

  switch (style) {
    case 'apa': {
      return `${authors} (${year}). ${title}. arXiv. https://arxiv.org/abs/${arxivId}`
    }
    case 'mla': {
      return `${authors}. "${title}." arXiv, ${year}, arxiv.org/abs/${arxivId}.`
    }
    case 'ieee': {
      return `[${index}] ${authors}, "${title}," arXiv:${arxivId}, ${year}.`
    }
  }
}

function formatFallback (citation: Citation, style: CitationStyle, index: number): string {
  const { authors, title, year, journal } = citation

  switch (style) {
    case 'apa': {
      const journalSegment = journal ? ` ${journal}.` : ''
      return `${authors} (${year}). ${title}.${journalSegment}`
    }
    case 'mla': {
      const journalPart = journal ? ` ${journal}, ${year}.` : ` ${year}.`
      return `${authors}. "${title}."${journalPart}`
    }
    case 'ieee': {
      const journalPart = journal ? ` ${journal}, ${year}.` : ` ${year}.`
      return `[${index}] ${authors}, "${title}",${journalPart}`
    }
  }
}

export function formatCitation (citation: Citation, style: CitationStyle, index: number): string {
  return citation.arxivId
    ? formatArxiv(citation, style, index)
    : formatFallback(citation, style, index)
}
