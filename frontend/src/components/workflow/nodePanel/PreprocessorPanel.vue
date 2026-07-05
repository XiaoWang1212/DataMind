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
      尚未設定前處理步驟。
    </div>
  </section>
</template>

<script setup lang="ts">
  const props = defineProps<{
    pipeline: Array<Record<string, unknown>>
  }>()

  const STEP_LABELS: Record<string, string> = {
    fill_na: '缺值填補',
    knn_impute: 'KNN 缺值填補',
    iterative_impute: 'MICE 多重插補',
    normalize: 'Min-Max 正規化',
    standardize: 'Z-score 標準化',
    one_hot: 'One-Hot 編碼',
    label_encode: 'Label 編碼',
    drop_columns: '移除欄位',
    remove_outliers_iqr: 'IQR 異常值處理',
    remove_outliers_zscore: 'Z-score 異常值處理',
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

<style scoped>
  .preprocessor-panel {
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
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .step-item {
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 12px;
    background: #f8fafc;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    font-size: 11px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .step-label {
    font-size: 13px;
    font-weight: 600;
    color: #1e293b;
  }

  .step-params {
    display: flex;
    flex-direction: column;
    gap: 3px;
    padding-left: 28px;
  }

  .param-row {
    display: flex;
    gap: 6px;
    font-size: 12px;
  }

  .param-key {
    color: #64748b;
    min-width: 80px;
  }

  .param-val {
    color: #0f172a;
    font-weight: 500;
  }

  .empty-hint {
    color: #6b7280;
    font-size: 13px;
  }
</style>
