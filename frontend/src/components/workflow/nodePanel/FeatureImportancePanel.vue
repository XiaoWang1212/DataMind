<template>
  <section class="feature-importance-panel">
    <div v-if="groupedResults.length > 0" class="fi-controls">
      <div class="fi-field">
        <span class="fi-field__label">模型</span>
        <CustomSelect
          v-model="selectedModel"
          class="fi-select"
          :options="modelOptions"
        />
      </div>
      <div class="fi-field">
        <span class="fi-field__label">fold</span>
        <CustomSelect
          v-model="selectedFold"
          class="fi-select"
          :options="foldOptions"
        />
      </div>
    </div>

    <div
      v-if="currentImportance.length > 0"
      class="fi-table"
    >
      <div class="fi-row fi-row--header">
        <div class="fi-cell">Feature</div>
        <div class="fi-cell fi-cell--num">Importance</div>
      </div>
      <div
        v-for="item in currentImportance"
        :key="item.feature"
        class="fi-row"
      >
        <div class="fi-cell fi-cell--feature">{{ item.feature }}</div>
        <div class="fi-cell fi-cell--num">{{ formatImportance(item.importance) }}</div>
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

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'

  interface FeatureImportanceItem {
    feature: string
    importance: number
  }

  interface ResultItem {
    model_name: string
    split_name: string
    feature_importance: FeatureImportanceItem[]
  }

  interface GroupedResult {
    model_name: string
    splits: Array<{
      split_name: string
      feature_importance: FeatureImportanceItem[]
    }>
  }

  const props = defineProps<{
    workflowResult?: Record<string, unknown> | null
  }>()

  const rawResults = computed<Array<Record<string, unknown>>>(() => {
    const results = props.workflowResult?.results
    if (!Array.isArray(results)) return []
    return results as Array<Record<string, unknown>>
  })

  const importanceResults = computed<ResultItem[]>(() =>
    rawResults.value
      .map(result => {
        const model_name = String(result.model_name ?? 'Unknown model')
        const split_name = String(result.split_name ?? 'Unknown split')
        const feature_importance = Array.isArray(result.feature_importance)
          ? (result.feature_importance as Array<Record<string, unknown>>)
            .filter(
              item =>
                item
                && typeof item === 'object'
                && typeof item.feature === 'string'
                && typeof item.importance === 'number',
            )
            .map(item => ({
              feature: String(item.feature),
              importance: Number(item.importance),
            }))
          : []

        return { model_name, split_name, feature_importance }
      })
      .filter(item => item.feature_importance.length > 0),
  )

  const groupedResults = computed<GroupedResult[]>(() => {
    const groups = new Map<string, GroupedResult>()

    for (const result of importanceResults.value) {
      const existing = groups.get(result.model_name)
      const entry = {
        split_name: result.split_name,
        feature_importance: result.feature_importance,
      }

      if (existing) {
        existing.splits.push(entry)
      } else {
        groups.set(result.model_name, {
          model_name: result.model_name,
          splits: [entry],
        })
      }
    }

    return Array.from(groups.values())
  })

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

  // 換模型（或結果載入）時，fold 一律重置為該模型的第一個
  watch(currentModel, model => {
    const splits = model?.splits ?? []
    selectedFold.value = splits[0]?.split_name ?? ''
  }, { immediate: true })

  function formatImportance (value: number): string {
    return value.toFixed(4)
  }
</script>

<style scoped>
  .feature-importance-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 0 0 16px;
  }

  /* 控制列：模型｜下拉  fold｜下拉，label 在下拉左邊、兩組並排 */
  .fi-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .fi-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .fi-field__label {
    font-size: 13px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .fi-select {
    width: 160px;
  }

  /* 表格沿用 Test & Score 的圓角卡片樣式，維持結果面板一致 */
  .fi-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--color-surface);
  }

  .fi-row {
    display: grid;
    grid-template-columns: 1fr 140px;
    gap: 0;
    align-items: center;
  }

  .fi-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .fi-row:not(.fi-row--header):hover {
    background: color-mix(in oklab, var(--color-accent) 3.5%, transparent);
  }

  .fi-row--header {
    font-size: 12px;
    font-weight: 500;
    color: var(--color-secondary);
    background: var(--color-surface);
  }

  .fi-row--header .fi-cell {
    padding: 8px 14px;
  }

  .fi-cell {
    padding: 11px 14px;
    color: var(--color-text);
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
  }

  .fi-cell--feature {
    color: var(--color-text);
  }

  .fi-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
