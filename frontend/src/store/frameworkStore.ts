import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createFramework, type CreateFrameworkPayload, listFrameworks } from '@/api/framework'

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

  return { frameworks, loadFrameworks, addFramework }
})
