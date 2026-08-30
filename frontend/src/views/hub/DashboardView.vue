<template>
  <div class="dashboard">
    <PageHeader subtitle="歡迎回來，這是您的研究概覽。" title="主頁" />

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
      <p v-if="activities.length === 0" class="activity-empty">
        還沒有任何活動，建立專案或提取框架後會顯示在這裡。
      </p>
      <div
        v-for="(item, i) in activities"
        :key="`${item.name}-${item.date}-${i}`"
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
  import { computed } from 'vue'
  import { RouterLink } from 'vue-router'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { type Project, useProjectStore } from '@/store/projectStore'

  const projectStore = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const PROJECT_STATUS_LABEL: Record<Project['status'], string> = {
    draft: '專案草稿',
    running: '專案進行中',
    completed: '專案已完成',
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
    status: string
    date: string
    time: string
  }

  // 合併專案跟框架的建立紀錄，依日期排序，只取最近幾筆
  const activities = computed<ActivityItem[]>(() => {
    const fromProjects: ActivityItem[] = projectStore.projects.map(p => ({
      name: p.name,
      status: PROJECT_STATUS_LABEL[p.status],
      date: p.date,
      time: relativeDateLabel(p.date),
    }))
    const fromFrameworks: ActivityItem[] = frameworkStore.frameworks.map(f => ({
      name: f.title,
      status: '框架已提取',
      date: f.date,
      time: relativeDateLabel(f.date),
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
