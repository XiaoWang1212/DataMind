import { Extension } from '@tiptap/core'
import { Table } from '@tiptap/extension-table'
import { Plugin, PluginKey, type Transaction } from '@tiptap/pm/state'
import { TableMap } from '@tiptap/pm/tables'
import type { EditorView } from '@tiptap/pm/view'
import type { Node as PMNode } from '@tiptap/pm/model'

const MIN_COL_WIDTH = 40

type TMap = ReturnType<typeof TableMap.get>

// Table 節點多加一個「使用者是否已經手動調過整張表格寬度」的旗標。跟一般的欄界拖曳
// （鄰欄互相增減、表格總寬不變）不一樣，這裡指的是「表格總寬本身真的變了」的那種調整
// （典型情境：拖最後一欄，沒有鄰欄可以補償）。一旦標記過，rescaleMismatchedColumnWidths
// 就永遠跳過這張表，不會再把使用者剛調好的寬度拉回去貼齊容器——比照 Word/Excel，手動
// 調過大小的表格維持使用者調的大小，只有從頭到尾沒被動過寬度的表格才會自動貼齊容器。
export const ResizableTable = Table.extend({
  addAttributes () {
    return {
      ...this.parent?.(),
      manuallyResized: {
        default: false,
        parseHTML: () => false,
        renderHTML: () => ({}),
      },
    }
  },
})

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

// 依 row 0 的代表格收集每一欄的 colwidth[0]，跨 rescale 跟 appendTransaction 共用同一份
// 「這張表目前欄寬總和是多少」的邏輯，確保兩邊看到的是同一套數字。
//
// representativeCellPos 只做「垂直去重」（同一格跨列時只算一次），沒有做「水平去重」：
// colspan=2 的儲存格在它涵蓋的兩個 col 都會回傳同一個 cellPos。若不擋掉，同一格的
// colwidth[0] 會被重複加進總和，把總寬灌水。相鄰 col 拿到同一個 cellPos 就代表是同一格，跳過。
//
// 去重之後這個總和的意義是「row 0 各代表格 colwidth[0] 之和」，不等於瀏覽器實際渲染出來
// 的寬度總和——colspan 儲存格涵蓋的其他欄（colwidth[1] 以後）從來沒被 setColumnWidth 寫過
// （它永遠只寫 index 0），渲染時仍讀著舊值。這代表含 colspan 的表格重新縮放後跟容器寬度
// 會有一次性、固定量的殘差，不會累積或失控。要徹底對齊，須讓 setColumnWidth 支援寫入
// colspan 儲存格 colwidth 陣列裡的每一個元素，這不在目前的範圍內。
//
// width == null 擋「還沒被 seedMissingColumnWidths 處理過」；Number.isFinite 額外擋
// 「文件裡已經寫進 NaN」——早一版的邏輯在容器寬度量到 0 時會把 NaN 寫進 colwidth，存檔
// 存下來的舊文件可能還帶著這個髒值。NaN 通過 == null 檢查（NaN 不是 null），若不額外擋，
// NaN 會被當成合法寬度往下算，永遠卡在「每次 view 更新都再 dispatch 一次 NaN」的迴圈。
function collectColumnWidths (node: PMNode, map: TMap): { col: number, width: number }[] | null {
  const cols: { col: number, width: number }[] = []
  let prevCellPos = -1
  for (let col = 0; col < map.width; col++) {
    const cellPos = representativeCellPos(map, col)
    if (cellPos === -1) return null
    if (cellPos === prevCellPos) continue
    prevCellPos = cellPos
    const cellNode = node.nodeAt(cellPos)
    const width = cellNode?.attrs.colwidth?.[0]
    if (width == null || !Number.isFinite(width)) return null
    cols.push({ col, width })
  }
  return cols
}

function sumWidths (cols: { col: number, width: number }[]): number {
  return cols.reduce((sum, c) => sum + c.width, 0)
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

      if (!tr) {
        tr = state.tr
        // 這是自動量測凍結，不是使用者編輯，不該佔用一步 undo（也避免 Ctrl+Z 復原
        // 這個動作後，下一個 view 更新又立刻把它重新量測寫回去，undo 形同無效）。
        tr.setMeta('addToHistory', false)
      }
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
//    這個標記就整個跳過，不做鄰欄補償、也不判定成「使用者手動調整」。
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
    // 使用者已經手動調過這張表格的整體寬度（見 ResizableTable 的 manuallyResized），
    // 就不再自動貼齊容器——尊重使用者調過的大小，不要每次編輯都把它拉回去。
    if (node.attrs.manuallyResized) return false

    const map = TableMap.get(node)
    const cols = collectColumnWidths(node, map)
    if (!cols) return false
    const totalWidth = sumWidths(cols)

    const availableWidth = findTableWrapperWidth(view, pos)
    // 容器暫時沒有被渲染（隱藏分頁、display:none、路由切換中）時量到的是 0，不是 null。
    // 不擋的話 scale 會變 0，整排欄寬被寫成 0；下一輪 totalWidth 也變 0，scale 變成
    // 0/0 = NaN，而 NaN === width 永遠是 false，等於每次 view 更新都往文件寫一次 NaN。
    if (availableWidth == null || availableWidth <= 0) return false
    if (totalWidth <= 0) return false
    if (Math.abs(availableWidth - totalWidth) <= RESCALE_TOLERANCE_PX) return false

    // 每一欄各自 Math.round 的話，四捨五入的殘差會累加，欄數一多總和就可能超出
    // RESCALE_TOLERANCE_PX，而這次 dispatch 正好被重入旗標擋住後續遞迴，沒有第二輪
    // 自動修正，表格會一直差幾個 px。所以最後一欄不算 scale，直接吃剩下的餘數，
    // 讓總和精準落在 Math.round(availableWidth)。
    //
    // 縮小方向（availableWidth < totalWidth）逐欄夾在 MIN_COL_WIDTH 下限之上，而不是
    // 「只要有欄已經貼底，整張表就放棄縮小」。後者聽起來安全，實際上會讓任何天生就有
    // 窄欄的表格（例如 15 欄擠進 600px 容器，出生時每欄本來就在 40px 上下）永久失去
    // 被縮小的能力——側欄展開、視窗變窄之類的情境只會讓表格溢出容器，不會再自動修正，
    // 而且沒有任何後續動作能讓它恢復。逐欄夾制之後，被夾住多拿到的寬度就讓最後一欄的
    // 餘數分配自然吸收；如果全部欄早就在下限、夾完總和依然超過容器，算出來的新寬度會
    // 跟原寬度一樣，下面的「newWidth === width 就不 dispatch」會讓這一輪等同不做事，
    // 不會卡死也不會把任何一欄壓破下限。放大方向（availableWidth > totalWidth）不夾，
    // scale > 1 只會讓欄寬變大，不會製造新的下限違規。
    const isShrinking = availableWidth < totalWidth
    const scale = availableWidth / totalWidth
    const target = Math.round(availableWidth)
    let assigned = 0
    for (const [i, entry] of cols.entries()) {
      const { col, width } = entry
      const isLast = i === cols.length - 1
      let newWidth = isLast ? target - assigned : Math.round(width * scale)
      if (isShrinking) newWidth = Math.max(MIN_COL_WIDTH, newWidth)
      assigned += newWidth
      if (newWidth === width) continue
      if (!tr) {
        tr = state.tr
        tr.setMeta(RESCALE_META_KEY, true)
        // 同 seedMissingColumnWidths：自動校正不是使用者編輯，不佔用一步 undo，
        // 否則 Ctrl+Z 復原這個動作後，下一次 view 更新又會立刻偵測到「總寬對不上
        // 容器」再自動校正回去，undo 等於沒有作用；還會被 appendTransaction 誤判成
        // 一次使用者編輯（雖然有 RESCALE_META_KEY 擋掉了鄰欄補償/manuallyResized
        // 判定，但仍會留在 history 堆疊裡佔位）。
        tr.setMeta('addToHistory', false)
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
 * 那一欄，欄寬直接加總、表格總寬跟著變。這裡補四件事：
 *
 * 1. seedMissingColumnWidths（view 更新時）：新表格的欄位還沒有明確寬度時，把目前
 *    實際渲染寬度凍結成 colwidth，畫面不變，但讓後續縮放有基準。
 * 2. appendTransaction：偵測到某一欄的 colwidth 改變時，把差值從緊鄰右邊那一欄扣掉
 *    （多列、colspan 一起處理），讓表格總寬維持不變，行為跟 Excel/Word 拖曳欄界一致。
 * 3. rescaleMismatchedColumnWidths（view 更新時）：欄寬總和跟容器實際可用寬度對不上時
 *    （例如版面改版讓容器變寬變窄），按原比例整批重新縮放，讓表格一律填滿容器寬度。
 * 4. appendTransaction 同時偵測「這次編輯讓表格總寬真的變了」（例如拖最後一欄沒有鄰欄
 *    可補償、或補償撞到 MIN_COL_WIDTH 夾擠），標記 manuallyResized，之後第 3 點就不會
 *    再把使用者剛調好的寬度拉回去貼齊容器。
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
            if (node.attrs.manuallyResized) return false // 已經標記過，不用再比較

            const map = TableMap.get(node)
            const oldTableNode = oldState.doc.nodeAt(pos)
            // 只比對列數（childCount）不夠：像 setContent 這種整段換掉文件內容的操作，
            // 有可能在同一個文件位置留下「列數剛好一樣、但欄數完全不同」的兩張不相干表格
            // （例如舊表格 3 欄、新表格 2 欄），會被誤判成「同一張表格的某一欄被改寬了」。
            // 欄數（TableMap.width）也一致，才真的有可能是同一張表格的欄寬被使用者調整過。
            const canCompare = !!oldTableNode
              && oldTableNode.type === node.type
              && oldTableNode.childCount === node.childCount
              && TableMap.get(oldTableNode).width === map.width

            if (!canCompare) return false

            // 這一輪的內部欄界補償（col 0 到 width-2）有沒有真的抓到一筆 delta——用來
            // 跟「拖最後一欄」區分開。拖最後一欄的寬度變化這個迴圈永遠看不到（迴圈上限
            // 就是 width-2），所以 sawInternalDelta 維持 false；但一般拖內部欄界，就算
            // 補償撞到 MIN_COL_WIDTH 夾擠、沒能完全吸收差值，這裡也會是 true。下面判斷
            // 總寬是否變動時，只有「完全沒有內部補償來源」才可能是使用者故意的總寬調整，
            // 避免把「內部拖曳撞到下限」誤判成「使用者手動調整整張表格寬度」（那樣會讓
            // 一次撞到下限的拖曳永久關掉這張表格的自動貼齊能力）。
            let sawInternalDelta = false

            for (let col = 0; col < map.width - 1; col++) {
              const cellPos = representativeCellPos(map, col)
              if (cellPos === -1) continue

              const newCell = node.nodeAt(cellPos)
              const oldCell = oldTableNode!.nodeAt(cellPos)
              if (!newCell || !oldCell) continue

              const newWidth = newCell.attrs.colwidth?.[0]
              const oldWidth = oldCell.attrs.colwidth?.[0]
              if (newWidth == null || oldWidth == null || newWidth === oldWidth) continue

              sawInternalDelta = true

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

            if (sawInternalDelta) return false

            // 鄰欄補償跑完之後，看這張表的欄寬總和是否真的變了（例如拖的是最後一欄，
            // 上面的迴圈從來沒把它當「有鄰欄可補償」的來源處理過）。用 resultTr.doc
            // （若這張表已經有補償被排進去）取代 newState.doc 來讀最終欄寬，確保讀到的
            // 是補償後的結果。
            const finalDoc = resultTr ? resultTr.doc : newState.doc
            const finalTableNode = finalDoc.nodeAt(pos)
            if (!finalTableNode) return false

            const oldCols = collectColumnWidths(oldTableNode!, TableMap.get(oldTableNode!))
            const newCols = collectColumnWidths(finalTableNode, TableMap.get(finalTableNode))
            // 欄數相同（TableMap.width 一致）不代表「同一批儲存格結構沒變」——mergeCells/
            // splitCell 可能在 width 不變的情況下改變 row 0 的實際儲存格分佈（去重後的
            // cols 陣列長度就會不同），也可能改變整個節點的 nodeSize。這類結構性變化不是
            // 使用者拖曳欄寬造成的總寬差異，不該被標記成 manuallyResized（一旦標記就永久
            // 卡死，例如合併儲存格後這張表格會永遠失去自動貼齊容器的能力）。用 nodeSize
            // 是否相同（結構完全沒變，只有 colwidth 屬性變了）加上去重後欄位數量、欄位
            // 索引是否一一對應，把這類情況排除在外，只留下「結構不變、純粹欄寬總和變了」
            // 的情況——那才是真正的使用者手動調整。
            const structurallyUnchanged = !!oldTableNode
              && oldTableNode.nodeSize === finalTableNode.nodeSize
              && !!oldCols && !!newCols
              && oldCols.length === newCols.length
              && oldCols.every((c, i) => newCols[i]?.col === c.col)
            if (structurallyUnchanged && oldCols && newCols) {
              const oldTotal = sumWidths(oldCols)
              const newTotal = sumWidths(newCols)
              if (Math.abs(newTotal - oldTotal) > RESCALE_TOLERANCE_PX) {
                if (!resultTr) resultTr = newState.tr
                resultTr.setNodeMarkup(pos, undefined, { ...finalTableNode.attrs, manuallyResized: true })
              }
            }

            return false
          })

          return resultTr
        },
      }),
    ]
  },
})
