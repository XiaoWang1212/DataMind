import { Mark, mergeAttributes } from '@tiptap/core'

export interface CitationMarkOptions {
  citationIndex: Record<string, number>
}

export const CitationMark = Mark.create<CitationMarkOptions>({
  name: 'citation',

  addOptions () {
    return {
      citationIndex: {},
    }
  },

  addAttributes () {
    return {
      citationId: {
        default: null,
        parseHTML: element => element.dataset.citationId,
        renderHTML: attributes => {
          if (!attributes.citationId) {
            return {}
          }
          return { 'data-citation-id': attributes.citationId }
        },
      },
      // 這次引用實際依據的來源片段，跟書目資訊（標題/作者/期刊）分開存——
      // 同一篇論文在不同段落被引用時，這個值可能不一樣
      relevantChunk: {
        default: null,
        parseHTML: element => element.dataset.relevantChunk,
        renderHTML: attributes => {
          if (!attributes.relevantChunk) {
            return {}
          }
          return { 'data-relevant-chunk': attributes.relevantChunk }
        },
      },
    }
  },

  parseHTML () {
    return [{ tag: 'span[data-citation-id]' }]
  },

  renderHTML ({ HTMLAttributes }) {
    const citationId = HTMLAttributes['data-citation-id'] as string | undefined
    const number = citationId ? this.options.citationIndex[citationId] : undefined

    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'class': 'citation-mark',
        'data-citation-number': number ?? '',
      }),
      0,
    ]
  },
})
