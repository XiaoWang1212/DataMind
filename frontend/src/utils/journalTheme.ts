// frontend/src/utils/journalTheme.ts
export interface JournalAccent {
  main: string
  soft: string
  text: string
}

// 三個期刊是分類色不是狀態色，借用 §2.3 的節點分類 token，避開綠/琥珀/紅
const JOURNAL_ACCENTS: Record<string, JournalAccent> = {
  'JAMIA': { main: 'var(--color-node-visualize)', soft: 'var(--color-surface-alt)', text: 'var(--color-node-visualize)' },
  'npj Digital Medicine': { main: 'var(--color-node-model)', soft: 'var(--color-surface-alt)', text: 'var(--color-node-model)' },
  'BMC Medical Informatics and Decision Making': { main: 'var(--color-node-source)', soft: 'var(--color-surface-alt)', text: 'var(--color-node-source)' },
}

const DEFAULT_ACCENT: JournalAccent = { main: 'var(--color-ink-soft)', soft: 'var(--color-surface-alt)', text: 'var(--color-ink-soft)' }

export function getJournalAccent (journal: string): JournalAccent {
  return JOURNAL_ACCENTS[journal] ?? DEFAULT_ACCENT
}
