import type { JSONContent } from '@tiptap/core'
import type { ArxivCitationSource, ArxivGenerateResult } from '@/api/arxiv'
import type { Citation, PaperReport } from '@/constants/reportData'

function parseParagraphToContent (
  paragraphText: string,
  sources: ArxivCitationSource[] | undefined,
): JSONContent[] {
  const tokens = paragraphText.split(/((?:\[\d+\])+)/g).filter(token => token !== '')
  const nodes: JSONContent[] = []

  for (const token of tokens) {
    if (/^(?:\[\d+\])+$/.test(token)) {
      const firstDigits = token.match(/\d+/)?.[0]
      if (!firstDigits) {
        continue
      }
      const citationId = `cite-${firstDigits}`
      // 這段話實際引用到的 chunk，跟 citations 陣列裡「這篇論文預設摘錄」分開存，
      // 找不到（例如非 arXiv 生成的內容）就是 null，彈窗會 fall back 用預設摘錄
      const relevantChunk = sources?.find(s => s.ref_id === Number(firstDigits))?.relevant_chunk ?? null
      const attrs = { citationId, relevantChunk }
      const prev = nodes.at(-1)

      if (prev && prev.type === 'text' && !prev.marks) {
        // 引用標記依附在「前一句」文字上,不寫進文字內容本身
        prev.marks = [{ type: 'citation', attrs }]
      } else {
        // 沒有前一句可依附(例如段落一開頭就是引用標記):用零寬空白當文字節點,
        // 只是為了承載 citation mark,避免 ProseMirror 不允許空文字節點
        nodes.push({ type: 'text', text: '​', marks: [{ type: 'citation', attrs }] })
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
        arxivId: ref.arxiv_id || undefined,
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

    for (const [index, paragraph] of paragraphs.entries()) {
      // 前端這裡切段落的規則（\n\n---\n\n 分章節、\n\n 分段落）跟後端組
      // paper_markdown、_build_citation_map 切 paragraph_index 用的是同一份文字、
      // 同一套規則，兩邊算出來的段落序號天生對得上，不需要後端多傳任何資料
      const sources = result.citation_map.find(
        entry => entry.section === heading && entry.paragraph_index === index,
      )?.sources
      docContent.push({ type: 'paragraph', content: parseParagraphToContent(paragraph, sources) })
    }
  }

  return {
    title: topic,
    content: { type: 'doc', content: docContent },
    citations: buildCitations(result),
    citationStyle: 'apa',
  }
}

function renderTextContent (node: JSONContent, citationIndex: Record<string, number>): string {
  if (node.type === 'text') {
    const citationId = node.marks?.find(mark => mark.type === 'citation')?.attrs?.citationId as string | undefined
    const citationSuffix = citationId ? `[${citationIndex[citationId] ?? citationId}]` : ''
    return (node.text ?? '') + citationSuffix
  }
  return (node.content ?? []).map(child => renderTextContent(child, citationIndex)).join('')
}

export function buildPaperText (report: PaperReport, citationIndex: Record<string, number>): string {
  const lines: string[] = [`# ${report.title}`]

  for (const node of report.content.content ?? []) {
    if (node.type === 'heading') {
      lines.push(`## ${renderTextContent(node, citationIndex)}`)
    } else if (node.type === 'paragraph') {
      lines.push(renderTextContent(node, citationIndex))
    }
  }

  return lines.join('\n\n')
}
