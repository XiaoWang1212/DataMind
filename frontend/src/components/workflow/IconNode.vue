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
      :class="[colorClass, { 'node-highlighted': highlighted, 'flash-add': flashType === 'add', 'flash-remove': flashType === 'remove' }]"
    >
      <!-- running 時顯示 spinner，其餘顯示 icon -->
      <div v-if="status === 'running'" class="node-spinner" />
      <span v-else class="node-icon"><v-icon :icon="icon" size="26" /></span>
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

  // 從節點 data 取出顏色 class（例如 node-yellow / node-pending）
  const colorClass = computed(() =>
    String(props.data?.colorClass ?? 'node-purple'),
  )

  // 選取指示線的顏色，對應各 colorClass 的底色（壓深過，淺色在近白的畫布上看不見）
  const LABEL_ACCENTS: Record<string, string> = {
    'node-pending': '#7c88a8',
    'node-purple': '#005dff',
    'node-yellow': '#c2a935',
  }
  const accentColor = computed(() => LABEL_ACCENTS[colorClass.value] ?? '#005dff')

  // demo 動畫狀態（running 時顯示 spinner）
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
    overflow: hidden;
    width: var(--icon-size);
    height: var(--icon-size);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
  }

  .flash-add::before,
  .flash-remove::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    animation: flash-overlay 1.2s linear forwards;
    pointer-events: none;
    z-index: 0;
  }

  .flash-add::before {
    background: #06b6d4;
  }

  .flash-remove::before {
    background: #ef4444;
  }

  @keyframes flash-overlay {
    0%   { opacity: 0; }
    8%   { opacity: 0.85; }
    30%  { opacity: 0.85; }
    42%  { opacity: 0; }
    58%  { opacity: 0; }
    70%  { opacity: 0.85; }
    92%  { opacity: 0.85; }
    100% { opacity: 0; }
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
    border: 3px solid rgba(255, 255, 255, 0.35);
    border-top-color: #fff;
    border-radius: 50%;
    animation: node-spin 0.75s linear infinite;
  }

  @keyframes node-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .icon-node-label {
    min-height: 32px;
    text-align: center;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-ink);
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
    background: var(--node-accent, #005dff);
    animation: underline-in 0.2s ease-out;
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

  .node-yellow {
    background: #f0e274;
    color: #fdfdfd;
  }

  .node-pending {
    background: #ced3e9;
  }

  .node-purple {
    background: linear-gradient(165deg, #005dff 0%, #4c8cff 100%);
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
