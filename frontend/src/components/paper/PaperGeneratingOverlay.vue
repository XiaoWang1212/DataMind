<template>
  <div
    v-if="visible"
    ref="rootRef"
    aria-live="polite"
    class="pgo"
    role="status"
  >
    <div class="pgo-card">
      <!-- 字樣本體。字母、疊在字上的圖層、落下的方塊都由 build() 依實際量到的
           字母位置產生，所以換字級或字型 fallback 都還是對齊的 -->
      <div ref="wmRef" class="pgo-wm">
        <span ref="grpDataRef" class="pgo-grp" /><span ref="grpMindRef" class="pgo-grp" />
      </div>

      <div class="pgo-captions">
        <span>下載參考文獻中…</span>
        <span>整理實驗結果中…</span>
        <span>比對引用來源中…</span>
        <span>撰寫章節中…</span>
      </div>

      <div
        aria-label="生成進度"
        :aria-valuenow="Math.round(progress)"
        class="pgo-progress"
        role="progressbar"
      >
        <div class="pgo-progress-fill" :style="{ width: `${progress}%` }" />
      </div>

      <p class="pgo-hint">這可能需要幾分鐘，請不要關閉視窗</p>

      <!-- 逸出口。刻意延遲出現：正常等待時不該把「放棄」放在眼前，
           但後端卡住時必須有路可走，否則只能重整頁面。
           一直留在版面上、只切換可見度 —— 用 v-if 的話卡片會在它出現時抽高一截 -->
      <button
        class="pgo-abandon"
        :class="{ 'pgo-abandon--on': showAbandon }"
        :tabindex="showAbandon ? 0 : -1"
        type="button"
        @click="handleAbandon"
      >
        放棄並返回
      </button>
    </div>

  </div>
</template>

<script setup lang="ts">
  import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

  const props = defineProps<{ visible: boolean, complete?: boolean }>()
  const emit = defineEmits<{ abandon: [] }>()

  // 後端 /api/rag/arxiv/generate 是一發同步請求，拿不到真實進度，只能依經過時間估算。
  // 前段快、後段趨緩，停在 90% 等實際完成，避免進度條到底了工作還沒結束。
  // 節奏與上方那四句階段文字無關：那四句是 17 秒一輪的循環動畫，不對應真實階段
  const PROGRESS_CEILING = 90
  // 衰減常數。60 秒約到 60%、兩分鐘約 80%、三分鐘約 87%
  const PROGRESS_TAU_MS = 55_000
  const PROGRESS_TICK_MS = 240

  const WORD_A = 'Data'
  // ı 是無點的 i（U+0131）。i 的點另外做成獨立元素，才能離開字身去別的地方
  const WORD_B = ['M', 'ı', 'n', 'd']

  const SPARK_SVG = `
    <svg viewBox="0 0 36 36">
      <circle class="pgo-halo" cx="18" cy="18" r="9"/>
      <path class="pgo-core" d="M18 1.6c1 8.4 6.9 14.3 15.3 15.3-8.4 1-14.3 6.9-15.3 15.3-1-8.4-6.9-14.3-15.3-15.3C11.1 15.9 17 10 18 1.6Z"/>
    </svg>`

  const ABANDON_DELAY_MS = 30_000

  const rootRef = ref<HTMLElement | null>(null)
  const wmRef = ref<HTMLElement | null>(null)
  const grpDataRef = ref<HTMLElement | null>(null)
  const grpMindRef = ref<HTMLElement | null>(null)
  const showAbandon = ref(false)
  const progress = ref(0)
  let progressTimer: number | undefined
  let progressStart = 0

  function tickProgress (): void {
    const elapsed = performance.now() - progressStart
    progress.value = PROGRESS_CEILING * (1 - Math.exp(-elapsed / PROGRESS_TAU_MS))
  }

  function startProgress (): void {
    progress.value = 0
    progressStart = performance.now()
    progressTimer = window.setInterval(tickProgress, PROGRESS_TICK_MS)
  }

  function stopProgress (): void {
    window.clearInterval(progressTimer)
    progressTimer = undefined
  }

  // 生成完成到畫面切走之間還有存檔要跑，那段時間夠這條走完最後一段
  watch(() => props.complete, done => {
    if (!done) return
    stopProgress()
    progress.value = 100
  })

  // 逐字母的 keyframes 由 JS 產生（每個字母壓扁比例不同、方塊落點每圈不同），
  // 掛在這個節點上。元件收起來時一併移除
  // 所有循環動畫共用的起點。每個動畫預設從「自己的元素被建立的那一刻」開始算，
  // 但字母、星星、描邊層都是 build() 建出來的，而 build() 會在字型載入完成、
  // 每圈結束、視窗縮放時重跑 —— 沒有共用時鐘的話，它們會跟固定在版面上的
  // 階段文字愈差愈多，最後變成字樣在上墨、文字還停在第一句
  let loopStart: number | null = null
  let genStyle: HTMLStyleElement | undefined
  let abandonTimer: number | undefined
  let grpHeight = 0
  // 每一圈換一組數值：表格裡的長條、引用網的節點位置、哪些字母會接到文獻方塊。
  // 一圈 17 秒，等三分鐘會看十圈，十次一模一樣會被看出是同一段在重播
  let variant = 0

  function rnd (i: number): number {
    const x = Math.sin(variant * 37.13 + i * 91.7) * 10_000
    return x - Math.floor(x)
  }

  function buildLetters (): void {
    if (!grpDataRef.value || !grpMindRef.value) return
    grpDataRef.value.innerHTML = [...WORD_A]
      .map((ch, i) => `<span class="pgo-ltr" data-w="${i}">${ch}</span>`)
      .join('')
    grpMindRef.value.innerHTML = WORD_B
      .map((ch, i) => `<span class="pgo-ltr" data-w="${i + 4}">${ch}</span>`)
      .join('')
      + `<span class="pgo-tittle">
           <span class="pgo-dot"></span>
           <span class="pgo-spark"><span class="pgo-spin">${SPARK_SVG}</span></span>
         </span>`
  }

  interface LetterBox { cx: number, w: number }

  // 量出每個字母的中心與寬度。所有圖形的位置都從這裡推出來，不寫死座標。
  // 用 offsetLeft/offsetWidth 而不是 getBoundingClientRect —— 後者回傳的是套過
  // transform 之後的座標，卡片進場的 scale 動畫還在跑時量到的值會整組偏掉
  function measure (grp: HTMLElement): LetterBox[] {
    return Array.from(grp.querySelectorAll<HTMLElement>('.pgo-ltr'), el => ({
      cx: el.offsetLeft + el.offsetWidth / 2,
      w: el.offsetWidth,
    }))
  }

  function svgLayer (w: number, h: number, inner: string, cls: string): string {
    return `<svg class="pgo-layer ${cls}" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"
             style="top:${(grpHeight - h) / 2}px">${inner}</svg>`
  }

  function build (): void {
    const wm = wmRef.value
    const grpData = grpDataRef.value
    const grpMind = grpMindRef.value
    if (!wm || !grpData || !grpMind) return

    buildLetters()

    const fs = Number.parseFloat(getComputedStyle(wm).fontSize)
    grpHeight = grpData.offsetHeight

    const cellW = fs * 0.44
    const cellH = fs * 0.19
    const gapY = fs * 0.09

    const wmW = wm.offsetWidth
    const A = measure(grpData)
    const B = measure(grpMind)
    // 兩個字群的 offsetParent 都是 .pgo-wm，所以 offsetLeft 就是相對整組字的位置
    const boxA = { left: grpData.offsetLeft, width: grpData.offsetWidth, height: grpData.offsetHeight }
    const boxB = { left: grpMind.offsetLeft, width: grpMind.offsetWidth, height: grpMind.offsetHeight }

    // ---------- 表格：每一欄對準一個字母 ----------
    // 對得上是因為 workflow 的實驗結果在這個產品裡本來就是一張表
    const hA = boxA.height
    const midY = hA / 2
    let mids = ''
    let sides = ''
    let lit = ''
    for (const { cx } of A) {
      const x = cx - cellW / 2
      mids += `<rect class="pgo-cell-mid" x="${x}" y="${midY - cellH / 2}" width="${cellW}" height="${cellH}" rx="2.5"/>`
      for (const dir of [-1, 1]) {
        const y = midY - cellH / 2 + dir * (cellH + gapY)
        sides += `<rect class="pgo-cell-side" x="${x}" y="${y}" width="${cellW}" height="${cellH}" rx="2.5"
                    style="transform-origin:${cx}px ${midY}px"/>`
      }
      for (const dy of [-(cellH + gapY), 0, cellH + gapY]) {
        const y = midY - cellH / 2 + dy
        lit += `<rect class="pgo-cell-lit" x="${x}" y="${y}" width="${cellW}" height="${cellH}" rx="2.5"/>`
        // 每格裡一條長短不一的細條 = 數值。沒有它，表格讀起來只是一堆空格子
        const ratio = 0.3 + rnd(cx + dy * 3) * 0.62
        lit += `<rect class="pgo-cell-bar" x="${x + cellW * 0.12}" y="${y + cellH * 0.34}"
                  width="${(cellW * 0.76 * ratio).toFixed(1)}" height="${(cellH * 0.32).toFixed(1)}" rx="1.5"/>`
      }
    }
    grpData.insertAdjacentHTML('beforeend',
                               svgLayer(boxA.width, hA, sides + mids + `<g class="pgo-wipe-cells">${lit}</g>`, 'pgo-layer-table'))

    // ---------- 引用關係網：節點從字母中心出發，再散開成星座 ----------
    // 刻意不排成整齊的層狀 —— 層狀會讀成神經網路，但模型是 workflow 早就跑完的事，
    // 這一步在做的是文獻引用
    const hB = boxB.height
    const midB = hB / 2
    const r = fs * 0.075
    const spread = fs * 0.3
    const W = boxB.width
    const jx = (i: number): number => (rnd(200 + i) - 0.5) * W * 0.07
    const jy = (i: number): number => (rnd(300 + i) - 0.5) * spread * 0.5
    const targets = [
      { x: W * 0.08 + jx(0), y: midB - spread * 1.05 + jy(0) },
      { x: W * 0.27 + jx(1), y: midB + spread * 1.3 + jy(1) },
      { x: W * 0.74 + jx(2), y: midB - spread * 1.35 + jy(2) },
      { x: W * 0.95 + jx(3), y: midB + spread * 0.85 + jy(3) },
    ]
    // 中間那顆是「本篇論文」，最後才長出來，比較大
    const hub = { x: W * 0.51, y: midB, r: r * 1.5 }
    const extra = { x: W * 0.66, y: midB + spread * 1.15, r }

    let nodes = ''
    let nodesLit = ''
    for (const [i, { cx }] of B.entries()) {
      const t = targets[i]
      if (!t) continue
      const style = `--tx:${(t.x - cx).toFixed(1)}px; --ty:${(t.y - midB).toFixed(1)}px`
      nodes += `<circle class="pgo-node" cx="${cx}" cy="${midB}" r="${r}" style="${style}"/>`
      nodesLit += `<circle class="pgo-node pgo-node-lit" cx="${cx}" cy="${midB}" r="${r}" style="${style}"/>`
    }
    for (const e of [extra, hub]) {
      nodes += `<circle class="pgo-node pgo-node-extra" cx="${e.x}" cy="${e.y}" r="${e.r}"/>`
      nodesLit += `<circle class="pgo-node pgo-node-extra pgo-node-lit" cx="${e.x}" cy="${e.y}" r="${e.r}"/>`
    }

    let edges = ''
    const link = (a: { x: number, y: number }, b: { x: number, y: number }): void => {
      const len = Math.hypot(b.x - a.x, b.y - a.y).toFixed(1)
      edges += `<path class="pgo-edge" d="M${a.x.toFixed(1)} ${a.y.toFixed(1)} L${b.x.toFixed(1)} ${b.y.toFixed(1)}" style="--len:${len}"/>`
    }
    // 每篇文獻都連向本篇論文，再補一條文獻之間的交叉引用
    for (const t of [...targets, extra]) link(t, hub)
    const crossRef = targets[1]
    if (crossRef) link(crossRef, extra)

    grpMind.insertAdjacentHTML('beforeend',
                               svgLayer(boxB.width, hB, edges + nodes + `<g class="pgo-wipe-nodes">${nodesLit}</g>`, 'pgo-layer-net'))

    // ---------- 星星的位置與航點 ----------
    const iCenter = B[1]?.cx ?? 0
    const tittle = grpMind.querySelector<HTMLElement>('.pgo-tittle')
    if (tittle) {
      tittle.style.left = `${iCenter}px`
      tittle.style.top = `${fs * 0.09}px`

      const homeAbs = boxB.left + iCenter
      const px = (v: number): string => `${v.toFixed(1)}px`
      // 設在 wm 上而不是星星上：build() 每圈都會重建星星那個元素，
      // 設在它身上等於每圈都得重設一次；自訂屬性會繼承，設在穩定的祖先最安全
      const setVar = (k: string, v: string): void => wm.style.setProperty(k, v)
      const margin = fs * 0.23
      setVar('--sweep-from', px(wmW - homeAbs + margin))
      setVar('--sweep-to', px(-homeAbs - margin))
      setVar('--to-data', px(boxA.left + boxA.width / 2 - homeAbs))
      setVar('--to-mind', px(boxB.left + boxB.width / 2 - homeAbs))
      // 上墨時筆尖的路徑：整組字的左緣 → 三分之一 → 三分之二 → 右緣
      setVar('--pen-l', px(-homeAbs + fs * 0.05))
      setVar('--pen1', px(wmW * 0.34 - homeAbs))
      setVar('--pen2', px(wmW * 0.66 - homeAbs))
      setVar('--pen-r', px(wmW - homeAbs - fs * 0.05))
    }

    // ---------- 落下的文獻方塊。一塊 = 抓到一篇 ----------
    for (const el of Array.from(wm.querySelectorAll('.pgo-chip'))) el.remove()
    const chipSet = new Set<number>()
    const centers = [
      ...A.map(m => boxA.left + m.cx),
      ...B.map(m => boxB.left + m.cx),
    ]
    for (const [i, cx] of centers.entries()) {
      // 每圈略過約三成。每個字母都接到方塊的話就只是裝飾性的波浪，
      // 有選擇性才讀得出來是「被砸中」
      if (rnd(100 + i) < 0.3) continue
      chipSet.add(i)
      const chip = document.createElement('span')
      chip.className = 'pgo-chip'
      chip.innerHTML = '<i></i><i></i><i></i>'
      chip.style.left = `${cx.toFixed(1)}px`
      chip.style.setProperty('--cw', `${(fs * 0.3).toFixed(1)}px`)
      chip.style.animation = `pgo-chip-${i} var(--pgo-loop) linear infinite`
      wm.append(chip)
    }

    // ---------- 描邊層與上墨層 ----------
    // 跟本體同一串文字、同一個容器座標，所以會完全重疊。字形從頭到尾都是同一個，
    // 差別只有空心變實心 —— 換成別的字形就會變成「換字體」而不是「被寫出來」
    for (const el of Array.from(wm.querySelectorAll('.pgo-copy'))) el.remove()
    for (const cls of ['pgo-ghost', 'pgo-ink']) {
      const el = document.createElement('span')
      el.className = `pgo-copy ${cls}`
      el.textContent = 'DataMınd'
      wm.append(el)
    }

    generateLetterKeyframes(A, B, cellW, fs, chipSet)
    syncLoops()
  }

  // 每個字母一組 keyframes：方塊落點各自錯開、壓扁比例各自不同。
  // 不用 animation-delay —— delay 會讓該元素的整條時間軸位移，第二圈就跟別人對不上
  function generateLetterKeyframes (
    A: LetterBox[], B: LetterBox[], cellW: number, fs: number, chipSet: Set<number>,
  ): void {
    const css: string[] = []
    const all = [
      ...A.map(a => ({ ...a, kind: 'data' as const })),
      ...B.map(b => ({ ...b, kind: 'mind' as const })),
    ]

    for (const [idx, item] of all.entries()) {
      // 文獻方塊由右往左依序落下，星星也是從字尾掃到字頭
      const w0 = 12 + (all.length - 1 - idx) * 2 // 砸中的瞬間
      const w1 = w0 + 1.4 // 沉到最低
      const w2 = w0 + 4.2 // 彈回原位
      const hit = chipSet.has(idx)

      if (hit) {
        const cs = w0 - 3.4
        css.push(`@keyframes pgo-chip-${idx}{`
          + `0%,${cs.toFixed(1)}%{opacity:0;transform:translate(-50%,-${(fs * 0.95).toFixed(0)}px) scale(.85) rotate(-7deg);`
          // 落下要加速，那是重力。用 ease-out 會看起來像被放下來，不是掉下來
          + 'animation-timing-function:cubic-bezier(.55,0,.85,.42)}'
          + `${(cs + 0.7).toFixed(1)}%{opacity:1}`
          + `${w0.toFixed(1)}%{opacity:1;transform:translate(-50%,${(fs * 0.3).toFixed(0)}px) scale(1) rotate(0deg)}`
          + `${(w0 + 1.9).toFixed(1)}%{opacity:0;transform:translate(-50%,${(fs * 0.34).toFixed(0)}px) scale(.2) rotate(0deg)}`
          + `${(w0 + 2).toFixed(1)}%,100%{opacity:0;transform:translate(-50%,-${(fs * 0.95).toFixed(0)}px) scale(.85)}}`)
      }

      // 壓扁後每條橫槓要一樣寬，所以 scaleX 是「格子寬 ÷ 該字母實際寬度」，逐字不同
      const squash = `translateY(0) scale(${(cellW / item.w).toFixed(3)}, 0.22)`

      // 擦掉：由右往左，所以越右邊的字母越早消失
      const eStart = 78.4 + (all.length - 1 - idx) * 0.3
      const eEnd = eStart + 1

      // clip-path 必須在「每一個」中間影格都寫出來。只寫頭尾的話 CSS 會在兩點之間
      // 一路內插，整組字會從第 12% 就開始慢慢被切掉
      const OPEN = 'clip-path:inset(0 0 0 0)'
      let k = `@keyframes pgo-ltr-${idx}{`
      k += `0%,${w0.toFixed(1)}%{transform:none;opacity:1;filter:blur(0);${OPEN}}`
      if (hit) {
        // 被砸中往下一沉，再用 spring 彈回來。受力與釋放不該是同一條曲線
        k += `${w1.toFixed(1)}%{transform:translateY(5px);${OPEN};animation-timing-function:var(--ease-spring)}`
      }
      k += `${w2.toFixed(1)}%{transform:none;${OPEN}}`

      if (item.kind === 'data') {
        // 交接時字母是一條橫槓、表格中間那列也是一條橫槓，形狀對得上才換得掉
        k += `33%{transform:none;opacity:1;filter:blur(0);${OPEN}}`
        k += `36.5%{transform:${squash};opacity:1;filter:blur(1.5px);${OPEN}}`
        k += `38.5%{transform:${squash};opacity:0;filter:blur(1.5px);${OPEN}}`
        // 格子全部收完、只剩中間那條橫槓，此時畫面安靜，才把橫槓交還給字母。
        // 出場若與入場等速、又同時動好幾個東西，看起來就是影片倒帶
        k += `53.6%{transform:${squash};opacity:0;filter:blur(1.5px);${OPEN}}`
        k += `54.4%{transform:${squash};opacity:1;filter:blur(1.5px);${OPEN};animation-timing-function:var(--ease-spring)}`
        k += `57.4%{transform:none;opacity:1;filter:blur(0);${OPEN}}`
        // 被擦掉 → 一直空白到上墨寫完 → 排版好的字才接手
        k += `${eStart.toFixed(1)}%{transform:none;opacity:1;${OPEN}}`
        k += `${eEnd.toFixed(1)}%{transform:none;opacity:1;clip-path:inset(0 100% 0 0)}`
        k += `96.3%{transform:none;opacity:0;clip-path:inset(0 100% 0 0)}`
        k += `96.4%{transform:none;opacity:0;${OPEN}}`
        k += `97.6%,100%{transform:none;opacity:1;${OPEN}}`
      } else {
        k += `59%{transform:none;opacity:1;filter:blur(0);${OPEN}}`
        k += `62.5%{transform:scale(0.16);opacity:1;filter:blur(1.5px);${OPEN}}`
        k += `64.5%{transform:scale(0.16);opacity:0;filter:blur(1.5px);${OPEN}}`
        // Mind 的字母從 64.5% 起就不在了，不需要再被擦一次
        k += `96.4%{transform:none;opacity:0;${OPEN}}`
        k += `97.6%,100%{transform:none;opacity:1;${OPEN}}`
      }
      k += '}'
      css.push(k, `.pgo .pgo-ltr[data-w="${idx}"]{animation:pgo-ltr-${idx} var(--pgo-loop) var(--ease-in-out) infinite}`)
    }

    if (genStyle) genStyle.textContent = css.join('\n')
  }

  // 把所有無限循環的動畫對到同一個起點。只動 startTime，不重播，
  // 所以重建出來的元素會直接接在當下的相位上，不會從頭再演一次
  function syncLoops (): void {
    const root = rootRef.value
    if (!root) return
    loopStart ??= Number(document.timeline.currentTime ?? 0)
    for (const a of root.getAnimations({ subtree: true })) {
      if (a.effect?.getTiming().iterations !== Number.POSITIVE_INFINITY) continue
      a.startTime = loopStart
    }
  }

  function onIteration (e: AnimationEvent): void {
    // 事件在 0% 觸發，重建正好接在循環的接縫上，不會切到動畫中段
    if (e.animationName !== 'pgo-journey') return
    variant++
    build()
  }

  function start (): void {
    genStyle = document.createElement('style')
    document.head.append(genStyle)
    void nextTick(async () => {
      build()
      // 字型載入完成後字寬會變，重量一次
      if (document.fonts) {
        await document.fonts.ready
        build()
      }
      wmRef.value?.addEventListener('animationiteration', onIteration as EventListener)
      window.addEventListener('resize', build)
    })
    abandonTimer = window.setTimeout(() => {
      showAbandon.value = true
    }, ABANDON_DELAY_MS)
    startProgress()
  }

  function stop (): void {
    stopProgress()
    progress.value = 0
    wmRef.value?.removeEventListener('animationiteration', onIteration as EventListener)
    window.removeEventListener('resize', build)
    window.clearTimeout(abandonTimer)
    loopStart = null
    genStyle?.remove()
    genStyle = undefined
    showAbandon.value = false
    variant = 0
  }

  function handleAbandon (): void {
    emit('abandon')
  }

  watch(() => props.visible, v => (v ? start() : stop()), { immediate: true })
  onBeforeUnmount(stop)
</script>

<!-- 刻意不用 scoped：字母、圖層、方塊都是在 runtime 用 innerHTML 建出來的，
     那些節點拿不到 scoped 的 data-v 屬性，scoped 規則會全部落空。
     改成全部收在 .pgo 底下，並把 keyframes 名稱加 pgo- 前綴避免撞名 -->
<style>
  .pgo {
    position: fixed;
    inset: 0;
    z-index: 2400;
    display: grid;
    place-items: center;
    background: rgba(15, 23, 42, 0.45);
    animation: pgo-scrim var(--dur-base) var(--ease-out) backwards;

    /* 一圈 17 秒。所有動畫共用這個 duration，靠百分比對齊 */
    --pgo-loop: 17s;
  }
  @keyframes pgo-scrim { from { opacity: 0; } }

  /* 實色底，卡片本身不套 backdrop-filter —— 疊在深色遮罩前面會把深色一起模糊進來 */
  .pgo-card {
    width: min(560px, calc(100% - 32px));
    /* 上方留白：星星飛到最高點時上緣在字樣上方 1em（航點 0.7em ＋ 自身半徑 0.3em），
       文獻方塊的起點是 0.95em。60px 字級下兩者都約 60px，再留 40px 才不會貼邊 */
    padding: 100px 40px 34px;
    border-radius: var(--radius-lg);
    background: var(--color-surface);
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 30px;
    /* 只淡入、不縮放：字母位置是量出來的，進場若帶 transform 會讓量測落在
       縮放中的畫面上，整組圖層跟著偏掉 */
    animation: pgo-card-in var(--dur-slow) var(--ease-out) backwards;
  }
  @keyframes pgo-card-in {
    from { opacity: 0; }
  }

  /* ================= 字樣 ================= */
  .pgo-wm {
    position: relative;
    /* 頁面把 font-family 設成 -apple-system，繼承下來字形會整組換掉。
       字樣要用品牌字型，所以這裡明寫 */
    font-family: var(--font-heading);
    font-size: clamp(38px, 8vw, 60px);
    font-weight: 500;
    letter-spacing: 0.01em;
    line-height: 1;
    white-space: nowrap;
    color: var(--color-ink);
    user-select: none;
  }
  .pgo-grp { position: relative; display: inline-block; }
  .pgo-ltr {
    display: inline-block;
    transform-origin: center center;
    will-change: transform, opacity;
  }

  /* ================= 疊在字上的圖層 ================= */
  .pgo-layer { position: absolute; left: 0; top: 0; pointer-events: none; overflow: visible; }
  .pgo-layer * { transform-box: fill-box; transform-origin: center; }

  /* --- 表格 --- */
  .pgo-cell-mid {
    fill: color-mix(in oklab, var(--color-ink) 88%, transparent);
    opacity: 0;
    animation: pgo-cell-mid var(--pgo-loop) var(--ease-out) infinite;
  }
  .pgo-cell-side {
    fill: none;
    stroke: color-mix(in oklab, var(--color-ink) 34%, transparent);
    stroke-width: 1.2;
    transform: scaleY(0);
    animation: pgo-cell-side var(--pgo-loop) var(--ease-out) infinite;
  }
  .pgo-cell-lit { fill: color-mix(in oklab, var(--color-ink-vivid) 85%, transparent); }
  .pgo-cell-bar { fill: color-mix(in oklab, var(--color-ink) 70%, transparent); }

  /* 中間那格要撐到收合全部結束才交還給字母 —— 交接的瞬間畫面必須是安靜的 */
  @keyframes pgo-cell-mid {
    0%, 35% { opacity: 0; }
    38%, 53.6% { opacity: 1; }
    54.4%, 100% { opacity: 0; }
  }
  /* 上下兩格從中間那格翻出來。收的時候比翻開快一倍以上，而且要在交接開始前收完 */
  @keyframes pgo-cell-side {
    0%, 37% { transform: scaleY(0); opacity: 0; }
    43%, 51% { transform: scaleY(1); opacity: 1; }
    52.8%, 100% { transform: scaleY(0); opacity: 0; }
  }
  /* 逐格亮起用一道遮罩掃過去，不用逐格 delay。
     同一個 clip 走三段：從左灌進來 → 停 → 從左退出去。
     退出去用同一邊所以是退潮；從右側退回去才是倒帶，那會看到顏色往回縮 */
  .pgo-wipe-cells {
    clip-path: inset(0 100% 0 0);
    animation: pgo-wipe-cells var(--pgo-loop) var(--ease-in-out) infinite;
  }
  @keyframes pgo-wipe-cells {
    0%, 43% { clip-path: inset(0 100% 0 0); }
    51% { clip-path: inset(0 0 0 0); }
    53.2% { clip-path: inset(0 0 0 100%); }
    53.3%, 100% { clip-path: inset(0 100% 0 0); }
  }

  /* --- 引用關係網 --- */
  .pgo-node {
    fill: var(--color-surface);
    stroke: var(--color-ink);
    stroke-width: 1.6;
    opacity: 0;
    animation: pgo-node-life var(--pgo-loop) var(--ease-in-out) infinite;
  }
  /* 字母縮小到快看不見時，節點在同一個位置長出來接手，之後才散開 */
  @keyframes pgo-node-life {
    0%, 61% { opacity: 0; transform: translate(0, 0) scale(0.3); }
    64% { opacity: 1; transform: translate(0, 0) scale(1); }
    70%, 76% { opacity: 1; transform: translate(var(--tx), var(--ty)) scale(1); }
    80% { opacity: 0; transform: translate(var(--tx), var(--ty)) scale(0.5); }
    80.1%, 100% { opacity: 0; transform: translate(0, 0) scale(0.3); }
  }
  .pgo-node-extra { animation: pgo-node-extra var(--pgo-loop) var(--ease-out) infinite; }
  @keyframes pgo-node-extra {
    0%, 68% { opacity: 0; transform: scale(0.3); }
    73%, 76% { opacity: 1; transform: scale(1); }
    80%, 100% { opacity: 0; transform: scale(0.3); }
  }
  .pgo-node-lit { fill: var(--color-ink); stroke: var(--color-ink); }
  .pgo-wipe-nodes {
    clip-path: inset(0 100% 0 0);
    animation: pgo-wipe-nodes var(--pgo-loop) var(--ease-in-out) infinite;
  }
  @keyframes pgo-wipe-nodes {
    0%, 72% { clip-path: inset(0 100% 0 0); }
    75%, 80% { clip-path: inset(0 0 0 0); }
    80.1%, 100% { clip-path: inset(0 100% 0 0); }
  }
  .pgo-edge {
    stroke: color-mix(in oklab, var(--color-ink) 32%, transparent);
    stroke-width: 1.2;
    fill: none;
    stroke-dasharray: var(--len);
    stroke-dashoffset: var(--len);
    animation: pgo-edge-draw var(--pgo-loop) var(--ease-in-out) infinite;
  }
  /* 線是被擦掉，不是倒著收回去。收回去會看到線往回縮，像影片倒帶 */
  @keyframes pgo-edge-draw {
    0%, 70% { stroke-dashoffset: var(--len); opacity: 1; }
    75%, 76.5% { stroke-dashoffset: 0; opacity: 1; }
    79.5% { stroke-dashoffset: 0; opacity: 0; }
    79.6%, 100% { stroke-dashoffset: var(--len); opacity: 0; }
  }

  /* ================= 落下的文獻方塊 ================= */
  .pgo-chip {
    position: absolute;
    top: 0;
    left: 0;
    width: var(--cw);
    height: calc(var(--cw) * 1.3);
    padding: calc(var(--cw) * 0.16) calc(var(--cw) * 0.14);
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: calc(var(--cw) * 0.12);
    background: var(--color-surface);
    border: 1.2px solid color-mix(in oklab, var(--color-ink) 34%, transparent);
    border-radius: 3px;
    opacity: 0;
    pointer-events: none;
  }
  .pgo-chip i {
    display: block;
    height: 1.5px;
    border-radius: 1px;
    background: color-mix(in oklab, var(--color-ink) 28%, transparent);
  }
  .pgo-chip i:nth-child(2) { width: 68%; }

  /* ================= 描邊層與上墨層 ================= */
  .pgo-copy { position: absolute; left: 0; top: 0; white-space: nowrap; pointer-events: none; }
  /* Roboto 的字檔是從變體字型產生的靜態實例，字符輪廓沒有合併 —— d 在檔案裡是
     豎筆與碗兩個互相重疊的封閉輪廓。text-stroke 會把每一條輪廓都描出來，重疊處
     的線就會露出來變成交叉。
     解法是讓填色蓋在描邊之上（paint-order）、並填成卡片底色：落在字形內部的
     描邊會被填色遮掉，只留下最外圈與字腔，就是想要的空心字 */
  .pgo-ghost {
    color: var(--color-surface);
    -webkit-text-stroke: 0.02em color-mix(in oklab, var(--color-ink) 38%, transparent);
    paint-order: stroke fill;
    opacity: 0;
    animation: pgo-ghost var(--pgo-loop) var(--ease-out) infinite;
  }
  @keyframes pgo-ghost {
    0%, 80.5% { opacity: 0; }
    82.5%, 96% { opacity: 1; }
    98%, 100% { opacity: 0; }
  }
  .pgo-ink {
    color: var(--color-ink);
    clip-path: inset(0 100% 0 0);
    animation: pgo-ink var(--pgo-loop) linear infinite;
  }
  /* 上墨用 linear：筆尖也是 linear 移動，兩邊同速，墨才會正好長在筆尖後面 */
  @keyframes pgo-ink {
    0%, 82% { clip-path: inset(0 100% 0 0); opacity: 1; }
    96%, 96.4% { clip-path: inset(0 0 0 0); opacity: 1; }
    98%, 100% { clip-path: inset(0 0 0 0); opacity: 0; }
  }

  /* ================= 拆下來的 i 的點 ================= */
  .pgo-tittle {
    position: absolute;
    width: 0;
    height: 0;
    animation: pgo-journey var(--pgo-loop) var(--ease-in-out) infinite;
  }
  @keyframes pgo-journey {
    0%, 3% { transform: translate(0, 0); }
    9% { transform: translate(0, -0.37em); }
    12% { transform: translate(var(--sweep-from), -0.37em); }
    25% { transform: translate(var(--sweep-to), -0.37em); }
    30%, 56% { transform: translate(var(--to-data), -0.7em); }
    61%, 76% { transform: translate(var(--to-mind), -0.7em); }
    /* 擦掉：從最右一路掃回最左，整組字被清空 */
    78% { transform: translate(var(--sweep-from), -0.43em); }
    81% { transform: translate(var(--sweep-to), -0.43em); }
    /* 落到字身高度當筆尖，跟著上墨的前緣由左往右。中間多放兩個停點，
       筆速才不會被 ease-in-out 弄成一段一段的加減速 */
    82% { transform: translate(var(--pen-l), 0.15em); }
    86.7% { transform: translate(var(--pen1), 0.15em); }
    91.3% { transform: translate(var(--pen2), 0.15em); }
    96% { transform: translate(var(--pen-r), 0.15em); }
    /* 寫完最後才回來點上 i 的那一點 —— 手寫本來就是最後才點 i */
    98.5%, 100% { transform: translate(0, 0); }
  }

  .pgo-dot {
    position: absolute;
    left: -0.055em;
    top: 0;
    width: 0.11em;
    height: 0.11em;
    border-radius: 50%;
    background: var(--color-ink);
    animation: pgo-dot var(--pgo-loop) var(--ease-out) infinite;
  }
  @keyframes pgo-dot {
    0%, 4% { opacity: 1; transform: scale(1); }
    8%, 98% { opacity: 0; transform: scale(0.4); }
    99.4%, 100% { opacity: 1; transform: scale(1); }
  }

  /* 基礎 opacity 是 0：prefers-reduced-motion 會把所有動畫關掉，
     沒有這行的話星星會直接停在畫面上 */
  /* 尺寸與航點一律用 em：寫死 px 的話換字級星星就會相對變大、飛到錯的高度 */
  .pgo-spark {
    position: absolute;
    left: 0;
    top: 0;
    width: 0.6em;
    height: 0.6em;
    margin: -0.3em 0 0 -0.3em;
    opacity: 0;
    animation: pgo-spark var(--pgo-loop) var(--ease-out) infinite;
  }
  @keyframes pgo-spark {
    0%, 3% { opacity: 0; transform: scale(0.2); }
    10%, 81% { opacity: 1; transform: scale(1); }
    /* 當筆尖時縮小，才像筆尖不像掛在字旁邊的裝飾 */
    82.5%, 96% { opacity: 1; transform: scale(0.62); }
    98.5%, 100% { opacity: 0; transform: scale(0.2); }
  }
  .pgo-spin { display: block; width: 100%; height: 100%; animation: pgo-spin 3.7s linear infinite; }
  @keyframes pgo-spin { to { transform: rotate(360deg); } }
  .pgo-spark svg { display: block; width: 100%; height: 100%; overflow: visible; }
  .pgo-core { fill: var(--color-ink-vivid); }
  .pgo-halo {
    fill: none;
    stroke: var(--color-ink-vivid);
    stroke-width: 1.2;
    transform-box: fill-box;
    transform-origin: center;
    animation: pgo-halo 3.7s var(--ease-out) infinite;
  }
  @keyframes pgo-halo {
    0% { transform: scale(0.6); opacity: 0.45; }
    70%, 100% { transform: scale(1.7); opacity: 0; }
  }

  /* ================= 階段文字 ================= */
  .pgo-captions {
    position: relative;
    height: 1.6em;
    width: 100%;
    text-align: center;
  }
  .pgo-captions span {
    position: absolute;
    inset: 0;
    font-size: 13px;
    color: var(--color-ink-soft);
    opacity: 0;
    filter: blur(3px);
  }
  /* 四句用 blur 交叉淡出，不用滑動 —— 長等待畫面裡的位移看久了會煩 */
  .pgo-captions span:nth-child(1) { animation: pgo-cap1 var(--pgo-loop) var(--ease-out) infinite; }
  .pgo-captions span:nth-child(2) { animation: pgo-cap2 var(--pgo-loop) var(--ease-out) infinite; }
  .pgo-captions span:nth-child(3) { animation: pgo-cap3 var(--pgo-loop) var(--ease-out) infinite; }
  .pgo-captions span:nth-child(4) { animation: pgo-cap4 var(--pgo-loop) var(--ease-out) infinite; }
  @keyframes pgo-cap1 { 0%, 4% { opacity: 0; filter: blur(3px); } 9%, 26% { opacity: 1; filter: blur(0); } 31%, 100% { opacity: 0; filter: blur(3px); } }
  @keyframes pgo-cap2 { 0%, 30% { opacity: 0; filter: blur(3px); } 35%, 50% { opacity: 1; filter: blur(0); } 55%, 100% { opacity: 0; filter: blur(3px); } }
  @keyframes pgo-cap3 { 0%, 54% { opacity: 0; filter: blur(3px); } 59%, 74% { opacity: 1; filter: blur(0); } 79%, 100% { opacity: 0; filter: blur(3px); } }
  @keyframes pgo-cap4 { 0%, 78% { opacity: 0; filter: blur(3px); } 82%, 97% { opacity: 1; filter: blur(0); } 99.5%, 100% { opacity: 0; filter: blur(3px); } }

  .pgo-progress {
    width: min(280px, 70%);
    height: 4px;
    /* 卡片的 gap 是 30px，這裡收窄成跟下面那句提示差不多的間距，三者才讀得出是一組 */
    margin: -16px 0 0;
    border-radius: 999px;
    background: var(--color-surface-alt);
    overflow: hidden;
  }

  /* transition 的時間比 tick 間隔長一點，一格一格的跳動才會被抹平成連續移動 */
  .pgo-progress-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--color-ink);
    transition: width 320ms linear;
  }

  .pgo-hint {
    margin: -18px 0 0;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  /* 它只是出口，不是選項 —— 正常等待的人不該注意到它。
     淡到只在刻意找的時候才看得見，hover 才回到一般次要文字的濃度 */
  .pgo-abandon {
    margin-top: 2px;
    padding: 4px 8px;
    font: inherit;
    font-size: 12px;
    color: color-mix(in oklab, var(--color-ink-soft) 45%, transparent);
    background: transparent;
    border: 0;
    cursor: pointer;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--dur-slow) var(--ease-out), color var(--dur-fast) ease;
  }
  .pgo-abandon--on { opacity: 1; pointer-events: auto; }
  .pgo-abandon--on:hover { color: var(--color-ink-soft); }

  /* 動畫被全域的 prefers-reduced-motion reset 關掉時，這裡停在完整、乾淨的字樣 */
  @media (prefers-reduced-motion: reduce) {
    .pgo-captions span:nth-child(1) { opacity: 1; filter: blur(0); }
  }
</style>
