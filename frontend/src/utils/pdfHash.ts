// 用 PDF 內容而不是檔名判斷重複：同一份檔案必定相同，不同檔案必定不同。
// 在瀏覽器算完就能比對，不必先把檔案上傳到後端
export async function computePdfHash (file: File): Promise<string | null> {
  // crypto.subtle 只在安全情境下存在（https 或 localhost）。用區網 IP 以 http
  // 開發時會沒有，此時回傳 null 讓呼叫端退回只比檔名
  if (!globalThis.crypto?.subtle) {
    return null
  }

  const buffer = await file.arrayBuffer()
  const digest = await globalThis.crypto.subtle.digest('SHA-256', buffer)
  return [...new Uint8Array(digest)]
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('')
}
