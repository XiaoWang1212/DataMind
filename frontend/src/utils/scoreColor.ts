// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80

// 進度條填色（圖形元素，只需過 3:1）：低分用鮮豔金黃，跟成功色的視覺份量對稱
const FILL_COLOR_HIGH = 'var(--color-success)'
const FILL_COLOR_LOW = 'var(--color-score-low)'

// 分數數字文字色（疊白底，需過 4.5:1）：低分文字改用 warning-text 的深色版本，
// score-low 那個鮮豔金黃疊白底只有 2.55:1，不能直接當文字用
const TEXT_COLOR_HIGH = 'var(--color-success-text)'
const TEXT_COLOR_LOW = 'var(--color-warning-text)'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? FILL_COLOR_HIGH : FILL_COLOR_LOW
}

export function getScoreTextColor (score: number): string {
  return score >= SCORE_THRESHOLD ? TEXT_COLOR_HIGH : TEXT_COLOR_LOW
}
