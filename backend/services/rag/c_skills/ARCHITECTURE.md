# Skills 資料夾架構說明

## 📋 總覽

這是一個為 **AI 助手（如 Claude）** 設計的技能庫系統，提供完整的 Office 文件處理能力。當用戶要求 AI 執行文件相關任務時，AI 會參考這些技能文檔中的方法、範例代碼和工具腳本來完成任務。

### 核心理念
- **即用性**：提供完整的代碼範例和可執行腳本
- **分層設計**：從基礎入門到進階操作的漸進式文檔
- **多技術棧**：同時支援 Python 和 JavaScript 實作
- **標準化**：每個格式都遵循相同的文檔結構模式

---

## 🗂️ 整體架構

```
skills/
├── pdf/          # PDF 文件處理
├── docx/         # Word 文件處理
├── pptx/         # PowerPoint 簡報處理
└── xlsx/         # Excel 試算表處理
```

每個子資料夾都是一個獨立的**技能模組**，包含完整的文檔、腳本工具和資源文件。

---

## 📄 PDF 處理模組 (`pdf/`)

### 功能範圍
- **文本提取**：從 PDF 中提取純文本、保留排版
- **表格提取**：識別並提取表格數據為結構化格式
- **文件操作**：合併、分割、旋轉頁面
- **表單處理**：填寫可編輯表單、提取表單欄位
- **OCR**：從掃描 PDF 中識別文字
- **安全性**：加密/解密、密碼保護

### 文檔結構
```
pdf/
├── SKILL.md          # 基礎技能入門（快速參考）
├── FORMS.md          # 表單填寫專用指南
├── REFERENCE.md      # 進階操作和詳細參考
└── scripts/          # 8 個實用工具腳本
    ├── fill_fillable_fields.py           # 填寫可編輯欄位
    ├── fill_pdf_form_with_annotations.py # 使用標註填寫表單
    ├── extract_form_field_info.py        # 提取表單欄位資訊
    ├── check_fillable_fields.py          # 檢查可填寫欄位
    ├── check_bounding_boxes.py           # 檢查邊界框
    ├── create_validation_image.py        # 創建驗證圖片
    └── convert_pdf_to_images.py          # PDF 轉圖片
```

### 技術棧
- **Python**: pypdf, pdfplumber, reportlab, pytesseract
- **CLI**: qpdf, pdftotext, pdfimages (poppler-utils)

### 典型使用場景
- 批量提取發票、合約中的數據
- 自動化填寫政府表單
- 合併多份報告為單一文件
- 從掃描文件中提取可搜尋文字

---

## 📝 Word 文件處理模組 (`docx/`)

### 功能範圍
- **文件創建**：從零建立專業 Word 文件
- **內容編輯**：修改現有文件內容
- **追蹤修訂**：實作 Redlining 工作流（修訂模式）
- **評論系統**：添加、讀取文件評論
- **格式保留**：維持原有樣式和結構
- **深度操作**：透過 OOXML 進行底層編輯

### 文檔結構
```
docx/
├── SKILL.md          # 主要技能指南（含工作流決策樹）
├── docx-js.md        # JavaScript 實作方法
├── ooxml.md          # OOXML 底層格式說明
├── ooxml/            # OOXML 相關資源
│   ├── schemas/      # XML 架構定義
│   └── scripts/      # 打包/解包工具
└── scripts/          # 核心處理模組
    ├── document.py   # 文件處理核心（50KB）
    ├── utilities.py  # 工具函數庫（13KB）
    └── templates/    # 文件模板
```

### 技術棧
- **Python**: python-docx, pandoc, lxml
- **JavaScript**: docx (npm)
- **格式**: OOXML (Office Open XML)

### 工作流決策樹（from SKILL.md）
1. **讀取/分析** → 使用 pandoc 轉 markdown
2. **創建新文件** → 使用高階 API (python-docx)
3. **編輯自己的文件** → 基礎 OOXML 編輯
4. **編輯他人文件** → **Redlining 工作流**（保留修訂記錄）
5. **法律/學術/商業文件** → **必須使用 Redlining**

### 典型使用場景
- 批量生成客製化合約
- 協作文件的修訂追蹤
- 提取文件評論進行分析
- 保留格式的內容替換

---

## 🎨 PowerPoint 簡報處理模組 (`pptx/`)

### 功能範圍
- **簡報創建**：程式化建立專業簡報
- **內容編輯**：修改投影片內容和版面
- **HTML 轉換**：將 HTML 內容轉為 PowerPoint
- **設計元素**：主題、色彩、字型管理
- **版面配置**：投影片佈局、母片編輯
- **備註與評論**：處理演講者備註和評論

### 文檔結構
```
pptx/
├── SKILL.md          # 主要技能指南
├── html2pptx.md      # HTML 轉 PPTX 特殊功能
├── html2pptx.tgz     # HTML 轉換工具包
├── ooxml.md          # OOXML 格式說明
├── ooxml/            # OOXML 相關資源
│   ├── schemas/      # XML 架構定義
│   └── scripts/      # 打包/解包工具
└── scripts/          # 實用工具
    ├── inventory.py  # 簡報資源清單（38KB）
    ├── replace.py    # 內容替換工具（13KB）
    ├── rearrange.py  # 投影片重排（8KB）
    └── thumbnail.py  # 縮圖生成（15KB）
```

### 技術棧
- **Python**: python-pptx, lxml, markitdown
- **格式**: OOXML, HTML
- **工具**: html2pptx (custom package)

### 關鍵 XML 結構
```
ppt/
├── presentation.xml              # 簡報元數據
├── slides/slide{N}.xml           # 各投影片內容
├── notesSlides/notesSlide{N}.xml # 演講者備註
├── slideLayouts/                 # 版面配置模板
├── slideMasters/                 # 母片模板
├── theme/theme1.xml              # 主題（色彩、字型）
└── media/                        # 媒體文件
```

### 典型使用場景
- 從數據自動生成銷售報告簡報
- 批量更新企業簡報模板
- 將網頁內容轉為簡報格式
- 提取簡報主題色彩和字型

---

## 📊 Excel 試算表處理模組 (`xlsx/`)

### 功能範圍
- **試算表創建**：建立包含公式和格式的試算表
- **數據分析**：讀取、處理、分析試算表數據
- **公式處理**：創建、驗證、重新計算公式
- **財務模型**：專業財務模型標準（色彩編碼、格式規範）
- **格式保留**：編輯時維持現有格式和公式
- **多格式支援**：xlsx, xlsm, csv, tsv

### 文檔結構
```
xlsx/
├── SKILL.md          # 完整技能指南（含財務模型規範）
└── recalc.py         # 公式重新計算工具
```

### 核心要求（from SKILL.md）

#### 1. 零錯誤原則
- **所有 Excel 文件必須零公式錯誤**（#REF!, #DIV/0!, #VALUE! 等）

#### 2. 財務模型色彩編碼標準
| 顏色 | RGB | 用途 |
|------|-----|------|
| 🔵 藍色 | 0,0,255 | 硬編碼輸入、可變參數 |
| ⚫ 黑色 | 0,0,0 | 所有公式和計算 |
| 🟢 綠色 | 0,128,0 | 工作表內部連結 |
| 🔴 紅色 | 255,0,0 | 外部文件連結 |
| 🟡 黃底 | 255,255,0 | 需要注意的關鍵假設 |

#### 3. 數字格式標準
- **年份**: 文字格式 ("2024" 不是 "2,024")
- **貨幣**: $#,##0 格式，在標題標明單位
- **零值**: 顯示為 "-"
- **百分比**: 0.0% (一位小數)
- **負數**: 使用括號 (123) 而非 -123

### 技術棧
- **Python**: openpyxl, pandas, xlrd, xlsxwriter
- **格式**: XLSX, XLSM, CSV, TSV

### 典型使用場景
- 建立財務預測模型
- 批量處理數據報表
- 自動化數據驗證和計算
- 從 CSV 生成格式化的 Excel 報告

---

## 🔧 共通設計模式

### 1. 分層文檔結構
```
SKILL.md           → 快速入門、常用操作
↓
REFERENCE.md       → 進階技術、詳細說明
↓
專用主題.md        → 特殊功能（如 FORMS.md, html2pptx.md）
```

### 2. YAML Frontmatter
每個 SKILL.md 都包含標準化的 metadata：
```yaml
---
name: pdf
description: "技能描述，說明使用時機和主要功能"
---
```

### 3. OOXML 底層存取
**DOCX 和 PPTX** 都支援 OOXML 層級的操作：
- **解包**: `python ooxml/scripts/unpack.py <file> <output_dir>`
- **直接編輯 XML**: 修改文件結構、樣式、元數據
- **重新打包**: 生成修改後的文件

這允許執行高階 API 無法完成的複雜操作。

### 4. 多語言支援
- **Python**: 主要實作語言，適合後端處理
- **JavaScript**: 部分模組提供 JS 實作（如 docx-js.md）
- **CLI 工具**: 提供命令列介面選項（qpdf, pandoc 等）

---

## 🎯 使用方式

### AI 助手的工作流程

1. **接收任務**: 用戶要求「合併這 3 個 PDF」
2. **查詢技能庫**: AI 讀取 `pdf/SKILL.md`
3. **選擇方法**: 找到合併 PDF 的代碼範例
4. **執行任務**:
   - 使用範例代碼
   - 或調用 scripts/ 中的工具
5. **回報結果**: 完成任務並告知用戶

### 人類開發者的使用方式

1. **參考文檔**: 查閱 SKILL.md 學習基礎操作
2. **進階學習**: 閱讀 REFERENCE.md 深入理解
3. **使用工具**: 直接執行 scripts/ 中的腳本
4. **定製化**: 基於範例代碼客製化功能

---

## 📦 技術棧總覽

### Python 函式庫
| 格式 | 主要函式庫 |
|------|-----------|
| PDF  | pypdf, pdfplumber, reportlab, pytesseract |
| DOCX | python-docx, lxml, pandoc |
| PPTX | python-pptx, lxml, markitdown |
| XLSX | openpyxl, pandas, xlsxwriter |

### 命令列工具
- **qpdf**: PDF 操作
- **pandoc**: 文件格式轉換
- **poppler-utils**: PDF 工具集 (pdftotext, pdfimages)

### 格式標準
- **OOXML**: Office Open XML（docx, pptx, xlsx 的底層格式）
- **XML**: 結構化數據存取
- **ZIP**: Office 文件實際上是 ZIP 壓縮檔

---

## 🚀 擴展性

### 新增技能模組
如需添加新的文件格式支援（如 ODP, RTF 等）：

```
skills/
└── <format>/
    ├── SKILL.md          # 必須：基礎技能指南
    ├── REFERENCE.md      # 可選：進階參考
    ├── scripts/          # 可選：實用工具腳本
    └── ooxml/            # 可選：如果是 OOXML 格式
```

### SKILL.md 模板結構
```markdown
---
name: format_name
description: "功能描述"
---

# 格式處理

## Overview
簡介

## Quick Start
快速開始範例

## Common Tasks
常見任務

## Reference
參考資料
```

---

## 💡 最佳實踐

### 文檔撰寫
- ✅ 提供可直接執行的代碼範例
- ✅ 包含錯誤處理和邊界情況
- ✅ 說明各方法的適用場景
- ✅ 提供決策樹幫助選擇方法

### 腳本開發
- ✅ 每個腳本專注單一功能
- ✅ 提供清晰的命令列介面
- ✅ 包含使用說明和錯誤提示
- ✅ 處理常見的錯誤情況

### 維護原則
- ✅ 保持文檔與代碼同步
- ✅ 測試所有範例代碼
- ✅ 更新時遵循現有結構模式
- ✅ 保留向後相容性

---

## 📚 相關資源

### 官方文檔
- [python-docx](https://python-docx.readthedocs.io/)
- [python-pptx](https://python-pptx.readthedocs.io/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- [pypdf](https://pypdf.readthedocs.io/)

### 格式規範
- [OOXML 標準](http://www.ecma-international.org/publications/standards/Ecma-376.htm)
- [PDF 規範](https://www.adobe.com/devnet/pdf/pdf_reference.html)

---

## 📝 版本資訊

**當前版本**: 1.0
**最後更新**: 2025-10-12
**維護者**: AI Skills Team

---

## 🤝 貢獻指南

如需添加新功能或改進現有文檔：
1. 遵循現有的資料夾結構
2. 保持文檔風格一致
3. 提供完整的代碼範例
4. 更新本 ARCHITECTURE.md

---

## ⚠️ 注意事項

1. **版權**: 處理文件時注意版權和授權問題
2. **隱私**: 不要在範例中使用真實的敏感數據
3. **相依性**: 確保所有範例的相依套件都已說明
4. **錯誤處理**: 所有生產代碼都應包含適當的錯誤處理

---

**這個技能庫的最終目標**: 讓 AI 助手能夠像人類專家一樣，熟練處理各種 Office 文件格式的複雜任務。
