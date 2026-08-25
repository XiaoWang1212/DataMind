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
  align-items: flex-start;
  gap: 24px;
  padding: 24px 0;
}

.a4-page {
  width: 794px;
  height: 1123px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-card);
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
  font-size: 12px;
  color: var(--color-ink-soft);
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
  transition: background var(--dur-fast) var(--ease-out);
}

:deep(.citation-mark:hover) {
  background: color-mix(in oklab, var(--color-ink) 24%, white);
}

:deep(.references-title) {
  margin: 28px 0 12px;
  padding-top: 18px;
  border-top: 1px solid var(--color-border);
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text);
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
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
}

/* 下載 PDF：畫面上的卡片裝飾（邊框/陰影/圓角/頁間留白）在紙上沒有意義，拿掉；
   每頁之間強制分頁，最後一頁後面不留空白頁。
   .a4-page 平常用 display:flex + 固定 height 撐出畫面上的卡片高度、把頁碼推到底部，
   但 WeasyPrint 的 flexbox 支援對「固定高度 + flex-direction:column」這種組合算不準，
   會導致內容被裁切、padding 跑掉（右側幾乎貼邊、上方留白過大）；PDF 分頁本來就是
   WeasyPrint 用 break-after 處理，不需要固定高度去撐版面，這裡改回單純的 block、
   高度隨內容自然展開，讓 96px 的 padding 在四邊都正確生效 */
@media print {
  .paginated-paper {
    gap: 0;
    padding: 0;
  }

  .a4-page {
    display: block;
    width: auto;
    height: auto;
    margin: 0;
    border: none;
    border-radius: 0;
    box-shadow: none;
    break-after: page;
  }

  .a4-page:last-child {
    break-after: auto;
  }

  .measure-container {
    display: none;
  }
}
</style>
