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

  /* 四個變體共用同一套 hover：底色明顯位移一階 + 抬起 2px。
     觸控裝置點一下就會觸發 hover 並卡在 hover 態，所以整組 gate 起來 */
  @media (hover: hover) and (pointer: fine) {
    .app-btn:hover:not(:disabled) {
      transform: translateY(-2px);
    }

    /* :active 要贏過 hover 的抬升，否則按下去沒有壓下感 */
    .app-btn:active:not(:disabled) {
      transform: scale(0.96);
    }

    /* 深底按鈕往「亮」的方向走：藏青已經很暗，再加深看不出變化。
       止於 88% —— 再亮下去白字對比會掉太多 */
    .app-btn--primary:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 88%, white);
      box-shadow: 0 5px 14px color-mix(in oklab, var(--color-ink) 34%, transparent);
    }

    /* 淺底三個變體的底色位移都被文字對比卡住（ghost 過場中仍是 ink-soft 字、
       danger 是 error-text），所以「看得見」主要靠抬升與陰影，底色只做輔助 */
    .app-btn--secondary:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 8%, white);
      box-shadow: inset 0 0 0 1px var(--color-border-strong), var(--shadow-card);
    }

    .app-btn--ghost:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 8%, white);
      color: var(--color-ink);
      box-shadow: var(--shadow-card);
    }

    .app-btn--danger:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-error) 14%, white);
      box-shadow: var(--shadow-card);
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
