import type { Project } from '@/store/projectStore'

// 用 null 判斷而非空物件：使用者可能全部選「資料表中沒有此變數」，
// 那時對映是 {} 但他確實走完了流程，不該再被推回這一頁
function needsMapping (project: Project): boolean {
  return project.status !== 'completed' && project.columnMapping == null
}

// 進行中代表 workflow 還沒跑完，直接點進去繼續；其他狀態先進詳情頁
export function projectLink (project: Project): string {
  if (needsMapping(project)) return `/hub/projects/${project.id}/mapping`
  return project.status === 'running'
    ? `/workflow?project=${project.id}`
    : `/hub/projects/${project.id}`
}
