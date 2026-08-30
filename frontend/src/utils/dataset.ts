/**
 * 資料集讀寫工具：CSV 與 Excel 共用。
 *
 * SheetJS 的解析與寫回只寫在這裡，欄位對齊頁與 DataTablePanel 都從這裡取用，
 * 不要在各自的元件裡再抄一份。
 */

import * as XLSX from 'xlsx'
import { decodeFileText, parseCsvLine } from './csv'

const EXCEL_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/** 未對應欄位與論文變數撞名時加的後綴。 */
const COLLISION_SUFFIX = '__原始'

export function getFileExtension (file: File): string {
  const name = file.name || ''
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase()
}

export function isExcelFile (file: File): boolean {
  const ext = getFileExtension(file)
  return ext === 'xlsx' || ext === 'xls'
}

function toCellText (cell: unknown): string {
  return cell === null || cell === undefined ? '' : String(cell)
}

/** 讀 Excel 第一張工作表，回傳字串化的列（整列空白的略過）。 */
export async function readExcelRows (file: File): Promise<string[][]> {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array' })
  const sheetName = workbook.SheetNames[0]
  if (!sheetName) {
    return []
  }

  const sheet = workbook.Sheets[sheetName]!
  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' })
  return rows
    .map(row => row.map(cell => toCellText(cell)))
    .filter(row => row.some(cell => cell.trim().length > 0))
}

/** 讀出整張表（第一列是表頭），CSV 與 Excel 都能吃。 */
export async function readTableRows (file: File): Promise<string[][]> {
  if (isExcelFile(file)) {
    return readExcelRows(file)
  }

  const text = await decodeFileText(file)
  return text
    .replace(/\r\n/g, '\n')
    .split('\n')
    .filter(line => line.trim().length > 0)
    .map(line => parseCsvLine(line))
}

/** 只要表頭與前幾筆的話用這個，畫分布圖那種要全部資料的用 readTableRows。 */
export async function readTablePreview (
  file: File,
  sampleRows = 5,
): Promise<{ columns: string[], rows: string[][] }> {
  const rows = await readTableRows(file)
  if (rows.length === 0) {
    return { columns: [], rows: [] }
  }
  return { columns: rows[0]!, rows: rows.slice(1, sampleRows + 1) }
}

/**
 * 依對映把表頭換成論文變數名。
 *
 * 沒對應到的欄位若剛好與某個論文變數同名，改寫後表頭會出現兩個同名欄位，
 * pandas 會自作主張改成 age / age.1，引擎就可能挑到錯的那一欄。
 * 這裡把「沒對應到的那一欄」加後綴避開。
 */
export function buildRenamedHeader (
  columns: string[],
  renameByColumn: Map<string, string>,
): string[] {
  const targets = new Set<string>()
  for (const name of columns) {
    const renamed = renameByColumn.get(name)
    if (renamed) {
      targets.add(renamed)
    }
  }

  const used = new Set<string>([...targets, ...columns])

  return columns.map(name => {
    const renamed = renameByColumn.get(name)
    if (renamed) {
      return renamed
    }
    if (!targets.has(name)) {
      return name
    }

    let candidate = `${name}${COLLISION_SUFFIX}`
    let serial = 2
    while (used.has(candidate)) {
      candidate = `${name}${COLLISION_SUFFIX}${serial}`
      serial += 1
    }
    used.add(candidate)
    return candidate
  })
}

/** 欄位名含逗號或引號時要包起來，否則改寫後的表頭會被拆錯欄。 */
function escapeCsvCell (value: string): string {
  if (!/[",\n]/.test(value)) {
    return value
  }
  return `"${value.replace(/"/g, '""')}"`
}

/** 算出改名後的表頭，以及要保留的原始欄位索引（沒被任何變數用到的欄位不會出現在這裡）。 */
function buildRewritePlan (
  columns: string[],
  renameByColumn: Map<string, string>,
  dropColumns: Set<string>,
): { keepIndices: number[], header: string[] } {
  const keepIndices: number[] = []
  const keptColumns: string[] = []
  for (const [index, name] of columns.entries()) {
    if (dropColumns.has(name)) {
      continue
    }
    keepIndices.push(index)
    keptColumns.push(name)
  }
  return { keepIndices, header: buildRenamedHeader(keptColumns, renameByColumn) }
}

async function rewriteCsv (
  file: File,
  renameByColumn: Map<string, string>,
  dropColumns: Set<string>,
): Promise<File> {
  const text = await decodeFileText(file)
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const headerIndex = lines.findIndex(line => line.trim().length > 0)
  if (headerIndex === -1) {
    return file
  }

  const originalHeader = parseCsvLine(lines[headerIndex]!)
  const { keepIndices, header } = buildRewritePlan(originalHeader, renameByColumn, dropColumns)

  // 沒有要刪欄位時維持原本「只換表頭、資料列原樣寫回」的做法：
  // 逐列重新解析會连帶把每個儲存格 trim 掉，沒必要在不刪欄位時冒這個風險
  if (dropColumns.size === 0) {
    lines[headerIndex] = header.map(name => escapeCsvCell(name)).join(',')
    return new File([lines.join('\n')], file.name, { type: file.type || 'text/csv' })
  }

  const rewritten = lines.map((line, index) => {
    if (index === headerIndex) {
      return header.map(name => escapeCsvCell(name)).join(',')
    }
    if (line.trim().length === 0) {
      return line
    }
    // trim:false 保留原始儲存格內容，只動要刪的欄位，不要順便改掉其他欄位的空白
    const cells = parseCsvLine(line, { trim: false })
    return keepIndices.map(i => escapeCsvCell(cells[i] ?? '')).join(',')
  })
  return new File([rewritten.join('\n')], file.name, { type: file.type || 'text/csv' })
}

/**
 * 資料格不轉字串：轉了之後整張表在 pandas 眼中都變成文字，數值欄位就廢了。
 */
async function rewriteExcel (
  file: File,
  renameByColumn: Map<string, string>,
  dropColumns: Set<string>,
): Promise<File> {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  const sheetName = workbook.SheetNames[0]
  if (!sheetName) {
    return file
  }

  const sheet = workbook.Sheets[sheetName]!
  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' })
  const headerIndex = rows.findIndex(
    row => row.some(cell => toCellText(cell).trim().length > 0),
  )
  if (headerIndex === -1) {
    return file
  }

  const originalHeader = rows[headerIndex]!.map(cell => toCellText(cell))
  const { keepIndices, header } = buildRewritePlan(originalHeader, renameByColumn, dropColumns)

  const rewrittenRows = rows.map((row, index) =>
    index === headerIndex ? header : keepIndices.map(i => row[i]),
  )
  workbook.Sheets[sheetName] = XLSX.utils.aoa_to_sheet(rewrittenRows, { cellDates: true })

  const bookType = getFileExtension(file) === 'xls' ? 'xls' : 'xlsx'
  const output = XLSX.write(workbook, { bookType, type: 'array' }) as ArrayBuffer
  return new File([output], file.name, { type: file.type || EXCEL_MIME })
}

/**
 * 依對映改寫表頭，並移除沒被任何變數認領的原始欄位；Excel 仍是合法活頁簿，副檔名不變。
 * dropColumns 留空時等同只改表頭，不動任何欄位。
 */
export async function rewriteDataset (
  file: File,
  renameByColumn: Map<string, string>,
  dropColumns: Set<string> = new Set(),
): Promise<File> {
  return isExcelFile(file)
    ? await rewriteExcel(file, renameByColumn, dropColumns)
    : await rewriteCsv(file, renameByColumn, dropColumns)
}
