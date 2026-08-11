import { onBeforeUnmount, onMounted, type Ref } from 'vue'

// 滑鼠距離按鈕多遠開始亮。貼到邊框時最亮，超過這個距離完全不亮
const PROXIMITY = 90

// 模組層級的註冊表：所有按鈕共用一個 listener，不隨按鈕數量增加
const tracked = new Set<HTMLElement>()
let listening = false
let frame = 0
let pointerX = 0
let pointerY = 0

function update (): void {
  frame = 0
  for (const el of tracked) {
    const rect = el.getBoundingClientRect()
    // 滑鼠到矩形的距離，在框內時為 0
    const dx = Math.max(rect.left - pointerX, 0, pointerX - rect.right)
    const dy = Math.max(rect.top - pointerY, 0, pointerY - rect.bottom)
    const distance = Math.hypot(dx, dy)
    const glow = distance > PROXIMITY ? 0 : 1 - distance / PROXIMITY
    el.style.setProperty('--mx', `${pointerX - rect.left}px`)
    el.style.setProperty('--my', `${pointerY - rect.top}px`)
    el.style.setProperty('--glow', glow.toFixed(3))
  }
}

function onPointerMove (event: PointerEvent): void {
  pointerX = event.clientX
  pointerY = event.clientY
  if (frame === 0) {
    frame = requestAnimationFrame(update)
  }
}

// 觸控裝置點一下就會觸發 hover，反光會亮在手指底下不滅；直接不註冊
function supportsHover (): boolean {
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches
}

export function useSpecularHover (target: Ref<HTMLElement | null>): void {
  onMounted(() => {
    if (!target.value || !supportsHover()) {
      return
    }
    tracked.add(target.value)
    if (!listening) {
      window.addEventListener('pointermove', onPointerMove, { passive: true })
      listening = true
    }
  })

  onBeforeUnmount(() => {
    if (target.value) {
      tracked.delete(target.value)
    }
    if (tracked.size === 0 && listening) {
      window.removeEventListener('pointermove', onPointerMove)
      listening = false
      if (frame) {
        cancelAnimationFrame(frame)
        frame = 0
      }
    }
  })
}
