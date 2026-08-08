<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">專案</h1>
      <p class="page-sub">管理您的研究專案與分析</p>
    </div>

    <!-- New project button -->
    <RouterLink class="new-btn" to="/hub/projects/new">
      <v-icon icon="mdi-folder-plus-outline" size="17" />
      新專案
    </RouterLink>

    <!-- Project list -->
    <div class="project-list">
      <RouterLink
        v-for="project in store.projects"
        :key="project.id"
        class="project-card"
        :to="projectLink(project)"
      >
        <div class="project-main">
          <div class="project-title-row">
            <span class="project-name">{{ project.name }}</span>
            <span class="badge" :class="`badge--${project.status}`">
              {{ statusLabel[project.status] }}
            </span>
          </div>
          <div class="project-meta">框架：{{ project.frameworkName }}</div>
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
        </div>
        <v-icon class="project-arrow" icon="mdi-chevron-right" size="18" />
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Project } from '@/store/projectStore'
import { RouterLink } from 'vue-router'
import { useProjectStore } from '@/store/projectStore'

const store = useProjectStore()

const statusLabel: Record<string, string> = {
  completed: '已完成',
  running: '進行中',
  draft: '草稿',
}

function projectLink(project: Project): string {
  return project.status === 'running'
    ? `/workflow?project=${project.id}`
    : `/hub/projects/${project.id}`
}
</script>

<style scoped>
.page-header {
  margin-bottom: 22px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── New button ── */
.new-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  margin-bottom: 18px;
  transition: background 0.15s;
}

.new-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Project list ── */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.project-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 22px;
  text-decoration: none;
  transition: border-color 0.15s;
}

.project-card:hover {
  border-color: #c7d2fe;
}

.project-main {
  flex: 1;
  min-width: 0;
}

.project-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.project-name {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-ink);
}

/* ── Badges ── */
.badge {
  font-size: 11.5px;
  font-weight: 500;
  padding: 2px 9px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #2347c5;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: var(--color-secondary);
}

/* ── Meta ── */
.project-meta {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-bottom: 5px;
}

.project-date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--color-secondary);
}

.date-icon {
  color: var(--color-secondary);
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
  color: var(--color-secondary);
}

.progress-pct {
  font-size: 12px;
  color: var(--color-secondary);
}

.progress-track {
  height: 5px;
  background: #f0f0f0;
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #f59e0b;
  border-radius: 99px;
  transition: width 0.3s;
}

.project-arrow {
  color: #c4c9d4;
  flex-shrink: 0;
  margin-left: 16px;
}
</style>
