<template>
  <span class="status-badge" :class="[`status-badge--${status}`, `status-badge--${variant}`]">
    <span v-if="variant === 'dot'" aria-hidden="true" class="status-badge-dot" />
    <slot />
  </span>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    status: 'success' | 'warning' | 'danger' | 'neutral'
    variant?: 'dot' | 'badge'
  }>(), {
    variant: 'badge',
  })
</script>

<style scoped>
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.4;
    white-space: nowrap;
  }

  .status-badge--badge {
    padding: 3px 10px;
    border-radius: 999px;
  }

  .status-badge-dot {
    flex-shrink: 0;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  /* 圓點是實色小面積用飽和值，文字疊在淺底上要用深一階的值才過 4.5:1 */
  .status-badge--success { color: var(--color-success-text); }
  .status-badge--warning { color: var(--color-warning-text); }
  .status-badge--danger { color: var(--color-error-text); }
  .status-badge--neutral { color: var(--color-ink-soft); }

  .status-badge--success .status-badge-dot { background: var(--color-success); }
  .status-badge--warning .status-badge-dot { background: var(--color-warning); }
  .status-badge--danger .status-badge-dot { background: var(--color-error); }
  .status-badge--neutral .status-badge-dot { background: var(--color-ink-soft); }

  .status-badge--badge.status-badge--success { background: var(--color-success-bg); }
  .status-badge--badge.status-badge--warning { background: var(--color-warning-bg); }
  .status-badge--badge.status-badge--danger { background: var(--color-error-bg); }
  .status-badge--badge.status-badge--neutral { background: var(--color-surface-alt); }
</style>
