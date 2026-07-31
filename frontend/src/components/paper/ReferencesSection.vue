<template>
  <section v-if="citations.length > 0" class="references-section">
    <h3 class="references-title">參考文獻</h3>
    <ol v-if="citationStyle === 'ieee'" class="references-list references-list--numbered">
      <li v-for="(citation, index) in citations" :key="citation.id">
        {{ formatCitation(citation, citationStyle, index + 1) }}
      </li>
    </ol>
    <ul v-else class="references-list">
      <li v-for="(citation, index) in citations" :key="citation.id">
        {{ formatCitation(citation, citationStyle, index + 1) }}
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
  import type { Citation, CitationStyle } from '@/constants/reportData'
  import { formatCitation } from '@/utils/paper/formatCitation'

  defineProps<{
    citations: Citation[]
    citationStyle: CitationStyle
  }>()
</script>

<style scoped>
  .references-section {
    margin-top: 28px;
    padding-top: 18px;
    border-top: 1px solid #d8dbe3;
  }

  .references-title {
    margin: 0 0 12px;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .references-list {
    margin: 0;
    padding-left: 22px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .references-list li {
    font-size: 12.5px;
    line-height: 1.7;
    color: var(--color-ink);
  }

  .references-list:not(.references-list--numbered) {
    list-style: none;
    padding-left: 0;
  }
</style>
