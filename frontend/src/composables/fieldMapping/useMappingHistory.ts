import type { Ref } from 'vue'
import type { MappingItem } from '@/types/fieldMapping'
import { onBeforeUnmount, onMounted, ref, toRaw } from 'vue'

// Ctrl+Z 用的快照堆疊。上限避免使用者改很久之後記憶體一直長大
const MAX_UNDO = 50

interface Snapshot { items: MappingItem[], locked: string[] }

/**
 * 對映表的復原/重做。鍵盤監聽也包在裡面，所以頁面只需要在改動前呼叫 pushHistory()。
 *
 * @param deps.onRestore 還原之後要做的事（例如清掉錯誤訊息、存草稿）
 */
export function useMappingHistory (deps: {
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  onRestore: () => void
}) {
  const undoStack = ref<Snapshot[]>([])
  const redoStack = ref<Snapshot[]>([])

  /**
   * 改動前先存快照。沒有復原的話，點錯一步只能整頁重跑。
   *
   * locked 一定要跟著存：只還原 items 的話，復原後那一列看起來回到未對應，
   * 但它還留在 locked 裡，之後所有 AI 建議都會被靜默忽略，而聊天仍回「已更新」。
   */
  function snapshot (): Snapshot {
    return { items: structuredClone(toRaw(deps.items.value)), locked: [...deps.locked.value] }
  }

  function restore (snap: Snapshot): void {
    deps.items.value = snap.items
    deps.locked.value = new Set(snap.locked)
    deps.onRestore()
  }

  function pushHistory (): void {
    undoStack.value.push(snapshot())
    if (undoStack.value.length > MAX_UNDO) {
      undoStack.value.shift()
    }
    // 做了新動作，原本能重做的那條分支就失效了
    redoStack.value = []
  }

  function undo (): void {
    const previous = undoStack.value.pop()
    if (!previous) {
      return
    }
    redoStack.value.push(snapshot())
    restore(previous)
  }

  function redo (): void {
    const next = redoStack.value.pop()
    if (!next) {
      return
    }
    undoStack.value.push(snapshot())
    restore(next)
  }

  /** 焦點在輸入框時不攔截：那時使用者要復原的是自己打的字。 */
  function onKeydown (event: KeyboardEvent): void {
    if (!(event.metaKey || event.ctrlKey)) {
      return
    }

    // 重做的按法各家不同：Mac 是 ⌘⇧Z，Windows 上 Ctrl+Y 與 Ctrl+Shift+Z 都常見，三種都收
    const key = event.key.toLowerCase()
    const isRedo = (key === 'z' && event.shiftKey) || key === 'y'
    const isUndo = key === 'z' && !event.shiftKey
    if (!isRedo && !isUndo) {
      return
    }

    const target = event.target as HTMLElement | null
    const tag = target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) {
      return
    }

    event.preventDefault()
    if (isRedo) {
      redo()
    } else {
      undo()
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

  return { pushHistory }
}
