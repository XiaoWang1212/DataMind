<template>
  <!-- 自訂節點 UI：左 target / 右 source + 圓形 icon + label -->
  <div class="icon-node-wrap">
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
    <div class="icon-node" :class="colorClass">
      <!-- running 時顯示 spinner，其餘顯示 icon -->
      <div v-if="status === 'running'" class="node-spinner" />
      <v-icon v-else :icon="icon" size="26" />
    </div>

    <!-- 節點標籤（支援換行） -->
    <div class="icon-node-label">{{ label }}</div>
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

  // demo 動畫狀態（running 時顯示 spinner）
  const status = computed(() => props.data?.status ?? null)
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
    width: var(--icon-size);
    height: var(--icon-size);
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
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
    color: #242424;
    white-space: pre-line;
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
