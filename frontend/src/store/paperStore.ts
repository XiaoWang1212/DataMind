import type { PaperReport } from '@/constants/reportData'
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePaperStore = defineStore('paper', () => {
  const generatedReport = ref<PaperReport | null>(null)

  function setGeneratedReport (report: PaperReport): void {
    generatedReport.value = report
  }

  function clearGeneratedReport (): void {
    generatedReport.value = null
  }

  return { generatedReport, setGeneratedReport, clearGeneratedReport }
})
