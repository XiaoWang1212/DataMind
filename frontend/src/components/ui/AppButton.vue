<template>
  <component
    :is="to ? RouterLink : 'button'"
    ref="root"
    class="app-btn"
    :class="[
      `app-btn--${variant}`,
      {
        'app-btn--icon-only': iconOnly,
        'app-btn--ai-loading': loading && variant === 'ai',
      },
    ]"
    v-bind="to ? { to } : { disabled: disabled || loading, type }"
  >
    <span v-if="loading && variant !== 'ai'" aria-hidden="true" class="app-btn-spinner" />
    <span class="app-btn-body" :class="{ 'app-btn-body--loading': loading && variant !== 'ai' }">
      <slot />
    </span>
  </component>
</template>

<script setup lang="ts">
  import { RouterLink } from 'vue-router'

  // 給了 to 就渲染成 RouterLink，讓「長得像按鈕的連結」不必各頁再刻一份樣式。
  // disabled / type 只對 button 有意義，不會掛到連結上
  withDefaults(defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'ai'
    type?: 'button' | 'submit' | 'reset'
    to?: string
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(), {
    variant: 'primary',
    type: 'button',
    to: undefined,
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
    text-decoration: none;
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

  /* 實色底另用 --color-ink-solid 而不是 --color-ink：深色主題的 ink 是淺藍，
     直接當底會太亮、白字也壓不住 */
  .app-btn--primary {
    background: var(--color-ink-solid);
    color: var(--color-inverted);
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

  .app-btn--ai {
    background: linear-gradient(100deg, var(--color-ai-from) 0%, var(--color-ai-to) 100%);
    color: var(--color-inverted);
  }

  /* hover 是每天會看幾十次的互動，只做底色位移與陰影兩件事。
     觸控裝置點一下就會觸發 hover 並卡在 hover 態，所以整組 gate 起來 */
  @media (hover: hover) and (pointer: fine) {
    /* 藏青已經很暗，往亮的方向走才看得出變化 */
    .app-btn--primary:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink-solid) 88%, var(--color-surface));
      box-shadow: 0 2px 8px color-mix(in oklab, var(--color-ink-solid) 28%, transparent);
    }

    .app-btn--secondary:hover:not(:disabled) {
      box-shadow: inset 0 0 0 1px var(--color-ink), var(--shadow-card);
    }

    .app-btn--ghost:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-ink) 8%, var(--color-surface));
      color: var(--color-ink);
    }

    .app-btn--danger:hover:not(:disabled) {
      background: color-mix(in oklab, var(--color-error) 14%, var(--color-surface));
    }

    .app-btn--ai:hover:not(:disabled) {
      background: linear-gradient(
        100deg,
        color-mix(in oklab, var(--color-ai-from) 88%, var(--color-surface)) 0%,
        color-mix(in oklab, var(--color-ai-to) 88%, var(--color-surface)) 100%
      );
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

  .app-btn--ai-loading {
    position: relative;
    overflow: hidden;
  }

  .app-btn--ai-loading:disabled {
    opacity: 1;
  }

  .app-btn--ai-loading::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
      100deg,
      transparent 20%,
      color-mix(in oklab, var(--color-inverted) 16%, transparent) 50%,
      transparent 80%
    );
    background-size: 260% 100%;
    animation: app-btn-ai-sweep 2.4s linear infinite;
  }

  @keyframes app-btn-ai-sweep {
    from { background-position: 140% 0; }
    to { background-position: -140% 0; }
  }
</style>
