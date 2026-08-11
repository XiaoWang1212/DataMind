# FieldMappingView 重構 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `frontend/src/views/hub/FieldMappingView.vue`（1381 行）拆成 3 個呈現元件 + 2 個邏輯 composable + 1 個協調頁面，行為完全不變。

**Architecture:** 三個元件一律 props down / emits up，子元件永不修改 props——所有資料變更邏輯留在 page，只是改由 emit 觸發而非直接呼叫。兩個 composable 各自持有完全自包含的狀態（undo/redo 快照堆疊、localStorage 草稿），透過 deps 物件接收頁面的 ref。每個任務結束時 app 必須可建置、功能完整。

**Tech Stack:** Vue 3.5 `<script setup>` + TypeScript strict + Vuetify 4 + Vite（無自動化測試框架）

## Global Constraints

- **行為完全不變。** 這是重構不是重新設計。使用者看到的畫面與互動結果必須與拆分前一致
- **不改任何 CSS 數值。** 樣式只是換檔案放，不調整顏色、間距、圓角
- **子元件不修改 props。** 所有 mapping 資料變更由 page 執行
- 專案沒有自動化測試，每個任務的驗證是：`npm run build`（含 `vue-tsc` 型別檢查）通過 + 新檔案 eslint 零錯誤 + 該任務對應的人工互動檢查
- 搬移程式碼時**連同原有註解一起搬**，不要重寫或省略——那些註解記錄了當初踩過的坑
- 每個任務結束後 app 必須維持可建置、可運行，不留下半拆狀態
- **本計畫引用的所有行號都是「重構開始前」原始檔案的行號**（`FieldMappingView.vue` 1381 行的版本）。每完成一個任務，該檔案就會變短、行號隨之位移，所以從 Task 2 開始請**以選擇器名稱或符號名稱定位**（例如「找 `.mapping-scroll` 這條規則」「找 `optionsFor` 這個函式」），行號只當作原始位置的參考

---

## File Structure

| 動作 | 路徑 | 職責 |
|---|---|---|
| 新增 | `frontend/src/components/hub/fieldMapping/DatasetPreview.vue` | 資料預覽表（純呈現，無 emits） |
| 新增 | `frontend/src/components/hub/fieldMapping/MappingChatPanel.vue` | AI 對話面板：訊息串、輸入框、自己的捲動與 textarea 行為 |
| 新增 | `frontend/src/components/hub/fieldMapping/MappingTable.vue` | 對映表格：排序、下拉選項計算、狀態徽章、操作按鈕 |
| 新增 | `frontend/src/composables/fieldMapping/useMappingDraft.ts` | localStorage 草稿存讀 |
| 新增 | `frontend/src/composables/fieldMapping/useMappingHistory.ts` | undo/redo 快照堆疊與鍵盤快捷鍵 |
| 修改 | `frontend/src/types/fieldMapping.ts` | 新增 `SKIP_VALUE` 常數 |
| 修改 | `frontend/src/views/hub/FieldMappingView.vue` | 縮成協調者 |

**CSS 搬移總表**（現行行號，依任務順序處理）：

| 區塊 | 現行行號 | 去處 |
|---|---|---|
| `.preview-block` ~ `.preview-table th` | 1166-1197 | Task 1 → DatasetPreview |
| `.mapping-chat` ~ `.chat-send:disabled` | 1245-1371 | Task 2 → MappingChatPanel |
| `.chat-send:hover:not(:disabled)`（**與 `.confirm-btn` 共用一條規則**） | 1235-1238 | Task 2 → **必須拆成兩條**，見 Task 2 Step 4 |
| `.mapping-scroll` ~ `@keyframes row-flash` | 943-1152 | Task 3 → MappingTable |
| `@media (prefers-reduced-motion)`（**內含 `.confirm-all-btn` 與 `.check-btn` 共用一條規則**） | 1154-1164 | Task 3 → **必須拆成兩個 media query**，見 Task 3 Step 5 |
| 全域 `.status-tooltip` 區塊 | 1374-1381 | Task 3 → MappingTable 的第二個（非 scoped）`<style>` |
| 其餘（`.mapping-page`、`.page-*`、`.back-link`、`.load-error*`、`.mapping-layout`、`.mapping-main`、`.mapping-loading`、`.confirm-all-btn`、`.mapping-footer`、`.footer-*`、`.confirm-btn*`） | — | 留在 page |

---

### Task 1: DatasetPreview 元件

最小、零狀態耦合的區塊，先做它來建立元件目錄與 props 慣例。

**Files:**
- Create: `frontend/src/components/hub/fieldMapping/DatasetPreview.vue`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`（移除 template 141-155 與 CSS 1166-1197，改為引用元件）

**Interfaces:**
- Consumes: 無（第一個任務）
- Produces: `DatasetPreview` 元件，props `{ columns: string[], rows: string[][] }`，無 emits

- [ ] **Step 1: 建立元件檔案**

Create `frontend/src/components/hub/fieldMapping/DatasetPreview.vue`：

```vue
<template>
  <div class="preview-block">
    <div class="preview-title">資料預覽（前 {{ rows.length }} 筆）</div>
    <div class="preview-scroll">
      <table class="preview-table">
        <thead>
          <tr><th v-for="col in columns" :key="col">{{ col }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i">
            <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    columns: string[]
    rows: string[][]
  }>()
</script>

<style scoped>
</style>
```

- [ ] **Step 2: 把預覽表的 CSS 搬進元件**

把 `FieldMappingView.vue` 第 1166-1197 行（`.preview-block`、`.preview-title`、`.preview-scroll`、`.preview-table`、`.preview-table th, .preview-table td` 共用規則、`.preview-table th`）**原封不動**剪下，貼進上一步的 `<style scoped>` 區塊，然後從 `FieldMappingView.vue` 刪掉這段。

不要改任何數值。這幾條規則彼此沒有跨區塊共用，直接整段搬即可。

- [ ] **Step 3: 頁面改用元件**

在 `FieldMappingView.vue` 的 template，把這段（現行 141-155 行）：

```vue
        <div v-if="!loading && previewColumns.length" class="preview-block">
          <div class="preview-title">資料預覽（前 {{ previewRows.length }} 筆）</div>
          <div class="preview-scroll">
            <table class="preview-table">
              <thead>
                <tr><th v-for="col in previewColumns" :key="col">{{ col }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in previewRows" :key="i">
                  <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
```

換成：

```vue
        <DatasetPreview
          v-if="!loading && previewColumns.length"
          :columns="previewColumns"
          :rows="previewRows"
        />
```

並在 script 區加入 import（放在既有的 `CustomSelect` import 附近，維持 import 的字母排序）：

```ts
  import DatasetPreview from '@/components/hub/fieldMapping/DatasetPreview.vue'
```

- [ ] **Step 4: 建置與型別檢查**

Run: `cd frontend && npm run build`
Expected: 成功，無錯誤（結尾的 chunk size 警告是既有的，與本次改動無關）

- [ ] **Step 5: Lint 新檔案**

Run: `cd frontend && npx eslint src/components/hub/fieldMapping/DatasetPreview.vue`
Expected: 零錯誤零警告

- [ ] **Step 6: 人工檢查**

`npm run dev`（或 `docker compose up -d`），登入後開啟任一有資料集的專案的欄位對齊頁（`/hub/projects/<id>/mapping`）。確認：
- 「資料預覽（前 N 筆）」區塊仍然顯示，欄位標題與內容跟改動前一致
- 表格外觀（邊框、底色、字級）沒有變化
- 欄位很多時仍可水平捲動

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/hub/fieldMapping/DatasetPreview.vue frontend/src/views/hub/FieldMappingView.vue
git commit -m "refactor: extract DatasetPreview from FieldMappingView"
```

---

### Task 2: MappingChatPanel 元件

**Files:**
- Create: `frontend/src/components/hub/fieldMapping/MappingChatPanel.vue`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: Task 1 建立的 `components/hub/fieldMapping/` 目錄
- Produces: `MappingChatPanel` 元件，props `{ history: ChatMessage[], pending: boolean, available: boolean, loading: boolean }`，emits `send: [message: string]`。頁面的 `sendMessage` 簽章改為 `async function sendMessage (message: string): Promise<void>`

- [ ] **Step 1: 建立元件檔案**

Create `frontend/src/components/hub/fieldMapping/MappingChatPanel.vue`：

```vue
<template>
  <aside class="mapping-chat">
    <div class="chat-head">
      <div class="chat-head-icon">
        <v-icon icon="mdi-chat-processing-outline" size="18" />
      </div>
      <span>AI 助理</span>
    </div>

    <div v-if="loading" class="chat-offline">
      AI 助理需等待欄位對應結果產生後才能使用。
    </div>
    <div v-else-if="!available" class="chat-offline">
      AI 建議暫時無法使用，可用左側下拉選單手動對應。
    </div>

    <div ref="scrollRef" class="chat-body">
      <div v-if="!loading && available" class="chat-bubble chat-bubble--assistant chat-bubble--opener">
        {{ CHAT_OPENER }}
      </div>
      <div
        v-for="(message, i) in history"
        :key="i"
        class="chat-bubble"
        :class="`chat-bubble--${message.role}`"
      >
        {{ message.content }}
      </div>
      <div v-if="pending" class="chat-bubble chat-bubble--assistant chat-bubble--pending">
        思考中…
      </div>
    </div>

    <form class="chat-input" @submit.prevent="submit">
      <textarea
        ref="fieldRef"
        v-model="draft"
        class="chat-field"
        :disabled="!available || pending"
        placeholder="例如：Braden 分數是 braden_total"
        rows="1"
        @input="autoGrow"
        @keydown="onFieldKeydown"
      />
      <button
        class="chat-send"
        type="submit"
        :disabled="!available || pending || !draft.trim()"
      >
        送出
      </button>
    </form>
  </aside>
</template>

<script setup lang="ts">
  import type { ChatMessage } from '@/types/fieldMapping'
  import { nextTick, ref, watch } from 'vue'

  const props = defineProps<{
    history: ChatMessage[]
    pending: boolean
    available: boolean
    loading: boolean
  }>()

  const emit = defineEmits<{
    send: [message: string]
  }>()

  // 開場白：不進 history，不存草稿
  const CHAT_OPENER = '我可以協助調整左側的欄位對應，請直接以文字說明您的需求，'
    + '例如「年齡對應到 pt_age」或「BMI 這一欄資料表中沒有」。'

  // 約 5 行，超過就內部捲動
  const CHAT_FIELD_MAX_HEIGHT = 118

  const draft = ref('')
  const scrollRef = ref<HTMLElement | null>(null)
  const fieldRef = ref<HTMLTextAreaElement | null>(null)

  function autoGrow (): void {
    const el = fieldRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, CHAT_FIELD_MAX_HEIGHT)}px`
    // 沒滿高度就不留 scrollbar，一行字的時候才不會看起來怪怪的
    el.style.overflowY = el.scrollHeight > CHAT_FIELD_MAX_HEIGHT ? 'auto' : 'hidden'
  }

  function onFieldKeydown (event: KeyboardEvent): void {
    if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
    event.preventDefault()
    submit()
  }

  function submit (): void {
    const message = draft.value.trim()
    if (!message || props.pending) return
    draft.value = ''
    if (fieldRef.value) {
      fieldRef.value.style.height = 'auto'
      fieldRef.value.style.overflowY = 'hidden'
    }
    emit('send', message)
  }

  // 訊息數或「思考中」狀態一變就捲到最新一則。
  // 原本由頁面在送出前後各呼叫一次，改由面板監看自己的 props，行為一樣
  watch(
    [() => props.history.length, () => props.pending],
    async () => {
      await nextTick()
      if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    },
  )
</script>

<style scoped>
</style>
```

- [ ] **Step 2: 把對話面板的 CSS 搬進元件**

把 `FieldMappingView.vue` 第 1245-1371 行（`.mapping-chat`、`.chat-head-icon`、`.chat-head`、`.chat-offline`、`.chat-body`、`.chat-bubble` 及其四個修飾子、`.chat-input`、`.chat-field`、`.chat-field:disabled`、`.chat-send`、`.chat-send:disabled`）**原封不動**剪下貼進 `<style scoped>`，並從 `FieldMappingView.vue` 刪掉這段。

- [ ] **Step 3: 處理跨元件共用的 hover 規則（容易漏掉，會讓送出鈕 hover 失效）**

`FieldMappingView.vue` 第 1235-1238 行是一條**兩個元件共用**的規則：

```css
  .confirm-btn:hover:not(:disabled),
  .chat-send:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }
```

它夾在 `.confirm-btn`（1219）與 `.confirm-btn:disabled`（1240）中間，不在上一步搬走的連續區段裡。必須拆成兩條：

在 `FieldMappingView.vue` 把上面那條改成只留 confirm-btn：

```css
  .confirm-btn:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }
```

在 `MappingChatPanel.vue` 的 `<style scoped>` 內，`.chat-send` 規則後面加上：

```css
  .chat-send:hover:not(:disabled) {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }
```

- [ ] **Step 4: 頁面改用元件**

在 `FieldMappingView.vue` 的 template，把整個 `<aside class="mapping-chat">...</aside>`（現行 170-221 行，含上方的 `<!-- 右：AI 對話 -->` 註解）換成：

```vue
      <!-- 右：AI 對話 -->
      <MappingChatPanel
        :available="aiAvailable"
        :history="chatHistory"
        :loading="loading"
        :pending="chatPending"
        @send="sendMessage"
      />
```

script 區加入 import：

```ts
  import MappingChatPanel from '@/components/hub/fieldMapping/MappingChatPanel.vue'
```

- [ ] **Step 5: 頁面移除已搬走的對話狀態與行為**

從 `FieldMappingView.vue` 的 script 刪掉這些（都已移入元件）：

- `CHAT_OPENER` 常數（現行 258-260）
- `CHAT_FIELD_MAX_HEIGHT` 常數（現行 304）
- `chatDraft`、`chatScroll`、`chatFieldRef` 三個 ref（現行 297、299、300）
- `autoGrowChatField` 函式（現行 306-313）
- `onChatFieldKeydown` 函式（現行 315-319）
- `scrollChatToBottom` 函式（現行 706-709）

保留 `chatHistory`、`chatPending`（頁面仍持有這兩個狀態並傳給元件）。

把 `sendMessage` 改成接收訊息參數，並刪掉已由元件負責的三件事（清空草稿、重設 textarea 高度、捲到底）：

```ts
  async function sendMessage (message: string): Promise<void> {
    chatHistory.value.push({ role: 'user', content: message })
    chatPending.value = true

    try {
      const { actions, reply } = await refineFieldMapping({
        mappingState: {
          total_required: items.value.length,
          matched_count: confirmedCount.value,
          mapping_status: items.value,
        },
        userColumns: userColumns.value,
        userMessage: message,
        chatHistory: chatHistory.value.slice(0, -1),
      })
      if (actions.length > 0) pushHistory()
      const changed = applyActions(actions)
      for (const variable of changed) flash(variable)
      if (changed.length > 0) saveDraft()
      chatHistory.value.push({ role: 'assistant', content: reply })
    } catch (error) {
      chatHistory.value.push({
        role: 'assistant',
        content: error instanceof Error ? error.message : 'AI 目前無法回應，請改用下拉選單。',
      })
    } finally {
      chatPending.value = false
      // 前綴 mapping- 才不會和 ResultView 的聊天撞 key。
      // 那組函式的型別是 { role, text }，這裡是 { role, content }，純本地暫存所以轉型即可。
      saveChatHistoryToStorage(
        `mapping-${projectId.value}`,
        chatHistory.value as unknown as import('@/api/resultAnalysis').ChatMessage[],
      )
    }
  }
```

- [ ] **Step 6: 清掉不再使用的 import**

`nextTick` 原本只被 `scrollChatToBottom` 使用，該函式已刪除。確認後從 `FieldMappingView.vue` 第 234 行的 vue import 移除 `nextTick`：

Run: `cd frontend && grep -n "nextTick" src/views/hub/FieldMappingView.vue`
Expected: 只剩 import 那一行（或已無結果）。若只剩 import 行，把它從 import 清單移除，改成：

```ts
  import { computed, onBeforeUnmount, onMounted, ref, toRaw } from 'vue'
```

- [ ] **Step 7: 建置與 lint**

Run: `cd frontend && npm run build && npx eslint src/components/hub/fieldMapping/MappingChatPanel.vue`
Expected: build 成功；eslint 零錯誤

- [ ] **Step 8: 人工檢查**

開啟欄位對齊頁，確認：
- 對話面板外觀與位置跟改動前一致（頭部圖示、訊息泡泡顏色、輸入框）
- 開場白仍顯示
- 打字時輸入框會自動長高，超過約 5 行後改成內部捲動
- Enter 送出、Shift+Enter 換行；中文輸入法組字中按 Enter 不會誤送
- **送出後輸入框清空並回到單行高度**
- **送出後訊息捲到最新一則；AI 回覆進來時也會捲到底**
- 送出鈕 hover 時顏色變深（驗證 Step 3 的規則拆分沒做錯）
- AI 回覆後左側表格有正確套用建議
- 資料還在載入時顯示「AI 助理需等待欄位對應結果產生後才能使用」；AI 不可用時顯示離線提示且輸入框不可打字

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/hub/fieldMapping/MappingChatPanel.vue frontend/src/views/hub/FieldMappingView.vue
git commit -m "refactor: extract MappingChatPanel from FieldMappingView"
```

---

### Task 3: MappingTable 元件

最大的一塊。含 `SKIP_VALUE` 移到共用型別檔（page 與表格都需要）。

**Files:**
- Create: `frontend/src/components/hub/fieldMapping/MappingTable.vue`
- Modify: `frontend/src/types/fieldMapping.ts`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: Task 1、Task 2 建立的元件目錄
- Produces: `SKIP_VALUE` 常數（從 `@/types/fieldMapping` 匯出，值為 `'__skip__'`）；`MappingTable` 元件，props `{ items: MappingItem[], userColumns: UserColumn[], targetName: string, flashed: Set<string> }`，emits `'update:selection': [item: MappingItem, value: string]`、`'confirm': [item: MappingItem]`、`'unconfirm': [item: MappingItem]`

- [ ] **Step 1: `SKIP_VALUE` 移到型別檔**

在 `frontend/src/types/fieldMapping.ts` 檔尾加上：

```ts
/**
 * 下拉選單「資料表中沒有此變數」的哨兵值。
 * 選到它代表使用者明確表示略過，狀態會變成 SKIPPED。
 */
export const SKIP_VALUE = '__skip__'
```

從 `FieldMappingView.vue` 刪掉區域的 `const SKIP_VALUE = '__skip__'`（現行 248 行），改成從型別檔 import（併入既有的 type import 之外，另加一行值的 import）：

```ts
  import { SKIP_VALUE } from '@/types/fieldMapping'
```

- [ ] **Step 2: 建立元件檔案**

Create `frontend/src/components/hub/fieldMapping/MappingTable.vue`：

```vue
<template>
  <div class="mapping-scroll">
    <table class="mapping-table">
      <thead>
        <tr>
          <th class="col-var">論文變數</th>
          <th class="col-col">你的欄位</th>
          <th class="col-status">狀態</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="item in sortedItems"
          :key="item.paper_variable"
          :class="{ 'row-flash': flashed.has(item.paper_variable) }"
        >
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
          <td class="col-col">
            <CustomSelect
              :aria-label="`${item.paper_variable} 對應到的資料表欄位`"
              :highlight="item.status === 'UNMATCHED'"
              :model-value="item.matched_user_column ?? selectionKey(item)"
              :options="optionsFor(item)"
              placeholder="請選擇"
              @update:model-value="value => emit('update:selection', item, value)"
            />
            <div v-if="item.sample_values.length" class="col-samples">
              {{ item.sample_values.slice(0, 3).join('、') }}
            </div>
            <!-- 配不出來時給幾個最接近的讓使用者一鍵選，不必自己在幾十個欄位裡翻 -->
            <div v-if="item.status === 'UNMATCHED' && item.candidate_columns.length" class="col-candidates">
              <span class="candidates-label">可能是</span>
              <button
                v-for="name in item.candidate_columns"
                :key="name"
                class="candidate-chip"
                :title="`選擇 ${name}`"
                type="button"
                @click="emit('update:selection', item, name)"
              >
                {{ name }}
              </button>
            </div>
          </td>
          <td class="col-status">
            <div class="status-cell">
              <!-- 用 v-tooltip 而非 CSS 絕對定位：外層 .mapping-scroll 有 overflow，
                   自製的提示會被裁掉，v-tooltip 會 teleport 出去 -->
              <v-tooltip
                content-class="status-tooltip"
                location="bottom end"
                max-width="210"
                :text="STATUS_HINT[item.status]"
              >
                <template #activator="{ props: tooltipProps }">
                  <span
                    v-bind="tooltipProps"
                    class="status-chip"
                    :class="`status-chip--${item.status.toLowerCase()}`"
                    tabindex="0"
                  >
                    {{ STATUS_LABEL[item.status] }}
                  </span>
                </template>
              </v-tooltip>
              <button
                v-if="item.status === 'NEEDS_REVIEW'"
                :aria-label="`${item.paper_variable}：對應正確，標記為已確認`"
                class="check-btn"
                title="對應正確，標記為已確認"
                type="button"
                @click="emit('confirm', item)"
              >
                <v-icon icon="mdi-check" size="16" />
              </button>
              <button
                v-else-if="item.status === 'CONFIRMED'"
                :aria-label="`${item.paper_variable}：取消確認`"
                class="undo-btn"
                title="取消確認"
                type="button"
                @click="emit('unconfirm', item)"
              >
                <v-icon icon="mdi-undo-variant" size="14" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
  import type { MappingItem, UserColumn } from '@/types/fieldMapping'
  import { computed } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import { SKIP_VALUE } from '@/types/fieldMapping'

  const props = defineProps<{
    items: MappingItem[]
    userColumns: UserColumn[]
    targetName: string
    flashed: Set<string>
  }>()

  const emit = defineEmits<{
    'update:selection': [item: MappingItem, value: string]
    'confirm': [item: MappingItem]
    'unconfirm': [item: MappingItem]
  }>()

  const STATUS_LABEL: Record<string, string> = {
    CONFIRMED: '已確認',
    AUTO_MATCHED: '已對應',
    NEEDS_REVIEW: '待確認',
    UNMATCHED: '未對應',
    SKIPPED: '不使用',
  }

  // 滑過標籤時顯示。用一般說法，避免「信心度」這類系統內部用語
  const STATUS_HINT: Record<string, string> = {
    CONFIRMED: '您已確認此對應正確。如需修改，請點選右側的復原按鈕。',
    AUTO_MATCHED: '欄位名稱與資料內容皆相符，可直接使用。',
    NEEDS_REVIEW: '兩邊名稱不同，此為 AI 依語意提供的建議對應，請確認無誤後點選右側的勾選按鈕。',
    UNMATCHED: '資料表中沒有相符的欄位，請由左側選單自行指定。',
    SKIPPED: '您已指定資料表中沒有此變數，執行時將會略過。',
  }

  function isTarget (item: MappingItem): boolean {
    return item.paper_variable === props.targetName
  }

  // target 永遠排最前面：它配錯的話整個實驗都白做，不能混在幾十列裡被滑過去
  const sortedItems = computed(() => {
    const list = [...props.items]
    list.sort((a, b) => Number(isTarget(b)) - Number(isTarget(a)))
    return list
  })

  function selectionKey (item: MappingItem): string {
    return item.status === 'SKIPPED' ? SKIP_VALUE : ''
  }

  function optionsFor (item: MappingItem) {
    const taken = new Map<string, string>()
    for (const other of props.items) {
      if (other.paper_variable !== item.paper_variable && other.matched_user_column) {
        taken.set(other.matched_user_column, other.paper_variable)
      }
    }
    const options = props.userColumns.map(column => ({
      value: column.name,
      label: column.name,
      hint: taken.has(column.name) ? `已對應至 ${taken.get(column.name)}` : undefined,
    }))
    // target 一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '資料表中沒有此變數', hint: undefined })
    }
    return options
  }
</script>

<style scoped>
</style>

<!-- v-tooltip 會 teleport 到元件外，scoped 樣式管不到，所以另開一個全域區塊 -->
<style>
  .status-tooltip {
    padding: 7px 10px !important;
    font-size: 12px !important;
    line-height: 1.55 !important;
  }
</style>
```

注意 template 裡 v-tooltip 的 activator slot：原本是 `#activator="{ props }"`，在元件內會與 `defineProps` 產生的 `props` 變數同名，因此改名為 `tooltipProps`（`v-bind="tooltipProps"`）。行為不變。

- [ ] **Step 3: 把表格的 CSS 搬進元件**

把 `FieldMappingView.vue` 第 943-1152 行**原封不動**剪下貼進元件的 `<style scoped>`（第一個 style 區塊），並從 `FieldMappingView.vue` 刪掉這段。這段包含：`.mapping-scroll`、`.mapping-table`、`.mapping-table th`、`.mapping-table td`、`.col-status`、`.col-col`、`.target-badge`、`.var-name`、`.var-type`、`.col-samples`、`.col-candidates`、`.candidates-label`、`.candidate-chip` 及其 hover/focus、`.status-chip` 及五個狀態修飾子與 `[tabindex]` 規則、`.status-cell`、`.check-btn` 及 hover、`.check-btn:focus-visible, .undo-btn:focus-visible`、`.check-btn::after, .undo-btn::after`、`.undo-btn` 及 hover、`.row-flash`、`@keyframes row-flash`。

- [ ] **Step 4: 刪掉頁面裡的全域 tooltip 區塊**

`FieldMappingView.vue` 檔尾的第二個 `<style>` 區塊（現行 1374-1381，含上方註解）已在 Step 2 複製進元件，從頁面刪掉整段。

- [ ] **Step 5: 拆開 reduced-motion 的共用規則（容易漏掉）**

`FieldMappingView.vue` 第 1154-1164 行的 media query 同時服務兩邊：

```css
  @media (prefers-reduced-motion: reduce) {
    .row-flash {
      animation: none;
      background: #fef9c3;
    }

    .confirm-all-btn,
    .check-btn {
      transition: none;
    }
  }
```

`.row-flash` 與 `.check-btn` 屬於表格，`.confirm-all-btn` 屬於頁面標題列。拆成兩份。

在 `MappingTable.vue` 的 `<style scoped>` 末端加上：

```css
  @media (prefers-reduced-motion: reduce) {
    .row-flash {
      animation: none;
      background: #fef9c3;
    }

    .check-btn {
      transition: none;
    }
  }
```

在 `FieldMappingView.vue` 把原本那段整個換成：

```css
  @media (prefers-reduced-motion: reduce) {
    .confirm-all-btn {
      transition: none;
    }
  }
```

- [ ] **Step 6: 頁面改用元件**

在 `FieldMappingView.vue` 的 template，把 `<div v-else class="mapping-scroll">` 到對應 `</div>`（現行 41-139 行，即整個表格）換成：

```vue
        <MappingTable
          v-else
          :flashed="flashed"
          :items="items"
          :target-name="targetName"
          :user-columns="userColumns"
          @confirm="confirmRow"
          @unconfirm="unconfirmRow"
          @update:selection="applySelection"
        />
```

script 區加入 import：

```ts
  import MappingTable from '@/components/hub/fieldMapping/MappingTable.vue'
```

- [ ] **Step 7: 頁面移除已搬走的表格邏輯**

從 `FieldMappingView.vue` 的 script 刪掉（都已移入元件）：

- `STATUS_LABEL` 常數（現行 250-256）
- `STATUS_HINT` 常數（現行 263-269）
- `isTarget` 函式（現行 327-329）
- `sortedItems` computed（現行 332-336）
- `selectionKey` 函式（現行 352-354）
- `optionsFor` 函式（現行 356-373）

保留 `items`、`userColumns`、`targetName`、`flashed`、`applySelection`、`confirmRow`、`unconfirmRow`、`flash`——這些頁面仍需要。

注意 `applySelection`、`confirmRow`、`unconfirmRow` 的簽章不變，可直接當 emit handler 使用；`applySelection` 內部仍使用 `SKIP_VALUE`（Step 1 已改為從型別檔 import）。

`CustomSelect` 的 import 現在只有元件用得到——確認頁面已無使用後移除：

Run: `cd frontend && grep -n "CustomSelect" src/views/hub/FieldMappingView.vue`
Expected: 只剩 import 那一行。確認後把該行從 `FieldMappingView.vue` 刪除。

- [ ] **Step 8: 建置與 lint**

Run: `cd frontend && npm run build && npx eslint src/components/hub/fieldMapping/MappingTable.vue src/types/fieldMapping.ts`
Expected: build 成功；eslint 零錯誤

- [ ] **Step 9: 人工檢查**

開啟欄位對齊頁，確認：
- 表格外觀完全一致（表頭、列高、狀態徽章顏色、星號目標標記）
- 預測目標那一列排在最前面
- 下拉選單可正常展開，已被別列佔用的欄位顯示「已對應至 X」提示
- **選一個已被別列使用的欄位 → 該列變已確認、原持有者退回未對應且閃爍黃底**
- 非目標變數的下拉最後有「資料表中沒有此變數」選項；目標變數**沒有**這個選項
- 選「資料表中沒有此變數」→ 狀態變「不使用」
- 未對應列的「可能是」候選 chip 可一鍵選取
- 待確認列的勾選按鈕、已確認列的復原按鈕都正常
- **滑鼠移到狀態徽章上，tooltip 正常顯示且不被表格裁切**（驗證 Step 4 的全域樣式有跟著搬）
- 開啟系統的「減少動態效果」後，被改動的列不再有動畫但仍有黃色底提示（驗證 Step 5）

- [ ] **Step 10: Commit**

```bash
git add frontend/src/components/hub/fieldMapping/MappingTable.vue frontend/src/types/fieldMapping.ts frontend/src/views/hub/FieldMappingView.vue
git commit -m "refactor: extract MappingTable from FieldMappingView"
```

---

### Task 4: useMappingDraft composable

**Files:**
- Create: `frontend/src/composables/fieldMapping/useMappingDraft.ts`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: `MappingItem`、`UserColumn` 型別
- Produces: `useMappingDraft(deps)` → `{ saveDraft: () => void, loadDraft: () => boolean, clearDraft: () => void }`，deps 形狀為 `{ projectId: Ref<number>, items: Ref<MappingItem[]>, locked: Ref<Set<string>>, aiAvailable: Ref<boolean>, userColumns: Ref<UserColumn[]> }`

- [ ] **Step 1: 建立 composable**

Create `frontend/src/composables/fieldMapping/useMappingDraft.ts`：

```ts
import type { Ref } from 'vue'
import type { MappingItem, UserColumn } from '@/types/fieldMapping'
import { computed } from 'vue'

/**
 * 存編輯中的草稿。沒有它的話重新整理會把改過的全部沖掉，還會再打一次 Gemini。
 * 真正的結果是按下「確認並執行」才寫進資料庫。
 */
export function useMappingDraft (deps: {
  projectId: Ref<number>
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  aiAvailable: Ref<boolean>
  userColumns: Ref<UserColumn[]>
}) {
  const draftKey = computed(() => `datamind_field_mapping_draft_${deps.projectId.value}`)

  function columnSignature (): string {
    return deps.userColumns.value.map(c => c.name).join('|')
  }

  function saveDraft (): void {
    if (!deps.projectId.value) return
    try {
      localStorage.setItem(draftKey.value, JSON.stringify({
        columns: columnSignature(),
        items: deps.items.value,
        locked: [...deps.locked.value],
        aiAvailable: deps.aiAvailable.value,
      }))
    } catch (error) {
      console.warn('無法保存欄位對映草稿', error)
    }
  }

  function clearDraft (): void {
    localStorage.removeItem(draftKey.value)
  }

  function loadDraft (): boolean {
    try {
      const raw = localStorage.getItem(draftKey.value)
      if (!raw) return false
      const saved = JSON.parse(raw) as {
        columns?: string
        items?: MappingItem[]
        locked?: string[]
        aiAvailable?: boolean
      }
      // 換了資料集就不能沿用舊草稿，裡面的欄位名已經對不上了
      if (saved.columns !== columnSignature()) {
        clearDraft()
        return false
      }
      if (!Array.isArray(saved.items) || saved.items.length === 0) return false
      deps.items.value = saved.items
      deps.locked.value = new Set<string>(saved.locked)
      // 沿用當初的可用狀態：寫死 true 的話，Gemini 掛掉時重整會讓離線提示消失、
      // 輸入框又變成可打，送出才發現還是不通
      deps.aiAvailable.value = saved.aiAvailable ?? true
      return true
    } catch {
      localStorage.removeItem(draftKey.value)
      return false
    }
  }

  return { saveDraft, loadDraft, clearDraft }
}
```

注意 `clearDraft` 的定義位置移到 `loadDraft` 之前（`loadDraft` 內部會呼叫它）。原始檔是靠函式提升（hoisting）運作，這裡改成宣告在前，行為相同但更好讀。

- [ ] **Step 2: 頁面改用 composable**

從 `FieldMappingView.vue` 刪掉 `draftKey` computed（現行 278）、`saveDraft`、`loadDraft`、`columnSignature`、`clearDraft` 四個函式（現行 508-560）。

在 script 內、所有 ref 宣告之後（`aiAvailable`、`userColumns`、`items`、`locked`、`projectId` 都必須已經宣告）加入：

```ts
  const { saveDraft, loadDraft, clearDraft } = useMappingDraft({
    projectId,
    items,
    locked,
    aiAvailable,
    userColumns,
  })
```

並加入 import：

```ts
  import { useMappingDraft } from '@/composables/fieldMapping/useMappingDraft'
```

其餘 `saveDraft()` / `loadDraft()` / `clearDraft()` 的呼叫點全部不動（現行 382、399、448、462、483、505、757、820、828）。

- [ ] **Step 3: 建置與 lint**

Run: `cd frontend && npm run build && npx eslint src/composables/fieldMapping/useMappingDraft.ts`
Expected: build 成功；eslint 零錯誤

- [ ] **Step 4: 人工檢查**

- 在欄位對齊頁改幾個對應（下拉選欄位、按確認）→ **重新整理頁面，改過的內容還在**，且沒有重新觸發自動配對
- 回到專案列表，換一個**使用不同資料集**的專案進入欄位對齊 → 該專案顯示自己的配對結果，不會誤用前一個專案的草稿
- 完成一次「確認並執行」→ 再回到該頁時草稿已清除

- [ ] **Step 5: Commit**

```bash
git add frontend/src/composables/fieldMapping/useMappingDraft.ts frontend/src/views/hub/FieldMappingView.vue
git commit -m "refactor: extract useMappingDraft from FieldMappingView"
```

---

### Task 5: useMappingHistory composable

**Files:**
- Create: `frontend/src/composables/fieldMapping/useMappingHistory.ts`
- Modify: `frontend/src/views/hub/FieldMappingView.vue`

**Interfaces:**
- Consumes: Task 4 的 `saveDraft`（頁面在 `onRestore` 回呼裡使用）
- Produces: `useMappingHistory(deps)` → `{ pushHistory: () => void }`，deps 形狀為 `{ items: Ref<MappingItem[]>, locked: Ref<Set<string>>, onRestore: () => void }`

- [ ] **Step 1: 建立 composable**

Create `frontend/src/composables/fieldMapping/useMappingHistory.ts`：

```ts
import type { Ref } from 'vue'
import type { MappingItem } from '@/types/fieldMapping'
import { onBeforeUnmount, onMounted, ref, toRaw } from 'vue'

// Ctrl+Z 用的快照堆疊。上限避免使用者改很久之後記憶體一直長大
const MAX_UNDO = 50

interface Snapshot { items: MappingItem[], locked: string[] }

/**
 * 對映表的復原/重做。鍵盤監聽也包在裡面，所以頁面只需要在改動前呼叫 pushHistory()。
 *
 * @param deps.onRestore 還原之後要做的事（例如清掉錯誤訊息、存草稿）
 */
export function useMappingHistory (deps: {
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  onRestore: () => void
}) {
  const undoStack = ref<Snapshot[]>([])
  const redoStack = ref<Snapshot[]>([])

  /**
   * 改動前先存快照。沒有復原的話，點錯一步只能整頁重跑。
   *
   * locked 一定要跟著存：只還原 items 的話，復原後那一列看起來回到未對應，
   * 但它還留在 locked 裡，之後所有 AI 建議都會被靜默忽略，而聊天仍回「已更新」。
   */
  function snapshot (): Snapshot {
    return { items: structuredClone(toRaw(deps.items.value)), locked: [...deps.locked.value] }
  }

  function restore (snap: Snapshot): void {
    deps.items.value = snap.items
    deps.locked.value = new Set(snap.locked)
    deps.onRestore()
  }

  function pushHistory (): void {
    undoStack.value.push(snapshot())
    if (undoStack.value.length > MAX_UNDO) undoStack.value.shift()
    // 做了新動作，原本能重做的那條分支就失效了
    redoStack.value = []
  }

  function undo (): void {
    const previous = undoStack.value.pop()
    if (!previous) return
    redoStack.value.push(snapshot())
    restore(previous)
  }

  function redo (): void {
    const next = redoStack.value.pop()
    if (!next) return
    undoStack.value.push(snapshot())
    restore(next)
  }

  /** 焦點在輸入框時不攔截：那時使用者要復原的是自己打的字。 */
  function onKeydown (event: KeyboardEvent): void {
    if (!(event.metaKey || event.ctrlKey)) return

    // 重做的按法各家不同：Mac 是 ⌘⇧Z，Windows 上 Ctrl+Y 與 Ctrl+Shift+Z 都常見，三種都收
    const key = event.key.toLowerCase()
    const isRedo = (key === 'z' && event.shiftKey) || key === 'y'
    const isUndo = key === 'z' && !event.shiftKey
    if (!isRedo && !isUndo) return

    const target = event.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return

    event.preventDefault()
    if (isRedo) redo()
    else undo()
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

  return { pushHistory }
}
```

- [ ] **Step 2: 頁面改用 composable**

從 `FieldMappingView.vue` 刪掉：`MAX_UNDO` 常數、`Snapshot` interface、`undoStack`/`redoStack` 兩個 ref（現行 321-325）、`snapshot`、`restore`、`pushHistory`、`undo`、`redo`（現行 385-421）、`onKeydown`（現行 423-441），以及註冊鍵盤監聽的那兩行 lifecycle（現行 769-770）。

在 `useMappingDraft` 的呼叫之後加入（順序重要：`onRestore` 用到 `saveDraft`）：

```ts
  const { pushHistory } = useMappingHistory({
    items,
    locked,
    // 還原後沿用原本 restore 的收尾：清掉舊錯誤、把還原結果存回草稿
    onRestore: () => {
      saveError.value = ''
      saveDraft()
    },
  })
```

並加入 import：

```ts
  import { useMappingHistory } from '@/composables/fieldMapping/useMappingHistory'
```

其餘 `pushHistory()` 的呼叫點全部不動（現行 378、445、454、473、684）。

- [ ] **Step 3: 清掉不再使用的 import**

`toRaw` 原本只被 `snapshot` 使用、`onBeforeUnmount` 只被鍵盤監聽使用，兩者都已移入 composable。

Run: `cd frontend && grep -n "toRaw\|onBeforeUnmount" src/views/hub/FieldMappingView.vue`
Expected: 只剩 import 那一行。確認後把 vue 的 import 改成：

```ts
  import { computed, onMounted, ref } from 'vue'
```

- [ ] **Step 4: 建置與 lint**

Run: `cd frontend && npm run build && npx eslint src/composables/fieldMapping/useMappingHistory.ts`
Expected: build 成功；eslint 零錯誤

- [ ] **Step 5: 人工檢查**

- 改幾個對應後按 **Ctrl+Z**（Mac 用 ⌘+Z）→ 回到上一步
- 按 **Ctrl+Shift+Z** 與 **Ctrl+Y** → 都能重做
- **游標點進右側 AI 對話輸入框、打幾個字後按 Ctrl+Z** → 復原的是輸入框裡的文字，左側表格不受影響
- **復原一個「曾被 AI 改過的列」，然後再請 AI 改同一個變數** → AI 的建議能正常套用（驗證 `locked` 有跟著快照還原；若 locked 沒還原，AI 會回「已更新」但表格沒動）
- 離開此頁再回來 → 不會出現重複的鍵盤監聽（連按 Ctrl+Z 一次只回一步）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/composables/fieldMapping/useMappingHistory.ts frontend/src/views/hub/FieldMappingView.vue
git commit -m "refactor: extract useMappingHistory from FieldMappingView"
```

---

### Task 6: 全案驗收

**Files:** 無新增/修改，純驗證（若發現問題才回頭修）

**Interfaces:**
- Consumes: Task 1-5 的全部成果
- Produces: 無（終點任務）

- [ ] **Step 1: 確認檔案大小達成目標**

Run:
```bash
cd frontend && wc -l src/views/hub/FieldMappingView.vue \
  src/components/hub/fieldMapping/*.vue \
  src/composables/fieldMapping/*.ts
```
Expected: `FieldMappingView.vue` 約 450-500 行（spec 的預估值，不是硬性門檻——重點是它只剩協調職責）。若明顯超出（例如仍有 700 行以上），檢查是否有該搬走的區塊沒搬乾淨。

- [ ] **Step 2: 確認頁面已無殘留的子元件細節**

Run:
```bash
cd frontend && grep -nE "STATUS_LABEL|STATUS_HINT|optionsFor|sortedItems|chatDraft|CHAT_OPENER|undoStack|draftKey|columnSignature" src/views/hub/FieldMappingView.vue
```
Expected: 無任何結果（全都已移入元件或 composable）

- [ ] **Step 3: 完整建置與型別檢查**

Run: `cd frontend && npm run build`
Expected: 成功，無錯誤

- [ ] **Step 4: Lint 全部新檔案與改過的頁面**

Run:
```bash
cd frontend && npx eslint src/components/hub/fieldMapping/ src/composables/fieldMapping/ src/types/fieldMapping.ts src/views/hub/FieldMappingView.vue
```
Expected: 新檔案零錯誤。`FieldMappingView.vue` 本來就有既有的 lint 問題（改動前基準為 8 errors / 96 warnings，且多為 `vue/html-indent` 之類的既有風格問題）——確認**沒有新增**錯誤即可，數量應該因為程式碼變少而下降。

- [ ] **Step 5: 走完 spec 的完整人工檢查清單**

依 `docs/superpowers/specs/2026-08-11-field-mapping-view-refactor-design.md` 的「驗收」章節逐項確認：

- [ ] 下拉選單指定欄位 → 該列變「已確認」；若該欄位原屬另一列，原持有者退回「未對應」且閃爍
- [ ] 下拉選「資料表中沒有此變數」→ 該列變「不使用」
- [ ] 「可能是」候選 chip 一鍵選取
- [ ] 待確認列的勾選按鈕 → 變已確認；已確認列的復原按鈕 → 退回待確認
- [ ] 「全部確認」一次處理所有待確認列
- [ ] Ctrl+Z 復原、Ctrl+Shift+Z 與 Ctrl+Y 重做
- [ ] 焦點在聊天輸入框時打 Ctrl+Z 不會觸發表格復原
- [ ] 復原一個被 AI 改過的列後，該列能再次接受 AI 建議
- [ ] AI 對話送出訊息 → 套用建議、被改動的列閃爍；使用者手動確認過的列不被覆蓋
- [ ] 送出後輸入框清空並回到單行高度、訊息捲到最新一則
- [ ] 重新整理頁面 → 編輯中的對映還在
- [ ] 換一個資料集 → 舊草稿失效，重新自動配對
- [ ] 「確認並執行」→ 依對映改寫表頭後跳轉 workflow

- [ ] **Step 6: Commit（僅在前面步驟有修正時需要）**

若驗收過程沒有發現問題，這個任務不需要額外 commit，直接標記完成。若有修正，比照對應任務的 commit message 慣例個別提交。
