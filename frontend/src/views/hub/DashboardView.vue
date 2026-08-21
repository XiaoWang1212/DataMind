<template>
  <div class="dashboard">
    <PageHeader subtitle="歡迎回來，這是您的研究概覽。" title="儀表板" />

    <div class="stat-grid enter-stagger">
      <div v-for="stat in stats" :key="stat.label" class="stat-card">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-number">{{ stat.value }}</div>
        <div class="stat-trend">
          <v-icon icon="mdi-trending-up" size="14" />
          {{ stat.trend }}
        </div>
      </div>
    </div>

    <div class="action-grid enter-stagger">
      <RouterLink class="action-card" to="/hub/library/extract">
        <div class="action-icon-wrap">
          <v-icon icon="mdi-file-document-plus-outline" size="22" />
        </div>
        <div class="action-text">
          <div class="action-title">提取新框架</div>
          <div class="action-desc">上傳研究論文以提取方法論和變數</div>
        </div>
      </RouterLink>

      <RouterLink class="action-card" to="/hub/projects/new">
        <div class="action-icon-wrap">
          <v-icon icon="mdi-folder-plus-outline" size="22" />
        </div>
        <div class="action-text">
          <div class="action-title">建立新專案</div>
          <div class="action-desc">將框架套用至您的資料集並執行分析</div>
        </div>
      </RouterLink>
    </div>

    <div class="activity-card">
      <div class="activity-header">
        <v-icon icon="mdi-clock-outline" size="18" />
        <span class="activity-title">最近活動</span>
      </div>
      <div
        v-for="(item, i) in activities"
        :key="i"
        class="activity-item"
        :class="{ 'activity-item--last': i === activities.length - 1 }"
      >
        <div class="activity-info">
          <div class="activity-name">{{ item.name }}</div>
          <div class="activity-status">{{ item.status }}</div>
        </div>
        <div class="activity-time">{{ item.time }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { RouterLink } from 'vue-router'
  import PageHeader from '@/components/ui/PageHeader.vue'

  const stats = [
    { label: '框架總數', value: '24', trend: '本週新增 3 個' },
    { label: '活躍專案', value: '8', trend: '2 個進行中' },
    { label: '已完成分析', value: '156', trend: '本月新增 12 個' },
  ]

  const activities = [
    { name: 'CNN 架構分析', status: '框架已提取', time: '2 小時前' },
    { name: '市場情緒研究', status: '專案已完成', time: '5 小時前' },
    { name: '回歸模型模板', status: '框架已儲存', time: '1 天前' },
  ]
</script>

<style scoped>
  .dashboard {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* ── 統計 ── */
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }

  .stat-card {
    padding: 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }

  .stat-label {
    margin-bottom: 8px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  /* 用藏青讓三個數字成為畫面的視覺錨點 */
  .stat-number {
    margin-bottom: 10px;
    font-size: 32px;
    font-weight: 500;
    line-height: 1;
    color: var(--color-ink);
  }

  .stat-trend {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* ── 行動 ── */
  .action-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-bottom: 16px;
  }

  .action-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    text-decoration: none;
    transition: transform var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  .action-card:hover {
    transform: translateY(-2px);
    border-color: var(--color-ink);
    box-shadow: var(--shadow-card);
  }

  .action-icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: var(--radius-sm);
    /* 從品牌色推導，不另外引入游離色碼 */
    background: color-mix(in oklab, var(--color-ink) 10%, white);
    color: var(--color-ink);
  }

  .action-title {
    margin-bottom: 3px;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text);
  }

  .action-desc {
    font-size: 13px;
    line-height: 1.45;
    color: var(--color-ink-soft);
  }

  /* ── 最近活動 ── */
  .activity-card {
    padding: 20px 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }

  .activity-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    color: var(--color-text);
  }

  .activity-title {
    font-size: 15px;
    font-weight: 500;
  }

  /* 負邊距讓 hover 底色延伸到卡片邊緣 */
  .activity-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0 -24px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--color-border);
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .activity-item:hover {
    background: var(--color-surface-alt);
  }

  .activity-item--last {
    border-bottom: none;
    padding-bottom: 0;
  }

  .activity-name {
    margin-bottom: 4px;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .activity-status {
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .activity-time {
    margin-left: 24px;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-ink-soft);
  }
</style>
