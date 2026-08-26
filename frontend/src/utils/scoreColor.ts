// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80

// 進度條填色，圖形元素只需過 3:1
const FILL_COLOR_HIGH = 'var(--color-success)'
const FILL_COLOR_LOW = 'var(--color-score-low)'

// 文字色需過 4.5:1，score-low 的金黃疊白底只有 2.55:1 不能當文字
const TEXT_COLOR_HIGH = 'var(--color-success-text)'
const TEXT_COLOR_LOW = 'var(--color-warning-text)'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? FILL_COLOR_HIGH : FILL_COLOR_LOW
}

export function getScoreTextColor (score: number): string {
  return score >= SCORE_THRESHOLD ? TEXT_COLOR_HIGH : TEXT_COLOR_LOW
}
