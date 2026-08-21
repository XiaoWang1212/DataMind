<template>
  <Teleport to="body">
    <svg v-if="citation && connector" aria-hidden="true" class="citation-connector">
      <path class="citation-connector-line" :d="connector.d" />
      <circle class="citation-connector-dot" :cx="connector.x" :cy="connector.y" r="2.5" />
    </svg>

    <article
      v-if="citation"
      ref="cardRef"
      class="citation-popover-card glass-menu enter-rise"
      :style="cardStyle"
    >
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
  </Teleport>
</template>

<script setup lang="ts">
  import type { CSSProperties } from 'vue'
  import type { Citation } from '@/constants/reportData'
  import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

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
  const connector = ref<{ d: string, x: number, y: number } | null>(null)

  function positionCard () {
    const target = props.target
    const card = cardRef.value
    if (!target || !card) {
      cardStyle.value = hiddenStyle
      connector.value = null
      return
    }

    const rect = target.getBoundingClientRect()
    const cardHeight = card.offsetHeight
    const markCenterY = rect.top + rect.height / 2
    // 卡片往上讓 ENTRY_OFFSET，連接線才能從標記水平拉過來而不是斜的
    const ENTRY_OFFSET = 26
    const top = Math.min(
      Math.max(8, markCenterY - ENTRY_OFFSET),
      Math.max(8, window.innerHeight - cardHeight - 8),
    )

    // 對齊右側的參考文獻欄而不是貼著引用標記，才不會蓋住正在讀的正文。
    // clientWidth 不含垂直捲軸，用 innerWidth 會被推出畫面
    const viewportRight = document.documentElement.clientWidth - 16
    const column = document.querySelector('.paper-citations')
    const left = Math.max(
      8,
      column
        ? Math.min(column.getBoundingClientRect().left, viewportRight - cardWidth)
        : viewportRight - cardWidth,
    )

    cardStyle.value = {
      position: 'fixed',
      top: `${top}px`,
      left: `${left}px`,
      width: `${cardWidth}px`,
    }

    // 從引用標記右緣水平連到卡片左緣。只有卡片被視窗上下緣夾住、
    // 進入點落到卡片外時才會有一點斜度
    const startX = rect.right + 2
    const startY = markCenterY
    const endX = left - 6
    const endY = Math.min(Math.max(startY, top + 10), top + cardHeight - 10)
    if (endX <= startX) {
      connector.value = null
      return
    }
    connector.value = {
      d: `M ${startX} ${startY} L ${endX} ${endY}`,
      x: startX,
      y: startY,
    }
  }

  watch(() => [props.citation, props.target], async () => {
    if (!props.citation || !props.target) {
      cardStyle.value = hiddenStyle
      return
    }
    cardStyle.value = hiddenStyle
    connector.value = null
    await nextTick()
    positionCard()
  }, { immediate: true })

  // Guard is based on the click's real target, not firing order relative to
  // PaperEditor's citation handling (that runs on ProseMirror's own
  // `mouseup`, which always precedes this native `click` regardless of DOM
  // depth) — so this stays correct even if that ordering ever changes.
  function handleDocumentClick (event: MouseEvent) {
    if (!props.citation) return
    const target = event.target as HTMLElement
    if (cardRef.value?.contains(target)) return
    if (target.closest('[data-citation-id]')) return
    emit('close')
  }

  // 引用標記會隨內文捲動，連接線的起點要跟著重算；捲動容器不只 window，
  // 用 capture 才收得到內層容器冒不上來的 scroll
  let repositionFrame = 0
  function handleReposition () {
    if (!props.citation || repositionFrame) return
    repositionFrame = requestAnimationFrame(() => {
      repositionFrame = 0
      positionCard()
    })
  }

  onMounted(() => {
    document.addEventListener('click', handleDocumentClick)
    window.addEventListener('scroll', handleReposition, true)
    window.addEventListener('resize', handleReposition)
  })

  onUnmounted(() => {
    document.removeEventListener('click', handleDocumentClick)
    window.removeEventListener('scroll', handleReposition, true)
    window.removeEventListener('resize', handleReposition)
    if (repositionFrame) cancelAnimationFrame(repositionFrame)
  })
</script>

<style scoped>
  /* 連接線鋪滿視窗，只負責畫線，不吃事件 */
  .citation-connector {
    position: fixed;
    inset: 0;
    width: 100%;
    height: 100%;
    z-index: 2399;
    pointer-events: none;
    overflow: visible;
  }

  .citation-connector-line {
    fill: none;
    stroke: var(--color-ink-vivid);
    stroke-width: 1.5;
    stroke-linecap: round;
    opacity: 0.55;
    /* 1200 只要大於實際線長即可，用單一數值省下量測 */
    stroke-dasharray: 1200;
    animation: citation-draw var(--dur-slow) var(--ease-out) backwards;
  }

  .citation-connector-dot {
    fill: var(--color-ink-vivid);
    animation: citation-dot var(--dur-fast) var(--ease-out) backwards;
  }

  @keyframes citation-draw {
    from { stroke-dashoffset: 1200; }
    to { stroke-dashoffset: 0; }
  }

  @keyframes citation-dot {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @media (prefers-reduced-motion: reduce) {
    .citation-connector-line,
    .citation-connector-dot {
      animation: none;
    }
  }

  /* 底色、邊框、圓角、陰影由 .glass-menu 提供。scoped 樣式不在 CSS layer 內、
     優先權高於 glass.css，在這裡重寫任何一項都會蓋掉玻璃 */
  .citation-popover-card {
    max-height: min(400px, calc(100vh - 16px));
    overflow-y: auto;
    z-index: 2400;
    padding: 12px 14px;
  }

  .citation-label {
    margin: 0 0 6px;
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .snippet-label {
    margin-top: 10px;
  }

  .citation-field {
    margin: 0 0 3px;
    font-size: 12px;
    line-height: 1.55;
    color: var(--color-text);
  }

  .citation-field span {
    margin-right: 4px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .citation-snippet {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    font-style: italic;
    color: var(--color-ink-soft);
  }
</style>
