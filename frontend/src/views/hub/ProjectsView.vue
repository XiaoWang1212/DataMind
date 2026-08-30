<template>
  <div class="projects">
    <PageHeader subtitle="管理您的研究專案與分析" title="專案">
      <template #actions>
        <AppButton variant="primary" @click="goToCreate">
          <v-icon icon="mdi-folder-plus-outline" size="17" />
          新專案
        </AppButton>
      </template>
    </PageHeader>

    <!-- Project list -->
    <div class="project-list enter-stagger">
      <RouterLink
        v-for="project in store.projects"
        :key="project.id"
        class="project-card"
        :to="projectLink(project)"
      >
        <div class="project-title-row">
          <span class="project-name">{{ project.name }}</span>
          <StatusBadge :status="statusTone[project.status]">
            {{ statusLabel[project.status] }}
          </StatusBadge>
        </div>
        <div class="project-meta">框架：{{ frameworkTitle(project) }}</div>
        <div class="project-date">
          <v-icon class="date-icon" icon="mdi-calendar-outline" size="13" />
          {{ project.date }}
        </div>
        <div v-if="project.status === 'running'" class="progress-wrap">
          <div class="progress-label-row">
            <span class="progress-label">分析進度</span>
            <span class="progress-pct">{{ project.progress }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-bar" :style="{ width: `${project.progress}%` }" />
          </div>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { Project } from '@/store/projectStore'
  import { RouterLink, useRouter } from 'vue-router'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { projectLink } from '@/utils/projectLink'

  const router = useRouter()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const statusLabel: Record<Project['status'], string> = {
    completed: '已完成',
    running: '進行中',
    draft: '草稿',
  }

  // 草稿是「還沒開始」而不是警示，用 neutral 才不會把狀態色當裝飾用
  const statusTone: Record<Project['status'], 'success' | 'warning' | 'neutral'> = {
    completed: 'success',
    running: 'warning',
    draft: 'neutral',
  }

  function frameworkTitle (project: Project): string {
    return frameworkStore.frameworks.find(fw => fw.id === project.frameworkId)?.title ?? '（未選擇）'
  }

  function goToCreate (): void {
    router.push('/hub/projects/new')
  }
</script>

<style scoped>
  .projects {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* ── Project grid ── */
  .project-list {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
  }

  /* hover 跟框架庫的 .fw-card 同一套 */
  .project-card {
    display: flex;
    flex-direction: column;
    padding: 18px 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    text-decoration: none;
    transition: transform var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  .project-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in oklab, var(--color-ink) 24%, white);
    box-shadow: var(--shadow-card);
  }

  .project-title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }

  .project-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* ── Meta ── */
  .project-meta {
    margin-bottom: 5px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .project-date {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .date-icon {
    color: var(--color-ink-soft);
  }

  /* ── Progress ── */
  .progress-wrap {
    margin-top: 10px;
  }

  .progress-label-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
  }

  .progress-label {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .progress-pct {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .progress-track {
    height: 5px;
    border-radius: 999px;
    background: var(--color-surface-alt);
    overflow: hidden;
  }

  /* 進度條沿用「進行中」徽章的琥珀，讓同一張卡上的狀態訊號一致 */
  .progress-bar {
    height: 100%;
    border-radius: 999px;
    background: var(--color-warning);
    transition: width var(--dur-base) var(--ease-in-out);
  }

</style>
