<template>
  <section class="paper-section">
    <h3 class="section-heading">{{ section.heading }}</h3>
    <p
      v-for="(paragraph, pIndex) in section.paragraphs"
      :key="pIndex"
      class="section-paragraph"
    >
      <template v-for="(segment, sIndex) in paragraph" :key="sIndex">
        <!-- data-citation-id 是 PaperPage 捲動定位用的 DOM 契約(空白分隔的多個 id),改動需同步 PaperPage -->
        <mark
          v-if="citationIdsOf(segment).length > 0"
          class="cite-highlight"
          :class="{ 'cite-highlight--active': citationIdsOf(segment).includes(activeCitationId ?? '') }"
          :data-citation-id="citationIdsOf(segment).join(' ')"
          role="button"
          tabindex="0"
          @click="$emit('citation-click', firstCitationId(segment))"
          @keydown.enter.prevent="$emit('citation-click', firstCitationId(segment))"
          @keydown.space.prevent="$emit('citation-click', firstCitationId(segment))"
        >{{ segment.text }}<template v-for="cid in citationIdsOf(segment)" :key="cid"> [{{ citationIndex[cid] }}]</template></mark>
        <template v-else>{{ segment.text }}</template>
      </template>
    </p>
  </section>
</template>

<script setup lang="ts">
  import type { PaperSection, PaperSegment } from '@/constants/reportData'

  defineProps<{
    section: PaperSection
    activeCitationId: string | null
    citationIndex: Record<string, number>
  }>()

  defineEmits<{
    (e: 'citation-click', citationId: string): void
  }>()

  function citationIdsOf (segment: PaperSegment): string[] {
    return segment.citationIds ?? []
  }

  function firstCitationId (segment: PaperSegment): string {
    return citationIdsOf(segment)[0] ?? ''
  }
</script>

<style scoped>
  .paper-section {
    margin-bottom: 22px;
  }

  .section-heading {
    margin: 0 0 10px;
    font-size: 15px;
    font-weight: 700;
    color: #1c2130;
  }

  .section-paragraph {
    margin: 0 0 12px;
    font-size: 13.5px;
    line-height: 1.9;
    color: #2a2f3a;
    text-align: justify;
    text-indent: 2em;
  }

  .cite-highlight {
    background: #fdf0a8;
    padding: 1px 2px;
    border-radius: 3px;
    cursor: pointer;
    transition: background 0.2s ease;
  }

  .cite-highlight:hover {
    background: #fae57e;
  }

  .cite-highlight:focus-visible {
    outline: 2px solid #c9ad2a;
    outline-offset: 1px;
  }

  .cite-highlight--active {
    background: #f7dc5a;
    box-shadow: 0 0 0 2px rgba(201, 173, 42, 0.35);
  }
</style>
