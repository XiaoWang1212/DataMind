<template>
  <div class="table-shell">
    <slot />
  </div>
</template>

<style scoped>
  /* overflow 讓表格四角吃到容器圓角；欄多時由內部橫向捲動，頁面本身不橫捲 */
  .table-shell {
    overflow: auto;
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }
</style>
