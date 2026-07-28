<template>
  <div>
    <svg
      :height="size"
      :viewBox="`0 0 ${size} ${size}`"
      :width="size"
      class="chart-svg"
      xmlns="http://www.w3.org/2000/svg"
    >
      <polygon
        v-for="ring in gridRings"
        :key="ring.scale"
        class="chart-gridline"
        fill="none"
        stroke="#e8ebf1"
        stroke-width="1"
        :points="ring.points"
      />
      <line
        v-for="axis in axes"
        :key="`axis-${axis.metric}`"
        class="chart-axis-line"
        stroke="#d8dbe3"
        stroke-width="1"
        :x1="center"
        :x2="axis.labelX"
        :y1="center"
        :y2="axis.labelY"
      />
      <text
        v-for="axis in axes"
        :key="`label-${axis.metric}`"
        class="chart-axis-label"
        fill="#6f7480"
        font-size="10"
        :text-anchor="axis.anchor"
        :x="axis.textX"
        :y="axis.textY"
      >
        {{ axis.metric }}
      </text>

      <polygon
        v-for="(model, modelIndex) in models"
        :key="model"
        class="chart-radar-shape"
        :fill="colorForIndex(modelIndex)"
        fill-opacity="0.18"
        :points="polygonPoints(model)"
        :stroke="colorForIndex(modelIndex)"
        stroke-width="1.5"
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
    size?: number
  }>(), {
    size: 320,
  })

  const center = computed(() => props.size / 2)
  const radius = computed(() => props.size / 2 - 40)

  const models = computed(() => [...new Set(props.series.map(point => point.model))])
  const metrics = computed(() => [...new Set(props.series.map(point => point.metric))])

  const maxByMetric = computed(() => {
    const map = new Map<string, number>()
    for (const metric of metrics.value) {
      const values = props.series.filter(p => p.metric === metric).map(p => p.value)
      map.set(metric, Math.max(...values, 0) || 1)
    }
    return map
  })

  function angleForAxis (axisIndex: number): number {
    return (Math.PI * 2 * axisIndex) / metrics.value.length - Math.PI / 2
  }

  function pointForValue (axisIndex: number, ratio: number): { x: number, y: number } {
    const angle = angleForAxis(axisIndex)
    return {
      x: center.value + Math.cos(angle) * radius.value * ratio,
      y: center.value + Math.sin(angle) * radius.value * ratio,
    }
  }

  const axes = computed(() => metrics.value.map((metric, axisIndex) => {
    const onAxis = pointForValue(axisIndex, 1)
    const label = pointForValue(axisIndex, 1.18)
    const angle = angleForAxis(axisIndex)
    const cos = Math.cos(angle)
    const anchor = cos > 0.2 ? 'start' : cos < -0.2 ? 'end' : 'middle'
    return {
      metric,
      labelX: onAxis.x,
      labelY: onAxis.y,
      textX: label.x,
      textY: label.y,
      anchor,
    }
  }))

  const gridRings = computed(() => [0.25, 0.5, 0.75, 1].map(scale => ({
    scale,
    points: metrics.value
      .map((_, axisIndex) => {
        const point = pointForValue(axisIndex, scale)
        return `${point.x},${point.y}`
      })
      .join(' '),
  })))

  function polygonPoints (model: string): string {
    return metrics.value
      .map((metric, axisIndex) => {
        const point = props.series.find(p => p.metric === metric && p.model === model)
        const max = maxByMetric.value.get(metric) ?? 1
        const ratio = point ? point.value / max : 0
        const { x, y } = pointForValue(axisIndex, ratio)
        return `${x},${y}`
      })
      .join(' ')
  }
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

  .chart-radar-shape {
    stroke-width: 1.5;
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
