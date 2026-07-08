<template>
  <aside class="citation-panel">
    <article
      v-for="(citation, index) in citations"
      :key="citation.id"
      :ref="el => setCardRef(citation.id, el)"
      class="citation-card"
      :class="{ 'citation-card--active': citation.id === activeCitationId }"
      @click="$emit('select', citation.id)"
    >
      <p class="citation-label">
        <v-icon icon="mdi-book-open-variant-outline" size="13" />
        來源文獻 [{{ index + 1 }}]
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
  </aside>
</template>

<script setup lang="ts">
  import type { ComponentPublicInstance } from 'vue'
  import type { Citation } from '@/constants/reportData'
  import { watch } from 'vue'

  const props = defineProps<{
    citations: Citation[]
    activeCitationId: string | null
  }>()

  defineEmits<{
    (e: 'select', citationId: string): void
  }>()

  const cardRefs = new Map<string, HTMLElement>()

  function setCardRef (id: string, el: Element | ComponentPublicInstance | null) {
    if (el instanceof HTMLElement) {
      cardRefs.set(id, el)
    } else {
      cardRefs.delete(id)
    }
  }

  watch(
    () => props.activeCitationId,
    id => {
      if (!id) return
      cardRefs.get(id)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    },
  )
</script>

<style scoped>
  .citation-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .citation-card {
    background: #fffbe8;
    border: 1px solid #eadf9e;
    border-radius: 12px;
    padding: 12px 14px;
    cursor: pointer;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
  }

  .citation-card:hover {
    border-color: #d8c65e;
  }

  .citation-card--active {
    border-color: #c9ad2a;
    box-shadow: 0 2px 10px rgba(180, 150, 30, 0.22);
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
