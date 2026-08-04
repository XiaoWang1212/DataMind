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

export interface RenamedColumn {
  from: string
  to: string
}

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
  if (!sheetName) return []

  const sheet = workbook.Sheets[sheetName]!
  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' })
  return rows
    .map(row => row.map(cell => toCellText(cell)))
    .filter(row => row.some(cell => cell.trim().length > 0))
}

/** 讀出表頭與前 sampleRows 筆資料列，CSV 與 Excel 都能吃。 */
export async function readTablePreview (
  file: File,
  sampleRows = 5,
): Promise<{ columns: string[], rows: string[][] }> {
  if (!isExcelFile(file)) {
    const text = await decodeFileText(file)
    const lines = text
      .replace(/\r\n/g, '\n')
      .split('\n')
      .filter(line => line.trim().length > 0)
    if (lines.length === 0) return { columns: [], rows: [] }
    return {
      columns: parseCsvLine(lines[0]!),
      rows: lines.slice(1, sampleRows + 1).map(line => parseCsvLine(line)),
    }
  }

  const rows = await readExcelRows(file)
  if (rows.length === 0) return { columns: [], rows: [] }
  return { columns: rows[0]!, rows: rows.slice(1, sampleRows + 1) }
}

/**
 * 依對映把表頭換成論文變數名。
 *
 * 沒對應到的欄位若剛好與某個論文變數同名，改寫後表頭會出現兩個同名欄位，
 * pandas 會自作主張改成 age / age.1，引擎就可能挑到錯的那一欄。
 * 這裡把「沒對應到的那一欄」加後綴避開，並回報改了哪些，讓畫面能先告知使用者。
 */
export function buildRenamedHeader (
  columns: string[],
  renameByColumn: Map<string, string>,
): { header: string[], adjusted: RenamedColumn[] } {
  const targets = new Set<string>()
  for (const name of columns) {
    const renamed = renameByColumn.get(name)
    if (renamed) targets.add(renamed)
  }

  const used = new Set<string>([...targets, ...columns])
  const adjusted: RenamedColumn[] = []

  const header = columns.map(name => {
    const renamed = renameByColumn.get(name)
    if (renamed) return renamed
    if (!targets.has(name)) return name

    let candidate = `${name}${COLLISION_SUFFIX}`
    let serial = 2
    while (used.has(candidate)) {
      candidate = `${name}${COLLISION_SUFFIX}${serial}`
      serial += 1
    }
    used.add(candidate)
    adjusted.push({ from: name, to: candidate })
    return candidate
  })

  return { header, adjusted }
}

/** 欄位名含逗號或引號時要包起來，否則改寫後的表頭會被拆錯欄。 */
function escapeCsvCell (value: string): string {
  if (!/[",\n]/.test(value)) return value
  return `"${value.replace(/"/g, '""')}"`
}

async function rewriteCsvHeader (
  file: File,
  renameByColumn: Map<string, string>,
): Promise<File> {
  const text = await decodeFileText(file)
  const lines = text.replace(/\r\n/g, '\n').split('\n')
  const headerIndex = lines.findIndex(line => line.trim().length > 0)
  if (headerIndex >= 0) {
    const { header } = buildRenamedHeader(parseCsvLine(lines[headerIndex]!), renameByColumn)
    lines[headerIndex] = header.map(name => escapeCsvCell(name)).join(',')
  }
  return new File([lines.join('\n')], file.name, { type: file.type || 'text/csv' })
}

/**
 * Excel 只換表頭那一列，資料列原樣寫回。
 *
 * 資料格不轉字串：轉了之後整張表在 pandas 眼中都變成文字，數值欄位就廢了。
 */
async function rewriteExcelHeader (
  file: File,
  renameByColumn: Map<string, string>,
): Promise<File> {
  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true })
  const sheetName = workbook.SheetNames[0]
  if (!sheetName) return file

  const sheet = workbook.Sheets[sheetName]!
  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' })
  const headerIndex = rows.findIndex(
    row => row.some(cell => toCellText(cell).trim().length > 0),
  )
  if (headerIndex === -1) return file

  const { header } = buildRenamedHeader(
    rows[headerIndex]!.map(cell => toCellText(cell)),
    renameByColumn,
  )
  rows[headerIndex] = header
  workbook.Sheets[sheetName] = XLSX.utils.aoa_to_sheet(rows, { cellDates: true })

  const bookType = getFileExtension(file) === 'xls' ? 'xls' : 'xlsx'
  const output = XLSX.write(workbook, { bookType, type: 'array' }) as ArrayBuffer
  return new File([output], file.name, { type: file.type || EXCEL_MIME })
}

/** 改寫表頭後回傳新檔案；Excel 仍是合法活頁簿，副檔名不變。 */
export async function rewriteDatasetHeader (
  file: File,
  renameByColumn: Map<string, string>,
): Promise<File> {
  return isExcelFile(file)
    ? await rewriteExcelHeader(file, renameByColumn)
    : await rewriteCsvHeader(file, renameByColumn)
}
