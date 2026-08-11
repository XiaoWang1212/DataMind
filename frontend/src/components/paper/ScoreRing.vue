<template>
  <v-progress-circular
    bg-color="#e8ebf1"
    class="score-ring"
    :color="ringColor"
    :model-value="score"
    :size="size"
    :width="strokeWidth"
  >
    <span class="score-ring__value" :style="{ fontSize: `${fontSize}px` }">{{ score }}</span>
  </v-progress-circular>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = withDefaults(defineProps<{
    score: number
    size?: number
    strokeWidth?: number
    fontSize?: number
  }>(), {
    size: 96,
    strokeWidth: 8,
  })

  const ringColor = computed(() => getScoreColor(props.score))
  const fontSize = computed(() => props.fontSize ?? Math.round(props.size / 3.4))
</script>

<style scoped>
  .score-ring__value {
    font-weight: 700;
    color: #1c2130;
  }
</style>
