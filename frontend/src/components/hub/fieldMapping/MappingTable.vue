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
            <v-tooltip
              v-if="item.definition"
              content-class="status-tooltip"
              location="bottom"
              max-width="240"
              :text="item.definition"
            >
              <template #activator="{ props: tooltipProps }">
                <v-icon
                  v-bind="tooltipProps"
                  class="var-info-icon"
                  icon="mdi-information-outline"
                  size="14"
                />
              </template>
            </v-tooltip>
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
            <div v-if="item.sample_values.length > 0" class="col-samples">
              {{ item.sample_values.slice(0, 3).join('、') }}
            </div>
            <!-- 配不出來時提供最接近的幾個欄位，讓使用者一鍵選取 -->
            <div v-if="item.status === 'UNMATCHED' && item.candidate_columns.length > 0" class="col-candidates">
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
              <!-- 用 v-tooltip 而非 CSS 定位，外層 .mapping-scroll 有 overflow 會裁掉自製的提示 -->
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

  // 滑過標籤時顯示，用一般說法避免「信心度」這類系統內部用語
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

  // 預測目標排最前面，避免混在其他變數中被忽略
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
    // 預測目標一定要有對應欄位，不提供「沒有這個變數」的選項
    if (!isTarget(item)) {
      options.push({ value: SKIP_VALUE, label: '資料表中沒有此變數', hint: undefined })
    }
    return options
  }
</script>

<style scoped>
  /* 下拉欄固定寬度，視窗窄時由表格自己捲，避免撐開整頁 */
  .mapping-scroll {
    overflow-x: auto;
  }

  .mapping-table {
    width: 100%;
    min-width: 520px;
    border-collapse: collapse;
    /* fixed 避免超長欄位名稱撐寬整欄，交給 .cs-label 做 ellipsis */
    table-layout: fixed;
    font-size: 13px;
  }

  .mapping-table th {
    padding: 8px 10px;
    text-align: left;
    font-weight: 600;
    color: var(--color-secondary);
    border-bottom: 1px solid #e8e8e8;
  }

  .mapping-table td {
    padding: 10px;
    border-bottom: 1px solid #f0f1f3;
    vertical-align: top;
  }

  /* 要放得下「待確認」標籤和勾選按鈕，避免標籤換行 */
  .col-status {
    width: 124px;
  }

  .col-col {
    width: 260px;
  }

  .target-badge {
    color: #d97706;
    margin-right: 4px;
  }

  .var-name {
    font-weight: 600;
    color: var(--color-text);
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

  .col-samples {
    margin-top: 4px;
    font-size: 11px;
    color: #94a3b8;
  }

  .col-candidates {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 6px;
  }

  .candidates-label {
    font-size: 11px;
    color: #94a3b8;
  }

  .candidate-chip {
    padding: 2px 8px;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    background: #fff;
    font-size: 11px;
    color: var(--color-secondary);
    cursor: pointer;
    transition: background-color 0.15s, border-color 0.15s;
  }

  .candidate-chip:hover {
    background: var(--color-background);
    border-color: var(--color-accent);
  }

  .candidate-chip:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .status-chip {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 600;
    /* 不換行，避免文字折行後圓角變成一顆球 */
    white-space: nowrap;
  }

  .status-chip--auto_matched {
    background: #dcfce7;
    color: #15803d;
  }

  .status-chip--needs_review {
    background: #fef3c7;
    color: #b45309;
  }

  .status-chip--unmatched {
    background: #fee2e2;
    color: #b91c1c;
  }

  .status-chip--skipped {
    background: #f0f1f3;
    color: var(--color-secondary);
  }

  .status-chip--confirmed {
    background: #dcfce7;
    color: #15803d;
  }

  .status-chip[tabindex] {
    cursor: help;
  }

  .status-chip[tabindex]:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  .status-cell {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  /* 標籤放在按鈕前面，讓使用者先知道狀態再決定是否確認 */
  .check-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 26px;
    height: 26px;
    border: 1px solid #cbd5e1;
    border-radius: 50%;
    background: #fff;
    color: #94a3b8;
    cursor: pointer;
    transition: background-color 0.15s, border-color 0.15s, color 0.15s;
  }

  /* 不用綠色，那是「已確認」的語意色，會跟旁邊的「待確認」混淆 */
  .check-btn:hover {
    background: #f0f1f3;
    border-color: #94a3b8;
    /* 從色票推導，不另外引入游離色碼 */
    color: color-mix(in oklab, var(--color-secondary) 60%, white);
  }

  .check-btn:focus-visible,
  .undo-btn:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }

  /* 視覺上 26px，用 ::after 把可點範圍撐到 40px 以符合觸控尺寸 */
  .check-btn::after,
  .undo-btn::after {
    content: '';
    position: absolute;
    inset: -7px;
  }

  .undo-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: none;
    border-radius: 7px;
    background: none;
    color: #cbd5e1;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
  }

  .undo-btn:hover {
    background: #f0f1f3;
    color: var(--color-secondary);
  }

  /* 讓被改動的列閃一下，提示改到哪些欄位 */
  .row-flash {
    animation: row-flash 2s ease-out;
  }

  @keyframes row-flash {
    0%, 40% { background: #fef9c3; }
    100% { background: transparent; }
  }

  /* 改用靜態底色取代動畫，避免動態效果造成不適又不損失提示 */
  @media (prefers-reduced-motion: reduce) {
    .row-flash {
      animation: none;
      background: #fef9c3;
    }

    .check-btn {
      transition: none;
    }
  }
</style>

<!-- v-tooltip 會 teleport 到元件外，scoped 樣式管不到，因此另開全域區塊 -->
<style>
  .status-tooltip {
    padding: 7px 10px !important;
    font-size: 12px !important;
    line-height: 1.55 !important;
  }
</style>
