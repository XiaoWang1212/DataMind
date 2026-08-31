<template>
  <section class="preprocessor-panel">
    <template v-if="pipeline.length > 0">
      <div class="step-count">共 {{ pipeline.length }} 個前處理步驟</div>

      <div class="steps">
        <div
          v-for="(step, index) in pipeline"
          :key="index"
          class="step-item"
        >
          <div class="step-header">
            <span class="step-index">{{ index + 1 }}</span>
            <span class="step-label">{{ preprocessStepLabel(step, datasetColumns) }}</span>
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
      尚未設定前處理步驟。
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { DatasetColumn } from '@/utils/workflow/fillNaColumnSplit'
  import { FILL_NA_STRATEGY_LABELS, preprocessStepLabel } from '@/utils/workflow/fillNaColumnSplit'

  withDefaults(defineProps<{
    pipeline: Array<Record<string, unknown>>
    datasetColumns?: DatasetColumn[]
  }>(), {
    datasetColumns: () => [],
  })

  // columns 常常是一長串欄位名稱，卡片裡放不下會跟其他卡片重疊，不顯示
  const HIDDEN_KEYS = new Set(['type', 'columns'])

  // 參數值照 Settings 面板的說法顯示，同一個步驟在兩邊看到的字才一致
  function paramValueLabel (step: Record<string, unknown>, key: string, value: unknown): string {
    if (step.type === 'fill_na' && key === 'strategy') {
      return FILL_NA_STRATEGY_LABELS[String(value)] ?? String(value)
    }
    return String(value)
  }

  function visibleParams (step: Record<string, unknown>): [string, string][] {
    return Object.entries(step)
      .filter(([k]) => !HIDDEN_KEYS.has(k))
      .map(([k, v]) => [k, paramValueLabel(step, k, v)])
  }
</script>

<style scoped>
  .preprocessor-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .steps {
    display: grid;
    /* 與 Settings 面板的步驟卡片同寬，兩邊看到的排版才一致 */
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
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
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
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
    background: color-mix(in oklab, var(--color-ink) 12%, var(--color-surface));
    color: var(--color-ink);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 500;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-text);
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
    border-top: 1px solid var(--color-border);
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    line-height: 1.35;
    color: var(--color-text);
    font-weight: 500;
    /* key 是 nowrap，值不給收縮空間的話會把整排撐出卡片 */
    min-width: 0;
  }

  .empty-hint {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
