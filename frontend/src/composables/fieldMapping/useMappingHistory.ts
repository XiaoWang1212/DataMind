import type { Ref } from 'vue'
import type { MappingItem } from '@/types/fieldMapping'
import { onBeforeUnmount, onMounted, ref, toRaw } from 'vue'

// 設上限，避免快照無限累積佔記憶體
const MAX_UNDO = 50

interface Snapshot { items: MappingItem[], locked: string[] }

// 對映表的復原/重做，鍵盤監聽包在裡面，頁面只需在改動前呼叫 pushHistory()
export function useMappingHistory (deps: {
  items: Ref<MappingItem[]>
  locked: Ref<Set<string>>
  onRestore: () => void
}) {
  const undoStack = ref<Snapshot[]>([])
  const redoStack = ref<Snapshot[]>([])

  // locked 要跟著存，只還原 items 的話該列仍留在 locked 裡，之後的 AI 建議會被忽略
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
    // 做了新動作，原本的重做分支失效
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

  // 焦點在輸入框時不攔截，那時要復原的是使用者打的字
  function onKeydown (event: KeyboardEvent): void {
    if (!(event.metaKey || event.ctrlKey)) {
      return
    }

    // 重做的按法各平台不同，⌘⇧Z、Ctrl+Shift+Z、Ctrl+Y 三種都接受
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
