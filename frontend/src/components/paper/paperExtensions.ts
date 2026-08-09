import { Link } from '@tiptap/extension-link'
import { Subscript } from '@tiptap/extension-subscript'
import { Superscript } from '@tiptap/extension-superscript'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TextAlign } from '@tiptap/extension-text-align'
import { StarterKit } from '@tiptap/starter-kit'
import { AlignableImage } from '@/components/paper/alignableImage'
import { CitationMark } from '@/components/paper/citationMark'
import { ColoredTableCell, ColoredTableHeader } from '@/components/paper/coloredTableCell'

export function buildPaperContentExtensions (citationIndex: Record<string, number>) {
  return [
    StarterKit.configure({ heading: { levels: [1, 2, 3] }, link: false }),
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Link.configure({ openOnClick: false, autolink: true }),
    Superscript,
    Subscript,
    Table.configure({ resizable: true }),
    TableRow,
    ColoredTableHeader,
    ColoredTableCell,
    AlignableImage.configure({ inline: false }),
    CitationMark.configure({ citationIndex }),
  ]
}
