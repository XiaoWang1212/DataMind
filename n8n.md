# n8n API 文件

## 說明

目前是接收論文 PDF，透過 AI 分析後回傳結構化的研究方法資料。
服務由本地端透過 ngrok 對外暴露，使用前請確認 Yvonne 的電腦有啟動 n8n 與 ngrok。

---

## 端點

```
POST https://ideally-strewn-papyrus.ngrok-free.dev/webhook/analyze-paper
```

---

## Request

Content-Type: `multipart/form-data`

| 欄位 | 型別 | 說明 |
|------|------|------|
| data | File | 論文 PDF 檔案 |

---

## Response

| 欄位 | 型別 | 說明 |
|------|------|------|
| success | Boolean | 是否成功 |
| fullReport_zh | String | 完整研究方法報告（繁體中文，Markdown 格式） |
| fullReport_en | String | 完整研究方法報告（英文，Markdown 格式） |
| features | Array | 論文特徵變數清單，供後端 NLP 使用 |
| models | Array | 論文使用的模型清單，供後端 NLP 使用 |
| workflowNodes | Array | Vue Flow 節點資料，供前端流程圖使用 |
| workflowEdges | Array | Vue Flow 連線資料，供前端流程圖使用 |

### features 結構

```json
{
  "name": "Age",
  "type": "numerical",
  "description_zh": "患者年齡",
  "description_en": "Patient age"
}
```

### models 結構

```json
{
  "name": "Random Forest",
  "type": "Ensemble Learning",
  "purpose_zh": "透過多個決策樹投票提高分類準確性",
  "purpose_en": "Improves classification accuracy through voting across multiple decision trees"
}
```

### workflowNodes 結構

```json
{
  "id": "1",
  "type": "iconNode",
  "position": { "x": 0, "y": 0 },
  "sourcePosition": "right",
  "targetPosition": "left",
  "data": {
    "icon": "mdi-database",
    "label": "資料收集",
    "colorClass": "node-pending",
    "description": "收集原始資料",
    "category": "data",
    "fields": [],
    "config": {}
  }
}
```

### workflowEdges 結構

```json
{
  "id": "e1-2",
  "source": "1",
  "target": "2",
  "type": "default"
}
```

---

## 注意事項

- 每次分析約需 1 至 2 分鐘
- 服務需本地端 n8n 與 ngrok 有啟動才會通
- 上傳欄位名稱必須為 `data`，否則 API 無法正確接收檔案
- `name` 與 `type` 欄位一律為英文；`description_zh`、`purpose_zh` 為繁體中文；`description_en`、`purpose_en` 為英文