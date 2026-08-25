/** 把畫面上已經渲染好的 .paginated-paper（含 A4 分頁、引用樣式、CSS 變數）
 * 包成一份獨立、可以直接丟給後端 WeasyPrint 轉檔的 HTML 文件。
 *
 * 直接複製目前頁面上所有 stylesheet 的 cssText，而不是手動重新描述一份樣式：
 * 一來 .a4-page 等規則本來就是 Vue 的 scoped style（帶 data-v-* attribute
 * selector），複製當下渲染出來的 DOM（outerHTML，attribute 也在）配上複製當下
 * 的樣式表，天生就對得上，不用自己重建 scoping；二來 CSS 變數（--color-text
 * 等主題色）也一起帶到了，不用另外複製一份容易忘記同步。
 *
 * 螢光筆（citation-mark 的底色）只在畫面上方便使用者點擊查看引用來源，PDF 裡
 * 沒有意義，用一條 !important 規則蓋掉——不管原本規則的 scoping/specificity
 * 多高都蓋得掉。
 */
export function buildPaperExportHtml (root: HTMLElement): string {
  const styleText = Array.from(document.styleSheets)
    .map(sheet => {
      try {
        return Array.from(sheet.cssRules).map(rule => rule.cssText).join('\n')
      } catch {
        // 跨來源的 stylesheet 讀不到 cssRules（例如外部字型），略過即可
        return ''
      }
    })
    .join('\n')

  return `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
${styleText}

/* 明確定死頁面尺寸跟頁邊距：.a4-page 自己的 96px padding 就是唯一的留白，
   不要再讓 WeasyPrint 的預設 @page margin 疊上去，兩層留白疊加會讓版面看起來歪掉 */
@page {
  size: A4;
  margin: 0;
}

body {
  margin: 0;
}

.citation-mark {
  background: none !important;
}
</style>
</head>
<body>
${root.outerHTML}
</body>
</html>`
}
