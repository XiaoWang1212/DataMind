// frontend/src/utils/journalTheme.ts
export interface JournalAccent {
  main: string
  soft: string
  text: string
}

const JOURNAL_ACCENTS: Record<string, JournalAccent> = {
  JAMIA: { main: '#1058d6', soft: '#eaf1fd', text: '#1058d6' },
  'npj Digital Medicine': { main: '#8a6d1a', soft: '#fffbe8', text: '#8a6d1a' },
  'BMC Medical Informatics and Decision Making': { main: '#0d5d73', soft: '#e6f3f6', text: '#0d5d73' },
}

const DEFAULT_ACCENT: JournalAccent = { main: '#4a4f5c', soft: '#eef0f4', text: '#4a4f5c' }

export function getJournalAccent (journal: string): JournalAccent {
  return JOURNAL_ACCENTS[journal] ?? DEFAULT_ACCENT
}
