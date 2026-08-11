import { TableCell } from '@tiptap/extension-table-cell'
import { TableHeader } from '@tiptap/extension-table-header'

function backgroundColorAttribute () {
  return {
    backgroundColor: {
      default: null,
      parseHTML: (element: HTMLElement) => element.style.backgroundColor || null,
      renderHTML: (attributes: { backgroundColor?: string | null }) =>
        attributes.backgroundColor ? { style: `background-color: ${attributes.backgroundColor}` } : {},
    },
  }
}

export const ColoredTableCell = TableCell.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      ...backgroundColorAttribute(),
    }
  },
})

export const ColoredTableHeader = TableHeader.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      ...backgroundColorAttribute(),
    }
  },
})
