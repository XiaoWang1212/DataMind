import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { fetchWorkflowJob, WorkflowJobNotFoundError } from '@/api/workflow'
import { clearActiveJobIdFromStorage, loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'

const JOB_POLL_INTERVAL_MS = 2000

export interface Project {
  id: string
  name: string
  description: string
  frameworkId: number | null
  frameworkName: string
  datasetName: string
  status: 'draft' | 'running' | 'completed'
  date: string
  progress: number
  accuracy?: string
  keyFinding?: string
  variables: number
}

export interface ActiveProjectContext {
  projectId: string
  datasetFile: File | null
  frameworkId: number | null
}

const STORAGE_KEY = 'datamind_projects'

const INITIAL_PROJECTS: Project[] = [
  {
    id: '1',
    name: '市場情緒研究',
    description: '',
    status: 'completed',
    frameworkId: 2,
    frameworkName: '市場情緒回歸',
    datasetName: 'customer_data.csv',
    date: '2026-05-29',
    progress: 100,
    accuracy: '87.3%',
    keyFinding: '購買頻率是流失率最強的預測因子（p < 0.001）',
    variables: 8,
  },
  {
    id: '2',
    name: '圖像分類實驗',
    description: '',
    status: 'running',
    frameworkId: 1,
    frameworkName: 'CNN 圖像分類',
    datasetName: 'image_dataset.csv',
    date: '2026-06-01',
    progress: 67,
    variables: 12,
  },
  {
    id: '3',
    name: '用戶導航分析',
    description: '',
    status: 'draft',
    frameworkId: 3,
    frameworkName: '用戶行為 RNN',
    datasetName: '',
    date: '2026-06-02',
    progress: 0,
    variables: 0,
  },
]

function loadFromStorage (): { projects: Project[], nextId: number } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return { projects: [...INITIAL_PROJECTS], nextId: INITIAL_PROJECTS.length + 1 }
    }
    const parsed = JSON.parse(raw) as { projects: Project[], nextId: number }
    if (Array.isArray(parsed.projects) && parsed.projects.length > 0) {
      return parsed
    }
  } catch {
    // ignore
  }
  return { projects: [...INITIAL_PROJECTS], nextId: INITIAL_PROJECTS.length + 1 }
}

export const useProjectStore = defineStore('project', () => {
  const saved = loadFromStorage()
  const projects = ref<Project[]>(saved.projects)
  const activeContext = ref<ActiveProjectContext | null>(null)
  let nextId = saved.nextId

  watch(
    projects,
    val => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ projects: val, nextId }))
      } catch { /* ignore */ }
    },
    { deep: true },
  )

  function addProject (p: Omit<Project, 'id'>): Project {
    const newProject: Project = { id: String(nextId++), ...p }
    projects.value = [newProject, ...projects.value]
    return newProject
  }

  function updateProjectStatus (projectId: string, status: Project['status']): void {
    const target = projects.value.find(p => p.id === projectId)
    if (target) {
      target.status = status
    }
  }

  function updateProjectProgress (projectId: string, progress: number): void {
    const target = projects.value.find(p => p.id === projectId)
    if (target) {
      target.progress = progress
    }
  }

  // store 是整個 App 生命週期內的單一實例，輪詢掛在這裡才不會因為離開 WorkflowWorkspace
  // 畫面（例如切回專案列表）就被砍掉，導致列表上的進度卡住、即使後端早就跑完了
  const jobPollers = new Map<string, { intervalId: number, jobId: string }>()

  function pollProjectJob (projectId: string, jobId: string): void {
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
            target.progress = Math.round((job.completedModels.length / job.totalModels) * 100)
          }

          if (job.status === 'done' || job.status === 'error') {
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            if (job.status === 'done') {
              target.progress = 100
              target.status = 'completed'
            }
          }
        } catch (error) {
          if (error instanceof WorkflowJobNotFoundError) {
            // job 在後端已經永久消失（重啟／超過 TTL），不是暫時性錯誤，停止輪詢並清掉過期紀錄
            window.clearInterval(intervalId)
            jobPollers.delete(projectId)
            clearActiveJobIdFromStorage(projectId)
            return
          }
          // 輪詢暫時失敗（網路抖動等），下一輪再試
        }
      })()
    }, JOB_POLL_INTERVAL_MS)
    jobPollers.set(projectId, { intervalId, jobId })
  }

  // App 重新載入時，把上次還在跑的 job 接續輪詢起來
  for (const p of projects.value) {
    const state = loadWorkflowStateFromStorage(p.id)
    if (state?.activeJobId) {
      pollProjectJob(p.id, state.activeJobId)
    }
  }

  function setActiveContext (ctx: ActiveProjectContext): void {
    activeContext.value = ctx
  }

  function clearActiveContext (): void {
    activeContext.value = null
  }

  return { projects, activeContext, addProject, updateProjectStatus, updateProjectProgress, pollProjectJob, setActiveContext, clearActiveContext }
})
