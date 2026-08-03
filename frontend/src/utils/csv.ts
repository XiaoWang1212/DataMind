/**
 * CSV 解析共用工具。
 *
 * DataTablePanel、DistributionPanel、欄位對齊頁三處共用，不要各自再抄一份。
 */

/** 解析一行 CSV，處理雙引號包住的欄位與跳脫的雙引號。 */
export function parseCsvLine (line: string): string[] {
  const out: string[] = []
  let cur = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i]
    const next = line[i + 1]

    if (ch === '"' && inQuotes && next === '"') {
      cur += '"'
      i += 1
      continue
    }

    if (ch === '"') {
      inQuotes = !inQuotes
      continue
    }

    if (ch === ',' && !inQuotes) {
      out.push(cur.trim())
      cur = ''
      continue
    }

    cur += ch
  }

  out.push(cur.trim())
  return out
}

/**
 * 讀檔並自動判斷編碼。
 *
 * 醫院匯出的資料表常見 Big5，UTF-8 解不出來或解出一堆替換字元時改用 Big5。
 */
export async function decodeFileText (file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  const decoderUtf8 = new TextDecoder('utf-8', { fatal: true })
  let utf8Text: string | null = null
  try {
    utf8Text = decoderUtf8.decode(buffer)
  } catch {
    utf8Text = null
  }

  const decoderBig5 = new TextDecoder('big5')
  const big5Text = decoderBig5.decode(buffer)

  if (!utf8Text) {
    return big5Text
  }

  const scoreText = (text: string) => {
    const headerLine = text.split(/\r?\n/, 1)[0] ?? ''
    const cjkCount = (headerLine.match(/[\u4E00-\u9FFF]/g) || []).length
    const replacementCount = (text.match(/\uFFFD/g) || []).length
    return cjkCount * 10 - replacementCount * 20
  }

  const utf8Score = scoreText(utf8Text)
  const big5Score = scoreText(big5Text)

  return big5Score > utf8Score ? big5Text : utf8Text
}

/** 讀出表頭與前 sampleRows 筆資料列。 */
export async function parseCsvPreview (
  file: File,
  sampleRows = 5,
): Promise<{ columns: string[]; rows: string[][] }> {
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
