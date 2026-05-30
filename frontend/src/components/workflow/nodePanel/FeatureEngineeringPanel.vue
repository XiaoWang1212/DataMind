<template>
  <section class="feature-engineering-panel">
    <div class="feature-engineering-summary">
      <div
        v-if="pipeline && pipeline.length > 0"
        class="feature-engineering-subtitle"
      >
        共有 {{ pipeline.length }} 個特徵工程步驟
      </div>
      <div v-else class="feature-engineering-subtitle">
        尚未找到特徵工程設定。
      </div>
    </div>

    <div v-if="pipeline && pipeline.length > 0" class="feature-engineering-steps">
      <div
        v-for="(step, index) in pipeline"
        :key="index"
        class="feature-engineering-step"
      >
        <div class="feature-engineering-step-index">Step {{ index + 1 }}</div>
        <pre>{{ formatStep(step) }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue'

  const props = defineProps<{
    pipeline?: Array<Record<string, unknown>> | null
  }>()

  const pipeline = computed(() => props.pipeline ?? [])

  function formatStep (step: Record<string, unknown>): string {
    try {
      return JSON.stringify(step, null, 2)
    } catch {
      return String(step)
    }
  }
</script>

<style scoped>
  .feature-engineering-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .feature-engineering-summary {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .feature-engineering-title {
    font-weight: 700;
    font-size: 16px;
    color: #0f172a;
  }

  .feature-engineering-subtitle {
    color: #475569;
    font-size: 13px;
  }

  .feature-engineering-steps {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .feature-engineering-step {
    padding: 14px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid rgba(148, 163, 184, 0.24);
  }

  .feature-engineering-step-index {
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
  }

  .feature-engineering-step pre {
    margin: 0;
    padding: 10px;
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid rgba(148, 163, 184, 0.16);
    color: #0f172a;
    font-size: 12px;
    overflow-x: auto;
  }
</style>
