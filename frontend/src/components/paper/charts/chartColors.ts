export const CHART_COLORS = ['#1058d6', '#2fb380', '#e08a1e', '#c2418f', '#5b6dd6', '#d64545']

export function colorForIndex (index: number): string {
  // Non-null assertion is safe: CHART_COLORS is a fixed non-empty literal and
  // `index % CHART_COLORS.length` is always a valid in-bounds index.
  // Needed because this project enables `noUncheckedIndexedAccess`, under which
  // element access types as `string | undefined`.
  return CHART_COLORS[index % CHART_COLORS.length]!
}
