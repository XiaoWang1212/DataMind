# 欄位對齊帶入變數定義 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把論文萃取時已經產生、但欄位對齊流程目前完全沒用到的變數定義（`features[].description_zh`）串接進 `semantic_match` 的 Gemini prompt，並在欄位對齊頁面用 tooltip 顯示給使用者看。

**Architecture:** 後端 `run_auto_mapping()` 把呼叫端傳來的 `definition` 原樣透傳進每筆輸出（不參與比分邏輯），`_format_pending()` 有定義時多印一段文字進 prompt。前端 `PaperVariable`/`MappingItem` 型別各加一個可選的 `definition` 欄位，`buildPaperVariables()` 從 `workflow_json.features[].description_zh` 取值，頁面上用既有的 `v-tooltip` pattern（跟狀態欄位那顆一樣）加一個 info icon 顯示。

**Tech Stack:** Python 3.11、Flask、Vue 3 `<script setup>`、TypeScript、Vuetify（`v-tooltip`、`v-icon`）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-11-field-mapping-variable-definition-design.md`
- **不**把定義加進純字串比對的演算法層（`_score_candidates`/`fuzzy_match`）——只用在 Gemini prompt 跟 UI tooltip
- **不**動論文萃取端、**不**動 `/api/field-mapping/chat`（`chat_refine`）
- 舊框架沒有 `description_zh` 時，`definition` 一路是 `None`/`undefined`，prompt 跟 UI 都要優雅降級（不印那段文字、不顯示 icon），不能報錯
- `backend/services/field_mapping_service.py` 是純函式模組（不依賴 Flask/Gemini），本專案沒有 pytest，用手動跑 python 腳本驗證；前端沒有 vitest，用 `npm run type-check` + 人工瀏覽器驗證

---

### Task 1: 後端 — definition 透傳與 prompt 顯示

**Files:**
- Modify: `backend/services/field_mapping_service.py:200-274`（`run_auto_mapping`）
- Modify: `backend/services/field_mapping_prompts.py:114-121`（`_format_pending`）

**Interfaces:**
- Consumes: 呼叫端（Task 3 之後由前端送出）在 `paper_variables` 每筆物件裡可選帶 `definition: str`
- Produces: `run_auto_mapping()` 回傳的 `mapping_status` 每筆物件多一個 `definition: str | None` 欄位；`_format_pending()` 的輸出字串在有定義時多附加該資訊，供 `field_mapping.py:65` 呼叫 `GeminiService().semantic_match(pending, columns)` 時使用

- [ ] **Step 1: `run_auto_mapping` 內部物件加 `definition`**

找到 `backend/services/field_mapping_service.py` 的（第 205-219 行）：

```python
    variables: list[dict] = []
    for raw in paper_variables or []:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        is_target = bool(raw.get("is_target", False))
        required_type = str(raw.get("type", "") or "")
        variables.append({
            "name": name,
            "type": required_type,
            "is_target": is_target,
            # target 一律視為必要，不管呼叫端傳什麼
            "required": True if is_target else bool(raw.get("required", True)),
            "candidates": _score_candidates(name, required_type, columns),
        })
```

改成（新增 `definition` 欄位，純儲存不參與 `_score_candidates` 的比分）：

```python
    variables: list[dict] = []
    for raw in paper_variables or []:
        name = str(raw.get("name", "")).strip()
        if not name:
            continue
        is_target = bool(raw.get("is_target", False))
        required_type = str(raw.get("type", "") or "")
        variables.append({
            "name": name,
            "type": required_type,
            "is_target": is_target,
            # target 一律視為必要，不管呼叫端傳什麼
            "required": True if is_target else bool(raw.get("required", True)),
            "definition": str(raw.get("definition") or "").strip() or None,
            "candidates": _score_candidates(name, required_type, columns),
        })
```

- [ ] **Step 2: 輸出的 `mapping_status` 每筆也帶上 `definition`**

找到（第 246-268 行）：

```python
    mapping_status = []
    for variable in variables:  # 依輸入順序輸出，前端不需要再排
        matched, score = assignment[variable["name"]]
        if matched is None:
            status = UNMATCHED
            score = 0.0
        else:
            status = _status_for(score)
            if variable["is_target"] and status == AUTO_MATCHED:
                status = NEEDS_REVIEW  # target 一律人工確認
        mapping_status.append({
            "paper_variable": variable["name"],
            "required_type": variable["type"],
            "matched_user_column": matched,
            "confidence_score": round(score, 4),
            "status": status,
            "sample_values": samples_by_name.get(matched, []) if matched else [],
            "candidate_columns": (
                [name for name, _ in variable["candidates"][:3]]
                if status == UNMATCHED
                else []
            ),
        })
```

改成（`mapping_status.append` 裡新增 `"definition"` 那一行，其餘不變）：

```python
    mapping_status = []
    for variable in variables:  # 依輸入順序輸出，前端不需要再排
        matched, score = assignment[variable["name"]]
        if matched is None:
            status = UNMATCHED
            score = 0.0
        else:
            status = _status_for(score)
            if variable["is_target"] and status == AUTO_MATCHED:
                status = NEEDS_REVIEW  # target 一律人工確認
        mapping_status.append({
            "paper_variable": variable["name"],
            "required_type": variable["type"],
            "matched_user_column": matched,
            "confidence_score": round(score, 4),
            "status": status,
            "sample_values": samples_by_name.get(matched, []) if matched else [],
            "candidate_columns": (
                [name for name, _ in variable["candidates"][:3]]
                if status == UNMATCHED
                else []
            ),
            "definition": variable["definition"],
        })
```

- [ ] **Step 3: `_format_pending` 有定義時附加到 prompt 文字**

找到 `backend/services/field_mapping_prompts.py` 的（第 114-121 行）：

```python
def _format_pending(items: list[dict]) -> str:
    if not items:
        return "（無待配對項目）"
    lines = []
    for item in items:
        required_type = item.get("required_type") or "未指定"
        lines.append(f"- {item['paper_variable']}（需要型態：{required_type}）")
    return "\n".join(lines)
```

改成：

```python
def _format_pending(items: list[dict]) -> str:
    if not items:
        return "（無待配對項目）"
    lines = []
    for item in items:
        required_type = item.get("required_type") or "未指定"
        definition = item.get("definition")
        suffix = f"；定義：{definition}" if definition else ""
        lines.append(f"- {item['paper_variable']}（需要型態：{required_type}{suffix}）")
    return "\n".join(lines)
```

- [ ] **Step 4: 手動驗證（純函式，跑一段 python 腳本）**

Run:
```bash
docker exec datamind-backend sh -lc "cd /app && .venv/bin/python -c \"
from services.field_mapping_service import run_auto_mapping
from services.field_mapping_prompts import _format_pending

paper_variables = [
    {'name': 'age', 'type': 'numerical', 'definition': '病患年齡'},
    {'name': 'weird_var_xyz', 'type': 'categorical', 'definition': '一個沒有對應欄位的變數'},
]
user_columns = [
    {'name': 'age', 'sample_values': ['52', '61']},
    {'name': 'gender', 'sample_values': ['M', 'F']},
]
result = run_auto_mapping(paper_variables, user_columns)
by_name = {item['paper_variable']: item for item in result['mapping_status']}
print('age definition:', by_name['age']['definition'])
print('weird_var_xyz definition:', by_name['weird_var_xyz']['definition'])

pending = [item for item in result['mapping_status'] if item['status'] != 'AUTO_MATCHED']
prompt_text = _format_pending(pending)
print('prompt contains definition line:', '定義：一個沒有對應欄位的變數' in prompt_text)

no_def_result = run_auto_mapping([{'name': 'x', 'type': 'numerical'}], user_columns)
print('no-definition case:', no_def_result['mapping_status'][0]['definition'])
\""
```
Expected：
- `age definition: 病患年齡`
- `weird_var_xyz definition: 一個沒有對應欄位的變數`
- `prompt contains definition line: True`
- `no-definition case: None`（沒帶 `definition` 的舊資料格式，優雅降級成 `None`，不報錯）

- [ ] **Step 5: Commit**

```bash
git add backend/services/field_mapping_service.py backend/services/field_mapping_prompts.py
git commit -m "feat: thread variable definition through field-mapping auto-matching and prompt"
```

---

### Task 2: 前端 — 型別與資料串接

**Files:**
- Modify: `frontend/src/types/fieldMapping.ts:14-19,27-35`（`PaperVariable`、`MappingItem`）
- Modify: `frontend/src/views/hub/FieldMappingView.vue:583-605`（`buildPaperVariables`）

**Interfaces:**
- Consumes: Task 1 的後端改動（`mapping_status` 每筆多一個 `definition` 欄位，`api/fieldMapping.ts` 的 `initFieldMapping`/`refineFieldMapping` 已經是整包 payload 直接序列化，不需要另外改）
- Produces: `PaperVariable.definition?: string`、`MappingItem.definition?: string`，供 Task 3 的 UI 使用

- [ ] **Step 1: `PaperVariable`／`MappingItem` 加 `definition`**

找到 `frontend/src/types/fieldMapping.ts` 的（第 13-19 行）：

```ts
/** 論文擷取出來的變數。is_target 的那一筆一律視為必要。 */
export interface PaperVariable {
  name: string
  type: string
  required?: boolean
  is_target?: boolean
}
```

改成：

```ts
/** 論文擷取出來的變數。is_target 的那一筆一律視為必要。 */
export interface PaperVariable {
  name: string
  type: string
  required?: boolean
  is_target?: boolean
  definition?: string
}
```

找到（第 27-35 行）：

```ts
export interface MappingItem {
  paper_variable: string
  required_type: string
  matched_user_column: string | null
  confidence_score: number
  status: MappingStatus
  sample_values: string[]
  candidate_columns: string[]
}
```

改成：

```ts
export interface MappingItem {
  paper_variable: string
  required_type: string
  matched_user_column: string | null
  confidence_score: number
  status: MappingStatus
  sample_values: string[]
  candidate_columns: string[]
  definition?: string
}
```

- [ ] **Step 2: `buildPaperVariables` 讀取 `description_zh`**

找到 `frontend/src/views/hub/FieldMappingView.vue` 的（第 583-605 行）：

```ts
  function buildPaperVariables (): PaperVariable[] {
    const project = projectStore.projects.find(p => p.id === projectId.value)
    const framework = frameworkStore.frameworks.find(f => f.id === project?.frameworkId)
    const workflowJson = framework?.workflowJson as
      | { features?: { name: string, type?: string }[], target_col?: string }
      | undefined

    const features = workflowJson?.features ?? []
    const targetCol = workflowJson?.target_col ?? ''
    targetName.value = targetCol

    const variables: PaperVariable[] = features.map(feature => ({
      name: feature.name,
      type: feature.type ?? '',
      is_target: feature.name === targetCol,
    }))

    // target 不在 features 裡時自己補一筆，否則使用者無從指定預測目標
    if (targetCol && !features.some(f => f.name === targetCol)) {
      variables.unshift({ name: targetCol, type: 'categorical', is_target: true })
    }
    return variables
  }
```

改成（`workflowJson` 型別多兩個防禦性欄位、`variables.map` 多帶 `definition`，其餘不變）：

```ts
  function buildPaperVariables (): PaperVariable[] {
    const project = projectStore.projects.find(p => p.id === projectId.value)
    const framework = frameworkStore.frameworks.find(f => f.id === project?.frameworkId)
    const workflowJson = framework?.workflowJson as
      | {
        features?: { name: string, type?: string, description_zh?: string, descriptionZh?: string }[]
        target_col?: string
      }
      | undefined

    const features = workflowJson?.features ?? []
    const targetCol = workflowJson?.target_col ?? ''
    targetName.value = targetCol

    const variables: PaperVariable[] = features.map(feature => ({
      name: feature.name,
      type: feature.type ?? '',
      is_target: feature.name === targetCol,
      definition: feature.description_zh ?? feature.descriptionZh,
    }))

    // target 不在 features 裡時自己補一筆，否則使用者無從指定預測目標
    if (targetCol && !features.some(f => f.name === targetCol)) {
      variables.unshift({ name: targetCol, type: 'categorical', is_target: true })
    }
    return variables
  }
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/fieldMapping.ts frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: carry variable definition from framework extraction into field mapping"
```

---

### Task 3: 前端 — 變數卡片顯示定義 tooltip

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue:56-65`（變數卡片 template）
- Modify: `frontend/src/views/hub/FieldMappingView.vue:982-992`（style，`.var-name`/`.var-type` 附近）

**Interfaces:**
- Consumes: Task 2 的 `MappingItem.definition?: string`

- [ ] **Step 1: 變數卡片加 info icon + tooltip**

找到（第 56-65 行）：

```html
              <td class="col-var">
                <span
                  v-if="isTarget(item)"
                  aria-label="預測目標"
                  class="target-badge"
                  role="img"
                >★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
```

改成：

```html
              <td class="col-var">
                <span
                  v-if="isTarget(item)"
                  aria-label="預測目標"
                  class="target-badge"
                  role="img"
                >★</span>
                <span class="var-name">{{ item.paper_variable }}</span>
                <v-tooltip
                  v-if="item.definition"
                  content-class="status-tooltip"
                  location="bottom"
                  max-width="240"
                  :text="item.definition"
                >
                  <template #activator="{ props }">
                    <v-icon
                      v-bind="props"
                      class="var-info-icon"
                      icon="mdi-information-outline"
                      size="14"
                    />
                  </template>
                </v-tooltip>
                <span class="var-type">{{ item.required_type || '型態未指定' }}</span>
              </td>
```

- [ ] **Step 2: 新增 `.var-info-icon` style**

找到（第 982-992 行）：

```css
  .var-name {
    font-weight: 600;
    color: var(--color-ink);
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }
```

改成（在 `.var-name` 和 `.var-type` 之間新增）：

```css
  .var-name {
    font-weight: 600;
    color: var(--color-ink);
  }

  .var-info-icon {
    margin-left: 4px;
    color: #94a3b8;
    cursor: help;
    vertical-align: middle;
  }

  .var-type {
    display: block;
    margin-top: 2px;
    font-size: 11px;
    color: #94a3b8;
  }
```

- [ ] **Step 3: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: exit code 0，無錯誤

- [ ] **Step 4: 人工瀏覽器驗證**

用一個 `workflow_json.features` 有 `description_zh` 的框架建立新專案，走到 `/hub/projects/:id/mapping`（欄位對齊頁）。

Expected:
- 有定義的變數名稱旁邊看得到一個小 info icon，滑鼠移上去/點擊會顯示定義文字（跟狀態欄位那顆 tooltip 視覺風格一致）
- 沒有定義的變數（或用舊框架測）不會顯示 icon，畫面跟改動前一樣，不會報錯
- 開瀏覽器 Network 分頁，確認 `POST /api/field-mapping/init` 的回應 `result.mapping_status` 裡看得到 `definition` 欄位
- 整體配對流程（自動配對、AI 語意建議、手動選擇、對話式修正）行為都跟改動前一致，沒有被這次改動影響

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/FieldMappingView.vue
git commit -m "feat: show variable definition tooltip on field-mapping cards"
```
