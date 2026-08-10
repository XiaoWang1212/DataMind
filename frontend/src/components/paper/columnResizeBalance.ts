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

const RESCALE_TOLERANCE_PX = 2
const RESCALE_META_KEY = 'columnResizeBalance$rescale'

// 表格的 .tableWrapper 是一般 block 層級的 <div>，寬度會忠實反映容器實際可用寬度，
// 不受表格自己目前 table-layout:fixed 的欄寬總和影響（跟量測表格本身寬度不一樣）。
// prosemirror-tables 的 TableView 建立的 DOM 結構本身就是 <div class="tableWrapper">
// 包住 <table>，view.nodeDOM(tableDocPos) 對表格節點回傳的就是這個 wrapper div；
// 這裡多做一層防呆（往內找、往外找）避免版本差異或未來 NodeView 實作改變時直接量到錯的元素。
function findTableWrapperWidth (view: EditorView, tableDocPos: number): number | null {
  const dom = view.nodeDOM(tableDocPos)
  if (!(dom instanceof HTMLElement)) return null

  let wrapper: HTMLElement | null = dom
  if (!wrapper.classList.contains('tableWrapper')) {
    wrapper = wrapper.closest('.tableWrapper') ?? wrapper.querySelector('.tableWrapper')
  }

  return (wrapper ?? dom).getBoundingClientRect().width
}

// 欄寬是「建立當下」量測凍結的固定像素值，之後容器寬度如果變了（例如編輯區版面改版），
// 欄寬不會自動跟著調整，會出現表格比容器窄（或寬）一截的狀況。這裡在每次 view 更新時，
// 比對每張表格「目前欄寬總和」跟「容器實際可用寬度」，對不上（超過 RESCALE_TOLERANCE_PX）
// 就按原本的相對比例整批重新縮放，讓表格一律填滿容器寬度。
//
// 跟拖曳欄界（下面的 appendTransaction）不會互相干擾，分兩個方向：
//
// 1. 這裡的觸發條件只看「總寬對不上容器」——拖曳過程中容器寬度沒變、欄寬總和也刻意
//    維持不變，不會被這裡判定為「對不上」而觸發重新縮放，這個方向沒有問題。
//
// 2. 反過來，我們這裡一次送出的 transaction 會同時改動好幾欄的 colwidth（等比例縮放
//    每一欄），而 appendTransaction 是「只要 docChanged 就看每一欄改了多少，把差值從
//    緊鄰右欄扣掉」——如果讓它處理我們這個 transaction，會把「好幾欄同時等比例變寬/
//    變窄」誤判成「使用者依序拖了好幾次欄界」，對每一欄都再疊加一次鄰欄補償，把等比例
//    縮放的結果弄亂。所以送出前用 setMeta 標記這個 transaction，appendTransaction 看到
//    這個標記就整個跳過，不做鄰欄補償。
//
// 另外，這裡的 view.dispatch 是在 Plugin.view() 的 update 回呼裡呼叫的：dispatch 會
// 同步地再次觸發所有 plugin 的 update 回呼（包含這個函式自己）。修好上面第 2 點之後，
// 重入時讀到的會是已經完整套用、總寬已對齊容器的狀態，正常情況下不會再觸發新的
// dispatch，但仍用一個旗標擋掉重入，避免萬一還有下一輪誤差需要處理時重複做多餘的工。
let isDispatchingRescale = false
function rescaleMismatchedColumnWidths (view: EditorView): void {
  if (isDispatchingRescale) return

  const { state } = view
  let tr: Transaction | null = null

  state.doc.descendants((node, pos) => {
    if (node.type.name !== 'table') return true
    const map = TableMap.get(node)

    // representativeCellPos 只做「垂直去重」（同一格跨列時只算一次），沒有做「水平去重」：
    // colspan=2 的儲存格在它涵蓋的兩個 col 都會回傳同一個 cellPos。若不擋掉，同一格的
    // colwidth[0] 會被重複加進 totalWidth，把總寬灌水、算出偏小的 scale，讓有合併儲存格
    // 的表格每次都被縮得比實際目標還小。相鄰 col 拿到同一個 cellPos 就代表是同一格，跳過。
    const cols: { col: number, width: number }[] = []
    let totalWidth = 0
    let prevCellPos = -1
    for (let col = 0; col < map.width; col++) {
      const cellPos = representativeCellPos(map, col)
      if (cellPos === -1) return false
      if (cellPos === prevCellPos) continue
      prevCellPos = cellPos
      const cellNode = node.nodeAt(cellPos)
      const width = cellNode?.attrs.colwidth?.[0]
      if (width == null) return false // 還沒被 seedMissingColumnWidths 處理過，這輪先跳過
      cols.push({ col, width })
      totalWidth += width
    }

    const availableWidth = findTableWrapperWidth(view, pos)
    // 容器暫時沒有被渲染（隱藏分頁、display:none、路由切換中）時量到的是 0，不是 null。
    // 不擋的話 scale 會變 0，整排欄寬被寫成 0；下一輪 totalWidth 也變 0，scale 變成
    // 0/0 = NaN，而 NaN === width 永遠是 false，等於每次 view 更新都往文件寫一次 NaN。
    if (availableWidth == null || availableWidth <= 0) return false
    if (totalWidth <= 0) return false
    if (Math.abs(availableWidth - totalWidth) <= RESCALE_TOLERANCE_PX) return false

    // 拖曳欄界時，鄰欄補償會用 Math.max(MIN_COL_WIDTH, ...) 夾住鄰欄寬度；夾住的那一刻
    // 起，欄寬總和會真的超過容器寬度（因為鄰欄沒能吃下全部的差值）。這時如果照常等比例
    // 縮小，會連使用者根本沒碰過的欄一起縮，甚至把已經被夾在下限的欄再壓到下限以下——
    // 正是這裡最該避免的互相干擾。已經有欄貼在下限的表格就當作「壓到底了」，不再縮小。
    // 只擋縮小方向；容器真的變寬（availableWidth > totalWidth）時放行，變寬不會再往下擠。
    if (availableWidth < totalWidth && cols.some(c => c.width <= MIN_COL_WIDTH)) return false

    // 每一欄各自 Math.round 的話，四捨五入的殘差會累加，欄數一多總和就可能超出
    // RESCALE_TOLERANCE_PX，而這次 dispatch 正好被重入旗標擋住後續遞迴，沒有第二輪
    // 自動修正，表格會一直差幾個 px。所以最後一欄不算 scale，直接吃剩下的餘數，
    // 讓總和精準落在 Math.round(availableWidth)。
    const scale = availableWidth / totalWidth
    const target = Math.round(availableWidth)
    let assigned = 0
    for (let i = 0; i < cols.length; i++) {
      const entry = cols[i]
      if (!entry) continue
      const { col, width } = entry
      const isLast = i === cols.length - 1
      const newWidth = isLast ? target - assigned : Math.round(width * scale)
      assigned += newWidth
      if (newWidth === width) continue
      if (!tr) {
        tr = state.tr
        tr.setMeta(RESCALE_META_KEY, true)
      }
      setColumnWidth(tr, pos + 1, map, col, newWidth)
    }

    return false
  })

  if (tr) {
    isDispatchingRescale = true
    try {
      view.dispatch(tr)
    } finally {
      isDispatchingRescale = false
    }
  }
}

/**
 * Tiptap 的表格縮放（@tiptap/extension-table 的 resizable）預設只會改被拖曳的
 * 那一欄，欄寬直接加總、表格總寬跟著變。這裡補三件事：
 *
 * 1. seedMissingColumnWidths（view 更新時）：新表格的欄位還沒有明確寬度時，把目前
 *    實際渲染寬度凍結成 colwidth，畫面不變，但讓後續縮放有基準。
 * 2. appendTransaction：偵測到某一欄的 colwidth 改變時，把差值從緊鄰右邊那一欄扣掉
 *    （多列、colspan 一起處理），讓表格總寬維持不變，行為跟 Excel/Word 拖曳欄界一致。
 * 3. rescaleMismatchedColumnWidths（view 更新時）：欄寬總和跟容器實際可用寬度對不上時
 *    （例如版面改版讓容器變寬變窄），按原比例整批重新縮放，讓表格一律填滿容器寬度。
 */
export const ColumnResizeBalance = Extension.create({
  name: 'columnResizeBalance',

  addProseMirrorPlugins () {
    return [
      new Plugin({
        key: new PluginKey('columnResizeBalance'),
        view (editorView) {
          seedMissingColumnWidths(editorView)
          rescaleMismatchedColumnWidths(editorView)
          return {
            update (view) {
              seedMissingColumnWidths(view)
              rescaleMismatchedColumnWidths(view)
            },
          }
        },
        appendTransaction (transactions, oldState, newState) {
          if (transactions.some(tr => tr.getMeta(RESCALE_META_KEY))) return null
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
