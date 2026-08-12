// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80
export const SCORE_COLOR_HIGH = 'var(--color-success)'
export const SCORE_COLOR_LOW = 'var(--color-warning)'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? SCORE_COLOR_HIGH : SCORE_COLOR_LOW
}
