<template>
  <header class="page-header">
    <div class="page-header-lead">
      <!-- 返回連結放標題上方一行，沿用專案原本的頁首排法 -->
      <div v-if="$slots.back" class="page-header-back">
        <slot name="back" />
      </div>
      <div class="page-header-titlerow">
        <h1 class="page-header-title">{{ title }}</h1>
        <slot name="meta" />
      </div>
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

  .page-header-titlerow {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-bottom: 4px;
  }

  /* 標題用藏青而非內文黑，在漸層背景上才跟內文拉開層級。
     白色 offset/blur 把字周圍打亮，讓標題從漸層裡浮出來 */
  .page-header-title {
    margin: 0;
    font-size: 22px;
    font-weight: 500;
    letter-spacing: -0.01em;
    color: var(--color-ink-strong);
    text-shadow:
      0 1px 0 rgba(255, 255, 255, 0.9),
      0 2px 8px rgba(255, 255, 255, 0.65);
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
