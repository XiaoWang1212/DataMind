/**
 * 結果表格的複製／匯出共用邏輯：ResultTableActions 用這裡的函式，
 * 各結果面板不需要各自處理 clipboard 或 xlsx 細節。
 */

import * as XLSX from 'xlsx'

function toCellText (cell: string | number): string {
  return typeof cell === 'number' ? String(cell) : cell
}

/** 組成 Tab 分隔文字，貼到 Excel/Sheets 會自動分欄。 */
export async function copyTableToClipboard (
  headers: string[],
  rows: Array<Array<string | number>>,
): Promise<void> {
  const lines = [headers, ...rows].map(row => row.map(cell => toCellText(cell)).join('\t'))
  await navigator.clipboard.writeText(lines.join('\n'))
}

/** 產生單一工作表的 .xlsx 並觸發瀏覽器下載。 */
export function exportTableToExcel (
  headers: string[],
  rows: Array<Array<string | number>>,
  filename: string,
): void {
  const sheet = XLSX.utils.aoa_to_sheet([headers, ...rows])
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, sheet, 'Sheet1')
  const output = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' }) as ArrayBuffer

  const blob = new Blob([output], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}.xlsx`
  link.click()
  URL.revokeObjectURL(url)
}
