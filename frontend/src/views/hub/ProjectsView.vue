<template>
  <div class="projects">
    <PageHeader subtitle="管理您的研究專案與分析" title="專案">
      <template #actions>
        <AppButton variant="secondary" @click="isEditing = !isEditing">
          <v-icon :icon="isEditing ? 'mdi-check' : 'mdi-pencil-outline'" size="17" />
          {{ isEditing ? '完成' : '編輯' }}
        </AppButton>
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
        v-slot="{ href, navigate }"
        custom
        :to="projectLink(project)"
      >
        <!-- 用 custom slot 自己渲染 <a>：先前用 component :is 在 RouterLink 與 div
             之間切換，元素型別一變 Vue 會重建整批卡片，enter-stagger 就跟著重播 -->
        <a
          class="project-card"
          :class="{ 'project-card--editing': isEditing }"
          :href="href"
          @click="isEditing ? $event.preventDefault() : navigate($event)"
        >
          <div class="project-title-row">
            <div class="project-icon-wrap">
              <v-icon icon="mdi-folder-outline" size="19" />
            </div>
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
          <!-- 一律留在版面上，只切換內容，避免進行中的卡片比其他卡片高一截。
               編輯模式借用同一塊位置放刪除鈕，卡片高度與其他元素的位置都不會動 -->
          <div class="progress-wrap" :class="{ 'progress-wrap--editing': isEditing }">
            <button
              v-if="isEditing"
              :aria-label="`刪除專案「${project.name}」`"
              class="project-delete-btn"
              type="button"
              @click.stop.prevent="requestDelete(project)"
            >
              <v-icon icon="mdi-trash-can-outline" size="16" />
            </button>
            <template v-else-if="project.status === 'running'">
              <div class="progress-label-row">
                <span class="progress-label">分析進度</span>
                <span class="progress-pct">{{ project.progress }}%</span>
              </div>
              <div class="progress-track">
                <div class="progress-bar" :style="{ width: `${project.progress}%` }" />
              </div>
            </template>
          </div>
        </a>
      </RouterLink>
    </div>

    <ConfirmDialog
      confirm-text="刪除"
      :message="`確定要刪除「${pendingDelete?.name}」嗎？此動作無法復原。`"
      title="刪除專案"
      :visible="pendingDelete !== null"
      @cancel="pendingDelete = null"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
  import type { Project } from '@/store/projectStore'
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import AppButton from '@/components/ui/AppButton.vue'
  import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'
  import { projectLink } from '@/utils/projectLink'

  const router = useRouter()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const isEditing = ref(false)
  const pendingDelete = ref<Project | null>(null)

  function requestDelete (project: Project): void {
    pendingDelete.value = project
  }

  async function confirmDelete (): Promise<void> {
    if (!pendingDelete.value) return
    try {
      await store.deleteProject(pendingDelete.value.id)
    } catch (error) {
      console.error('刪除專案失敗', error)
    } finally {
      pendingDelete.value = null
    }
  }

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
    /* 固定高度：專案名稱長短、有沒有進度條都不該讓同一列的卡片高低不一 */
    height: 168px;
    padding: 18px 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    text-decoration: none;
    transition: transform var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  /* 編輯模式下卡片不可點擊進入，游標改回預設、拿掉 hover 位移避免誤導 */
  .project-card--editing {
    cursor: default;
  }

  .project-card--editing:hover {
    transform: none;
  }

  /* 只有編輯模式看得到。卡片上已經有一堆方角圓角，這顆做成圓形不再多一種圓角 */
  .project-delete-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border: none;
    border-radius: 50%;
    background: var(--color-surface-alt);
    color: var(--color-error);
    cursor: pointer;
    transition: background var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }

  .project-delete-btn:hover {
    background: var(--color-error-bg);
    color: var(--color-error-text);
  }

  .project-delete-btn:active {
    transform: scale(0.94);
  }

  .project-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in oklab, var(--color-ink) 24%, var(--color-surface));
    box-shadow: var(--shadow-card);
  }

  .project-title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }

  /* 跟框架庫的 .fw-icon-wrap 同一套。純裝飾，不帶狀態資訊 —— 狀態由右邊的徽章負責 */
  .project-icon-wrap {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 10%, var(--color-surface));
    color: var(--color-ink);
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
    margin-top: auto;
    /* 標籤列 + 軌道的高度，空的時候一樣佔著 */
    min-height: 27px;
  }

  .progress-wrap--editing {
    display: flex;
    justify-content: flex-end;
    align-items: flex-end;
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
