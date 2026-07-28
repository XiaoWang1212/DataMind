<template>
  <div>
    <svg
      :height="height"
      :viewBox="`0 0 ${width} ${height}`"
      :width="width"
      class="chart-svg"
      xmlns="http://www.w3.org/2000/svg"
    >
      <line
        v-for="tick in yTicks"
        :key="`grid-${tick.value}`"
        class="chart-gridline"
        :x1="padding.left"
        :x2="width - padding.right"
        :y1="tick.y"
        :y2="tick.y"
      />
      <text
        v-for="tick in yTicks"
        :key="`label-${tick.value}`"
        class="chart-axis-label"
        text-anchor="end"
        :x="padding.left - 8"
        :y="tick.y + 4"
      >
        {{ tick.value.toFixed(2) }}
      </text>

      <g v-for="group in groups" :key="group.metric">
        <rect
          v-for="(bar, barIndex) in group.bars"
          :key="bar.model"
          :fill="colorForIndex(barIndex)"
          :height="bar.barHeight"
          :width="barWidth"
          :x="group.groupX + barIndex * (barWidth + barGap)"
          :y="bar.barY"
        />
        <text
          class="chart-axis-label"
          text-anchor="middle"
          :x="group.centerX"
          :y="height - padding.bottom + 18"
        >
          {{ group.metric }}
        </text>
      </g>

      <line
        class="chart-axis-line"
        :x1="padding.left"
        :x2="width - padding.right"
        :y1="height - padding.bottom"
        :y2="height - padding.bottom"
      />
    </svg>

    <ul class="chart-legend">
      <li v-for="(model, modelIndex) in models" :key="model" class="chart-legend-item">
        <span class="chart-legend-swatch" :style="{ background: colorForIndex(modelIndex) }" />
        {{ model }}
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { colorForIndex } from './chartColors'

  const props = withDefaults(defineProps<{
    series: { model: string, metric: string, value: number }[]
    width?: number
    height?: number
  }>(), {
    width: 520,
    height: 300,
  })

  const padding = { top: 16, right: 16, bottom: 46, left: 48 }
  const barWidth = 18
  const barGap = 6

  const models = computed(() => [...new Set(props.series.map(point => point.model))])
  const metrics = computed(() => [...new Set(props.series.map(point => point.metric))])

  const maxValue = computed(() => {
    const max = Math.max(0, ...props.series.map(point => point.value))
    return max === 0 ? 1 : max
  })

  const chartInnerHeight = computed(() => props.height - padding.top - padding.bottom)
  const chartInnerWidth = computed(() => props.width - padding.left - padding.right)

  const yTicks = computed(() => {
    const tickCount = 4
    return Array.from({ length: tickCount + 1 }, (_, index) => {
      const value = (maxValue.value / tickCount) * (tickCount - index)
      const y = padding.top + (chartInnerHeight.value / tickCount) * index
      return { value, y }
    })
  })

  const groups = computed(() => {
    const groupWidth = models.value.length * (barWidth + barGap)
    const totalGroupsWidth = metrics.value.length * groupWidth
    const gapBetweenGroups = (chartInnerWidth.value - totalGroupsWidth) / (metrics.value.length + 1)

    return metrics.value.map((metric, metricIndex) => {
      const groupX = padding.left + gapBetweenGroups * (metricIndex + 1) + groupWidth * metricIndex
      const bars = models.value.map(model => {
        const point = props.series.find(p => p.metric === metric && p.model === model)
        const value = point?.value ?? 0
        const barHeight = (value / maxValue.value) * chartInnerHeight.value
        return {
          model,
          barHeight,
          barY: padding.top + chartInnerHeight.value - barHeight,
        }
      })
      return { metric, groupX, centerX: groupX + groupWidth / 2, bars }
    })
  })
</script>

<style scoped>
  .chart-svg {
    display: block;
    max-width: 100%;
  }

  .chart-gridline {
    stroke: #e8ebf1;
    stroke-width: 1;
  }

  .chart-axis-line {
    stroke: #d8dbe3;
    stroke-width: 1;
  }

  .chart-axis-label {
    font-size: 10px;
    fill: #6f7480;
  }

  .chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
  }

  .chart-legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    color: #4a4f5c;
  }

  .chart-legend-swatch {
    width: 10px;
    height: 10px;
    border-radius: 2px;
  }
</style>
