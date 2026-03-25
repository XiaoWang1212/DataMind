# Skills 與 RAG 系統整合指南

## 📋 概述

本文檔說明如何將 Skills 文檔處理技能庫整合到 RAG (Retrieval-Augmented Generation) 系統中，提升知識庫對 Office 文檔格式的處理能力。

**目標讀者**: RAG 系統開發者、知識庫系統架構師、AI 應用工程師

**適用場景**:
- 企業知識庫管理系統
- 智能文檔問答系統
- AI 驅動的文檔處理平台
- 自動化報告生成系統

---

## 🎯 核心價值主張

### 傳統 RAG 系統的限制
❌ 只能處理純文本或簡單的 PDF
❌ 表格數據處理效果差
❌ 無法生成專業格式的輸出文檔
❌ Office 格式支援有限

### 整合 Skills 後的能力
✅ 支援 PDF、DOCX、PPTX、XLSX 等多種格式
✅ 智能提取表格和結構化數據
✅ 生成專業的 Office 格式報告
✅ 保留文檔原始格式和樣式
✅ 自動化文檔處理工作流程

---

## 🔄 RAG 系統整合架構

### 完整處理流程

```
┌─────────────────────────────────────────────────────────────┐
│                      用戶上傳文檔                            │
│            (PDF, DOCX, PPTX, XLSX, TXT, etc.)               │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              📄 Skills 文檔解析層                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   PDF    │  │   DOCX   │  │   PPTX   │  │   XLSX   │   │
│  │  解析器   │  │  解析器   │  │  解析器   │  │  解析器   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       ↓              ↓              ↓              ↓         │
│   文字+表格      Markdown        投影片文字    結構化數據    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  文本預處理與切分                            │
│  • 文本清理  • 分段 (Chunking)  • 元數據標註                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    向量化 (Embedding)                        │
│       使用 OpenAI/Cohere/本地模型生成向量表示                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  向量資料庫儲存                              │
│  ┌────────────────┐        ┌────────────────┐              │
│  │  向量資料庫     │        │ 結構化資料庫    │              │
│  │  (Pinecone/    │        │ (PostgreSQL/   │              │
│  │   Qdrant/      │        │  MongoDB)      │              │
│  │   Chroma)      │        │                │              │
│  │                │        │  • 表格數據     │              │
│  │ • 文本向量      │        │  • 元數據       │              │
│  │ • 元數據索引    │        │  • 原始文件     │              │
│  └────────────────┘        └────────────────┘              │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                      用戶查詢                                │
│            「請分析 Q3 銷售數據的趨勢」                       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  檢索相關內容                                │
│  • 語義搜尋 (Semantic Search)                               │
│  • 混合搜尋 (Hybrid Search: 向量 + 關鍵字)                  │
│  • 重排序 (Reranking)                                       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                  LLM 生成答案                                │
│        使用檢索到的上下文生成自然語言回答                     │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              📊 Skills 文檔生成層 (可選)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ PDF 生成  │  │ Word 生成 │  │ PPT 生成  │  │ Excel生成 │   │
│  │          │  │          │  │          │  │          │   │
│  │ reportlab│  │python-docx│  │python-pptx│  │ openpyxl │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│                    回傳給用戶                                │
│         • 文字答案  • 專業文檔  • 可視化圖表                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 階段一：文檔攝取 (Document Ingestion)

### 1.1 多格式文檔解析

#### PDF 文檔處理
```python
# 使用 skills/pdf 的方法
import pdfplumber
from pypdf import PdfReader

def process_pdf_for_rag(file_path):
    """
    處理 PDF 文檔，提取文字和表格
    """
    result = {
        'text': '',
        'tables': [],
        'metadata': {}
    }

    # 方法 1: 提取純文本
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            # 提取文字
            text = page.extract_text()
            result['text'] += f"\n=== Page {page_num} ===\n{text}"

            # 提取表格（重要！RAG 通常忽略表格）
            tables = page.extract_tables()
            for table_idx, table in enumerate(tables):
                if table:
                    import pandas as pd
                    df = pd.DataFrame(table[1:], columns=table[0])

                    # 轉為 Markdown 格式便於 RAG 檢索
                    table_markdown = df.to_markdown(index=False)

                    result['tables'].append({
                        'page': page_num,
                        'table_index': table_idx,
                        'content': table_markdown,
                        'raw_data': df.to_dict()
                    })

    # 方法 2: 提取元數據
    reader = PdfReader(file_path)
    if reader.metadata:
        result['metadata'] = {
            'title': reader.metadata.get('/Title', ''),
            'author': reader.metadata.get('/Author', ''),
            'subject': reader.metadata.get('/Subject', ''),
            'pages': len(reader.pages)
        }

    return result
```

#### DOCX 文檔處理
```python
# 使用 skills/docx 的方法
import subprocess
import json

def process_docx_for_rag(file_path):
    """
    處理 Word 文檔，轉換為 Markdown
    """
    # 使用 pandoc 轉換（保留結構）
    output_file = file_path.replace('.docx', '.md')

    subprocess.run([
        'pandoc',
        '--track-changes=all',  # 保留修訂記錄
        file_path,
        '-o', output_file
    ])

    with open(output_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()

    return {
        'text': markdown_content,
        'format': 'markdown',
        'metadata': {
            'source': file_path,
            'format': 'docx'
        }
    }
```

#### PPTX 簡報處理
```python
# 使用 skills/pptx 的方法
from pptx import Presentation

def process_pptx_for_rag(file_path):
    """
    處理 PowerPoint 簡報，提取投影片內容
    """
    prs = Presentation(file_path)
    slides_content = []

    for slide_num, slide in enumerate(prs.slides, start=1):
        slide_text = []

        # 提取所有文字框的內容
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                slide_text.append(shape.text)

        # 提取備註（演講者備註）
        notes_text = ""
        if slide.has_notes_slide:
            notes_slide = slide.notes_slide
            notes_text = notes_slide.notes_text_frame.text

        slides_content.append({
            'slide_number': slide_num,
            'content': '\n'.join(slide_text),
            'notes': notes_text
        })

    # 組合為完整文本
    full_text = '\n\n'.join([
        f"=== Slide {s['slide_number']} ===\n{s['content']}\nNotes: {s['notes']}"
        for s in slides_content
    ])

    return {
        'text': full_text,
        'slides': slides_content,
        'metadata': {
            'total_slides': len(prs.slides),
            'source': file_path
        }
    }
```

#### XLSX 試算表處理
```python
# 使用 skills/xlsx 的方法
import pandas as pd
import openpyxl

def process_xlsx_for_rag(file_path):
    """
    處理 Excel 試算表，提取結構化數據
    """
    # 讀取所有工作表
    excel_file = pd.ExcelFile(file_path)
    sheets_content = []

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)

        # 轉為 Markdown 格式
        markdown_table = df.to_markdown(index=False)

        # 也保留 JSON 格式供結構化查詢
        json_data = df.to_dict(orient='records')

        sheets_content.append({
            'sheet_name': sheet_name,
            'markdown': markdown_table,
            'json': json_data,
            'shape': df.shape  # (rows, columns)
        })

    # 組合為文本
    full_text = '\n\n'.join([
        f"=== Sheet: {s['sheet_name']} ===\n{s['markdown']}"
        for s in sheets_content
    ])

    return {
        'text': full_text,
        'sheets': sheets_content,
        'metadata': {
            'total_sheets': len(sheets_content),
            'source': file_path
        }
    }
```

### 1.2 統一處理介面

```python
class DocumentProcessor:
    """
    統一的文檔處理器，自動選擇合適的 skill
    """

    def __init__(self):
        self.processors = {
            '.pdf': process_pdf_for_rag,
            '.docx': process_docx_for_rag,
            '.pptx': process_pptx_for_rag,
            '.xlsx': process_xlsx_for_rag,
        }

    def process(self, file_path):
        """
        根據文件類型自動選擇處理器
        """
        import os
        ext = os.path.splitext(file_path)[1].lower()

        if ext not in self.processors:
            raise ValueError(f"Unsupported file type: {ext}")

        processor = self.processors[ext]
        return processor(file_path)

    def process_to_chunks(self, file_path, chunk_size=1000, overlap=200):
        """
        處理文檔並切分為適合 RAG 的文本塊
        """
        # 1. 解析文檔
        parsed = self.process(file_path)

        # 2. 切分文本
        chunks = self.split_text(parsed['text'], chunk_size, overlap)

        # 3. 為每個 chunk 添加元數據
        chunk_objects = []
        for idx, chunk in enumerate(chunks):
            chunk_objects.append({
                'text': chunk,
                'metadata': {
                    **parsed.get('metadata', {}),
                    'chunk_index': idx,
                    'total_chunks': len(chunks),
                    'source_file': file_path
                }
            })

        # 4. 單獨處理表格（如果有）
        if 'tables' in parsed:
            for table in parsed['tables']:
                chunk_objects.append({
                    'text': table['content'],
                    'metadata': {
                        'type': 'table',
                        'page': table.get('page'),
                        'source_file': file_path
                    }
                })

        return chunk_objects

    def split_text(self, text, chunk_size, overlap):
        """
        簡單的文本切分（實際應使用更智能的方法）
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)

        return chunks
```

### 1.3 RAG 攝取管道完整實作

```python
from typing import List, Dict
import numpy as np

class RAGIngestionPipeline:
    """
    完整的 RAG 攝取管道
    """

    def __init__(self, vector_db, embedding_model):
        self.doc_processor = DocumentProcessor()
        self.vector_db = vector_db
        self.embedding_model = embedding_model

    def ingest_document(self, file_path: str) -> Dict:
        """
        攝取單個文檔到 RAG 系統
        """
        # 1. 解析文檔
        print(f"Processing {file_path}...")
        chunks = self.doc_processor.process_to_chunks(file_path)

        # 2. 生成向量
        print(f"Generating embeddings for {len(chunks)} chunks...")
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embedding_model.embed(texts)

        # 3. 存入向量資料庫
        print(f"Storing in vector database...")
        ids = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc_id = self.vector_db.add(
                vector=embedding,
                text=chunk['text'],
                metadata=chunk['metadata']
            )
            ids.append(doc_id)

        return {
            'file': file_path,
            'chunks_processed': len(chunks),
            'document_ids': ids,
            'status': 'success'
        }

    def ingest_batch(self, file_paths: List[str]) -> List[Dict]:
        """
        批量攝取多個文檔
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.ingest_document(file_path)
                results.append(result)
            except Exception as e:
                results.append({
                    'file': file_path,
                    'status': 'error',
                    'error': str(e)
                })
        return results
```

---

## 🔍 階段二：智能檢索 (Retrieval)

### 2.1 混合檢索策略

```python
class HybridRetriever:
    """
    結合向量搜尋和結構化查詢的混合檢索器
    """

    def __init__(self, vector_db, structured_db):
        self.vector_db = vector_db
        self.structured_db = structured_db

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        混合檢索：向量搜尋 + 結構化查詢
        """
        results = []

        # 1. 向量搜尋（語義相似度）
        vector_results = self.vector_db.search(query, top_k=top_k)
        results.extend(vector_results)

        # 2. 如果查詢涉及表格或數字，查詢結構化資料庫
        if self._is_structured_query(query):
            structured_results = self.structured_db.query(query)
            results.extend(structured_results)

        # 3. 重排序
        reranked = self._rerank(query, results)

        return reranked[:top_k]

    def _is_structured_query(self, query: str) -> bool:
        """
        判斷是否為結構化查詢（涉及表格、數字、統計等）
        """
        keywords = ['表格', '數據', '統計', '總和', '平均', '最大', '最小',
                    'table', 'data', 'sum', 'average', 'max', 'min']
        return any(keyword in query.lower() for keyword in keywords)

    def _rerank(self, query: str, results: List[Dict]) -> List[Dict]:
        """
        重排序結果（可使用 Cohere Rerank 或其他模型）
        """
        # 簡化版：按相關性分數排序
        return sorted(results, key=lambda x: x.get('score', 0), reverse=True)
```

### 2.2 表格專用檢索

```python
class TableRetriever:
    """
    專門處理表格數據的檢索器
    """

    def __init__(self, structured_db):
        self.structured_db = structured_db

    def retrieve_table_data(self, query: str) -> List[Dict]:
        """
        檢索表格數據並返回結構化結果
        """
        # 1. 解析查詢意圖
        intent = self._parse_query_intent(query)

        # 2. 查詢相關表格
        tables = self.structured_db.find_tables(intent['keywords'])

        # 3. 如果查詢包含計算需求，執行計算
        if intent['requires_calculation']:
            results = self._calculate(tables, intent['calculation_type'])
        else:
            results = tables

        return results

    def _parse_query_intent(self, query: str) -> Dict:
        """
        解析查詢意圖（簡化版，實際應使用 NLU）
        """
        intent = {
            'keywords': [],
            'requires_calculation': False,
            'calculation_type': None
        }

        # 檢測計算需求
        if any(word in query for word in ['總和', '平均', 'sum', 'average']):
            intent['requires_calculation'] = True
            if '總和' in query or 'sum' in query:
                intent['calculation_type'] = 'sum'
            elif '平均' in query or 'average' in query:
                intent['calculation_type'] = 'average'

        return intent

    def _calculate(self, tables: List[Dict], calc_type: str) -> List[Dict]:
        """
        對表格數據執行計算
        """
        import pandas as pd
        results = []

        for table in tables:
            df = pd.DataFrame(table['data'])

            if calc_type == 'sum':
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                sums = df[numeric_cols].sum().to_dict()
                results.append({'table': table['name'], 'sums': sums})

            elif calc_type == 'average':
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                avgs = df[numeric_cols].mean().to_dict()
                results.append({'table': table['name'], 'averages': avgs})

        return results
```

---

## 🤖 階段三：生成與回答 (Generation)

### 3.1 RAG 生成管道

```python
class RAGGenerator:
    """
    RAG 生成器：結合檢索結果和 LLM 生成答案
    """

    def __init__(self, retriever, llm):
        self.retriever = retriever
        self.llm = llm

    def generate(self, query: str, return_sources: bool = True) -> Dict:
        """
        生成 RAG 答案
        """
        # 1. 檢索相關內容
        retrieved_docs = self.retriever.retrieve(query)

        # 2. 構建 prompt
        context = self._build_context(retrieved_docs)
        prompt = self._build_prompt(query, context)

        # 3. LLM 生成答案
        answer = self.llm.generate(prompt)

        # 4. 返回結果
        result = {
            'query': query,
            'answer': answer,
        }

        if return_sources:
            result['sources'] = self._format_sources(retrieved_docs)

        return result

    def _build_context(self, docs: List[Dict]) -> str:
        """
        構建上下文文本
        """
        context_parts = []
        for idx, doc in enumerate(docs, start=1):
            source = doc['metadata'].get('source_file', 'Unknown')
            text = doc['text']
            context_parts.append(f"[來源 {idx}: {source}]\n{text}")

        return '\n\n'.join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        """
        構建 LLM prompt
        """
        prompt = f"""請基於以下文檔內容回答問題。如果文檔中沒有相關資訊，請明確說明。

文檔內容：
{context}

問題：{query}

答案："""
        return prompt

    def _format_sources(self, docs: List[Dict]) -> List[Dict]:
        """
        格式化來源資訊
        """
        sources = []
        for doc in docs:
            sources.append({
                'file': doc['metadata'].get('source_file'),
                'page': doc['metadata'].get('page'),
                'chunk': doc['metadata'].get('chunk_index'),
                'preview': doc['text'][:200] + '...'
            })
        return sources
```

---

## 📊 階段四：文檔生成 (Document Generation)

### 4.1 從 RAG 結果生成專業文檔

```python
class DocumentGenerator:
    """
    使用 Skills 從 RAG 結果生成專業文檔
    """

    def generate_excel_report(self, rag_result: Dict, output_path: str):
        """
        生成 Excel 報告
        使用 skills/xlsx 的標準
        """
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "RAG Analysis Report"

        # 標題
        ws['A1'] = "RAG 分析報告"
        ws['A1'].font = Font(size=16, bold=True)

        # 查詢
        ws['A3'] = "查詢："
        ws['B3'] = rag_result['query']
        ws['A3'].font = Font(bold=True, color="0000FF")  # 藍色（輸入）

        # 答案
        ws['A5'] = "答案："
        ws['A5'].font = Font(bold=True)
        ws['A6'] = rag_result['answer']

        # 來源列表
        row = 8
        ws[f'A{row}'] = "資料來源："
        ws[f'A{row}'].font = Font(bold=True)

        row += 1
        ws[f'A{row}'] = "檔案"
        ws[f'B{row}'] = "頁碼"
        ws[f'C{row}'] = "預覽"

        # 標題行格式
        for col in ['A', 'B', 'C']:
            ws[f'{col}{row}'].font = Font(bold=True)
            ws[f'{col}{row}'].fill = PatternFill(start_color="FFFF00",
                                                   end_color="FFFF00",
                                                   fill_type="solid")

        row += 1
        for source in rag_result.get('sources', []):
            ws[f'A{row}'] = source['file']
            ws[f'B{row}'] = source.get('page', 'N/A')
            ws[f'C{row}'] = source['preview']
            row += 1

        # 調整列寬
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 10
        ws.column_dimensions['C'].width = 50

        wb.save(output_path)
        print(f"Excel 報告已生成: {output_path}")

    def generate_pdf_report(self, rag_result: Dict, output_path: str):
        """
        生成 PDF 報告
        使用 skills/pdf 的 reportlab 方法
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # 標題
        title = Paragraph("RAG 分析報告", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 0.5*inch))

        # 查詢
        query_text = f"<b>查詢：</b> {rag_result['query']}"
        story.append(Paragraph(query_text, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))

        # 答案
        answer_text = f"<b>答案：</b><br/>{rag_result['answer']}"
        story.append(Paragraph(answer_text, styles['Normal']))
        story.append(Spacer(1, 0.5*inch))

        # 來源
        story.append(Paragraph("<b>資料來源：</b>", styles['Heading2']))
        for idx, source in enumerate(rag_result.get('sources', []), start=1):
            source_text = f"{idx}. {source['file']} (頁碼: {source.get('page', 'N/A')})"
            story.append(Paragraph(source_text, styles['Normal']))
            story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        print(f"PDF 報告已生成: {output_path}")

    def generate_pptx_presentation(self, rag_result: Dict, output_path: str):
        """
        生成 PowerPoint 簡報
        使用 skills/pptx 的方法
        """
        from pptx import Presentation
        from pptx.util import Inches, Pt

        prs = Presentation()

        # 投影片 1: 標題
        slide1 = prs.slides.add_slide(prs.slide_layouts[0])
        title = slide1.shapes.title
        subtitle = slide1.placeholders[1]
        title.text = "RAG 分析報告"
        subtitle.text = f"查詢: {rag_result['query']}"

        # 投影片 2: 答案
        slide2 = prs.slides.add_slide(prs.slide_layouts[1])
        title2 = slide2.shapes.title
        content2 = slide2.placeholders[1]
        title2.text = "分析結果"
        content2.text = rag_result['answer']

        # 投影片 3: 資料來源
        slide3 = prs.slides.add_slide(prs.slide_layouts[1])
        title3 = slide3.shapes.title
        content3 = slide3.placeholders[1]
        title3.text = "資料來源"

        sources_text = '\n'.join([
            f"• {source['file']}"
            for source in rag_result.get('sources', [])
        ])
        content3.text = sources_text

        prs.save(output_path)
        print(f"PowerPoint 簡報已生成: {output_path}")
```

### 4.2 智能格式選擇

```python
class SmartDocumentGenerator:
    """
    根據查詢內容智能選擇輸出格式
    """

    def __init__(self):
        self.generator = DocumentGenerator()

    def generate_smart(self, rag_result: Dict, output_dir: str = '.'):
        """
        根據內容類型智能選擇生成格式
        """
        query = rag_result['query'].lower()

        # 決策邏輯
        if any(word in query for word in ['數據', '統計', '表格', 'data', 'table']):
            # 包含數據 → Excel
            output_path = f"{output_dir}/report.xlsx"
            self.generator.generate_excel_report(rag_result, output_path)
            return {'format': 'excel', 'path': output_path}

        elif any(word in query for word in ['簡報', '報告', 'presentation', 'slides']):
            # 需要簡報 → PowerPoint
            output_path = f"{output_dir}/presentation.pptx"
            self.generator.generate_pptx_presentation(rag_result, output_path)
            return {'format': 'pptx', 'path': output_path}

        else:
            # 一般查詢 → PDF
            output_path = f"{output_dir}/report.pdf"
            self.generator.generate_pdf_report(rag_result, output_path)
            return {'format': 'pdf', 'path': output_path}
```

---

## 🎨 前端整合 (Vue 3 專案)

### 5.1 文檔上傳服務

```typescript
// src/services/document.service.ts

import { api } from './api'

export interface UploadResult {
  fileId: string
  fileName: string
  fileType: string
  chunksProcessed: number
  status: 'success' | 'error'
  message?: string
}

export interface QueryRequest {
  query: string
  knowledgeBaseIds?: string[]
  topK?: number
}

export interface QueryResult {
  query: string
  answer: string
  sources: Array<{
    file: string
    page?: number
    preview: string
  }>
  confidence: number
}

export interface GenerateReportRequest {
  queryResultId: string
  format: 'pdf' | 'xlsx' | 'pptx' | 'docx'
}

class DocumentService {
  /**
   * 上傳文檔到知識庫
   */
  async uploadDocument(file: File, knowledgeBaseId: string): Promise<UploadResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('knowledgeBaseId', knowledgeBaseId)

    const response = await api.post<UploadResult>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      onUploadProgress: (progressEvent) => {
        const progress = progressEvent.loaded / (progressEvent.total || 1)
        console.log(`Upload progress: ${Math.round(progress * 100)}%`)
      }
    })

    return response.data
  }

  /**
   * 批量上傳文檔
   */
  async uploadDocuments(files: File[], knowledgeBaseId: string): Promise<UploadResult[]> {
    const uploadPromises = files.map(file =>
      this.uploadDocument(file, knowledgeBaseId)
    )

    return Promise.all(uploadPromises)
  }

  /**
   * 查詢知識庫
   */
  async query(request: QueryRequest): Promise<QueryResult> {
    const response = await api.post<QueryResult>('/knowledge/query', request)
    return response.data
  }

  /**
   * 生成報告文檔
   */
  async generateReport(request: GenerateReportRequest): Promise<Blob> {
    const response = await api.post('/knowledge/generate-report', request, {
      responseType: 'blob'
    })

    return response.data
  }

  /**
   * 下載生成的報告
   */
  downloadReport(blob: Blob, format: string, fileName: string = 'report') {
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${fileName}.${format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }
}

export const documentService = new DocumentService()
```

### 5.2 Vue Composable

```typescript
// src/composables/use-document-rag.ts

import { ref, computed } from 'vue'
import { documentService, type QueryRequest, type QueryResult } from '@/services/document.service'

export function useDocumentRAG() {
  const isUploading = ref(false)
  const isQuerying = ref(false)
  const isGenerating = ref(false)

  const uploadProgress = ref(0)
  const queryResult = ref<QueryResult | null>(null)
  const error = ref<string | null>(null)

  /**
   * 上傳文檔
   */
  const uploadDocument = async (file: File, knowledgeBaseId: string) => {
    isUploading.value = true
    error.value = null

    try {
      const result = await documentService.uploadDocument(file, knowledgeBaseId)

      if (result.status === 'error') {
        throw new Error(result.message || '上傳失敗')
      }

      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : '上傳失敗'
      throw e
    } finally {
      isUploading.value = false
    }
  }

  /**
   * 批量上傳
   */
  const uploadDocuments = async (files: File[], knowledgeBaseId: string) => {
    isUploading.value = true
    error.value = null

    try {
      const results = await documentService.uploadDocuments(files, knowledgeBaseId)
      const failed = results.filter(r => r.status === 'error')

      if (failed.length > 0) {
        error.value = `${failed.length} 個文件上傳失敗`
      }

      return results
    } catch (e) {
      error.value = e instanceof Error ? e.message : '批量上傳失敗'
      throw e
    } finally {
      isUploading.value = false
    }
  }

  /**
   * 查詢知識庫
   */
  const query = async (request: QueryRequest) => {
    isQuerying.value = true
    error.value = null

    try {
      const result = await documentService.query(request)
      queryResult.value = result
      return result
    } catch (e) {
      error.value = e instanceof Error ? e.message : '查詢失敗'
      throw e
    } finally {
      isQuerying.value = false
    }
  }

  /**
   * 生成並下載報告
   */
  const generateReport = async (
    queryResultId: string,
    format: 'pdf' | 'xlsx' | 'pptx' | 'docx',
    fileName?: string
  ) => {
    isGenerating.value = true
    error.value = null

    try {
      const blob = await documentService.generateReport({
        queryResultId,
        format
      })

      documentService.downloadReport(blob, format, fileName)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '生成報告失敗'
      throw e
    } finally {
      isGenerating.value = false
    }
  }

  /**
   * 清除查詢結果
   */
  const clearResult = () => {
    queryResult.value = null
    error.value = null
  }

  return {
    // State
    isUploading,
    isQuerying,
    isGenerating,
    uploadProgress,
    queryResult,
    error,

    // Actions
    uploadDocument,
    uploadDocuments,
    query,
    generateReport,
    clearResult
  }
}
```

### 5.3 Vue 組件範例

```vue
<!-- src/components/RAGQueryInterface.vue -->

<template>
  <div class="rag-query-interface">
    <!-- 文檔上傳區 -->
    <div class="upload-section">
      <h2>上傳文檔</h2>
      <input
        type="file"
        multiple
        accept=".pdf,.docx,.pptx,.xlsx"
        @change="handleFileSelect"
        :disabled="isUploading"
      />

      <div v-if="isUploading" class="progress">
        <progress :value="uploadProgress" max="100" />
        <span>上傳中... {{ uploadProgress }}%</span>
      </div>

      <div v-if="uploadResults.length" class="upload-results">
        <h3>上傳結果：</h3>
        <ul>
          <li v-for="result in uploadResults" :key="result.fileId">
            {{ result.fileName }} -
            處理了 {{ result.chunksProcessed }} 個文本塊
            <span :class="result.status">{{ result.status }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- 查詢區 -->
    <div class="query-section">
      <h2>查詢知識庫</h2>
      <textarea
        v-model="queryText"
        placeholder="輸入您的問題..."
        :disabled="isQuerying"
      />

      <div class="query-options">
        <label>
          檢索數量：
          <input v-model.number="topK" type="number" min="1" max="20" />
        </label>
      </div>

      <button
        @click="handleQuery"
        :disabled="!queryText || isQuerying"
        class="btn-primary"
      >
        {{ isQuerying ? '查詢中...' : '查詢' }}
      </button>
    </div>

    <!-- 結果顯示區 -->
    <div v-if="queryResult" class="result-section">
      <h2>查詢結果</h2>

      <div class="answer">
        <h3>答案：</h3>
        <p>{{ queryResult.answer }}</p>
        <div class="confidence">
          信心度: {{ (queryResult.confidence * 100).toFixed(1) }}%
        </div>
      </div>

      <div class="sources">
        <h3>資料來源：</h3>
        <div
          v-for="(source, idx) in queryResult.sources"
          :key="idx"
          class="source-item"
        >
          <div class="source-header">
            <strong>{{ source.file }}</strong>
            <span v-if="source.page">頁碼: {{ source.page }}</span>
          </div>
          <div class="source-preview">
            {{ source.preview }}
          </div>
        </div>
      </div>

      <!-- 生成報告按鈕 -->
      <div class="generate-section">
        <h3>生成報告：</h3>
        <div class="format-buttons">
          <button
            @click="handleGenerateReport('pdf')"
            :disabled="isGenerating"
          >
            PDF
          </button>
          <button
            @click="handleGenerateReport('xlsx')"
            :disabled="isGenerating"
          >
            Excel
          </button>
          <button
            @click="handleGenerateReport('pptx')"
            :disabled="isGenerating"
          >
            PowerPoint
          </button>
        </div>
        <div v-if="isGenerating" class="generating-status">
          正在生成報告...
        </div>
      </div>
    </div>

    <!-- 錯誤提示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useDocumentRAG } from '@/composables/use-document-rag'
import { useKnowledgeStore } from '@/stores/knowledge'

const knowledgeStore = useKnowledgeStore()

const {
  isUploading,
  isQuerying,
  isGenerating,
  uploadProgress,
  queryResult,
  error,
  uploadDocuments,
  query,
  generateReport
} = useDocumentRAG()

const queryText = ref('')
const topK = ref(5)
const uploadResults = ref<any[]>([])

const handleFileSelect = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return

  const files = Array.from(input.files)
  const knowledgeBaseId = knowledgeStore.currentKnowledgeBase?.id

  if (!knowledgeBaseId) {
    alert('請先選擇知識庫')
    return
  }

  try {
    const results = await uploadDocuments(files, knowledgeBaseId)
    uploadResults.value = results
  } catch (e) {
    console.error('上傳失敗:', e)
  }
}

const handleQuery = async () => {
  const knowledgeBaseId = knowledgeStore.currentKnowledgeBase?.id

  if (!knowledgeBaseId) {
    alert('請先選擇知識庫')
    return
  }

  await query({
    query: queryText.value,
    knowledgeBaseIds: [knowledgeBaseId],
    topK: topK.value
  })
}

const handleGenerateReport = async (format: 'pdf' | 'xlsx' | 'pptx') => {
  if (!queryResult.value) return

  // 假設後端返回了 query result ID
  const queryResultId = 'current-query-id'
  const fileName = `rag_report_${Date.now()}`

  await generateReport(queryResultId, format, fileName)
}
</script>

<style scoped>
.rag-query-interface {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.upload-section,
.query-section,
.result-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

textarea {
  width: 100%;
  min-height: 100px;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

.answer {
  background-color: #f3f4f6;
  padding: 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.sources {
  margin-top: 1rem;
}

.source-item {
  background-color: #fef3c7;
  padding: 1rem;
  margin-bottom: 0.5rem;
  border-radius: 4px;
}

.source-preview {
  color: #6b7280;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.format-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
}

.format-buttons button {
  padding: 0.5rem 1rem;
  background-color: #10b981;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-message {
  background-color: #fee2e2;
  color: #dc2626;
  padding: 1rem;
  border-radius: 4px;
  margin-top: 1rem;
}
</style>
```

---

## 🚀 後端 API 實作範例

### 6.1 FastAPI 端點

```python
# backend/api/rag.py

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel

from ..services.rag_service import RAGService
from ..services.document_service import DocumentService

router = APIRouter(prefix="/api", tags=["RAG"])

rag_service = RAGService()
doc_service = DocumentService()


class QueryRequest(BaseModel):
    query: str
    knowledgeBaseIds: Optional[List[str]] = None
    topK: int = 5


class GenerateReportRequest(BaseModel):
    queryResultId: str
    format: str  # 'pdf', 'xlsx', 'pptx', 'docx'


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    knowledgeBaseId: str = None
):
    """
    上傳並處理文檔
    """
    try:
        # 1. 保存文件
        file_path = await doc_service.save_uploaded_file(file)

        # 2. 使用 Skills 處理文檔
        result = await rag_service.ingest_document(file_path, knowledgeBaseId)

        return {
            "fileId": result['file_id'],
            "fileName": file.filename,
            "fileType": file.content_type,
            "chunksProcessed": result['chunks_processed'],
            "status": "success"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/query")
async def query_knowledge(request: QueryRequest):
    """
    查詢知識庫
    """
    try:
        result = await rag_service.query(
            query=request.query,
            knowledge_base_ids=request.knowledgeBaseIds,
            top_k=request.topK
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/knowledge/generate-report")
async def generate_report(request: GenerateReportRequest):
    """
    生成報告文檔
    """
    try:
        # 1. 獲取查詢結果
        query_result = await rag_service.get_query_result(request.queryResultId)

        # 2. 使用 Skills 生成文檔
        output_path = await doc_service.generate_document(
            query_result,
            format=request.format
        )

        # 3. 返回文件
        return FileResponse(
            output_path,
            media_type=f"application/{request.format}",
            filename=f"report.{request.format}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 6.2 RAG 服務層

```python
# backend/services/rag_service.py

from typing import List, Dict, Optional
import uuid

from ..skills.document_processor import DocumentProcessor
from ..database.vector_db import VectorDatabase
from ..llm.client import LLMClient


class RAGService:
    """
    完整的 RAG 服務實作
    """

    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.vector_db = VectorDatabase()
        self.llm_client = LLMClient()
        self.query_results_cache = {}  # 在生產環境應使用 Redis

    async def ingest_document(
        self,
        file_path: str,
        knowledge_base_id: str
    ) -> Dict:
        """
        攝取文檔到 RAG 系統
        """
        # 1. 使用 Skills 解析文檔
        chunks = self.doc_processor.process_to_chunks(file_path)

        # 2. 生成向量
        texts = [chunk['text'] for chunk in chunks]
        embeddings = await self.llm_client.embed(texts)

        # 3. 存入向量資料庫
        document_id = str(uuid.uuid4())

        for chunk, embedding in zip(chunks, embeddings):
            await self.vector_db.add(
                id=str(uuid.uuid4()),
                vector=embedding,
                text=chunk['text'],
                metadata={
                    **chunk['metadata'],
                    'document_id': document_id,
                    'knowledge_base_id': knowledge_base_id
                }
            )

        return {
            'file_id': document_id,
            'chunks_processed': len(chunks),
            'status': 'success'
        }

    async def query(
        self,
        query: str,
        knowledge_base_ids: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict:
        """
        查詢 RAG 系統
        """
        # 1. 生成查詢向量
        query_embedding = await self.llm_client.embed([query])

        # 2. 檢索相關文檔
        filter_conditions = {}
        if knowledge_base_ids:
            filter_conditions['knowledge_base_id'] = {'$in': knowledge_base_ids}

        retrieved_docs = await self.vector_db.search(
            vector=query_embedding[0],
            top_k=top_k,
            filter=filter_conditions
        )

        # 3. 構建上下文
        context = self._build_context(retrieved_docs)

        # 4. LLM 生成答案
        prompt = self._build_prompt(query, context)
        answer = await self.llm_client.generate(prompt)

        # 5. 格式化結果
        result = {
            'query': query,
            'answer': answer,
            'sources': self._format_sources(retrieved_docs),
            'confidence': self._calculate_confidence(retrieved_docs)
        }

        # 6. 緩存結果
        result_id = str(uuid.uuid4())
        self.query_results_cache[result_id] = result
        result['id'] = result_id

        return result

    async def get_query_result(self, query_result_id: str) -> Dict:
        """
        獲取緩存的查詢結果
        """
        if query_result_id not in self.query_results_cache:
            raise ValueError(f"Query result {query_result_id} not found")

        return self.query_results_cache[query_result_id]

    def _build_context(self, docs: List[Dict]) -> str:
        context_parts = []
        for idx, doc in enumerate(docs, start=1):
            source = doc['metadata'].get('source_file', 'Unknown')
            text = doc['text']
            context_parts.append(f"[來源 {idx}: {source}]\n{text}")
        return '\n\n'.join(context_parts)

    def _build_prompt(self, query: str, context: str) -> str:
        return f"""請基於以下文檔內容回答問題。

文檔內容：
{context}

問題：{query}

答案："""

    def _format_sources(self, docs: List[Dict]) -> List[Dict]:
        sources = []
        for doc in docs:
            sources.append({
                'file': doc['metadata'].get('source_file'),
                'page': doc['metadata'].get('page'),
                'preview': doc['text'][:200] + '...'
            })
        return sources

    def _calculate_confidence(self, docs: List[Dict]) -> float:
        if not docs:
            return 0.0

        # 簡化版：基於最高分數
        max_score = max(doc.get('score', 0) for doc in docs)
        return min(max_score, 1.0)
```

---

## 📊 性能優化建議

### 7.1 文檔處理優化

```python
# 並行處理多個文檔
import asyncio
from concurrent.futures import ThreadPoolExecutor

class OptimizedDocumentProcessor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    async def process_documents_parallel(self, file_paths: List[str]):
        """
        並行處理多個文檔
        """
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(
                self.executor,
                self.process_single_document,
                file_path
            )
            for file_path in file_paths
        ]

        results = await asyncio.gather(*tasks)
        return results
```

### 7.2 向量化批次處理

```python
# 批次生成向量以提高效率
class BatchEmbedder:
    def __init__(self, batch_size=32):
        self.batch_size = batch_size

    async def embed_in_batches(self, texts: List[str]):
        """
        分批生成向量
        """
        embeddings = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = await self.llm_client.embed(batch)
            embeddings.extend(batch_embeddings)

        return embeddings
```

### 7.3 緩存策略

```python
from functools import lru_cache
import hashlib

class CachedRetriever:
    """
    使用緩存優化重複查詢
    """

    def __init__(self):
        self.cache = {}

    def _hash_query(self, query: str) -> str:
        return hashlib.md5(query.encode()).hexdigest()

    async def retrieve_with_cache(self, query: str, top_k: int = 5):
        """
        帶緩存的檢索
        """
        cache_key = f"{self._hash_query(query)}:{top_k}"

        if cache_key in self.cache:
            print("Cache hit!")
            return self.cache[cache_key]

        # 執行實際檢索
        results = await self.vector_db.search(query, top_k)

        # 緩存結果
        self.cache[cache_key] = results

        return results
```

---

## 🎯 實戰案例

### 案例 1：合約管理系統

**場景**: 法務部門需要從大量合約中快速找到特定條款

```python
# 1. 批量上傳合約 PDF
contracts = [
    'contract_2024_001.pdf',
    'contract_2024_002.pdf',
    # ... 100 個合約
]

for contract in contracts:
    # 使用 skills/pdf 處理
    result = process_pdf_for_rag(contract)
    rag_service.ingest_document(result)

# 2. 查詢
query = "所有合約中關於違約金的條款是什麼？"
result = rag_service.query(query)

# 3. 生成 Excel 報告
generate_excel_report(result, 'penalty_clauses_summary.xlsx')
```

### 案例 2：財務報表分析

**場景**: 從季度 Excel 報表中提取並分析財務指標

```python
# 1. 上傳 Excel 財報
quarterly_reports = [
    'Q1_2024_financial.xlsx',
    'Q2_2024_financial.xlsx',
    'Q3_2024_financial.xlsx'
]

for report in quarterly_reports:
    # 使用 skills/xlsx 提取表格
    result = process_xlsx_for_rag(report)
    rag_service.ingest_document(result)

# 2. 分析查詢
query = "Q3 相比 Q1 的營收成長率是多少？"
result = rag_service.query(query)

# 3. 生成 PowerPoint 分析簡報
generate_pptx_presentation(result, 'quarterly_analysis.pptx')
```

### 案例 3：產品文檔問答

**場景**: 技術支援團隊需要快速查詢產品手冊

```python
# 1. 上傳產品文檔（混合格式）
product_docs = [
    'user_manual.pdf',
    'api_reference.docx',
    'troubleshooting_guide.pptx'
]

# 使用統一介面處理
doc_processor = DocumentProcessor()
for doc in product_docs:
    result = doc_processor.process(doc)
    rag_service.ingest_document(result)

# 2. 客戶問題
query = "如何重置密碼？"
answer = rag_service.query(query)

# 3. 生成 PDF 知識庫文章
generate_pdf_report(answer, 'kb_password_reset.pdf')
```

---

## 📈 監控與評估

### 8.1 關鍵指標

```python
class RAGMetrics:
    """
    RAG 系統性能指標
    """

    def __init__(self):
        self.metrics = {
            'total_queries': 0,
            'average_response_time': 0,
            'retrieval_accuracy': 0,
            'user_satisfaction': 0
        }

    def track_query(self, query_time: float, retrieved_docs: int):
        """
        追蹤查詢性能
        """
        self.metrics['total_queries'] += 1

        # 更新平均響應時間
        current_avg = self.metrics['average_response_time']
        total = self.metrics['total_queries']
        self.metrics['average_response_time'] = (
            (current_avg * (total - 1) + query_time) / total
        )

    def calculate_retrieval_quality(
        self,
        retrieved_docs: List[Dict],
        relevant_threshold: float = 0.7
    ) -> float:
        """
        計算檢索質量
        """
        if not retrieved_docs:
            return 0.0

        relevant_count = sum(
            1 for doc in retrieved_docs
            if doc.get('score', 0) >= relevant_threshold
        )

        return relevant_count / len(retrieved_docs)
```

### 8.2 日誌記錄

```python
import logging
from datetime import datetime

class RAGLogger:
    """
    RAG 系統日誌
    """

    def __init__(self):
        self.logger = logging.getLogger('RAG')

    def log_query(self, query: str, result: Dict, execution_time: float):
        """
        記錄查詢日誌
        """
        self.logger.info({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'sources_count': len(result.get('sources', [])),
            'confidence': result.get('confidence'),
            'execution_time_ms': execution_time * 1000
        })

    def log_document_ingestion(self, file_path: str, chunks: int):
        """
        記錄文檔攝取
        """
        self.logger.info({
            'timestamp': datetime.now().isoformat(),
            'action': 'document_ingestion',
            'file': file_path,
            'chunks_processed': chunks
        })
```

---

## 🔒 安全性考量

### 9.1 文件上傳安全

```python
import os
from pathlib import Path

class SecureFileHandler:
    """
    安全的文件處理
    """

    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def validate_file(self, file_path: str) -> bool:
        """
        驗證文件
        """
        # 1. 檢查副檔名
        ext = Path(file_path).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"不支援的文件類型: {ext}")

        # 2. 檢查文件大小
        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"文件過大: {file_size} bytes")

        # 3. 檢查文件內容（防止惡意文件）
        # 實際應用中應使用專業的病毒掃描工具

        return True
```

### 9.2 查詢權限控制

```python
class AccessControl:
    """
    存取控制
    """

    def check_knowledge_base_access(
        self,
        user_id: str,
        knowledge_base_id: str
    ) -> bool:
        """
        檢查用戶是否有權限存取知識庫
        """
        # 實作權限檢查邏輯
        pass

    def filter_results_by_permission(
        self,
        results: List[Dict],
        user_id: str
    ) -> List[Dict]:
        """
        根據權限過濾結果
        """
        filtered = []
        for result in results:
            kb_id = result['metadata'].get('knowledge_base_id')
            if self.check_knowledge_base_access(user_id, kb_id):
                filtered.append(result)

        return filtered
```

---

## 🎓 最佳實踐總結

### ✅ DO（推薦做法）

1. **文檔解析**
   - ✅ 使用 Skills 的標準化方法處理各種格式
   - ✅ 單獨提取和儲存表格數據
   - ✅ 保留文檔元數據（作者、日期、頁碼等）
   - ✅ 處理 OCR 文檔時進行文本清理

2. **文本切分**
   - ✅ 根據文檔結構智能切分（段落、章節）
   - ✅ 保持重疊（overlap）以避免上下文丟失
   - ✅ 為每個 chunk 添加豐富的元數據

3. **檢索優化**
   - ✅ 使用混合檢索（向量 + 關鍵字）
   - ✅ 實作重排序（reranking）
   - ✅ 緩存常見查詢結果

4. **生成優化**
   - ✅ 根據查詢類型選擇合適的輸出格式
   - ✅ 使用 Skills 生成專業格式文檔
   - ✅ 提供清晰的來源引用

### ❌ DON'T（避免做法）

1. **文檔處理**
   - ❌ 不要忽略表格和結構化數據
   - ❌ 不要丟失文檔格式資訊
   - ❌ 不要使用單一方法處理所有格式

2. **RAG 管道**
   - ❌ 不要只依賴向量搜尋
   - ❌ 不要返回過多或過少的上下文
   - ❌ 不要忽略檢索質量評估

3. **安全性**
   - ❌ 不要跳過文件驗證
   - ❌ 不要忽略權限控制
   - ❌ 不要洩露敏感文檔內容

---

## 🔮 未來擴展方向

### 1. 多模態支援
- 圖片理解（提取 PDF 中的圖表、圖片）
- 影片字幕提取和搜尋
- 音訊轉文字並納入 RAG

### 2. 進階 RAG 技術
- **HyDE** (Hypothetical Document Embeddings)
- **Self-RAG** (自我反思的 RAG)
- **Graph RAG** (基於知識圖譜的 RAG)
- **Agentic RAG** (Agent 驅動的 RAG)

### 3. 智能 Agent 整合
```python
class DocumentAgent:
    """
    智能文檔處理 Agent
    """

    def process_user_request(self, request: str):
        """
        根據自然語言請求自動選擇 Skill
        """
        # AI 決策：應該使用哪個 skill？
        if 'extract table' in request:
            return self.use_skill('pdf', 'extract_tables')
        elif 'create presentation' in request:
            return self.use_skill('pptx', 'create_from_data')
        # ...
```

---

## 📚 相關資源

### Skills 文檔
- [Skills 架構說明](./ARCHITECTURE.md)
- [PDF 處理指南](./pdf/SKILL.md)
- [Word 處理指南](./docx/SKILL.md)
- [PowerPoint 處理指南](./pptx/SKILL.md)
- [Excel 處理指南](./xlsx/SKILL.md)

### RAG 技術
- [LangChain RAG 教程](https://python.langchain.com/docs/use_cases/question_answering/)
- [LlamaIndex 文檔](https://docs.llamaindex.ai/)
- [向量資料庫比較](https://github.com/erikbern/ann-benchmarks)

### 前端框架
- [Vue 3 官方文檔](https://vuejs.org/)
- [Pinia 狀態管理](https://pinia.vuejs.org/)
- [TanStack Query](https://tanstack.com/query/latest)

---

## 🤝 貢獻與反饋

如有問題或建議，請聯繫開發團隊或提交 Issue。

**文檔版本**: 1.0
**最後更新**: 2025-10-12
**維護者**: RAG Integration Team

---

**下一步**: 開始實作！從文檔攝取開始，逐步建立完整的 RAG 系統。
