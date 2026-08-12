<template>
  <header class="page-header">
    <div class="page-header-lead">
      <!-- 返回連結放標題上方一行，沿用專案原本的頁首排法 -->
      <div v-if="$slots.back" class="page-header-back">
        <slot name="back" />
      </div>
      <h1 class="page-header-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
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
    min-width: 0;
  }

  .page-header-back {
    margin-bottom: 10px;
    font-size: 13px;
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
