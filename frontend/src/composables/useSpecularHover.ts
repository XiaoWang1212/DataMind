import { onBeforeUnmount, onMounted, type Ref } from 'vue'

// 游標離按鈕多遠開始預熱。刻意比按鈕大很多，光是「接近」就先亮起來
const PROXIMITY = 180

// 角度與亮度的指數平滑係數。數字越大跟得越緊，太緊會顯得生硬
const ANGLE_EASE = 7
const GLOW_EASE = 8

interface Tracked {
  el: HTMLElement
  angle: number
  glow: number
}

// 所有按鈕共用一個 listener 與一個 rAF 迴圈，不隨按鈕數量增加
const tracked = new Map<HTMLElement, Tracked>()
let running = false
let raf = 0
let last = 0
let pointerX = Number.NaN
let pointerY = Number.NaN

function smoothstep (t: number): number {
  return t * t * (3 - 2 * t)
}

function frame (now: number): void {
  const dt = Math.min((now - last) / 1000, 0.05)
  last = now
  let anyLit = false

  for (const item of tracked.values()) {
    const rect = item.el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    // 游標到矩形的距離，在按鈕上時為 0
    const dx = Math.max(rect.left - pointerX, 0, pointerX - rect.right)
    const dy = Math.max(rect.top - pointerY, 0, pointerY - rect.bottom)
    const distance = Math.hypot(dx, dy)
    const targetGlow = distance > PROXIMITY ? 0 : smoothstep(1 - distance / PROXIMITY)

    let targetAngle: number
    if (distance === 0) {
      // 游標在按鈕上時，光源停在對角線讓四角都吃到光，再隨游標位置輕微擺動
      const nx = (pointerX - cx) / (rect.width / 2)
      const ny = (cy - pointerY) / (rect.height / 2)
      targetAngle = Math.atan2(2 / rect.height, -2 / rect.width) + nx * 0.3 + ny * 0.15
    } else {
      targetAngle = Math.atan2(cy - pointerY, pointerX - cx)
    }

    // 取最短路徑，否則從 179° 轉到 -179° 會繞一整圈
    const diff = ((targetAngle - item.angle + Math.PI * 3) % (Math.PI * 2)) - Math.PI
    item.angle += diff * (1 - Math.exp(-dt * ANGLE_EASE))
    item.glow += (targetGlow - item.glow) * (1 - Math.exp(-dt * GLOW_EASE))

    item.el.style.setProperty('--sb-angle', `${(item.angle * 180) / Math.PI}deg`)
    item.el.style.setProperty('--glow', item.glow.toFixed(3))

    if (item.glow > 0.002 || targetGlow > 0) {
      anyLit = true
    }
  }

  // 全部暗下來就停掉迴圈，游標再靠近時由 onPointerMove 重新啟動
  if (anyLit) {
    raf = requestAnimationFrame(frame)
  } else {
    running = false
    raf = 0
  }
}

function onPointerMove (event: PointerEvent): void {
  pointerX = event.clientX
  pointerY = event.clientY
  if (!running && tracked.size > 0) {
    running = true
    last = performance.now()
    raf = requestAnimationFrame(frame)
  }
}

// 觸控裝置點一下就會觸發 hover，光會亮在手指底下不滅；偏好減少動態時也不跑
function shouldTrack (): boolean {
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useSpecularHover (target: Ref<HTMLElement | null>): void {
  onMounted(() => {
    if (!target.value || !shouldTrack()) {
      return
    }
    tracked.set(target.value, { el: target.value, angle: 2.4, glow: 0 })
    if (tracked.size === 1) {
      window.addEventListener('pointermove', onPointerMove, { passive: true })
    }
  })

  onBeforeUnmount(() => {
    if (target.value) {
      tracked.delete(target.value)
    }
    if (tracked.size === 0) {
      window.removeEventListener('pointermove', onPointerMove)
      if (raf) {
        cancelAnimationFrame(raf)
        raf = 0
      }
      running = false
    }
  })
}
