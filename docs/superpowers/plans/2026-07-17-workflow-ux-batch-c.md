# Workflow UX 批次 C 實作計畫：自製下拉元件 + 結果面板重做

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建一個可重用的 `CustomSelect` 取代原生 `<select>`，換掉 Settings / DataTable 的下拉，並用它重做 Feature Importance 面板；另外把 Feature Engineering 唯讀面板從 JSON 傾印改成卡片式。

**Architecture:** 純前端 Vue 3。新增一個無依賴的 `CustomSelect.vue`（teleport 浮層 + 鍵盤 + type-ahead），其餘面板改為它的消費者；兩個唯讀面板重做為卡片/下拉式。實作依元件先行的依賴順序。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript、Teleport、Vite。

## Global Constraints

- **無自動測試**：每個 task 的驗證為 `npm run build`（vue-tsc 型別檢查 + vite build）＋ `npm run dev` 手動操作。指令從 `frontend/` 執行。
- **使用者可見文字用繁體中文**。
- **Commit 前需取得使用者確認**；commit 訊息一行、英文、不加 `Co-Authored-By`、不引用私人筆記或其編號。
- `npm run lint` 是既有壞基線，不作為 gate；照現有檔案風格撰寫。
- 任務逐一實作、逐一 commit（同檔跨任務變更用「先做先 commit」的順序）。

---

### Task 1: `CustomSelect` 元件

**Files:**
- Create: `frontend/src/components/common/CustomSelect.vue`

**Interfaces:**
- Produces: 元件 `CustomSelect`，props `modelValue: string`、`options: {value:string;label:string;disabled?:boolean}[]`、`placeholder?: string`、`disabled?: boolean`、`highlight?: boolean`；emits `update:modelValue`、`change`。後續 task 依此消費。

- [ ] **Step 1: 建立元件檔**

Create `frontend/src/components/common/CustomSelect.vue` with exactly:

```vue
<template>
  <div
    ref="triggerRef"
    class="custom-select"
    :class="{ 'is-disabled': disabled, 'is-highlight': highlight, 'is-open': open }"
  >
    <button
      type="button"
      class="cs-trigger"
      role="combobox"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :disabled="disabled"
      @click="toggle"
      @keydown="onTriggerKeydown"
    >
      <span class="cs-label" :class="{ 'is-placeholder': !selectedLabel }">
        {{ selectedLabel ?? placeholder ?? '' }}
      </span>
      <span class="cs-chevron" aria-hidden="true">
        <svg width="16" height="16" viewBox="0 0 24 24"><path fill="currentColor" d="M7 10l5 5 5-5z" /></svg>
      </span>
    </button>

    <Teleport to="body">
      <ul
        v-if="open"
        ref="popupRef"
        class="cs-popup"
        role="listbox"
        :style="popupStyle"
        @keydown="onPopupKeydown"
      >
        <li
          v-for="(opt, i) in options"
          :key="opt.value"
          class="cs-option"
          :class="{
            'is-active': i === activeIndex,
            'is-selected': opt.value === modelValue,
            'is-disabled': opt.disabled,
          }"
          role="option"
          :aria-selected="opt.value === modelValue"
          :aria-disabled="opt.disabled || undefined"
          @mouseenter="activeIndex = i"
          @click="selectOption(opt)"
        >
          {{ opt.label }}
        </li>
      </ul>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

  interface Option { value: string, label: string, disabled?: boolean }

  const props = defineProps<{
    modelValue: string
    options: Option[]
    placeholder?: string
    disabled?: boolean
    highlight?: boolean
  }>()

  const emit = defineEmits<{
    'update:modelValue': [value: string]
    'change': [value: string]
  }>()

  const triggerRef = ref<HTMLElement | null>(null)
  const popupRef = ref<HTMLElement | null>(null)
  const open = ref(false)
  const activeIndex = ref(-1)
  const popupStyle = ref<Record<string, string>>({})

  const selectedLabel = computed(
    () => props.options.find(o => o.value === props.modelValue)?.label ?? null,
  )

  function firstEnabledIndex (): number {
    return props.options.findIndex(o => !o.disabled)
  }

  function updatePosition (): void {
    const el = triggerRef.value
    if (!el) return
    const r = el.getBoundingClientRect()
    if (r.bottom < 0 || r.top > window.innerHeight) {
      close()
      return
    }
    popupStyle.value = {
      position: 'fixed',
      top: `${r.bottom + 4}px`,
      left: `${r.left}px`,
      width: `${r.width}px`,
    }
  }

  function openPopup (): void {
    if (props.disabled || open.value) return
    open.value = true
    const sel = props.options.findIndex(o => o.value === props.modelValue)
    activeIndex.value = sel >= 0 ? sel : firstEnabledIndex()
    nextTick(updatePosition)
  }

  function close (): void {
    open.value = false
  }

  function toggle (): void {
    if (open.value) close()
    else openPopup()
  }

  function focusTrigger (): void {
    triggerRef.value?.querySelector('button')?.focus()
  }

  function selectOption (opt: Option): void {
    if (opt.disabled) return
    emit('update:modelValue', opt.value)
    emit('change', opt.value)
    close()
    focusTrigger()
  }

  function moveActive (delta: number): void {
    const n = props.options.length
    if (n === 0) return
    let i = activeIndex.value
    for (let step = 0; step < n; step += 1) {
      i = (i + delta + n) % n
      if (!props.options[i]?.disabled) {
        activeIndex.value = i
        break
      }
    }
  }

  let typeBuffer = ''
  let typeTimer: number | undefined

  function onTypeAhead (ch: string): void {
    typeBuffer += ch.toLowerCase()
    window.clearTimeout(typeTimer)
    typeTimer = window.setTimeout(() => {
      typeBuffer = ''
    }, 500)
    const idx = props.options.findIndex(
      o => !o.disabled && o.label.toLowerCase().startsWith(typeBuffer),
    )
    if (idx >= 0) activeIndex.value = idx
  }

  function onPopupKeydown (e: KeyboardEvent): void {
    switch (e.key) {
      case 'ArrowDown': {
        e.preventDefault()
        moveActive(1)
        break
      }
      case 'ArrowUp': {
        e.preventDefault()
        moveActive(-1)
        break
      }
      case 'Enter': {
        e.preventDefault()
        const opt = props.options[activeIndex.value]
        if (opt) selectOption(opt)
        break
      }
      case 'Escape': {
        e.preventDefault()
        close()
        break
      }
      case 'Tab': {
        close()
        break
      }
      default: {
        if (e.key.length === 1) onTypeAhead(e.key)
      }
    }
  }

  function onTriggerKeydown (e: KeyboardEvent): void {
    if (props.disabled) return
    if (!open.value) {
      if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(e.key)) {
        e.preventDefault()
        openPopup()
      }
      return
    }
    onPopupKeydown(e)
  }

  function onDocPointer (e: PointerEvent): void {
    const t = e.target as Node
    if (triggerRef.value?.contains(t) || popupRef.value?.contains(t)) return
    close()
  }

  watch(open, isOpen => {
    if (isOpen) {
      document.addEventListener('pointerdown', onDocPointer, true)
      window.addEventListener('scroll', updatePosition, true)
      window.addEventListener('resize', updatePosition)
    } else {
      document.removeEventListener('pointerdown', onDocPointer, true)
      window.removeEventListener('scroll', updatePosition, true)
      window.removeEventListener('resize', updatePosition)
      activeIndex.value = -1
    }
  })

  onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', onDocPointer, true)
    window.removeEventListener('scroll', updatePosition, true)
    window.removeEventListener('resize', updatePosition)
    window.clearTimeout(typeTimer)
  })
</script>

<style scoped>
  .custom-select {
    position: relative;
    width: 100%;
  }

  .cs-trigger {
    width: 100%;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px;
    padding: 0 8px;
    border: 1px solid rgba(0, 93, 255, 0.18);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.9);
    color: #0f172a;
    font-size: 13px;
    cursor: pointer;
    text-align: left;
  }

  .cs-trigger:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .is-highlight .cs-trigger {
    border-color: #94a3b8;
  }

  .cs-label {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cs-label.is-placeholder {
    color: #94a3b8;
  }

  .cs-chevron {
    display: flex;
    color: #005dff;
    flex-shrink: 0;
    transition: transform 0.15s;
  }

  .is-open .cs-chevron {
    transform: rotate(180deg);
  }

  .cs-popup {
    margin: 0;
    padding: 4px;
    list-style: none;
    max-height: 240px;
    overflow-y: auto;
    background: #fff;
    border: 1px solid rgba(0, 93, 255, 0.18);
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
    z-index: 3000;
  }

  .cs-option {
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 13px;
    color: #0f172a;
    cursor: pointer;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cs-option.is-active {
    background: rgba(0, 93, 255, 0.08);
  }

  .cs-option.is-selected {
    color: #005dff;
    font-weight: 600;
  }

  .cs-option.is-disabled {
    color: #cbd5e1;
    cursor: not-allowed;
  }
</style>
```

- [ ] **Step 2: 型別檢查**

Run（從 `frontend/`）：`npm run build`
Expected: 通過（元件本身可編譯；實際 UI 驗證在 Task 2 首個消費點）。

- [ ] **Step 3: Commit（先問使用者）**

```bash
git add frontend/src/components/common/CustomSelect.vue
git commit -m "feat: add reusable CustomSelect dropdown component"
```

---

### Task 2: 換掉 SettingsPanel 的 4 個 select

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue`

**Interfaces:**
- Consumes: `CustomSelect`（Task 1）。

- [ ] **Step 1: import 元件**

在 `SettingsPanel.vue` 的 `<script setup>` 頂端 `import { computed, ref, watch } from 'vue'` 之後加：

```ts
  import CustomSelect from '@/components/common/CustomSelect.vue'
```

- [ ] **Step 2: 前處理 add-bar type select（約第 27-30 行）**

原本：

```html
        <select v-model="newPreprocessType" class="type-select">
          <option disabled value="">選擇步驟類型</option>
          <option v-for="[k, v] in preprocessOptions" :key="k" :value="k">{{ v }}</option>
        </select>
```

改為：

```html
        <CustomSelect
          v-model="newPreprocessType"
          class="type-select"
          :options="preprocessOptions.map(([value, label]) => ({ value, label }))"
          placeholder="選擇步驟類型"
        />
```

- [ ] **Step 3: 特徵工程 add-bar type select（約第 95-98 行）**

原本：

```html
        <select v-model="newFEType" class="type-select">
          <option disabled value="">選擇步驟類型</option>
          <option v-for="[k, v] in featureOptions" :key="k" :value="k">{{ v }}</option>
        </select>
```

改為：

```html
        <CustomSelect
          v-model="newFEType"
          class="type-select"
          :options="featureOptions.map(([value, label]) => ({ value, label }))"
          placeholder="選擇步驟類型"
        />
```

- [ ] **Step 4: 模型 add-bar select（約第 149-162 行）**

原本：

```html
        <select
          v-model="selectedModel"
          class="type-select"
          :disabled="props.modelOptionsLoading || availableModels.length === 0"
        >
          <option disabled value="">
            {{ props.modelOptionsLoading ? '載入中…' : availableModels.length === 0 ? '已全部加入' : '選擇模型' }}
          </option>
          <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
        </select>
```

改為：

```html
        <CustomSelect
          v-model="selectedModel"
          class="type-select"
          :options="availableModels.map(m => ({ value: m, label: m }))"
          :placeholder="props.modelOptionsLoading ? '載入中…' : availableModels.length === 0 ? '已全部加入' : '選擇模型'"
          :disabled="props.modelOptionsLoading || availableModels.length === 0"
        />
```

- [ ] **Step 5: `fill_na` strategy 參數 select（約第 50-58 行）**

原本：

```html
                <select
                  class="param-select"
                  :value="step.strategy ?? 'mean'"
                  @change="patchPreprocessStep(i, 'strategy', ($event.target as HTMLSelectElement).value)"
                >
                  <option value="mean">均值</option>
                  <option value="median">中位數</option>
                  <option value="mode">眾數</option>
                </select>
```

改為：

```html
                <CustomSelect
                  class="param-select"
                  :model-value="String(step.strategy ?? 'mean')"
                  :options="[
                    { value: 'mean', label: '均值' },
                    { value: 'median', label: '中位數' },
                    { value: 'mode', label: '眾數' },
                  ]"
                  @update:model-value="patchPreprocessStep(i, 'strategy', $event)"
                />
```

- [ ] **Step 6: 型別檢查 + 手動驗證**

Run：`npm run build`（通過）。
`npm run dev` → Settings：三個 type/模型下拉與 strategy 都能開/選；模型下拉載入中/已全部加入時 disabled 且顯示對應 placeholder；浮層不被 step-body 捲動區裁掉；鍵盤 ↑↓/Enter/Esc 與打字 type-ahead 可用。

- [ ] **Step 7: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "feat: use CustomSelect for Settings panel dropdowns"
```

---

### Task 3: 換掉 DataTablePanel 的 Type / Role select

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue`

**Interfaces:**
- Consumes: `CustomSelect`（Task 1）。

- [ ] **Step 1: import 元件**

在 `DataTablePanel.vue` 的 `<script setup>` 的 `import { computed, ref, watch } from 'vue'` 之後加：

```ts
  import CustomSelect from '@/components/common/CustomSelect.vue'
```

- [ ] **Step 2: Type select（約第 71-79 行）**

原本：

```html
                  <select v-model="column.type">
                    <option
                      v-for="type in typeOptions"
                      :key="type"
                      :value="type"
                    >
                      {{ typeLabels[type] }}
                    </option>
                  </select>
```

改為（`column.type` 是 `ColumnType` union，用 `:model-value` + cast 寫回，避免 vue-tsc 報 `string` 不可指派給 union）：

```html
                  <CustomSelect
                    :model-value="column.type"
                    :options="typeOptions.map(t => ({ value: t, label: typeLabels[t] }))"
                    @update:model-value="column.type = $event as ColumnType"
                  />
```

- [ ] **Step 3: Role select（約第 82-103 行）**

原本（含 `.role-select-wrap` 內的 `<select>`）：

```html
                    <select
                      v-model="column.role"
                      class="role-select"
                      :class="{
                        'role-select--attention': props.loading && !hasTarget && !roleSelectTouched,
                      }"
                      @change="onRoleChange(index)"
                      @focus="handleRoleSelectFocus"
                    >
                      <option
                        v-for="role in roleOptions"
                        :key="role"
                        :value="role"
                      >
                        {{ roleLabels[role] }}
                      </option>
                    </select>
```

改為（保留外層 `.role-select-wrap` 與其後的 tap-hint；`column.role` 是 `ColumnRole` union，同樣用 `:model-value` + cast；`@focus` 改綁 `@focusin`）：

```html
                    <CustomSelect
                      class="role-select"
                      :model-value="column.role"
                      :options="roleOptions.map(r => ({ value: r, label: roleLabels[r] }))"
                      :highlight="props.loading && !hasTarget && !roleSelectTouched"
                      @update:model-value="column.role = $event as ColumnRole"
                      @change="onRoleChange(index)"
                      @focusin="handleRoleSelectFocus"
                    />
```

（`@update:model-value` 先寫回 `column.role`，接著 `@change` 才呼叫 `onRoleChange`，所以 demote 時讀到的已是新值。`@focusin` 是原生事件、會從內部按鈕冒泡到 `CustomSelect` 根元素，等同原本 `@focus` 的「碰過 Role 選單」語意，用來淡出 tap-hint。）

- [ ] **Step 4: 型別檢查 + 手動驗證**

Run：`npm run build`（通過）。
`npm run dev` → DataTable：Type / Role 都能開/選；Role 未選 target 時的注意態邊框（`highlight`）與 tap-hint 漣漪還在、碰過後漣漪淡出；重選 target 仍會把舊 target demote 回 feature；浮層不被表格 `overflow` 裁掉。

- [ ] **Step 5: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "feat: use CustomSelect for Data Table type and role dropdowns"
```

---

### Task 4: Feature Importance 面板重做（兩層下拉）

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue`

**Interfaces:**
- Consumes: `CustomSelect`（Task 1）；既有 `groupedResults`（`[{ model_name, splits: [{ split_name, feature_importance }] }]`）。

- [ ] **Step 1: 改寫 template**

把 `FeatureImportancePanel.vue` 的整個 `<template>`（第 1-62 行）改為：

```html
<template>
  <section class="feature-importance-panel">
    <div v-if="groupedResults.length > 0" class="fi-controls">
      <label class="fi-field">
        <span class="fi-field__label">模型</span>
        <CustomSelect
          v-model="selectedModel"
          :options="modelOptions"
        />
      </label>
      <label class="fi-field">
        <span class="fi-field__label">fold</span>
        <CustomSelect
          v-model="selectedFold"
          :options="foldOptions"
        />
      </label>
    </div>

    <div
      v-if="currentImportance.length > 0"
      class="importance-table"
    >
      <div class="importance-row importance-row--header">
        <div class="importance-cell">Feature</div>
        <div class="importance-cell">Importance</div>
      </div>
      <div
        v-for="item in currentImportance"
        :key="item.feature"
        class="importance-row"
      >
        <div class="importance-cell importance-cell--feature">{{ item.feature }}</div>
        <div class="importance-cell importance-cell--value">{{ formatImportance(item.importance) }}</div>
      </div>
    </div>

    <div v-else-if="groupedResults.length > 0" class="summary-empty">
      該抽樣沒有可用的特徵重要性資訊。
    </div>

    <div v-else class="summary-empty">
      尚未有特徵重要性結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>
```

- [ ] **Step 2: 加入選取狀態與 computed**

在 `<script setup>` 的 `import { computed } from 'vue'` 改成 `import { computed, ref, watch } from 'vue'`，並在 `groupedResults` computed 之後加：

```ts
  import CustomSelect from '@/components/common/CustomSelect.vue'

  const selectedModel = ref('')
  const selectedFold = ref('')

  const modelOptions = computed(() =>
    groupedResults.value.map(g => ({ value: g.model_name, label: g.model_name })),
  )

  const currentModel = computed(() =>
    groupedResults.value.find(g => g.model_name === selectedModel.value) ?? null,
  )

  const foldOptions = computed(() =>
    (currentModel.value?.splits ?? []).map(s => ({ value: s.split_name, label: s.split_name })),
  )

  const currentImportance = computed(() =>
    currentModel.value?.splits.find(s => s.split_name === selectedFold.value)?.feature_importance ?? [],
  )

  // 結果載入或換模型後，把選取校正到有效值（預設第一個模型 / 第一個 fold）
  watch(groupedResults, groups => {
    if (groups.length === 0) {
      selectedModel.value = ''
      return
    }
    if (!groups.some(g => g.model_name === selectedModel.value)) {
      selectedModel.value = groups[0]!.model_name
    }
  }, { immediate: true })

  watch([currentModel, () => selectedFold.value], ([model]) => {
    const splits = model?.splits ?? []
    if (splits.length > 0 && !splits.some(s => s.split_name === selectedFold.value)) {
      selectedFold.value = splits[0]!.split_name
    }
  }, { immediate: true })
```

（`import CustomSelect` 這行請放在 `<script setup>` 最上面與其他 import 一起；此處併列僅為就近說明。）

- [ ] **Step 3: 加入 controls 樣式，移除舊卡片樣式**

在 `<style scoped>` 移除只服務舊巢狀卡片的規則（`.importance-card`、`.importance-card__header`、`.importance-card__title`、`.importance-card__subtitle`、`.importance-split-list`、`.importance-split`、`.importance-split__title`、`.importance-list` 以及 `.feature-importance-panel h4`——若存在），保留 `.importance-table` / `.importance-row` / `.importance-cell` / `.summary-empty`，並新增：

```css
  .fi-controls {
    display: flex;
    gap: 12px;
  }

  .fi-field {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .fi-field__label {
    font-size: 12px;
    color: #64748b;
  }
```

- [ ] **Step 4: 型別檢查 + 手動驗證**

Run：`npm run build`（通過）。
`npm run dev`（需先跑完一次 workflow 才有結果）→ Feature Importance：兩顆下拉並排（模型 / fold）；選模型 → fold 選項跟著換、預設第一個；下面只顯示那一折的表；面板內**沒有**重複的「Feature Importance」標題（只剩 panel header 的）。

- [ ] **Step 5: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue
git commit -m "feat: rework Feature Importance panel into model/fold dropdowns"
```

---

### Task 5: Feature Engineering 面板卡片化

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue`

**Interfaces:**
- Consumes: 既有 `pipeline` prop（`Array<Record<string, unknown>>`，每步含 `type` 與參數）。

- [ ] **Step 1: 改寫 template**

把 `FeatureEngineeringPanel.vue` 的 `<template>`（第 1-26 行）改為：

```html
<template>
  <section class="feature-engineering-panel">
    <template v-if="pipeline.length > 0">
      <div class="step-count">共 {{ pipeline.length }} 個特徵工程步驟</div>

      <div class="steps">
        <div
          v-for="(step, index) in pipeline"
          :key="index"
          class="step-item"
        >
          <div class="step-header">
            <span class="step-index">{{ index + 1 }}</span>
            <span class="step-label">{{ stepLabel(step.type as string) }}</span>
          </div>
          <div v-if="visibleParams(step).length > 0" class="step-params">
            <div
              v-for="[key, val] in visibleParams(step)"
              :key="key"
              class="param-row"
            >
              <span class="param-key">{{ key }}</span>
              <span class="param-val">{{ val }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="empty-hint">
      尚未設定特徵工程步驟。
    </div>
  </section>
</template>
```

- [ ] **Step 2: 改寫 script**

把 `<script setup>`（第 28-43 行）改為：

```ts
<script setup lang="ts">
  import { computed } from 'vue'

  const props = defineProps<{
    pipeline?: Array<Record<string, unknown>> | null
  }>()

  const pipeline = computed(() => props.pipeline ?? [])

  const STEP_LABELS: Record<string, string> = {
    select_relevant_features: '特徵選擇',
    pca: 'PCA 降維',
    discretize_continuous: '連續→離散',
    continuize_discrete: '離散→連續',
    normalize_features: '特徵正規化',
    remove_sparse_features: '移除稀疏特徵',
  }

  function stepLabel (type: string): string {
    return STEP_LABELS[type] ?? type
  }

  const HIDDEN_KEYS = new Set(['type'])

  function visibleParams (step: Record<string, unknown>): [string, string][] {
    return Object.entries(step)
      .filter(([k]) => !HIDDEN_KEYS.has(k))
      .map(([k, v]) => [k, String(v)])
  }
</script>
```

- [ ] **Step 3: 換 style**

把 `<style scoped>`（第 46-100 行）整段換成 PreprocessorPanel 同款樣式：

```css
<style scoped>
  .feature-engineering-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: #475569;
  }

  .steps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: #1e293b;
    min-width: 0;
    word-break: break-word;
  }

  .step-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed #e2e8f0;
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    color: #0f172a;
    font-weight: 500;
  }

  .empty-hint {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

- [ ] **Step 4: 型別檢查 + 手動驗證**

Run：`npm run build`（通過）。
`npm run dev` → 點畫布上的 Feature Engineering 節點（需 workflow 有特徵工程步驟）→ 面板顯示卡片（step 圓圈 + 中文 label + `key: val`），不再是 JSON。

- [ ] **Step 5: Commit（先問使用者）**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue
git commit -m "feat: render Feature Engineering panel as cards instead of raw JSON"
```

---

## 完成後

五個 task 完成、`npm run build` 通過、手動驗證通過後，批次 C 收工。批次 A/B/C 合起來就是這輪 workflow UI/state 的全部改動。
