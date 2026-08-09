export type PaginationBlockKind = 'content' | 'referenceHeading' | 'referenceItem'

export interface PaginationBlock {
  kind: PaginationBlockKind
  html: string
  height: number
}

export function paginateBlocks (blocks: PaginationBlock[], maxHeightPx: number): PaginationBlock[][] {
  const pages: PaginationBlock[][] = [[]]
  let currentHeight = 0

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i]
    if (!block) continue

    const group = [block]
    let groupHeight = block.height

    if (block.kind === 'referenceHeading') {
      const next = blocks[i + 1]
      if (next) {
        group.push(next)
        groupHeight += next.height
      }
    }

    let currentPage = pages[pages.length - 1]
    if (currentPage === undefined) continue
    const pageHasContent = currentHeight > 0

    if (pageHasContent && currentHeight + groupHeight > maxHeightPx) {
      pages.push([])
      currentHeight = 0
      currentPage = pages[pages.length - 1]
      if (currentPage === undefined) continue
    }

    for (const b of group) {
      currentPage.push(b)
      currentHeight += b.height
    }

    if (group.length > 1) i += 1
  }

  return pages
}
