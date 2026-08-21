<template>
  <div class="project-detail">
    <template v-if="project">
      <PageHeader :subtitle="`框架：${frameworkTitle}`" :title="project.name">
        <template #back>
          <RouterLink class="back-link" to="/hub/projects">
            <v-icon icon="mdi-arrow-left" size="15" />
            返回專案
          </RouterLink>
        </template>
        <template #actions>
          <StatusBadge :status="statusTone[project.status]">
            {{ statusLabel[project.status] }}
          </StatusBadge>
        </template>
      </PageHeader>

      <!-- Detail panels -->
      <div class="detail-panels">
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
            <div class="result-divider" />
            <RouterLink class="view-result-btn" :to="`/hub/projects/${project.id}/result`">
              查看完整結果
              <v-icon icon="mdi-arrow-right" size="14" />
            </RouterLink>

            <div v-if="hasPaper !== null" class="paper-actions">
              <template v-if="hasPaper">
                <RouterLink class="paper-btn paper-btn--secondary" :to="`/paper/sources?project=${project.id}`">
                  重新生成論文
                </RouterLink>
                <RouterLink class="paper-btn" :to="`/paper?project=${project.id}`">
                  查看論文
                </RouterLink>
              </template>
              <RouterLink v-else class="paper-btn" :to="`/paper/sources?project=${project.id}`">
                生成論文
              </RouterLink>
            </div>
          </template>

          <!-- Running -->
          <template v-else-if="project.status === 'running'">
            <div class="running-state">
              <!-- 骨架屏佔住結果將來出現的位置，跑完換上真值時版面高度不跳 -->
              <div class="detail-skeleton">
                <div class="skeleton-line" style="width: 40%" />
                <div class="skeleton-line" style="width: 70%" />
                <div class="skeleton-line" style="width: 55%" />
              </div>
              <div class="running-text">分析進行中... {{ project.progress }}% 完成</div>
            </div>
          </template>

          <!-- Draft -->
          <template v-else>
            <div class="draft-state">尚未執行此專案</div>
          </template>

          <!-- Open in Workflow button -->
          <div class="open-workflow-wrap">
            <AppButton variant="primary" @click="openInWorkflow">
              <v-icon :icon="needsMapping ? 'mdi-table-arrow-right' : 'mdi-sitemap-outline'" size="16" />
              {{ needsMapping ? '繼續欄位對齊' : '在 Workflow 中開啟' }}
            </AppButton>
          </div>
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
            <div class="info-value">{{ project.datasetName || '（未上傳）' }}</div>
          </div>
          <div class="info-row">
            <div class="info-label">變數</div>
            <div class="info-value">{{ project.variables }} 個已對應</div>
          </div>
        </div>
      </div>
    </template>

    <!-- Not found -->
    <template v-else>
      <RouterLink class="back-link back-link--standalone" to="/hub/projects">
        <v-icon icon="mdi-arrow-left" size="15" />
        返回專案
      </RouterLink>
      <div class="not-found">找不到該專案</div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import { usePaperExists } from '@/composables/paper/usePaperExists'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { type Project, useProjectStore } from '@/store/projectStore'

  const route = useRoute()
  const router = useRouter()
  const store = useProjectStore()
  const frameworkStore = useFrameworkStore()

  const statusLabel: Record<Project['status'], string> = {
    completed: '已完成',
    running: '進行中',
    draft: '草稿',
  }

  // 與專案列表用同一組對應，同一個狀態在兩處長得一樣
  const statusTone: Record<Project['status'], 'success' | 'warning' | 'neutral'> = {
    completed: 'success',
    running: 'warning',
    draft: 'neutral',
  }

  const project = computed(() =>
    store.projects.find(p => p.id === Number(route.params.id)),
  )

  const frameworkTitle = computed(() =>
    frameworkStore.frameworks.find(fw => fw.id === project.value?.frameworkId)?.title ?? '（未選擇）',
  )

  const { hasPaper } = usePaperExists(computed(() => project.value?.id))

  // 欄位對映還沒完成的話，先回對齊頁 —— 這時候進 workflow 也是什麼都不能做
  const needsMapping = computed(() =>
    !!project.value
    && project.value.status !== 'completed'
    // 用 null 判斷而非空物件：全部選「資料表中沒有此變數」時對映是 {}，但流程已走完
    && project.value.columnMapping == null,
  )

  // 這裡是打開「已存在」的專案，畫布狀態要從 localStorage 還原；
  // 不能像 CreateProjectView 一樣呼叫 setActiveContext，否則 WorkflowWorkspace
  // 會誤判成全新專案而呼叫 executeWorkflow() 把已完成的 workflow 整個清空重來
  function openInWorkflow (): void {
    if (!project.value) return
    router.push(
      needsMapping.value
        ? `/hub/projects/${project.value.id}/mapping`
        : `/workflow?project=${project.value.id}`,
    )
  }
</script>

<style scoped>
  .project-detail {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    /* 對齊 22px 標題的第一行中線 */
    margin-top: 4px;
    font-size: 13px;
    color: var(--color-ink-soft);
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .back-link:hover {
    color: var(--color-ink);
  }

  .back-link--standalone {
    margin-top: 0;
    margin-bottom: 20px;
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
    padding: 22px 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }

  .card-title {
    margin-bottom: 20px;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text);
  }

  /* ── Results ── */
  .result-row {
    padding: 14px 0;
  }

  .result-divider {
    height: 1px;
    background: var(--color-border);
  }

  .result-label {
    margin-bottom: 6px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .result-value {
    font-size: 14px;
    color: var(--color-text);
  }

  /* 準確率是這頁唯一的展示型數字，用藏青當視覺錨點 */
  .result-value.large {
    font-size: 32px;
    font-weight: 500;
    line-height: 1;
    color: var(--color-ink);
  }

  .view-result-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding-top: 14px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink);
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .view-result-btn:hover {
    color: var(--color-ink-strong);
  }

  .paper-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding-top: 14px;
  }

  /* 樣式比照 ResultView 的論文按鈕，同一個功能在兩處要長得一樣 */
  .paper-btn {
    display: inline-flex;
    align-items: center;
    height: 34px;
    padding: 0 16px;
    border-radius: 999px;
    background: var(--color-ink);
    color: var(--color-surface);
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    white-space: nowrap;
    transition: background var(--dur-fast) var(--ease-out);
  }

  .paper-btn:hover {
    background: var(--color-ink-strong);
  }

  .paper-btn--secondary {
    background: var(--color-surface);
    color: var(--color-ink);
    box-shadow: inset 0 0 0 1px var(--color-border);
  }

  .paper-btn--secondary:hover {
    background: var(--color-surface);
    box-shadow: inset 0 0 0 1px var(--color-ink);
  }

  /* ── Running state ── */
  .running-state {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 24px 0;
  }

  .detail-skeleton {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .running-text {
    font-size: 14px;
    color: var(--color-ink-soft);
  }

  /* ── Draft state ── */
  .draft-state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 120px;
    font-size: 14px;
    color: var(--color-ink-soft);
  }

  /* ── Open workflow button ── */
  .open-workflow-wrap {
    margin-top: 4px;
    padding-top: 20px;
    border-top: 1px solid var(--color-border);
  }

  /* ── Project info ── */
  .info-row {
    padding: 12px 0;
    border-bottom: 1px solid var(--color-border);
  }

  .info-row:last-child {
    border-bottom: none;
  }

  .info-label {
    margin-bottom: 4px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .info-value {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text);
  }

  /* ── Not found ── */
  .not-found {
    padding: 48px;
    font-size: 14px;
    text-align: center;
    color: var(--color-ink-soft);
  }
</style>
