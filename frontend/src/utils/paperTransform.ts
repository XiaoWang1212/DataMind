import type { JSONContent } from '@tiptap/core'
import type { ArxivGenerateResult } from '@/api/arxiv'
import type { Citation, PaperReport } from '@/constants/reportData'

function parseParagraphToContent (paragraphText: string): JSONContent[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const nodes: JSONContent[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const firstDigits = token.match(/\d+/)?.[0]
      if (!firstDigits) continue
      const citationId = `cite-${firstDigits}`
      const prev = nodes.at(-1)

      if (prev && prev.type === 'text' && !prev.marks) {
        // 引用標記依附在「前一句」文字上,不寫進文字內容本身
        prev.marks = [{ type: 'citation', attrs: { citationId } }]
      } else {
        // 沒有前一句可依附(例如段落一開頭就是引用標記):用零寬空白當文字節點,
        // 只是為了承載 citation mark,避免 ProseMirror 不允許空文字節點
        nodes.push({ type: 'text', text: '​', marks: [{ type: 'citation', attrs: { citationId } }] })
      }
    } else {
      nodes.push({ type: 'text', text: token })
    }
  }

  return nodes
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
  const docContent: JSONContent[] = []

  for (const block of blocks) {
    const trimmed = block.trim()
    if (!trimmed.startsWith('## ') || trimmed.startsWith('## 參考文獻')) {
      continue
    }

    const newlineIndex = trimmed.indexOf('\n\n')
    const heading = trimmed.slice(3, newlineIndex === -1 ? undefined : newlineIndex).trim()
    const body = newlineIndex === -1 ? '' : trimmed.slice(newlineIndex + 2)

    docContent.push({
      type: 'heading',
      attrs: { level: 3 },
      content: [{ type: 'text', text: heading }],
    })

    const paragraphs = body
      .split('\n\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    for (const paragraph of paragraphs) {
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph) })
    }
  }

  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
  }
}
