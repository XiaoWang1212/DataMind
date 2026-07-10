import { computed, onBeforeUnmount, ref } from "vue";

/**
 * 抽屜有四個段落喔
 *   peeked (100px)    → 關閉的時候沒有完全關閉，還看得到title
 *   collapsed (280px) → 預設打開的高度，剛好能看到大部分的欄位
 *   expanded (54vh)   → 內容比較多時（e.g. dataTable）可以往上拉到更大
 *   full (90vh)       → 從 expanded 繼續往上拖，可以拉到接近整頁
 */

// ─── 各段高度（px）──────────────────────────────────────────────
const PEEKED_PX = 100;
const COLLAPSED_PX = 280;
function getExpandedPx(): number {
  return Math.round(window.innerHeight * 0.54);
}
function getFullPx(): number {
  return Math.round(window.innerHeight * 0.9);
}

// 吸附動畫時長（ms）
const SNAP_DURATION = 260;

type Stage = "peeked" | "collapsed" | "expanded" | "full";

// ─── 速度緩衝（ring buffer）──────────────────────────────────────
interface VelPoint {
  y: number;
  t: number;
}

function computeVelocity(buf: VelPoint[]): number {
  if (buf.length < 2) return 0;
  const first = buf[0]!;
  const last = buf[buf.length - 1]!;
  const dt = last.t - first.t;
  return dt > 0 ? (last.y - first.y) / dt : 0; // px/ms，正 = 往下 = 縮小
}

function pruneBuffer(buf: VelPoint[], now: number): void {
  const cutoff = now - 120;
  while (buf.length > 1 && buf[0]!.t < cutoff) buf.shift();
}

export function useDrawerDrag() {
  const stage = ref<Stage>("collapsed");
  const isDragging = ref(false);

  // 拖曳中的即時高度（null = 使用 stage 對應高度）
  const liveHeight = ref<number | null>(null);

  // expanded / full 的像素高度：每次 startDrag 時重新取視窗高度
  const expandedPx = ref(getExpandedPx());
  const fullPx = ref(getFullPx());

  const isExpanded = computed(() => stage.value === "expanded");
  const isFull = computed(() => stage.value === "full");

  function stagePx(s: Stage): number {
    if (s === "full") return fullPx.value;
    if (s === "expanded") return expandedPx.value;
    if (s === "collapsed") return COLLAPSED_PX;
    return PEEKED_PX;
  }

  const heightPx = computed<number>(() => {
    if (liveHeight.value !== null) return liveHeight.value;
    return stagePx(stage.value);
  });

  const style = computed(() => ({
    height: `${heightPx.value}px`,
    transition: isDragging.value
      ? "none"
      : `height ${SNAP_DURATION}ms cubic-bezier(0.4, 0, 0.2, 1)`,
  }));

  // ─── 拖曳狀態 ─────────────────────────────────────────────────
  const velBuf: VelPoint[] = [];
  let dragStartY = 0;
  let dragStartHeight = 0;

  // 區分「點擊」與「拖曳」：拖曳位移小於門檻就視為點擊（tap）
  const TAP_THRESHOLD_PX = 5;
  let moved = false;

  function getClientY(event: MouseEvent | TouchEvent): number {
    return "touches" in event
      ? (event.touches[0]?.clientY ?? 0)
      : event.clientY;
  }

  function startDrag(event: MouseEvent | TouchEvent): void {
    expandedPx.value = getExpandedPx();
    fullPx.value = getFullPx();
    dragStartY = getClientY(event);
    dragStartHeight = heightPx.value;
    liveHeight.value = dragStartHeight;
    isDragging.value = true;
    moved = false;
    velBuf.length = 0;
    velBuf.push({ y: dragStartY, t: performance.now() });

    window.addEventListener("mousemove", onDrag);
    window.addEventListener("mouseup", endDrag);
    window.addEventListener("touchmove", onDrag, { passive: false });
    window.addEventListener("touchend", endDrag);
  }

  function onDrag(event: MouseEvent | TouchEvent): void {
    if (!isDragging.value) return;
    if ("touches" in event) event.preventDefault();

    const currentY = getClientY(event);
    const delta = currentY - dragStartY;

    if (Math.abs(delta) > TAP_THRESHOLD_PX) moved = true;

    // 往下拖 delta 正 → 高度縮小；往上拖 delta 負 → 高度增大
    const newH = dragStartHeight - delta;
    liveHeight.value = Math.max(PEEKED_PX, Math.min(newH, fullPx.value));

    const now = performance.now();
    velBuf.push({ y: currentY, t: now });
    pruneBuffer(velBuf, now);
  }

  function endDrag(): void {
    if (!isDragging.value) return;
    removeListeners();

    // 沒有明顯位移 → 視為點擊 handle：只切換「關（peeked）」與「開到 expanded（54vh）」
    // 關著時點 → 開到 expanded；其餘狀態（collapsed / expanded / full）點 → 關閉
    if (!moved) {
      const next: Stage = stage.value === "peeked" ? "expanded" : "peeked";
      if (next === "expanded") expandedPx.value = getExpandedPx();
      isDragging.value = false;
      requestAnimationFrame(() => {
        stage.value = next;
        liveHeight.value = null;
      });
      return;
    }

    const currentH = liveHeight.value ?? stagePx(stage.value);
    const velocity = computeVelocity(velBuf);
    const target = resolveTarget(currentH, velocity);

    // 修正 transition 時序：
    // Vue 會將同一 sync block 內的所有響應式更新 batch 成一次 render。
    // 若直接在此設定 isDragging=false + liveHeight=null，瀏覽器只看到一個 frame：
    //   transition 從 none→enabled、height 從 currentH→targetH 同時發生
    //   → CSS transition 不觸發，畫面直接跳到目標高度。
    //
    // 正確順序：
    //   frame A：isDragging=false（transition 啟用），liveHeight 保持 currentH（height 不動）
    //   frame B：liveHeight=null → heightPx=stagePx(target)（瀏覽器從 currentH 動畫到 targetH）
    isDragging.value = false;
    requestAnimationFrame(() => {
      stage.value = target;
      liveHeight.value = null;
    });
  }

  // ─── 決定目標段 ────────────────────────────────────────────────
  function resolveTarget(currentH: number, velocity: number): Stage {
    // 用 momentum 投影：把目前高度沿速度方向再推 150ms 的距離
    // velocity > 0 = 往下拖（screen Y 增加）= 高度縮小
    // velocity < 0 = 往上拖                 = 高度增大
    const LOOKAHEAD_MS = 150;
    const projectedH = currentH - velocity * LOOKAHEAD_MS;

    const candidates: Array<{ target: Stage; px: number }> = [
      { target: "peeked", px: PEEKED_PX },
      { target: "collapsed", px: COLLAPSED_PX },
      { target: "expanded", px: expandedPx.value },
      { target: "full", px: fullPx.value },
    ];

    let nearest: { target: Stage; px: number } = candidates[0]!;
    let minDist = Infinity;
    for (const c of candidates) {
      const dist = Math.abs(projectedH - c.px);
      if (dist < minDist) {
        minDist = dist;
        nearest = c;
      }
    }
    return nearest.target; // 最低為 peeked，不會完全關閉
  }

  function reset(): void {
    stage.value = "collapsed";
    liveHeight.value = null;
    isDragging.value = false;
    velBuf.length = 0;
  }

  function expand(): void {
    expandedPx.value = getExpandedPx();
    stage.value = "expanded";
    liveHeight.value = null;
    isDragging.value = false;
  }

  function removeListeners(): void {
    window.removeEventListener("mousemove", onDrag);
    window.removeEventListener("mouseup", endDrag);
    window.removeEventListener("touchmove", onDrag);
    window.removeEventListener("touchend", endDrag);
  }

  onBeforeUnmount(removeListeners);

  return { isExpanded, isFull, style, startDrag, reset, expand };
}
