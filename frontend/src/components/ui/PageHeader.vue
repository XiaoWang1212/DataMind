<template>
  <header class="page-header">
    <div class="page-header-lead">
      <slot name="back" />
      <div class="page-header-text">
        <h1 class="page-header-title">{{ title }}</h1>
        <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
  defineProps<{
    title: string
    subtitle?: string
  }>()
</script>

<style scoped>
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 1.5rem;
  }

  .page-header-lead {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 0;
  }

  .page-header-text {
    min-width: 0;
  }

  .page-header-title {
    margin: 0 0 4px;
    font-size: 22px;
    font-weight: 500;
    color: var(--color-text);
  }

  .page-header-sub {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .page-header-actions {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    gap: 8px;
  }
</style>
