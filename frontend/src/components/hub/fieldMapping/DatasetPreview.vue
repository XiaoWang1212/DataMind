<template>
  <div class="preview-block">
    <div class="preview-title">資料預覽（前 {{ rows.length }} 筆）</div>
    <div class="preview-scroll">
      <table class="preview-table">
        <thead>
          <tr><th v-for="col in columns" :key="col">{{ col }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i">
            <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
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
    font-weight: 600;
    color: var(--color-secondary);
    margin-bottom: 8px;
  }

  .preview-scroll {
    overflow-x: auto;
  }

  .preview-table {
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-table th,
  .preview-table td {
    padding: 6px 10px;
    border: 1px solid #f0f1f3;
    color: var(--color-secondary);
  }

  .preview-table th {
    background: var(--color-background);
    font-weight: 600;
  }
</style>
