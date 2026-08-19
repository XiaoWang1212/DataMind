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
      box-shadow var(--dur-fast) var(--ease-out),
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

  .app-btn--primary {
    background: var(--color-ink);
    color: #fff;
  }

  .app-btn--secondary {
    background: var(--color-surface);
    color: var(--color-ink);
    box-shadow: inset 0 0 0 1px var(--color-border);
  }

  .app-btn--ghost {
    background: transparent;
    color: var(--color-ink-soft);
  }

  .app-btn--danger {
    background: var(--color-error-bg);
    color: var(--color-error-text);
  }

  /* hover 是每天會看幾十次的互動，只做底色位移與陰影兩件事。
     觸控裝置點一下就會觸發 hover 並卡在 hover 態，所以整組 gate 起來 */
  @media (hover: hover) and (pointer: fine) {
    /* 藏青已經很暗，往亮的方向走才看得出變化 */
    .app-btn--primary:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 88%, white);
      box-shadow: 0 2px 8px color-mix(in oklab, var(--color-ink) 28%, transparent);
    }

    .app-btn--secondary:hover:not(:disabled) {
      box-shadow: inset 0 0 0 1px var(--color-ink), var(--shadow-card);
    }

    .app-btn--ghost:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 8%, white);
      color: var(--color-ink);
    }

    .app-btn--danger:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-error) 14%, white);
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
