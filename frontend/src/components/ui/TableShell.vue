<template>
  <div class="table-shell" :class="{ 'table-shell--flush': flush }">
    <slot />
  </div>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    // 表格本身已經在一張卡片裡時用這個，否則會變成卡中卡
    flush?: boolean
  }>(), {
    flush: false,
  })
</script>

<style scoped>
  /* overflow 讓表格四角吃到容器圓角；欄多時由內部橫向捲動，頁面本身不橫捲 */
  .table-shell {
    overflow: auto;
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }

  .table-shell--flush {
    border-radius: 0;
    background: none;
    box-shadow: none;
  }
</style>
