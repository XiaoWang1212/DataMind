# DataTable 疑似 ID 欄位偵測 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `DataTablePanel.vue` 初始化欄位設定時，自動把疑似 ID 的欄位預設成 `Skip`（不是 `Feature`），並在使用者手動把疑似 ID 欄位設成 `Target` 時顯示警告提示。

**Architecture:** 新增一個純函式 `isLikelyIdColumn(header, values)`，結合欄名單字比對（避免 `valid` 這類誤判）與唯一值比例判斷。`buildColumnSettings()` 初始化沒有既有設定的欄位時呼叫它決定預設 `role`；另外新增一個 `columnLikelyIdFlags` computed（比照既有 `columnValueLabels` 的寫法），供 template 判斷要不要在 `Target` 選取時顯示警告文字。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript，純前端、單一檔案改動。

## Global Constraints

- 只影響「沒有既有設定」的欄位初始化預設值（`existing` 為 `undefined` 時）；已有 `existing.role` 的欄位完全不受影響，不能覆蓋使用者已經做過的選擇
- 不阻擋使用者手動選擇——偵測到疑似 ID 只改變預設值、顯示警告，不影響「繼續」按鈕的 `disabled` 邏輯（`hasTarget` 不變）
- 欄名比對要用「單字邊界」比對，不能用 `header.endsWith('id')` 這種簡單字串比對（會誤判 `valid`/`avoid` 這類欄名）
- 唯一值比例的門檻是「非空值筆數 ≥ 10」才啟用判斷，比例門檻是 `> 0.95`
- 不動 `type`（型別）偵測邏輯，只動 `role` 的預設值與警告顯示

---

### Task 1: 新增疑似 ID 欄位偵測與 UI 警告

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`

**Interfaces:**
- Produces: `isLikelyIdColumn(header: string, values: string[]): boolean`（純函式，不依賴元件狀態）
- Produces: `columnLikelyIdFlags` computed（`boolean[]`，跟 `columnSettings.value`/`columnValueLabels` 同樣用索引對齊）

- [ ] **Step 1: 新增拆字與偵測函式**

`DataTablePanel.vue` 現有的 `isLikelyDate()` 函式（第 204-209 行）之後、`getColumnTypeCandidates()`（第 211 行）之前，新增：

```typescript
  // 把欄名拆成單字：底線/連字號/空白當分隔符，另外在 camelCase 邊界（小寫或數字後接大寫）也拆開
  // 例如 "patient_id" -> ["patient", "id"]、"caseID" -> ["case", "ID"]
  function splitIntoWords (header: string): string[] {
    return header
      .split(/[_\-\s]+/)
      .flatMap(part => part.split(/(?<=[a-z0-9])(?=[A-Z])/))
      .filter(Boolean)
  }

  // 疑似 ID 欄位：欄名的某個單字剛好是 "id"（避免 "valid"/"avoid" 這種結尾剛好是 id 但不是獨立單字的誤判），
  // 或是非空值幾乎全部不重複（唯一值比例 > 0.95，且非空筆數 >= 10，樣本太少時比例不可靠）
  function isLikelyIdColumn (header: string, values: string[]): boolean {
    const words = splitIntoWords(header)
    if (words.some(word => word.toLowerCase() === 'id')) return true

    const nonEmpty = values.map(value => value?.trim() ?? '').filter(Boolean)
    if (nonEmpty.length < 10) return false
    const uniqueCount = new Set(nonEmpty).size
    return uniqueCount / nonEmpty.length > 0.95
  }
```

- [ ] **Step 2: 初始化時疑似 ID 欄位預設 `role: 'skip'`**

`buildColumnSettings()` 現有內容（第 235-251 行）：
```typescript
  function buildColumnSettings (useExisting = true): void {
    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      // 用索引而非名稱對位：Column Name 可編輯，改過名字後就跟 CSV 表頭對不上了
      const existing = useExisting ? props.columnConfig?.[index] : undefined
      const selectedType = existing?.type ?? (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? 'feature'

      return {
        name: existing?.name ?? header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })
  }
```
改成（只改 `selectedRole` 那一行）：
```typescript
  function buildColumnSettings (useExisting = true): void {
    columnSettings.value = previewColumns.value.map((header, index) => {
      const columnValues = previewDataRows.value.map(row => row[index] ?? '')
      const availableTypes = getColumnTypeCandidates(columnValues)
      // 用索引而非名稱對位：Column Name 可編輯，改過名字後就跟 CSV 表頭對不上了
      const existing = useExisting ? props.columnConfig?.[index] : undefined
      const selectedType = existing?.type ?? (availableTypes[0] ?? 'text')
      const selectedRole = existing?.role ?? (isLikelyIdColumn(header, columnValues) ? 'skip' : 'feature')

      return {
        name: existing?.name ?? header,
        type: selectedType,
        role: selectedRole,
        availableTypes,
      }
    })
  }
```

- [ ] **Step 3: 新增 `columnLikelyIdFlags` computed**

現有的 `columnValueLabels` computed（第 342-344 行）：
```typescript
  const columnValueLabels = computed<string[]>(() =>
    columnSettings.value.map((column, index) => computeColumnValueLabel(column, index)),
  )
```
在它之後新增：
```typescript

  // 用「目前的」column.name（使用者可能已經改過名字）跟原始數值重新判斷，
  // 不是沿用初始化當下算好的結果，確保使用者改名後警告狀態也會跟著更新
  const columnLikelyIdFlags = computed<boolean[]>(() =>
    columnSettings.value.map((column, index) => isLikelyIdColumn(column.name, getColumnRawValues(index))),
  )
```

- [ ] **Step 4: Template — 在 Role 欄加警告文字**

現有的 Role 欄（第 77-100 行）：
```html
                <td :class="{ 'target-cell': column.role === 'target' }">
                  <div class="role-select-wrap">
                    <CustomSelect
                      class="role-select"
                      :model-value="column.role"
                      :options="roleOptions.map(r => ({ value: r, label: roleLabels[r] }))"
                      :highlight="props.loading && !hasTarget && !roleSelectTouched"
                      @update:model-value="column.role = $event as ColumnRole"
                      @change="onRoleChange(index)"
                      @focusin="handleRoleSelectFocus"
                    />
                    <Transition v-if="index === 0" name="tap-hint-fade">
                      <span
                        v-if="props.loading && !roleSelectTouched && !hasTarget"
                        aria-hidden="true"
                        class="tap-hint"
                      >
                        <span class="tap-hint__ring" />
                        <span class="tap-hint__ring tap-hint__ring--delay" />
                        <span class="tap-hint__dot" />
                      </span>
                    </Transition>
                  </div>
                </td>
```
改成（在 `.role-select-wrap` 的 `</div>` 之前加警告文字）：
```html
                <td :class="{ 'target-cell': column.role === 'target' }">
                  <div class="role-select-wrap">
                    <CustomSelect
                      class="role-select"
                      :model-value="column.role"
                      :options="roleOptions.map(r => ({ value: r, label: roleLabels[r] }))"
                      :highlight="props.loading && !hasTarget && !roleSelectTouched"
                      @update:model-value="column.role = $event as ColumnRole"
                      @change="onRoleChange(index)"
                      @focusin="handleRoleSelectFocus"
                    />
                    <Transition v-if="index === 0" name="tap-hint-fade">
                      <span
                        v-if="props.loading && !roleSelectTouched && !hasTarget"
                        aria-hidden="true"
                        class="tap-hint"
                      >
                        <span class="tap-hint__ring" />
                        <span class="tap-hint__ring tap-hint__ring--delay" />
                        <span class="tap-hint__dot" />
                      </span>
                    </Transition>
                    <p
                      v-if="column.role === 'target' && columnLikelyIdFlags[index]"
                      class="id-warning"
                    >
                      這個欄位的值幾乎都不重複，可能不適合當分類目標
                    </p>
                  </div>
                </td>
```

- [ ] **Step 5: 加對應樣式**

`.target-row`/`.target-cell`（第 713-716 行）之前新增：
```css
  .id-warning {
    margin: 4px 0 0;
    font-size: 11px;
    line-height: 1.4;
    color: var(--color-warning-text);
  }
```

- [ ] **Step 6: 型別檢查**

Run: `cd frontend && npm run type-check`

Expected: 這個專案目前有既有的、跟 `@tiptap/*` 套件解析失敗有關的錯誤（環境缺套件、跟本次改動無關）。用 `npm run type-check 2>&1 | grep -c "error TS"` 記錄改動前後的數字，確認沒有增加，或用 `grep -i "DataTablePanel"` 確認輸出裡沒有這個檔案的錯誤。

- [ ] **Step 7: Commit**

```bash
cd /Users/xiaowang/Documents/Github/DataMind
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "feat: detect likely ID columns and default their role to skip"
```

---

## 完成後的人工驗證

Task 完成、commit 之後，在瀏覽器 `http://localhost:5173` 上驗證（前端 dev server 已在跑，直接測，不需要另開 worktree 連結）：

1. 上傳一份含 `patient_id`（或類似欄名，如 `case_id`、`ID`）欄位的 CSV，確認該欄位初始化時 Role 是 `Skip`，其餘一般欄位仍是 `Feature`
2. 上傳一份沒有明顯 ID 欄名、但某欄位數值幾乎每筆都不同（例如流水號）的 CSV，確認該欄位一樣被預設成 `Skip`
3. 把一個疑似 ID 欄位的 Role 手動改成 `Target`，確認出現警告文字「這個欄位的值幾乎都不重複，可能不適合當分類目標」，且「繼續」按鈕不受影響（選了 target 就能按）
4. 確認欄名像 `valid`、`avoid` 這類「結尾是 id 但不是獨立單字」的欄位不會被誤判成疑似 ID（初始化時維持 `Feature`，選成 target 也不會跳警告）
5. 重新整理頁面或切換節點再切回來，確認使用者手動調整過的 Role 不會被這個偵測邏輯覆蓋回去
6. 把疑似 ID 欄位的 Column Name 改掉（改成不像 ID 的名字），確認警告文字會跟著消失（因為 `columnLikelyIdFlags` 是依目前的 `column.name` 即時判斷，不是初始化當下的快照）
