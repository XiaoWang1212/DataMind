"""論文下載用的 HTML → PDF 轉檔。

前端已經把內容排成分頁好的獨立 HTML 文件（內嵌 CSS），這裡只單純轉檔，
不重新處理版面或引用邏輯。
"""

from weasyprint import HTML


def html_to_pdf(html: str) -> bytes:
    return HTML(string=html).write_pdf()
