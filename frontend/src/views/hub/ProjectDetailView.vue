<template>
  <div>
    <!-- Back link -->
    <RouterLink to="/hub/projects" class="back-link">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <!-- Page header -->
    <div v-if="project" class="page-header">
      <div class="title-row">
        <h1 class="page-title">{{ project.name }}</h1>
        <span class="badge" :class="`badge--${project.status}`">
          {{ statusLabel[project.status] }}
        </span>
      </div>
      <div class="framework-link">框架：{{ project.framework }}</div>
    </div>

    <!-- Detail panels -->
    <div v-if="project" class="detail-panels">
      <!-- Analysis results -->
      <div class="results-card">
        <div class="card-title">分析結果</div>

        <!-- Completed -->
        <template v-if="project.status === 'completed'">
          <div class="result-row">
            <div class="result-label">模型準確率</div>
            <div class="result-value large">{{ project.accuracy }}</div>
          </div>
          <div class="result-divider" />
          <div class="result-row">
            <div class="result-label">關鍵發現</div>
            <div class="result-value">{{ project.keyFinding }}</div>
          </div>
        </template>

        <!-- Running -->
        <template v-else-if="project.status === 'running'">
          <div class="running-state">
            <v-progress-circular
              indeterminate
              color="#d97706"
              size="52"
              width="4"
            />
            <div class="running-text">分析進行中... {{ project.progress }}% 完成</div>
          </div>
        </template>

        <!-- Draft -->
        <template v-else>
          <div class="draft-state">尚未執行此專案</div>
        </template>
      </div>

      <!-- Project info -->
      <div class="info-card">
        <div class="card-title">專案資訊</div>
        <div class="info-row">
          <div class="info-label">建立時間</div>
          <div class="info-value">{{ project.date }}</div>
        </div>
        <div class="info-row">
          <div class="info-label">資料集</div>
          <div class="info-value">{{ project.dataset }}</div>
        </div>
        <div class="info-row">
          <div class="info-label">變數</div>
          <div class="info-value">{{ project.variables }} 個已對應</div>
        </div>
      </div>
    </div>

    <!-- Not found -->
    <div v-else class="not-found">找不到該專案</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const statusLabel: Record<string, string> = {
  completed: '已完成',
  running: '進行中',
  draft: '草稿',
}

const projectsData = [
  {
    id: '1',
    name: '市場情緒研究',
    status: 'completed',
    framework: '市場情緒回歸',
    date: '2026-05-29',
    accuracy: '87.3%',
    keyFinding: '購買頻率是流失率最強的預測因子（p < 0.001）',
    dataset: 'customer_data.csv',
    variables: 8,
    progress: 100,
  },
  {
    id: '2',
    name: '圖像分類實驗',
    status: 'running',
    framework: 'CNN 圖像分類',
    date: '2026-06-01',
    accuracy: '',
    keyFinding: '',
    dataset: 'customer_data.csv',
    variables: 8,
    progress: 67,
  },
  {
    id: '3',
    name: '用戶導航分析',
    status: 'draft',
    framework: '用戶行為 RNN',
    date: '2026-06-02',
    accuracy: '',
    keyFinding: '',
    dataset: 'customer_data.csv',
    variables: 8,
    progress: 0,
  },
]

const project = computed(() =>
  projectsData.find(p => p.id === route.params.id),
)
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 24px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.badge {
  font-size: 12.5px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: #6b7280;
}

.page-header {
  margin-bottom: 22px;
}

.framework-link {
  font-size: 13px;
  color: #2347c5;
}

/* ── Panels ── */
.detail-panels {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}

.results-card,
.info-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 20px;
}

/* ── Results ── */
.result-row {
  padding: 14px 0;
}

.result-divider {
  height: 1px;
  background: #f0f1f3;
}

.result-label {
  font-size: 12.5px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.result-value {
  font-size: 14px;
  color: #111827;
}

.result-value.large {
  font-size: 30px;
  font-weight: 700;
}

/* ── Running state ── */
.running-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 0;
}

.running-text {
  font-size: 14px;
  color: #6b7280;
}

/* ── Draft state ── */
.draft-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  font-size: 14px;
  color: #9ca3af;
}

/* ── Project info ── */
.info-row {
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.info-value {
  font-size: 13.5px;
  color: #111827;
  font-weight: 500;
}

/* ── Not found ── */
.not-found {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}
</style>
