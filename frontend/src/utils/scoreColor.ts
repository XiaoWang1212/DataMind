// 分數不分高低，統一用品牌藍——曾經是「≥80 綠色/其餘金黃色」的二元判斷，
// 但多數分數落在 80 以下，金黃色佔滿畫面，跟評分失敗的警告色也撞在一起。
const SCORE_COLOR = 'var(--color-ink)'

export function getScoreColor (_score: number): string {
  return SCORE_COLOR
}
