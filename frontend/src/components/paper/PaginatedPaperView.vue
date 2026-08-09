<template>
  <div class="paginated-paper" @click="handleClick">
    <section v-for="(pageHtml, index) in pages" :key="index" class="a4-page">
      <div class="a4-page-content editor-content" v-html="pageHtml" />
      <div class="a4-page-number">第 {{ index + 1 }} 頁</div>
    </section>

    <div ref="measureContentRef" aria-hidden="true" class="measure-container editor-content" />
    <div ref="measureReferencesRef" aria-hidden="true" class="measure-container editor-content" />
  </div>
</template>

<script setup lang="ts">
  import type { JSONContent } from '@tiptap/core'
  import type { Citation, CitationStyle } from '@/constants/reportData'
  import { generateHTML } from '@tiptap/core'
  import { onMounted, ref, watch } from 'vue'
  import { assemblePageHtml } from '@/components/paper/assemblePageHtml'
  import { buildReferenceBlocks } from '@/components/paper/buildReferenceBlocks'
  import { paginateBlocks, type PaginationBlock } from '@/components/paper/paginateBlocks'
  import { buildPaperContentExtensions } from '@/components/paper/paperExtensions'
  import '@/components/paper/paperContentTypography.css'

  const A4_CONTENT_HEIGHT_PX = 890

  const props = defineProps<{
    content: JSONContent
    citations: Citation[]
    citationStyle: CitationStyle
  }>()

  const emit = defineEmits<{
    (e: 'citation-click', payload: { citationId: string, target: HTMLElement }): void
  }>()

  const pages = ref<string[]>([])
  const measureContentRef = ref<HTMLDivElement | null>(null)
  const measureReferencesRef = ref<HTMLDivElement | null>(null)

  function measureFlow (elements: HTMLElement[]): number[] {
    return elements.map((el, i) => {
      const next = elements[i + 1]
      const height = next ? next.offsetTop - el.offsetTop : el.getBoundingClientRect().height
      return i === 0 ? height + el.offsetTop : height
    })
  }

  async function computePages () {
    const contentContainer = measureContentRef.value
    const referencesContainer = measureReferencesRef.value
    if (!contentContainer || !referencesContainer) return

    const citationIndex: Record<string, number> = {}
    for (const [index, citation] of props.citations.entries()) {
      citationIndex[citation.id] = index + 1
    }

    const contentHtml = generateHTML(props.content, buildPaperContentExtensions(citationIndex))
    contentContainer.innerHTML = contentHtml

    const images = Array.from(contentContainer.querySelectorAll('img'))
    await Promise.all([
      document.fonts.ready,
      ...images.map(img => img.decode().catch(() => {})),
    ])

    const contentEls = Array.from(contentContainer.children) as HTMLElement[]
    const contentHeights = measureFlow(contentEls)
    const contentBlocks: PaginationBlock[] = contentEls.map((el, i) => ({
      kind: 'content',
      html: el.outerHTML,
      height: contentHeights[i] ?? el.getBoundingClientRect().height,
    }))

    const referenceInputs = buildReferenceBlocks(props.citations, props.citationStyle)
    let referenceBlocks: PaginationBlock[] = []

    if (referenceInputs.length > 0) {
      const heading = referenceInputs[0]!
      const items = referenceInputs.slice(1)
      referencesContainer.innerHTML = `${heading.html}<ul class="references-list">${items.map(item => item.html).join('')}</ul>`

      const headingEl = referencesContainer.children[0] as HTMLElement
      const listEl = referencesContainer.children[1] as HTMLElement
      const liEls = Array.from(listEl.children) as HTMLElement[]
      const flowHeights = measureFlow([headingEl, ...liEls])

      referenceBlocks = [
        { kind: 'referenceHeading', html: heading.html, height: flowHeights[0] ?? headingEl.getBoundingClientRect().height },
        ...items.map((item, i) => ({
          kind: 'referenceItem' as const,
          html: item.html,
          height: flowHeights[i + 1] ?? liEls[i]?.getBoundingClientRect().height ?? 0,
        })),
      ]
    }

    const bucketed = paginateBlocks([...contentBlocks, ...referenceBlocks], A4_CONTENT_HEIGHT_PX)
    pages.value = bucketed.filter(pageBlocks => pageBlocks.length > 0).map(pageBlocks => assemblePageHtml(pageBlocks))

    contentContainer.innerHTML = ''
    referencesContainer.innerHTML = ''
  }

  function handleClick (event: MouseEvent) {
    const target = (event.target as HTMLElement).closest<HTMLElement>('[data-citation-id]')
    const citationId = target?.dataset.citationId
    if (citationId && target) {
      emit('citation-click', { citationId, target })
    }
  }

  onMounted(computePages)

  watch(
    [() => props.content, () => props.citations, () => props.citationStyle],
    computePages,
    { deep: true },
  )
</script>

<style scoped>
.paginated-paper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 24px 0;
}

.a4-page {
  width: 794px;
  height: 1123px;
  background: var(--card-bg);
  border: 1px solid var(--line);
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(28, 33, 48, 0.12);
  padding: 96px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.a4-page-content {
  flex: 1;
}

.a4-page-number {
  margin-top: 16px;
  text-align: center;
  font-size: 11px;
  color: var(--text-secondary);
}

.measure-container {
  position: fixed;
  left: -99999px;
  top: 0;
  width: 602px;
  visibility: hidden;
  pointer-events: none;
}

:deep(.citation-mark) {
  cursor: pointer;
  transition: background 0.2s ease;
}

:deep(.citation-mark:hover) {
  background: #fae57e;
}

:deep(.references-title) {
  margin: 28px 0 12px;
  padding-top: 18px;
  border-top: 1px solid #d8dbe3;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-ink);
}

:deep(.references-list) {
  margin: 0;
  padding-left: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

:deep(.references-list li) {
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--color-ink);
}
</style>
