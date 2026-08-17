import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createProject, type CreateProjectPayload, listProjects, updateProject } from '@/api/project'
import { fetchWorkflowJob, WorkflowJobNotFoundError } from '@/api/workflow'
import { clearActiveJobIdFromStorage, loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'

const JOB_POLL_INTERVAL_MS = 2000

export interface VariableMapping {
  column: string
  type: string
}

export interface Project {
  id: number
  name: string
  description: string
  frameworkId: number | null
  datasetName: string
  status: 'draft' | 'running' | 'completed'
  date: string
  progress: number
  accuracy?: string
  keyFinding?: string
  variables: number
  /** 對映關係：{ 論文變數名: { column: 使用者欄位名, type: 變數型別 } }。 */
  columnMapping?: Record<string, VariableMapping> | null
}

export interface ActiveProjectContext {
  projectId: number
  datasetFile: File | null
  frameworkId: number | null
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const activeContext = ref<ActiveProjectContext | null>(null)

  async function loadProjects (): Promise<void> {
    try {
      projects.value = await listProjects()
    } catch (error) {
      console.error('載入專案列表失敗', error)
      return
    }

    // App 重新載入時，把上次還在跑的 job 接續輪詢起來
    for (const p of projects.value) {
      const state = loadWorkflowStateFromStorage(String(p.id))
      if (state?.activeJobId) {
        pollProjectJob(p.id, state.activeJobId)
      }
    }
  }

  async function addProject (p: CreateProjectPayload): Promise<Project> {
    const created = await createProject(p)
    projects.value = [created, ...projects.value]
    return created
  }

  async function updateProjectStatus (projectId: number, status: Project['status']): Promise<void> {
    const target = projects.value.find(p => p.id === projectId)
    if (target) {
      target.status = status
    }
    try {
      await updateProject(projectId, { status, progress: target?.progress })
    } catch (error) {
      console.error('更新專案狀態失敗', error)
    }
  }

  // 執行過程中的進度只更新本地畫面；真正寫回資料庫的時機是狀態轉換
  // （updateProjectStatus 會把當下的 progress 一併帶進 PATCH），避免每次輪詢都打一次 API
  function setProjectProgress (projectId: number, progress: number): void {
    const target = projects.value.find(p => p.id === projectId)
    if (target) {
      target.progress = progress
    }
  }

  // store 是整個 App 生命週期內的單一實例，輪詢掛在這裡才不會因為離開 WorkflowWorkspace
  // 畫面（例如切回專案列表）就被砍掉，導致列表上的進度卡住、即使後端早就跑完了
  const jobPollers = new Map<number, { intervalId: number, jobId: string }>()

  function pollProjectJob (projectId: number, jobId: string): void {
    const existing = jobPollers.get(projectId)
    if (existing) {
      if (existing.jobId === jobId) {
        return
      }
      window.clearInterval(existing.intervalId)
    }

    const intervalId = window.setInterval(() => {
      ;(async () => {
        try {
          const job = await fetchWorkflowJob(jobId)
          const target = projects.value.find(p => p.id === projectId)
          if (!target) {
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            return
          }

          if (job.totalModels > 0) {
            // 進行中的 tick 只改本地畫面，不寫回資料庫；完成時才持久化（見下方）
            target.progress = Math.round((job.completedModels.length / job.totalModels) * 100)
          }

          if (job.status === 'done' || job.status === 'error') {
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            if (job.status === 'done') {
              target.progress = 100
              await updateProjectStatus(projectId, 'completed')
            }
          }
        } catch (error) {
          if (error instanceof WorkflowJobNotFoundError) {
            // job 在後端已經永久消失（重啟／超過 TTL），不是暫時性錯誤，停止輪詢並清掉過期紀錄
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            clearActiveJobIdFromStorage(String(projectId))
            return
          }
          // 輪詢暫時失敗（網路抖動等），下一輪再試
        }
      })()
    }, JOB_POLL_INTERVAL_MS)
    jobPollers.set(projectId, { intervalId, jobId })
  }

  // 供「放棄 job」流程呼叫：只停止輪詢、不做其他事（不寫回資料庫、不清 activeContext），
  // 讓呼叫端（例如中斷確認）自行決定後續要不要更新狀態
  function stopProjectJobPolling (projectId: number): void {
    const existing = jobPollers.get(projectId)
    if (!existing) return
    window.clearInterval(existing.intervalId)
    jobPollers.delete(projectId)
  }

  function setActiveContext (ctx: ActiveProjectContext): void {
    activeContext.value = ctx
  }

  function clearActiveContext (): void {
    activeContext.value = null
  }

  /**
   * 把欄位對映存回資料庫。
   *
   * store 是 API-backed 的：只改本地 ref 不等於存檔，一定要打 API，
   * 否則使用者重新整理就會發現對映不見了。
   */
  async function saveColumnMapping (
    projectId: number,
    mapping: Record<string, VariableMapping>,
  ): Promise<void> {
    const variables = Object.keys(mapping).length
    const target = projects.value.find(p => p.id === projectId)
    const previous = target && { columnMapping: target.columnMapping, variables: target.variables }
    if (target) {
      target.columnMapping = mapping
      target.variables = variables
    }
    try {
      await updateProject(projectId, { columnMapping: mapping, variables })
    } catch (error) {
      // API 失敗時要把本地狀態復原：store 絕不能在資料庫拒絕寫入的情況下，
      // 還讓畫面顯示這筆對映已經存檔
      if (target && previous) {
        target.columnMapping = previous.columnMapping
        target.variables = previous.variables
      }
      console.error('儲存欄位對映失敗', error)
      throw error
    }
  }

  return { projects, activeContext, loadProjects, addProject, updateProjectStatus, setProjectProgress, pollProjectJob, stopProjectJobPolling, setActiveContext, clearActiveContext, saveColumnMapping }
})
