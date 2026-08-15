import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createFramework, type CreateFrameworkPayload, listFrameworks, updateFramework } from '@/api/framework'

export interface Framework {
  id: number
  title: string
  subtitle: string
  tag: string
  date: string
  variables: number
  paperTitle: string
  description: string
  independentVars: string[]
  dependentVars: string[]
  hypotheses: string[]
  workflowJson?: Record<string, unknown>
}

export const useFrameworkStore = defineStore('framework', () => {
  const frameworks = ref<Framework[]>([])

  async function loadFrameworks (): Promise<void> {
    try {
      frameworks.value = await listFrameworks()
    } catch (error) {
      console.error('載入框架庫失敗', error)
    }
  }

  async function addFramework (fw: CreateFrameworkPayload): Promise<Framework> {
    const created = await createFramework(fw)
    frameworks.value = [created, ...frameworks.value]
    return created
  }

  async function renameFramework (id: number, title: string): Promise<void> {
    const target = frameworks.value.find(f => f.id === id)
    const previousTitle = target?.title
    if (target) {
      target.title = title
    }
    try {
      await updateFramework(id, { title })
    } catch (error) {
      if (target && previousTitle !== undefined) {
        target.title = previousTitle
      }
      console.error('更新框架名稱失敗', error)
      throw error
    }
  }

  return { frameworks, loadFrameworks, addFramework, renameFramework }
})
