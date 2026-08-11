import type { Ref } from 'vue'
import type { MappingItem, UserColumn } from '@/types/fieldMapping'
import { computed } from 'vue'

/**
 * 存編輯中的草稿。沒有它的話重新整理會把改過的全部沖掉，還會再打一次 Gemini。
 * 真正的結果是按下「確認並執行」才寫進資料庫。
 */
export function useMappingDraft (deps: {
  projectId: Ref<number>
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  aiAvailable: Ref<boolean>
  userColumns: Ref<UserColumn[]>
}) {
  const draftKey = computed(() => `datamind_field_mapping_draft_${deps.projectId.value}`)

  function columnSignature (): string {
    return deps.userColumns.value.map(c => c.name).join('|')
  }

  function saveDraft (): void {
    if (!deps.projectId.value) {
      return
    }
    try {
      localStorage.setItem(draftKey.value, JSON.stringify({
        columns: columnSignature(),
        items: deps.items.value,
        locked: [...deps.locked.value],
        aiAvailable: deps.aiAvailable.value,
      }))
    } catch (error) {
      console.warn('無法保存欄位對映草稿', error)
    }
  }

  function clearDraft (): void {
    localStorage.removeItem(draftKey.value)
  }

  function loadDraft (): boolean {
    try {
      const raw = localStorage.getItem(draftKey.value)
      if (!raw) {
        return false
      }
      const saved = JSON.parse(raw) as {
        columns?: string
        items?: MappingItem[]
        locked?: string[]
        aiAvailable?: boolean
      }
      // 換了資料集就不能沿用舊草稿，裡面的欄位名已經對不上了
      if (saved.columns !== columnSignature()) {
        clearDraft()
        return false
      }
      if (!Array.isArray(saved.items) || saved.items.length === 0) {
        return false
      }
      deps.items.value = saved.items
      deps.locked.value = new Set<string>(saved.locked)
      // 沿用當初的可用狀態：寫死 true 的話，Gemini 掛掉時重整會讓離線提示消失、
      // 輸入框又變成可打，送出才發現還是不通
      deps.aiAvailable.value = saved.aiAvailable ?? true
      return true
    } catch {
      localStorage.removeItem(draftKey.value)
      return false
    }
  }

  return { saveDraft, loadDraft, clearDraft }
}
