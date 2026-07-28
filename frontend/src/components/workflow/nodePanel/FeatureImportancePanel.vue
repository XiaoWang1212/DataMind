<template>
  <section class="feature-importance-panel">
    <h4>Feature Importance</h4>

    <div v-if="groupedResults.length > 0" class="importance-list">
      <div
        v-for="group in groupedResults"
        :key="group.model_name"
        class="importance-card"
      >
        <div class="importance-card__header">
          <div class="importance-card__title">{{ group.model_name }}</div>
          <div class="importance-card__subtitle">
            {{ group.splits.length }} 種抽樣結果
          </div>
        </div>

        <div class="importance-split-list">
          <div
            v-for="split in group.splits"
            :key="`${group.model_name}-${split.split_name}`"
            class="importance-split"
          >
            <div class="importance-split__title">
              {{ split.split_name }}
            </div>

            <div
              v-if="split.feature_importance.length > 0"
              class="importance-table"
            >
              <div class="importance-row importance-row--header">
                <div class="importance-cell">Feature</div>
                <div class="importance-cell">Importance</div>
              </div>
              <div
                v-for="item in split.feature_importance"
                :key="item.feature"
                class="importance-row"
              >
                <div class="importance-cell importance-cell--feature">
                  {{ item.feature }}
                </div>
                <div class="importance-cell importance-cell--value">
                  {{ formatImportance(item.importance) }}
                </div>
              </div>
            </div>

            <div v-else class="summary-empty">
              該抽樣沒有可用的特徵重要性資訊。
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="summary-empty">
      尚未有特徵重要性結果，請執行 Workflow 後再查看。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

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

  .feature-importance-panel h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }

  .importance-card {
    border-radius: 18px;
    overflow: hidden;
    background: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.16);
  }

  .importance-card__header {
    padding: 14px 16px;
    background: #f8fafc;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .importance-card__title {
    font-weight: 700;
    color: #0f172a;
    font-size: 14px;
  }

  .importance-card__subtitle {
    font-size: 12px;
    color: #475569;
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
