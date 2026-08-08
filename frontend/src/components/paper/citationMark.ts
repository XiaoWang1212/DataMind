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
        parseHTML: element => element.getAttribute('data-citation-id'),
        renderHTML: attributes => {
          if (!attributes.citationId) return {}
          return { 'data-citation-id': attributes.citationId }
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
        class: 'citation-mark',
        'data-citation-number': number ?? '',
      }),
      0,
    ]
  },
})
