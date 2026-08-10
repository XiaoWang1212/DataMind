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

<style scoped>
  .feature-engineering-panel {
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
    background: var(--color-surface);
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
    border-top: 1px dashed #e2e8f0;
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
    color: var(--color-text);
    font-weight: 500;
  }

  .empty-hint {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
