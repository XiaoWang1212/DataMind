<template>
  <button
    ref="root"
    class="app-btn"
    :class="[`app-btn--${variant}`, { 'app-btn--icon-only': iconOnly }]"
    :disabled="disabled || loading"
    :type="type"
  >
    <span v-if="loading" aria-hidden="true" class="app-btn-spinner" />
    <span class="app-btn-body" :class="{ 'app-btn-body--loading': loading }">
      <slot />
    </span>
  </button>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { useSpecularHover } from '@/composables/useSpecularHover'

  withDefaults(defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(), {
    variant: 'primary',
    type: 'button',
    disabled: false,
    loading: false,
    iconOnly: false,
  })

  const root = ref<HTMLElement | null>(null)
  useSpecularHover(root)
</script>

<style scoped>
  .app-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 18px;
    border: none;
    border-radius: 999px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.2;
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }

  .app-btn:active:not(:disabled) {
    transform: scale(0.96);
  }

  .app-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .app-btn--icon-only {
    width: 36px;
    height: 36px;
    padding: 8px;
  }

  /* 反光只顯示在 1px 邊框上：外層漸層減掉 content-box，剩下 padding 那圈。
     用 conic-gradient 而不是游標位置的光斑 —— 這是「光從某個角度照過來」，
     所以朝光與背光的兩條邊會同時反光，像真的鏡面。角度由 JS 每幀寫入 --sb-angle */
  .app-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    padding: 1px;
    border-radius: inherit;
    background: conic-gradient(
      from calc(var(--sb-angle, 0deg) - 90deg),
      var(--specular-color) 0deg,
      transparent 26deg,
      transparent 154deg,
      var(--specular-color) 180deg,
      transparent 206deg,
      transparent 334deg,
      var(--specular-color) 360deg
    );
    opacity: var(--glow, 0);
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask-composite: exclude;
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    pointer-events: none;
    /* 刻意不加 transition：角度與亮度每幀都在變，再疊轉場會讓反光拖在游標後面。
       平滑已經在 composable 裡用指數插值做掉了 */
  }

  /* 深底用白光、淺底用藏青光，否則反光在自己的底色上看不見 */
  .app-btn--primary {
    background: var(--color-ink);
    color: #fff;
    --specular-color: rgba(255, 255, 255, 0.9);
  }

  .app-btn--secondary {
    background: var(--color-surface);
    color: var(--color-ink);
    box-shadow: inset 0 0 0 1px var(--color-border);
    --specular-color: color-mix(in oklab, var(--color-ink) 70%, transparent);
  }

  .app-btn--ghost {
    background: transparent;
    color: var(--color-ink-soft);
    --specular-color: color-mix(in oklab, var(--color-ink) 55%, transparent);
  }

  .app-btn--danger {
    background: var(--color-error-bg);
    color: var(--color-error-text);
    --specular-color: color-mix(in oklab, var(--color-error) 70%, transparent);
  }

  /* 觸控裝置點一下會觸發 hover 並卡在 hover 底色，所以 hover 態一律 gate 起來 */
  @media (hover: hover) and (pointer: fine) {
    .app-btn--primary:hover:not(:disabled) {
      background: var(--color-ink-strong);
    }

    .app-btn--ghost:hover:not(:disabled) {
      color: var(--color-ink);
    }
  }

  /* loading 時內容留在原位只是隱形，避免按鈕寬度跳動 */
  .app-btn-body--loading {
    visibility: hidden;
  }

  .app-btn-spinner {
    position: absolute;
    width: 15px;
    height: 15px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: app-btn-spin 0.7s linear infinite;
  }

  @keyframes app-btn-spin {
    to { transform: rotate(360deg); }
  }
</style>
