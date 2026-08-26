"""html_to_pdf() 轉檔正確性 —— 只驗證輸出的位元組是合法 PDF（開頭是 %PDF 簽章），
不比對版面內容（那是 WeasyPrint 自己的職責，不是我們要測的）。

論文內容全是繁體中文，額外測一次中文字不會讓轉檔噴例外
（例如 Docker image 裡沒裝 CJK 字型時，WeasyPrint 本身不會報錯，但這裡至少
先確保轉檔流程本身不因為非 ASCII 字元而崩潰）。
"""

from services.report.pdf_export import html_to_pdf


def test_html_to_pdf_returns_valid_pdf_bytes():
    pdf_bytes = html_to_pdf("<h1>Hello</h1>")
    assert pdf_bytes[:5] == b"%PDF-"


def test_html_to_pdf_renders_traditional_chinese_without_error():
    pdf_bytes = html_to_pdf("<p>基於機器學習之電信客戶流失預測研究</p>")
    assert pdf_bytes[:5] == b"%PDF-"
