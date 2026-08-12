<template>
  <div class="preview-block">
    <div class="preview-title">資料預覽（前 {{ rows.length }} 筆）</div>
    <TableShell>
      <table class="ds-table">
        <thead>
          <tr><th v-for="col in columns" :key="col" class="ds-identifier">{{ col }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i">
            <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </TableShell>
  </div>
</template>

<script setup lang="ts">
  import TableShell from '@/components/ui/TableShell.vue'

  defineProps<{
    columns: string[]
    rows: string[][]
  }>()
</script>

<style scoped>
  .preview-block {
    padding-top: 4px;
  }

  .preview-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
    margin-bottom: 8px;
  }

  /* 欄位值多為短字串，斷行會讓列高不一致 */
  .preview-block :deep(.ds-table td) {
    white-space: nowrap;
  }
</style>
