<template>
  <Teleport to="body">
    <div v-if="citation" class="citation-popover-backdrop" @click="emit('close')">
      <article class="citation-popover-card" :style="cardStyle" @click.stop>
        <p class="citation-label">
          <v-icon icon="mdi-book-open-variant-outline" size="13" />
          來源文獻 [{{ index }}]
        </p>
        <p class="citation-field"><span>標題:</span>{{ citation.title }}</p>
        <p class="citation-field"><span>作者:</span>{{ citation.authors }} ({{ citation.year }})</p>
        <p class="citation-field"><span>期刊:</span>{{ citation.journal }}</p>

        <p class="citation-label snippet-label">
          <v-icon icon="mdi-text-search" size="13" />
          檢索片段
        </p>
        <p class="citation-snippet">{{ citation.snippet }}</p>
      </article>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
  import type { CSSProperties } from 'vue'
  import type { Citation } from '@/constants/reportData'
  import { computed } from 'vue'

  const props = defineProps<{
    citation: Citation | null
    target: HTMLElement | null
    index: number
  }>()

  const emit = defineEmits<{
    (e: 'close'): void
  }>()

  const cardWidth = 300

  const cardStyle = computed((): CSSProperties => {
    if (!props.target) return { display: 'none' }
    const rect = props.target.getBoundingClientRect()
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - cardWidth - 8)
    return {
      position: 'fixed',
      top: `${rect.bottom + 8}px`,
      left: `${left}px`,
      width: `${cardWidth}px`,
    }
  })
</script>

<style scoped>
  .citation-popover-backdrop {
    position: fixed;
    inset: 0;
    z-index: 2400;
    background: transparent;
  }

  .citation-popover-card {
    background: #fffbe8;
    border: 1px solid #eadf9e;
    border-radius: 12px;
    padding: 12px 14px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
  }

  .citation-label {
    margin: 0 0 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 700;
    color: #8a6d1a;
  }

  .snippet-label {
    margin-top: 10px;
  }

  .citation-field {
    margin: 0 0 3px;
    font-size: 12px;
    line-height: 1.55;
    color: #4a4433;
  }

  .citation-field span {
    font-weight: 700;
    color: #6d5c22;
  }

  .citation-snippet {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    font-style: italic;
    color: #5c5340;
  }
</style>
