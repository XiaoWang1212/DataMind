import type { Citation, CitationStyle } from '@/constants/reportData'
import { formatCitation } from '@/utils/paper/formatCitation'

export interface ReferenceBlockInput {
  kind: 'referenceHeading' | 'referenceItem'
  html: string
}

export function buildReferenceBlocks (citations: Citation[], citationStyle: CitationStyle): ReferenceBlockInput[] {
  if (citations.length === 0) return []

  const blocks: ReferenceBlockInput[] = [
    { kind: 'referenceHeading', html: '<h3 class="references-title">參考文獻</h3>' },
  ]

  citations.forEach((citation, index) => {
    const text = escapeHtml(formatCitation(citation, citationStyle, index + 1))
    blocks.push({ kind: 'referenceItem', html: `<li>${text}</li>` })
  })

  return blocks
}

function escapeHtml (value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
