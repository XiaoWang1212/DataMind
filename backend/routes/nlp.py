import sys
import re
from collections import defaultdict

class PaperParser:
    def __init__(self, text):
        # 統一處理換行與空白，避免 PDF 轉出的奇怪斷行干擾正則
        self.text = re.sub(r'\n+', '\n', text)

    # 1. 精準抓取表格（修正防線：限制表格長度或用空行/新段落切斷，避免吞掉內文）
    def extract_tables(self):
        # 修改後的 Pattern：抓取 Table X 開始，直到遇到連續兩個換行、或者是下一個大標題/表格為止
        # 這裡為了保險，我們改用更嚴格的限制，或者尋找表格的特徵（例如大量的引號、逗號或 CSV 格式）
        # 由於你的 text 來源看起來像包含 "The following table:\n\"Category\n\"" 這樣的標記，我們可以用這個特徵！
        
        pattern = r'(Table\s*\d+[\s\S]*?)(?=(?:Table\s*\d+)|(?:##)|(?:\n\s*\n\s*[A-Z][A-Z\s]{5,}\n)|$)'
        matches = re.finditer(pattern, self.text, re.IGNORECASE)

        tables = []
        for i, match in enumerate(matches):
            raw_content = match.group(1).strip()
            
            # 自行偵測這是不是真的表格內容（例如有沒有包含表格常見的 CSV/Markdown 引號，或特定關鍵字）
            # 限制長度不盲目抓取，如果超過 2000 字元可能就是吞到本文了，進行截斷
            tables.append({
                "table_id": f"Table {i+1}",
                "content": raw_content[:2500] 
            })
        return tables

    # 2. 抽 section（優化版：先清理掉干擾標記）
    def extract_sections(self):
        # 改進關鍵字，並確保它是獨立行或是段落開頭
        pattern = r'(?:\n|^)(?P<title>INTRODUCTION|MATERIALS|METHODS|DATA ANALYSIS|RESULTS|VARIABLES|DISCUSSION|CONCLUSION)[^\n]*'
        matches = list(re.finditer(pattern, self.text, re.IGNORECASE))

        sections = []
        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.text)

            title = match.group("title").strip().upper() # 統一轉大寫方便 LLM 辨識
            content = self.text[start:end].strip()

            # 移除內容中可能不小心夾帶的、大段表格文字的干擾（如果表格太長）
            # 這裡做一個簡單的 Clean
            content = re.sub(r'\"Category\",[\s\S]*?\"', '[Table Content Omitted]', content)

            if len(content) > 50:  
                sections.append({
                    "section_title": title,
                    "content": content[:3000]  # 放寬到 3000，留給 LLM 更多上下文脈絡
                })

        return sections

    # 3. key sentences（優化計分機制，避免雜訊句子卡位）
    def extract_key_sentences(self):
        sentences = re.split(r'(?<=[.!?])\s+', self.text)
        
        # 權重 1：核心模型與疾病
        core_keywords = ["random forest", "logistic regression", "pressure injury"]
        # 權重 2：不平衡資料與效能痛點（這是策略出現的地方）
        imbalance_keywords = ["imbalanced", "class imbalance", "false positive", "precision", "recall"]
        # 權重 3：臨床佈署與實務策略
        strategy_keywords = ["screening", "clinical", "nursing workload", "preventive", "decision support"]

        scored = []
        for s in sentences:
            s_clean = s.strip().replace('\n', ' ')
            if len(s_clean) < 50 or len(s_clean) > 300:
                continue
                
            score = 0
            if any(k in s_clean.lower() for k in core_keywords): score += 3
            if any(k in s_clean.lower() for k in imbalance_keywords): score += 2
            if any(k in s_clean.lower() for k in strategy_keywords): score += 2
            if re.search(r'\d+(\.\d+)?%?', s_clean): score += 1

            # 護欄：如果同時提及模型/痛點 且 提及臨床策略，優先級最高
            if score >= 4:
                scored.append((score, s_clean))

        scored.sort(reverse=True, key=lambda x: x[0])
        
        # 去重並取前 12-15 句
        seen = set()
        unique_sentences = []
        for _, s in scored:
            if s not in seen:
                seen.add(s)
                unique_sentences.append(s)
            if len(unique_sentences) >= 15:
                break
                
        return unique_sentences

    # 4. metadata
    def extract_metadata(self):
        models = []
        tools = []
        metrics = []
        processes = []

        text_lower = self.text.lower()

        # 稍微精準化關鍵字
        model_keywords = ["random forest", "logistic regression", "decision tree"]
        tool_keywords = ["weka", "pytorch", "tensorflow", "sklearn"]
        metric_keywords = ["accuracy", "precision", "recall", "f1-measure", "specificity", "auc"]
        process_keywords = ["bootstrap", "cross-validation", "feature selection", "imputation"]

        for m in model_keywords:
            if m in text_lower: models.append(m)
        for t in tool_keywords:
            if t in text_lower: tools.append(t)
        for m in metric_keywords:
            if m in text_lower: metrics.append(m)
        for p in process_keywords:
            if p in text_lower: processes.append(p)

        return {
            "models_mentioned": models,
            "tools_mentioned": tools,
            "metrics_mentioned": metrics,
            "process_keywords": processes
        }

    # 5. main pipeline
    def parse(self):
        return {
            "method_sections": self.extract_sections(),
            "tables": self.extract_tables(),
            "key_sentences": self.extract_key_sentences(),
            "metadata_candidates": self.extract_metadata(),
            "raw_text_length": len(self.text)
        }



def main():
    file_path = r"C:\Users\Tako\OneDrive\Desktop\datamind\DataMind\backend\samples\gemini_sample\data.txt"

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    parser = PaperParser(text)
    result = parser.parse()

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()