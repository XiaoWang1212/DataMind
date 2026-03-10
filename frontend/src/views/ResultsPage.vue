<template>
  <section class="results-page">

    <aside class="results-sidebar">
      <div class="sidebar-brand">
        <v-icon class="brand-icon" icon="mdi-shimmer" size="20" />
        <span class="brand-text">DataMind</span>
      </div>

      <v-btn
        class="add-btn"
        color="primary"
        prepend-icon="mdi-plus"
        rounded="lg"
      >新增</v-btn>

      <p class="section-title">最近使用</p>
      <div class="recent-list">
        <article
          v-for="item in recentRuns"
          :key="item.id"
          class="recent-item"
          :class="{ 'recent-item--active': item.active }"
        >
          <div>
            <p class="run-name">{{ item.name }}</p>
            <p class="run-time">{{ item.time }}</p>
          </div>
          <v-btn
            v-if="item.active"
            icon="mdi-dots-vertical"
            size="x-small"
            variant="text"
          />
        </article>
      </div>

      <div class="profile-box">
        <v-avatar color="primary" size="40">
          <v-icon icon="mdi-account" size="20" />
        </v-avatar>
        <div>
          <p class="profile-name">使用者帳號</p>
          <p class="profile-email">user123@email.com</p>
        </div>
      </div>
    </aside>

    <main class="results-main">
      <header class="results-toolbar">
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
        />

        <div class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="toolbar-tab"
            :class="{ 'toolbar-tab--active': tab.active }"
            type="button"
            @click="setActiveTab(tab.key)"
          >
            <v-icon :icon="tab.icon" size="14" />
            <span>{{ tab.label }}</span>
          </button>
        </div>
      </header>

      <section class="metric-grid">
        <article
          v-for="card in metricCards"
          :key="card.title"
          class="metric-card"
          :class="{ 'metric-card--accent': card.accent }"
        >
          <p class="metric-title">{{ card.title }}</p>
          <p class="metric-value">{{ card.value }}</p>
          <p class="metric-hint">{{ card.hint }}</p>
        </article>
      </section>

      <section class="insight-card">
        <div class="insight-header">
          <div class="insight-icon-wrap">
            <v-icon icon="mdi-shimmer" size="18" />
          </div>
          <h2 class="insight-title">AI生成洞察</h2>
        </div>

        <p class="insight-text">
          XGBoost模型以94.2%的準確率超越其他3個演算法。關鍵預測因素包括年齡、
          活動幅度與步態變化，模型在跌倒辨識上具備穩定泛化能力。
        </p>

        <div class="insight-tags">
          <span v-for="tag in insightTags" :key="tag" class="insight-tag">{{ tag }}</span>
        </div>
      </section>

      <section class="comparison-card">
        <div class="comparison-head">
          <h3>模型效能比較</h3>
          <p>所有模型均採用 5 折交叉驗證訓練</p>
        </div>

        <div class="table-wrap">
          <table class="result-table">
            <thead>
              <tr>
                <th>模型</th>
                <th>準確率</th>
                <th>精準度</th>
                <th>召回率</th>
                <th>F1 分數</th>
                <th>訓練時間</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in modelRows" :key="row.model">
                <td class="model-name">{{ row.model }}</td>
                <td :class="{ 'score-best': row.best }">{{ row.accuracy }}</td>
                <td>{{ row.precision }}</td>
                <td>{{ row.recall }}</td>
                <td>{{ row.f1 }}</td>
                <td>{{ row.time }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </main>
  </section>
</template>

<script setup lang="ts">
  import { onMounted, ref } from 'vue'

  onMounted(() => {
    document.title = 'DataMind'
  })

  interface RecentRun {
    id: string
    name: string
    time: string
    active?: boolean
  }

  interface MetricCard {
    title: string
    value: string
    hint: string
    accent?: boolean
  }

  interface ResultRow {
    model: string
    accuracy: string
    precision: string
    recall: string
    f1: string
    time: string
    best?: boolean
  }

  interface ToolbarTab {
    key: string
    label: string
    icon: string
    active?: boolean
  }

  const recentRuns: RecentRun[] = [
    { id: 'r1', name: 'XXXXXX', time: 'XX天前', active: true },
    { id: 'r2', name: 'XXXXXX', time: 'XX天前' },
    { id: 'r3', name: 'XXXXXX', time: 'XX天前' },
    { id: 'r4', name: 'XXXXXX', time: 'XX天前' },
    { id: 'r5', name: 'XXXXXX', time: 'XX天前' },
    { id: 'r6', name: 'XXXXXX', time: 'XX天前' },
  ]

  const tabs = ref<ToolbarTab[]>([
    { key: 'report', label: '報告', icon: 'mdi-file-document-outline', active: true },
    { key: 'code', label: '程式碼', icon: 'mdi-code-tags', active: false },
  ])

  const setActiveTab = (targetKey: ToolbarTab['key']) => {
    tabs.value.forEach((tab) => {
      tab.active = tab.key === targetKey
    })
  }

  const metricCards: MetricCard[] = [
    { title: '最佳模型', value: 'XGBoost', hint: '極限梯度提升' },
    { title: '準確率', value: '94.2%', hint: '較基準提升 +2.8%', accent: true },
    { title: 'F1 分數', value: '0.91', hint: '平衡表現' },
    { title: 'AUC_ROC', value: '0.96', hint: '優秀的區分能力' },
  ]

  const insightTags = ['模型信心度高', '未偵測到資料洩漏', '可投入生產環境']

  const modelRows: ResultRow[] = [
    {
      model: 'XGBoost',
      accuracy: '94.2%',
      precision: '0.93',
      recall: '0.89',
      f1: '0.91',
      time: '2 分 14 秒',
      best: true,
    },
    {
      model: 'Random Forest',
      accuracy: '92.8%',
      precision: '0.91',
      recall: '0.87',
      f1: '0.89',
      time: '1 分 58 秒',
    },
    {
      model: 'LightGBM',
      accuracy: '93.5%',
      precision: '0.92',
      recall: '0.88',
      f1: '0.90',
      time: '1 分 42 秒',
    },
    {
      model: 'SVM',
      accuracy: '89.7%',
      precision: '0.87',
      recall: '0.84',
      f1: '0.85',
      time: '3 分 36 秒',
    },
  ]
</script>

<style scoped>
  .results-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    --brand-soft: #ebf2ff;
    --good: #18a836;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    position: relative;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .results-sidebar {
    width: 240px;
    flex-shrink: 0;
    border: 1px solid var(--line);
    border-right: none;
    border-radius: 12px 0 0 12px;
    background: linear-gradient(180deg, #f3f4f8 0%, #eceef4 100%);
    padding: 18px 14px 0;
    display: flex;
    flex-direction: column;
  }

  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--brand);
    font-weight: 700;
    font-size: 31px;
  }

  .brand-icon {
    color: var(--brand);
  }

  .add-btn {
    margin-top: 14px;
    max-width: 100%;
    font-weight: 700;
    letter-spacing: 0;
    text-transform: none;
  }

  .section-title {
    margin: 18px 2px 10px;
    color: var(--text-secondary);
    font-size: 13px;
  }

  .recent-list {
    flex: 1;
    overflow: auto;
    padding-right: 4px;
  }

  .recent-item {
    border-radius: 10px;
    margin-bottom: 10px;
    padding: 10px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    border: 1px solid transparent;
  }

  .recent-item--active {
    border-color: #8bb3ed;
    background: #dce9fb;
  }

  .run-name {
    margin: 0;
    font-size: 30px;
    line-height: 1.15;
    font-weight: 700;
    color: #1051b8;
  }

  .run-time {
    margin: 2px 0 0;
    font-size: 24px;
    line-height: 1.1;
    color: #1b5cc2;
  }

  .profile-box {
    margin: 0 -14px;
    padding: 12px 14px;
    border-top: 1px solid var(--line);
    background: #f2f3f8;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .profile-name {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
  }

  .profile-email {
    margin: 0;
    font-size: 11px;
    color: #9ca1aa;
  }

  .results-main {
    flex: 1;
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: auto;
  }

  .results-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
    animation: slide-in 0.45s ease both;
  }

  .back-btn {
    color: #1f2430;
  }

  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

  .toolbar-tab {
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #5f6571;
    cursor: pointer;
    background: transparent;
    transition: all 0.2s ease;
  }

  .toolbar-tab--active {
    background: #ffffff;
    color: #192235;
    box-shadow: 0 1px 3px rgba(20, 38, 84, 0.12);
  }

  .metric-grid {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
    animation: reveal-up 0.42s ease both;
  }

  .metric-card:nth-child(2) {
    animation-delay: 0.05s;
  }

  .metric-card:nth-child(3) {
    animation-delay: 0.1s;
  }

  .metric-card:nth-child(4) {
    animation-delay: 0.15s;
  }

  .metric-card--accent .metric-value {
    color: var(--good);
  }

  .metric-title {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    color: #20232a;
  }

  .metric-value {
    margin: 8px 0 2px;
    font-size: 36px;
    font-weight: 700;
    line-height: 1.05;
  }

  .metric-hint {
    margin: 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .insight-card {
    margin-top: 12px;
    border-radius: 14px;
    color: #f7f9ff;
    padding: 14px 16px;
    background: linear-gradient(102deg, #4f86f0 0%, #4554df 100%);
    animation: reveal-up 0.5s ease both;
    animation-delay: 0.12s;
  }

  .insight-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .insight-icon-wrap {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.2);
  }

  .insight-title {
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
    font-weight: 700;
  }

  .insight-text {
    margin: 8px 0 10px;
    font-size: 13px;
    color: rgba(248, 251, 255, 0.93);
    line-height: 1.45;
  }

  .insight-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .insight-tag {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    background: rgba(255, 255, 255, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.35);
  }

  .comparison-card {
    margin-top: 12px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: #ffffff;
    overflow: hidden;
    animation: reveal-up 0.55s ease both;
    animation-delay: 0.18s;
  }

  .comparison-head {
    padding: 14px 18px;
    border-bottom: 1px solid var(--line-soft);
  }

  .comparison-head h3 {
    margin: 0;
    font-size: 29px;
  }

  .comparison-head p {
    margin: 3px 0 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .table-wrap {
    overflow: auto;
  }

  .result-table {
    width: 100%;
    min-width: 680px;
    border-collapse: collapse;
  }

  .result-table th,
  .result-table td {
    padding: 11px 18px;
    text-align: left;
    border-bottom: 1px solid var(--line-soft);
    font-size: 12px;
    white-space: nowrap;
  }

  .result-table th {
    font-weight: 700;
    color: #2a2f39;
    background: #fafbff;
  }

  .result-table tbody tr:last-child td {
    border-bottom: none;
  }

  .model-name {
    font-weight: 700;
    color: #1f2532;
  }

  .score-best {
    color: var(--good);
    font-weight: 700;
  }

  @keyframes reveal-up {
    from {
      opacity: 0;
      transform: translateY(10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1260px) {
    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .results-sidebar {
      width: 220px;
    }
  }

  @media (max-width: 920px) {
    .results-page {
      display: block;
      padding: 12px;
    }
    .results-sidebar {
      width: 100%;
      border-radius: 12px;
      border-right: 1px solid var(--line);
      padding-bottom: 12px;
    }

    .recent-list {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      max-height: 220px;
      padding-right: 0;
    }

    .recent-item {
      margin-bottom: 0;
    }

    .profile-box {
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      margin-left: 0;
      margin-right: 0;
    }

    .results-main {
      margin-top: 10px;
      border-radius: 12px;
      padding: 12px;
    }

    .insight-title,
    .comparison-head h3,
    .metric-value,
    .run-name,
    .run-time {
      font-size: clamp(20px, 4.2vw, 30px);
    }
  }

  @media (max-width: 640px) {
    .recent-list,
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .results-toolbar {
      align-items: flex-start;
      gap: 8px;
      flex-direction: column;
    }

    .toolbar-tabs {
      width: 100%;
      justify-content: space-between;
    }

    .toolbar-tab {
      flex: 1;
      justify-content: center;
    }

    .result-table {
      min-width: 620px;
    }
  }
</style>
