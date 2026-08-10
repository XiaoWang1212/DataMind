<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">儀表板</h1>
      <p class="page-sub">歡迎回來，這是您的研究概覽。</p>
    </div>

    <!-- Stat cards -->
    <div class="stat-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-number">{{ stat.value }}</div>
        <div class="stat-trend">
          <v-icon icon="mdi-trending-up" size="14" />
          {{ stat.trend }}
        </div>
      </div>
    </div>

    <!-- Action cards -->
    <div class="action-grid">
      <RouterLink to="/hub/library/extract" class="action-card">
        <div class="action-icon-wrap action-icon-wrap--blue">
          <v-icon icon="mdi-plus" size="22" color="#4f46e5" />
        </div>
        <div class="action-text">
          <div class="action-title">提取新框架</div>
          <div class="action-desc">上傳研究論文以提取方法論和變數</div>
        </div>
      </RouterLink>

      <RouterLink to="/hub/projects/new" class="action-card">
        <div class="action-icon-wrap action-icon-wrap--orange">
          <v-icon icon="mdi-plus" size="22" color="#f59e0b" />
        </div>
        <div class="action-text">
          <div class="action-title">建立新專案</div>
          <div class="action-desc">將框架套用至您的資料集並執行分析</div>
        </div>
      </RouterLink>
    </div>

    <!-- Recent activity -->
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
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Stats ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 22px 18px;
}

.stat-label {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-bottom: 10px;
  font-weight: 400;
}

.stat-number {
  font-size: 42px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1;
  margin-bottom: 12px;
  letter-spacing: -1px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Actions ── */
.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.action-card {
  background: #ffffff;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
}

.action-card:hover {
  border-color: #a5b4fc;
  background: #fafafa;
}

.action-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon-wrap--blue {
  background: #c7d2fe;
}

.action-icon-wrap--orange {
  background: #fed7aa;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 3px;
}

.action-desc {
  font-size: 12.5px;
  color: var(--color-secondary);
  line-height: 1.45;
}

/* ── Activity ── */
.activity-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
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
  font-weight: 600;
}

.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
  border-bottom: 1px solid #f0f0f0;
}

.activity-item--last {
  border-bottom: none;
  padding-bottom: 0;
}

.activity-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 4px;
}

.activity-status {
  font-size: 12.5px;
  color: var(--color-secondary);
}

.activity-time {
  font-size: 12.5px;
  color: var(--color-secondary);
  white-space: nowrap;
  margin-left: 24px;
}
</style>
