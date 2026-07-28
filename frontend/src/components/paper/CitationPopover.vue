<template>
  <Teleport to="body">
    <div v-if="citation" class="citation-popover-backdrop" @click="emit('close')">
      <article ref="cardRef" class="citation-popover-card" :style="cardStyle" @click.stop>
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
  import { nextTick, ref, watch } from 'vue'

  const props = defineProps<{
    citation: Citation | null
    target: HTMLElement | null
    index: number
  }>()

  const emit = defineEmits<{
    (e: 'close'): void
  }>()

  const cardWidth = 300

  const hiddenStyle: CSSProperties = {
    position: 'fixed',
    visibility: 'hidden',
    top: '0px',
    left: '0px',
    width: `${cardWidth}px`,
  }

  const cardRef = ref<HTMLElement | null>(null)
  const cardStyle = ref<CSSProperties>(hiddenStyle)

  function positionCard () {
    const target = props.target
    const card = cardRef.value
    if (!target || !card) {
      cardStyle.value = hiddenStyle
      return
    }

    const rect = target.getBoundingClientRect()
    const cardHeight = card.offsetHeight
    const left = Math.min(
      Math.max(8, rect.left),
      Math.max(8, window.innerWidth - cardWidth - 8),
    )

    const spaceBelow = window.innerHeight - rect.bottom - 8
    const placeAbove = spaceBelow < cardHeight && rect.top - 8 - cardHeight > 0
    const top = placeAbove
      ? Math.max(8, rect.top - 8 - cardHeight)
      : Math.min(rect.bottom + 8, Math.max(8, window.innerHeight - cardHeight - 8))

    cardStyle.value = {
      position: 'fixed',
      top: `${top}px`,
      left: `${left}px`,
      width: `${cardWidth}px`,
    }
  }

  watch(() => [props.citation, props.target], async () => {
    if (!props.citation || !props.target) {
      cardStyle.value = hiddenStyle
      return
    }
    cardStyle.value = hiddenStyle
    await nextTick()
    positionCard()
  }, { immediate: true })
</script>

<style scoped>
  .citation-popover-backdrop {
    position: fixed;
    inset: 0;
    z-index: 2400;
    background: transparent;
  }

  .citation-popover-card {
    max-height: min(400px, calc(100vh - 16px));
    overflow-y: auto;
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
