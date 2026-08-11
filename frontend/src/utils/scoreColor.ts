// frontend/src/utils/scoreColor.ts
export const SCORE_THRESHOLD = 80
export const SCORE_COLOR_HIGH = '#0d5d73'
export const SCORE_COLOR_LOW = '#8a6d1a'

export function getScoreColor (score: number): string {
  return score >= SCORE_THRESHOLD ? SCORE_COLOR_HIGH : SCORE_COLOR_LOW
}
