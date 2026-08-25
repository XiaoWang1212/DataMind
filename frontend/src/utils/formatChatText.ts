// AI 回覆常帶 **粗體** 標記，這裡只轉換這一種標記，不做完整 markdown 解析。
// 先跳脫 HTML 特殊字元，避免回覆內容被當成標籤解析。
export function renderChatText (text: string): string {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}
