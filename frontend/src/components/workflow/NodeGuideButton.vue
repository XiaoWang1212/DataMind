<template>
  <!-- 浮在畫布右下角的說明入口。抽屜展開時整組往上讓，避免被蓋住 -->
  <div class="node-guide" :style="{ '--guide-inset': `${bottomInset}px` }">
    <Transition name="guide-pop">
      <div
        v-if="open"
        ref="panelRef"
        aria-label="節點說明"
        class="guide-panel glass-panel"
        role="dialog"
      >
        <div class="guide-panel__head">
          <span class="guide-panel__title">各節點在做什麼</span>
          <button
            aria-label="關閉說明"
            class="guide-panel__close"
            type="button"
            @click="open = false"
          >
            <v-icon icon="mdi-close" size="16" />
          </button>
        </div>

        <ul class="guide-list">
          <li v-for="entry in entries" :key="entry.label" class="guide-item">
            <span
              class="guide-item__icon"
              :style="{ '--node-accent': `var(--color-node-${entry.nodeType})` }"
            >
              <v-icon :icon="entry.icon" size="17" />
            </span>
            <div class="guide-item__body">
              <p class="guide-item__label">{{ entry.label }}</p>
              <p class="guide-item__text">{{ entry.text }}</p>
            </div>
          </li>
        </ul>
      </div>
    </Transition>

    <button
      :aria-expanded="open"
      aria-label="節點說明"
      class="guide-trigger"
      :class="{ 'guide-trigger--on': open }"
      type="button"
      @click="open = !open"
    >
      <v-icon :icon="open ? 'mdi-close' : 'mdi-help'" size="18" />
    </button>
  </div>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, ref, watch } from 'vue'
  import { NODE_HELP } from '@/constants/workflowLabels'

  withDefaults(defineProps<{
    /** 底部抽屜遮住的高度，面板與按鈕一起往上讓開 */
    bottomInset?: number
  }>(), {
    bottomInset: 0,
  })

  const open = ref(false)
  const panelRef = ref<HTMLElement | null>(null)

  const entries = Object.values(NODE_HELP)

  function onKeydown (event: KeyboardEvent): void {
    if (event.key === 'Escape') open.value = false
  }

  watch(open, isOpen => {
    if (isOpen) {
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  })

  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
  /* 上下都撐開並靠底排列，面板長高時只會往上長到畫布頂端就停住，
     不會被畫布切掉。整層不吃指標事件，否則會蓋住畫布的平移操作 */
  .node-guide {
    position: absolute;
    top: 16px;
    right: 16px;
    bottom: calc(16px + var(--guide-inset, 0px));
    z-index: 5;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: flex-end;
    gap: 10px;
    pointer-events: none;
    transition: bottom var(--dur-base) var(--ease-out);
  }

  .node-guide > * {
    pointer-events: auto;
  }

  .guide-trigger {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border: 1px solid var(--color-border-strong);
    border-radius: 50%;
    background: var(--color-surface);
    color: var(--color-ink-soft);
    cursor: pointer;
    box-shadow: var(--shadow-card);
    transition: color var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }

  .guide-trigger:hover {
    color: var(--color-ink-vivid);
    border-color: var(--color-ink-vivid);
  }

  .guide-trigger:active {
    transform: scale(0.94);
  }

  .guide-trigger--on {
    color: var(--color-ink-vivid);
    border-color: var(--color-ink-vivid);
  }

  .guide-panel {
    width: 340px;
    /* 460px 是內容舒適的高度上限；實際能長多高由 flex 容器的剩餘空間決定，
       min-height: 0 才允許它被壓到比內容矮，超出的部分自己捲 */
    max-height: 460px;
    min-height: 0;
    overflow-y: auto;
    padding: 14px 16px;
    border-radius: var(--radius-md);
    /* 從右下角的觸發鈕長出來，而不是從自己的中心 */
    transform-origin: bottom right;
    box-shadow: var(--shadow-float);
  }

  .guide-panel__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 10px;
  }

  .guide-panel__title {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-text);
  }

  .guide-panel__close {
    display: flex;
    padding: 2px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-ink-soft);
    cursor: pointer;
  }

  .guide-panel__close:hover {
    color: var(--color-text);
  }

  .guide-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .guide-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  /* 填色與 IconNode 同一套，面板上的圓點才跟畫布上的節點對得起來 */
  .guide-item__icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--node-accent);
    color: var(--color-ink-strong);
  }

  /* 節點分類色兩個主題共用同一組粉彩，深色底上要改成淡填色 + 亮圖示才看得清 */
  .v-theme--dark .guide-item__icon {
    background: color-mix(in oklab, var(--node-accent) 24%, var(--color-surface));
    color: color-mix(in oklab, var(--node-accent) 82%, #fff);
  }

  .guide-item__label {
    margin: 0 0 2px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text);
  }

  .guide-item__text {
    margin: 0;
    font-size: 12px;
    line-height: 1.6;
    color: var(--color-ink-soft);
  }

  /* 從觸發鈕的方向長出來，收起時比展開快 */
  .guide-pop-enter-active {
    transition: opacity var(--dur-base) var(--ease-out),
      transform var(--dur-base) var(--ease-out);
  }

  .guide-pop-leave-active {
    transition: opacity var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }

  .guide-pop-enter-from,
  .guide-pop-leave-to {
    opacity: 0;
    transform: translateY(8px) scale(0.97);
  }

  @media (prefers-reduced-motion: reduce) {
    .guide-pop-enter-from,
    .guide-pop-leave-to {
      transform: none;
    }
  }

  @media (max-width: 600px) {
    .guide-panel {
      width: min(340px, calc(100vw - 48px));
    }
  }
</style>
