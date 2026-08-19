// 借用 §2.3 的節點分類色系，避開綠/琥珀/紅——那三色是狀態語意，混進圖表資料色會誤導
export const CHART_COLORS = [
  'var(--color-node-visualize)',
  'var(--color-node-model)',
  'var(--color-node-source)',
  'var(--color-node-transform)',
  'var(--color-node-evaluate)',
  'var(--color-ink-strong)',
]

export function colorForIndex (index: number): string {
  // Non-null assertion is safe: CHART_COLORS is a fixed non-empty literal and
  // `index % CHART_COLORS.length` is always a valid in-bounds index.
  // Needed because this project enables `noUncheckedIndexedAccess`, under which
  // element access types as `string | undefined`.
  return CHART_COLORS[index % CHART_COLORS.length]!
}
