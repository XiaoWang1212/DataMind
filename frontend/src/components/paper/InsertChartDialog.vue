<template>
  <v-dialog
    max-width="640"
    :model-value="modelValue"
    @update:model-value="value => emit('update:modelValue', value)"
  >
    <v-card class="insert-chart-dialog">
      <v-card-title>插入圖表</v-card-title>

      <v-card-text>
        <p v-if="summaries.length === 0" class="empty-hint">
          此專案尚無工作流程結果可插入
        </p>

        <template v-else>
          <v-btn-toggle v-model="chartType" class="chart-type-toggle" density="compact" mandatory>
            <v-btn value="bar">長條圖</v-btn>
            <v-btn value="radar">雷達圖</v-btn>
          </v-btn-toggle>

          <div class="picker-row">
            <div class="picker-column">
              <p class="picker-label">模型</p>
              <v-checkbox
                v-for="model in availableModels"
                :key="model"
                v-model="selectedModels"
                density="compact"
                hide-details
                :label="model"
                :value="model"
              />
            </div>
            <div class="picker-column">
              <p class="picker-label">指標</p>
              <v-checkbox
                v-for="metric in availableMetrics"
                :key="metric"
                v-model="selectedMetrics"
                density="compact"
                hide-details
                :label="metric"
                :value="metric"
              />
            </div>
          </div>

          <p v-if="chartSeries.length === 0" class="empty-hint">請至少選擇一項模型與指標</p>
          <div v-else ref="previewRef" class="chart-preview">
            <BarChart v-if="chartType === 'bar'" :series="chartSeries" />
            <RadarChart v-else :series="chartSeries" />
          </div>
        </template>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn class="bg-accent" color="accent" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { type ModelMetricSummary, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'
  import { colorForIndex } from '@/components/paper/charts/chartColors'
  import BarChart from '@/components/paper/charts/BarChart.vue'
  import RadarChart from '@/components/paper/charts/RadarChart.vue'

  const props = defineProps<{
    modelValue: boolean
    projectId: string | undefined
  }>()

  const emit = defineEmits<{
    (e: 'update:modelValue', value: boolean): void
    (e: 'insert', dataUrl: string): void
  }>()

  const chartType = ref<'bar' | 'radar'>('bar')
  const summaries = ref<ModelMetricSummary[]>([])
  const selectedModels = ref<string[]>([])
  const selectedMetrics = ref<string[]>([])
  const previewRef = ref<HTMLElement | null>(null)

  watch(() => props.modelValue, open => {
    if (!open) return
    const state = loadWorkflowStateFromStorage(props.projectId)
    summaries.value = summarizeWorkflowResult(state?.workflowResult ?? null)
    selectedModels.value = summaries.value.map(s => s.model_name)
    selectedMetrics.value = [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))]
  })

  const availableModels = computed(() => summaries.value.map(s => s.model_name))
  const availableMetrics = computed(() =>
    [...new Set(summaries.value.flatMap(s => s.metrics.map(m => m.metric)))],
  )

  const chartSeries = computed(() => {
    const points: { model: string, metric: string, value: number }[] = []
    for (const summary of summaries.value) {
      if (!selectedModels.value.includes(summary.model_name)) continue
      for (const metric of summary.metrics) {
        if (!selectedMetrics.value.includes(metric.metric)) continue
        points.push({ model: summary.model_name, metric: metric.metric, value: metric.valueRaw })
      }
    }
    return points
  })

  const legendModels = computed(() => [...new Set(chartSeries.value.map(point => point.model))])

  function svgToDataUrl (svgString: string): string {
    const bytes = new TextEncoder().encode(svgString)
    let binary = ''
    for (const byte of bytes) binary += String.fromCharCode(byte)
    return `data:image/svg+xml;base64,${btoa(binary)}`
  }

  function escapeXml (value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
  }

  function handleInsert () {
    const svgEl = previewRef.value?.querySelector('svg')
    if (!svgEl) return

    const width = Number(svgEl.getAttribute('width'))
    const chartHeight = Number(svgEl.getAttribute('height'))
    const legendRowHeight = 18
    const legendTop = chartHeight + 12
    const totalHeight = legendTop + legendModels.value.length * legendRowHeight

    const chartInnerMarkup = Array.from(svgEl.children)
      .map(child => new XMLSerializer().serializeToString(child))
      .join('')

    const legendMarkup = legendModels.value
      .map((model, index) => {
        const y = legendTop + index * legendRowHeight
        return `<rect x="8" y="${y}" width="10" height="10" rx="2" fill="${colorForIndex(index)}" />`
          + `<text x="24" y="${y + 9}" font-size="11" fill="#4a4f5c">${escapeXml(model)}</text>`
      })
      .join('')

    const svgString = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${totalHeight}" viewBox="0 0 ${width} ${totalHeight}">${chartInnerMarkup}${legendMarkup}</svg>`

    emit('insert', svgToDataUrl(svgString))
    emit('update:modelValue', false)
  }
</script>

<style scoped>
  .insert-chart-dialog {
    padding: 4px;
  }

  .empty-hint {
    font-size: 13px;
    color: var(--color-secondary);
    padding: 12px 0;
  }

  .chart-type-toggle {
    margin-bottom: 14px;
  }

  .picker-row {
    display: flex;
    gap: 24px;
    margin-bottom: 14px;
  }

  .picker-column {
    flex: 1;
    min-width: 0;
    max-height: 160px;
    overflow-y: auto;
  }

  .picker-label {
    margin: 0 0 4px;
    font-size: 12px;
    font-weight: 700;
    color: var(--color-secondary);
  }

  .chart-preview {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
  }
</style>
