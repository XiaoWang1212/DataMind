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
    gap: 16px;
    padding: 10px 0;
  }

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

  .importance-table {
    display: flex;
    flex-direction: column;
  }

  .importance-row {
    display: grid;
    grid-template-columns: 1fr 120px;
    gap: 0;
    align-items: center;
    padding: 12px 16px;
  }

  .importance-row--header {
    font-weight: 700;
    background: #f1f5f9;
    color: #0f172a;
  }

  .importance-cell {
    color: #0f172a;
    font-size: 13px;
    word-break: break-word;
  }

  .importance-cell--feature {
    color: #1f2937;
  }

  .importance-cell--value {
    text-align: right;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
    padding: 14px 16px;
  }
</style>
