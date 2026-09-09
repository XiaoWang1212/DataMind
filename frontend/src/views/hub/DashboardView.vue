<template>
  <div class="dashboard">
    <PageHeader subtitle="歡迎回來，這是您的研究概覽。" title="主頁" />

    <div class="dashboard-grid">
      <div class="action-row enter-stagger">
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
        <p v-if="activities.length === 0" class="activity-empty">
          還沒有任何活動，建立專案或提取框架後會顯示在這裡。
        </p>
        <div class="activity-list">
          <RouterLink
            v-for="(item, i) in activities"
            :key="`${item.name}-${item.date}-${i}`"
            class="activity-item"
            :class="{ 'activity-item--last': i === activities.length - 1 }"
            :to="item.link"
          >
            <span class="activity-icon">
              <v-icon :icon="item.icon" size="17" />
            </span>
            <div class="activity-info">
              <div class="activity-name-row">
                <span class="activity-name">{{ item.name }}</span>
                <StatusBadge :status="item.tone">{{ item.statusLabel }}</StatusBadge>
              </div>
              <div class="activity-meta">{{ item.meta }}</div>
            </div>
            <div class="activity-time">{{ item.time }}</div>
          </RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { RouterLink } from 'vue-router'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { type Project, useProjectStore } from '@/store/projectStore'
  import { projectLink } from '@/utils/projectLink'

  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const PROJECT_STATUS_LABEL: Record<Project['status'], string> = {
    draft: '草稿',
    running: '進行中',
    completed: '已完成',
  }

  // 與專案列表同一套配色：草稿是「還沒開始」而不是警示，用 neutral
  const PROJECT_STATUS_TONE: Record<Project['status'], ActivityItem['tone']> = {
    draft: 'neutral',
    running: 'warning',
    completed: 'success',
  }

  // date 是後端 created_at 格式化成 YYYY-MM-DD 的日期字串（沒有時分秒），
  // 所以只能做到「幾天前」這種天級的相對時間，不能像設計稿那樣精確到小時
  function relativeDateLabel (dateStr: string): string {
    const date = new Date(dateStr)
    if (Number.isNaN(date.getTime())) return dateStr

    const startOfDay = (d: Date): number => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()
    const diffDays = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86_400_000)

    if (diffDays <= 0) return '今天'
    if (diffDays === 1) return '昨天'
    if (diffDays < 30) return `${diffDays} 天前`
    return dateStr
  }

  interface ActivityItem {
    name: string
    icon: string
    statusLabel: string
    tone: 'success' | 'warning' | 'neutral'
    /** 次要資訊：專案顯示資料集、框架顯示分類標籤 */
    meta: string
    date: string
    time: string
    link: string
  }

  // 合併專案跟框架的建立紀錄，依日期排序，只取最近幾筆
  const activities = computed<ActivityItem[]>(() => {
    const fromProjects: ActivityItem[] = projectStore.projects.map(p => ({
      name: p.name,
      icon: 'mdi-folder-outline',
      statusLabel: PROJECT_STATUS_LABEL[p.status],
      tone: PROJECT_STATUS_TONE[p.status],
      meta: p.datasetName ? `資料集：${p.datasetName}` : '尚未選擇資料集',
      date: p.date,
      time: relativeDateLabel(p.date),
      link: projectLink(p),
    }))
    // 框架沒有單獨的詳情頁，退而連到框架庫列表
    const fromFrameworks: ActivityItem[] = frameworkStore.frameworks.map(f => ({
      name: f.title,
      icon: 'mdi-file-document-outline',
      statusLabel: '已提取',
      tone: 'neutral',
      meta: f.tag || f.subtitle || '已提取的論文框架',
      date: f.date,
      time: relativeDateLabel(f.date),
      link: '/hub/library',
    }))

    return [...fromProjects, ...fromFrameworks]
      .sort((a, b) => b.date.localeCompare(a.date))
      .slice(0, 5)
  })
</script>

<style scoped>
  .dashboard {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* ── 主頁面版面：行動卡片並排在上、最近活動全寬在下。兩者都只佔內容需要的高度，
     不硬撐到視窗底部，避免多出來的空白留在卡片內部 ── */
  .dashboard-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  /* ── 行動 ── */
  .action-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  @media (max-width: 860px) {
    .action-row {
      grid-template-columns: 1fr;
    }
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
    background: color-mix(in oklab, var(--color-ink) 10%, var(--color-surface));
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
  /* 下緣留白，讓最後一項 hover 的底色下方還看得到卡片白底 */
  .activity-card {
    padding: 20px 24px 16px;
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

  .activity-empty {
    margin: 0;
    padding: 14px 0;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  /* 抵銷卡片內距，讓每一項的 hover 底色與分隔線延伸到卡片邊緣 */
  .activity-list {
    margin: 0 -24px;
  }

  .activity-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 24px;
    border-bottom: 1px solid var(--color-border);
    color: inherit;
    cursor: pointer;
    text-decoration: none;
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .activity-item:hover {
    background: var(--color-surface-alt);
  }

  .activity-item--last {
    border-bottom: none;
  }

  .activity-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 10%, var(--color-surface));
    color: var(--color-ink);
  }

  .activity-info {
    /* 名稱過長時讓這一欄先被壓縮，避免時間被擠出卡片 */
    min-width: 0;
    flex: 1;
  }

  .activity-name-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .activity-name {
    overflow: hidden;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .activity-meta {
    overflow: hidden;
    font-size: 13px;
    color: var(--color-ink-soft);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .activity-time {
    margin-left: 8px;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-ink-soft);
  }
</style>
