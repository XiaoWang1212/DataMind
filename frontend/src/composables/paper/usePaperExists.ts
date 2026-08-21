import type { Ref } from 'vue'
import { ref, watch } from 'vue'
import { getReport } from '@/api/report'

// 是否已經有生成過的論文；null 代表查詢中，先不要顯示任何按鈕避免閃爍
export function usePaperExists (projectId: Ref<string | number | undefined>) {
  const hasPaper = ref<boolean | null>(null)

  async function check (): Promise<void> {
    if (!projectId.value) {
      hasPaper.value = false
      return
    }
    hasPaper.value = null
    try {
      const report = await getReport(String(projectId.value))
      hasPaper.value = report !== null
    } catch {
      // 查詢失敗就保守當作沒有論文，讓使用者至少還能走生成流程
      hasPaper.value = false
    }
  }

  watch(projectId, check, { immediate: true })

  return { hasPaper, refresh: check }
}
