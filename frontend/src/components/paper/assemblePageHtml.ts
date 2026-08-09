import type { PaginationBlock } from '@/components/paper/paginateBlocks'

export function assemblePageHtml (blocks: PaginationBlock[]): string {
  const parts: string[] = []
  let pendingItems: string[] = []

  const flushItems = () => {
    if (pendingItems.length === 0) return
    parts.push(`<ul class="references-list">${pendingItems.join('')}</ul>`)
    pendingItems = []
  }

  for (const block of blocks) {
    if (block.kind === 'referenceItem') {
      pendingItems.push(block.html)
      continue
    }
    flushItems()
    parts.push(block.html)
  }
  flushItems()

  return parts.join('')
}
