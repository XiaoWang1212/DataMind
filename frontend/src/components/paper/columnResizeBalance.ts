import { Extension } from '@tiptap/core'
import { Plugin, PluginKey, type Transaction } from '@tiptap/pm/state'
import { TableMap } from '@tiptap/pm/tables'
import type { EditorView } from '@tiptap/pm/view'

const MIN_COL_WIDTH = 40

type TMap = ReturnType<typeof TableMap.get>


function representativeCellPos (map: TMap, col: number): number {
  for (let row = 0; row < map.height; row++) {
    const idx = row * map.width + col
    const cellPos = map.map[idx]
    if (cellPos === undefined) continue
    if (row === 0 || cellPos !== map.map[idx - map.width]) {
      return cellPos
    }
  }
  return -1
}

function setColumnWidth (tr: Transaction, tableStart: number, map: TMap, col: number, width: number): void {
  for (let row = 0; row < map.height; row++) {
    const idx = row * map.width + col
    const cellPos = map.map[idx]
    if (cellPos === undefined) continue
    if (row !== 0 && cellPos === map.map[idx - map.width]) continue
    const cellDocPos = tableStart + cellPos
    const cellNode = tr.doc.nodeAt(cellDocPos)
    if (!cellNode) continue
    const colspan = cellNode.attrs.colspan ?? 1
    const colwidth = cellNode.attrs.colwidth ? cellNode.attrs.colwidth.slice() : new Array(colspan).fill(0)
    colwidth[0] = width
    tr.setNodeMarkup(cellDocPos, undefined, { ...cellNode.attrs, colwidth })
  }
}

// 表格剛插入時每一欄都還沒有 colwidth，瀏覽器用 table-layout:fixed 自動平分。
// 這裡把「當下實際渲染出來的寬度」直接量測、凍結成明確的 colwidth，畫面完全不變，
// 但之後每一欄都有基準可以互相增減（含使用者第一次縮放的那一次）。
// 一定要用量出來的真實寬度，不能用寫死的預設值——因為 table-layout:fixed 下，
// 欄寬總和小於容器寬度時，表格不會自動撐滿，會維持在欄寬總和的大小。
function seedMissingColumnWidths (view: EditorView): void {
  const { state } = view
  let tr: Transaction | null = null

  state.doc.descendants((node, pos) => {
    if (node.type.name !== 'table') return true
    const map = TableMap.get(node)

    for (let col = 0; col < map.width; col++) {
      const cellPos = representativeCellPos(map, col)
      if (cellPos === -1) continue
      const cellDocPos = pos + 1 + cellPos
      const cellNode = state.doc.nodeAt(cellDocPos)
      if (!cellNode || cellNode.attrs.colwidth) continue

      const dom = view.nodeDOM(cellDocPos)
      const width = dom instanceof HTMLElement ? Math.round(dom.getBoundingClientRect().width) : null
      if (!width) continue

      if (!tr) tr = state.tr
      setColumnWidth(tr, pos + 1, map, col, width)
    }

    return false
  })

  if (tr) view.dispatch(tr)
}

/**
 * Tiptap 的表格縮放（@tiptap/extension-table 的 resizable）預設只會改被拖曳的
 * 那一欄，欄寬直接加總、表格總寬跟著變。這裡補兩件事：
 *
 * 1. seedMissingColumnWidths（view 更新時）：新表格的欄位還沒有明確寬度時，把目前
 *    實際渲染寬度凍結成 colwidth，畫面不變，但讓後續縮放有基準。
 * 2. appendTransaction：偵測到某一欄的 colwidth 改變時，把差值從緊鄰右邊那一欄扣掉
 *    （多列、colspan 一起處理），讓表格總寬維持不變，行為跟 Excel/Word 拖曳欄界一致。
 */
export const ColumnResizeBalance = Extension.create({
  name: 'columnResizeBalance',

  addProseMirrorPlugins () {
    return [
      new Plugin({
        key: new PluginKey('columnResizeBalance'),
        view (editorView) {
          seedMissingColumnWidths(editorView)
          return {
            update (view) {
              seedMissingColumnWidths(view)
            },
          }
        },
        appendTransaction (transactions, oldState, newState) {
          if (!transactions.some(tr => tr.docChanged)) return null

          let resultTr: Transaction | null = null

          newState.doc.descendants((node, pos) => {
            if (node.type.name !== 'table') return true

            const map = TableMap.get(node)
            const oldTableNode = oldState.doc.nodeAt(pos)
            const canCompare = !!oldTableNode
              && oldTableNode.type === node.type
              && oldTableNode.childCount === node.childCount

            if (!canCompare) return false

            for (let col = 0; col < map.width - 1; col++) {
              const cellPos = representativeCellPos(map, col)
              if (cellPos === -1) continue

              const newCell = node.nodeAt(cellPos)
              const oldCell = oldTableNode!.nodeAt(cellPos)
              if (!newCell || !oldCell) continue

              const newWidth = newCell.attrs.colwidth?.[0]
              const oldWidth = oldCell.attrs.colwidth?.[0]
              if (newWidth == null || oldWidth == null || newWidth === oldWidth) continue

              const delta = newWidth - oldWidth
              const neighborCol = col + 1
              const neighborPos = representativeCellPos(map, neighborCol)
              if (neighborPos === -1) continue

              const neighborCell = node.nodeAt(neighborPos)
              const neighborWidth = neighborCell?.attrs.colwidth?.[0]
              if (neighborWidth == null) continue
              const targetNeighborWidth = Math.max(MIN_COL_WIDTH, neighborWidth - delta)
              if (targetNeighborWidth === neighborWidth) continue

              if (!resultTr) resultTr = newState.tr
              setColumnWidth(resultTr, pos + 1, map, neighborCol, targetNeighborWidth)
            }

            return false
          })

          return resultTr
        },
      }),
    ]
  },
})
