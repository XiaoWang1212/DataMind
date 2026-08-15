<template>
  <!-- 自訂節點 UI：左 target / 右 source + 圓形 icon + label -->
  <div
    class="icon-node-wrap"
    :style="{
      '--node-accent': accentColor,
      ...(highlightColor ? { '--highlight-color': highlightColor } : {}),
    }"
  >
    <!-- 右側輸出點：連到下一個節點 -->
    <Handle
      class="invisible-handle handle-right"
      :position="Position.Right"
      type="source"
    />
    <!-- 左側輸入點：接收前一個節點 -->
    <Handle
      class="invisible-handle handle-left"
      :position="Position.Left"
      type="target"
    />

    <!-- 節點主體 -->
    <div
      class="icon-node"
      :class="[nodeTypeClass, { 'node-highlighted': highlighted }]"
    >
      <!-- running 時顯示 spinner，其餘顯示 icon -->
      <div v-if="status === 'running'" class="node-spinner" />
      <span v-else class="node-icon"><v-icon :icon="icon" size="26" /></span>
      <!-- 完成狀態：右下角重疊的勾勾徽章 -->
      <span v-if="status === 'finished'" class="node-done-badge">
        <v-icon icon="mdi-check" size="13" />
      </span>

      <!-- 增刪元素時，浮在節點正上方的通知圖示，旋轉進出場、出現一下就消失 -->
      <Transition name="node-flash-pop">
        <div
          v-if="flashType"
          class="node-flash-chip"
          :class="`node-flash-chip--${flashType}`"
        >
          <v-icon :icon="flashType === 'add' ? 'mdi-plus' : 'mdi-minus'" size="13" />
        </div>
      </Transition>
    </div>

    <!-- 節點標籤（支援換行） -->
    <div class="icon-node-label">
      <span :class="{ 'label-selected': isSelected }">{{ label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Handle, type NodeProps, Position } from '@vue-flow/core'
  import { computed } from 'vue'

  // Vue Flow 傳入的節點資料（id/data/selected...）
  const props = defineProps<NodeProps>()

  // 從節點 data 取出 icon，沒有就用預設 icon
  const icon = computed(() => String(props.data?.icon ?? 'mdi-circle'))

  // 從節點 data 取出 label
  const label = computed(() => String(props.data?.label ?? ''))

  // 從節點 data 取出分類，決定底色 class（見 docs/DESIGN_SYSTEM.md §2.3）
  const nodeType = computed(() => String(props.data?.nodeType ?? 'source'))
  const nodeTypeClass = computed(() => `node-${nodeType.value}`)

  // 選取指示線的顏色，直接用分類色 token，不用 JS 對照表重算一次
  const accentColor = computed(() => `var(--color-node-${nodeType.value})`)

  // demo 動畫狀態（running 顯示 spinner、finished 顯示右下角徽章）
  const status = computed(() => props.data?.status ?? null)

  // 用 data.isSelected 而非 Vue Flow 的 props.selected：
  // WorkflowCanvas 設了 elements-selectable="false"，內建的 selected 永遠是 false
  const isSelected = computed(() => Boolean(props.data?.isSelected))

  // Settings 步驟高亮外框
  const highlighted = computed(() => Boolean(props.data?.highlighted))
  const highlightColor = computed(() => props.data?.highlightColor as string | null ?? null)

  // 增刪元素時的閃色特效
  const flashType = computed(() => props.data?.flashType as 'add' | 'remove' | null ?? null)
</script>

<style scoped>
  .icon-node-wrap {
    --icon-size: 58px;
    /* calc() 自動隨 icon-size 同步，不需手動維護 */
    --icon-half: calc(var(--icon-size) / 2);
    position: relative;
    width: 122px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .icon-node {
    position: relative;
    overflow: visible;
    width: var(--icon-size);
    height: var(--icon-size);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    /* 淺底配深色 icon（比照 Orange Data Mining 的構造），取代原本的飽和底配白色 icon */
    color: var(--color-ink-strong);
    border: 1.5px solid rgba(18, 36, 74, 0.16);
  }

  /* 增刪通知圖示：浮在節點正上方的小圓，不疊在節點本體色塊上，也不用紅/綠填色 */
  .node-flash-chip {
    position: absolute;
    top: -14px;
    left: 50%;
    transform: translate(-50%, -100%) rotate(0deg);
    z-index: 5;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    color: #fff;
    box-shadow: var(--shadow-card);
    pointer-events: none;
  }

  /* 新增：用節點自己的分類色（半透明），強調「這個節點類型剛被加入」 */
  .node-flash-chip--add {
    background: color-mix(in oklab, var(--node-accent) 88%, transparent);
  }

  /* 移除：中性深灰（半透明），不用紅色 */
  .node-flash-chip--remove {
    background: color-mix(in oklab, var(--color-ink-strong) 78%, transparent);
  }

  .node-flash-pop-enter-active,
  .node-flash-pop-leave-active {
    transition: opacity var(--dur-slow) ease, transform var(--dur-slow) ease;
  }

  /* 進場從逆時針轉回正、離場再順著同方向轉出去，看起來是一路轉過去而不是轉回頭 */
  .node-flash-pop-enter-from {
    opacity: 0;
    transform: translate(-50%, -100%) rotate(-270deg) scale(0.4);
  }

  .node-flash-pop-leave-to {
    opacity: 0;
    transform: translate(-50%, -100%) rotate(270deg) scale(0.4);
  }

  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, var(--color-accent));
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }

  @keyframes highlight-pulse {
    0%, 100% { box-shadow: 0 0 0 3px var(--highlight-color, var(--color-accent)); }
    50% { box-shadow: 0 0 0 6px var(--highlight-color, var(--color-accent)); }
  }

  .node-spinner,
  .node-icon {
    position: relative;
    z-index: 1;
  }

  .node-spinner {
    width: 22px;
    height: 22px;
    border: 3px solid color-mix(in oklab, var(--color-ink-strong) 25%, transparent);
    border-top-color: var(--color-ink-strong);
    border-radius: 50%;
    animation: node-spin 0.75s linear infinite;
  }

  @keyframes node-spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* 右下角重疊的完成徽章：outline 風格，白底+綠框+綠勾，不管節點本身是什麼色都能跟它分開 */
  .node-done-badge {
    position: absolute;
    right: -2px;
    bottom: -2px;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 19px;
    height: 19px;
    border-radius: 50%;
    background: var(--color-surface);
    border: 1.5px solid var(--color-success);
    color: var(--color-success);
  }

  .icon-node-label {
    min-height: 32px;
    text-align: center;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 500;
    color: var(--color-text);
    white-space: pre-line;
  }

  /* inline-block 讓 span 高度貼合文字；掛在外層 .icon-node-label 的話，
     它的 min-height 會把線推得離單行標籤很遠 */
  .label-selected {
    position: relative;
    display: inline-block;
    padding-bottom: 8px;
  }

  .label-selected::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 34px;
    height: 2px;
    transform: translateX(-50%);
    border-radius: 2px;
    background: var(--node-accent, var(--color-node-source));
    animation: underline-in var(--dur-base) var(--ease-out);
  }

  @keyframes underline-in {
    from {
      transform: translateX(-50%) scaleX(0);
      opacity: 0;
    }

    to {
      transform: translateX(-50%) scaleX(1);
      opacity: 1;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .label-selected::after {
      animation: none;
    }
  }

  .node-source {
    background: var(--color-node-source);
  }

  .node-transform {
    background: var(--color-node-transform);
  }

  .node-visualize {
    background: var(--color-node-visualize);
  }

  .node-model {
    background: var(--color-node-model);
  }

  .node-evaluate {
    background: var(--color-node-evaluate);
  }

  .invisible-handle {
    opacity: 0;
    width: 8px;
    height: 8px;
    border: none;
    background: transparent;
    /* 垂直方向對齊到 icon 圓形中心，不是整個節點 wrapper 的中心 */
    top: var(--icon-half) !important;
  }

  /* 把 left/right handle 從容器邊緣移到 icon 邊緣 */
  .handle-left {
    left: calc(50% - var(--icon-half)) !important;
  }

  .handle-right {
    right: calc(50% - var(--icon-half)) !important;
  }

  @media (max-width: 1024px) {
    .icon-node-wrap {
      --icon-size: 54px;
      width: 108px;
    }

    .icon-node-label {
      font-size: 12px;
      min-height: 28px;
    }
  }

  @media (max-width: 768px) {
    .icon-node-wrap {
      --icon-size: 48px;
      width: 96px;
      gap: 6px;
    }

    .icon-node-label {
      font-size: 11px;
      line-height: 1.15;
      min-height: 24px;
    }
  }
</style>
