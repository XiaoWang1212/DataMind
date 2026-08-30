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
            <template v-if="bestModel || pipelineRows.length > 0">
              <div class="result-row">
                <div class="result-label">最佳模型</div>
                <div class="result-value result-value--model">{{ bestModel?.modelName ?? '—' }}</div>
                <div v-if="bestModel && primaryMetric" class="result-metric-hint">
                  {{ primaryMetric }}: {{ bestModel.valueFormatted }}
                </div>
              </div>
              <div class="result-divider" />

              <template v-if="pipelineRows.length > 0">
                <div v-for="row in pipelineRows" :key="row.label" class="result-row result-row--compact">
                  <div class="result-label">
                    {{ row.label }}
                    <span v-if="row.count" class="result-count">{{ row.count }} 個</span>
                  </div>
                  <div class="pipeline-pills">
                    <span v-for="value in row.values" :key="value" class="pipeline-pill">{{ value }}</span>
                  </div>
                </div>
              </template>
              <div v-else class="result-empty">找不到此專案的執行紀錄</div>
            </template>
            <div v-else class="result-empty">找不到此專案的執行紀錄</div>

            <div class="result-divider" />

            <!-- 一主一次一輕：這張卡的主題是結果，所以「查看完整結果」才是主要動作 -->
            <div class="result-actions">
              <AppButton :to="`/hub/projects/${project.id}/result`" variant="primary">
                查看完整結果
                <v-icon icon="mdi-arrow-right" size="14" />
              </AppButton>
              <template v-if="hasPaper !== null">
                <template v-if="hasPaper">
                  <AppButton :to="`/paper?project=${project.id}`" variant="secondary">
                    查看技術報告
                  </AppButton>
                  <RouterLink class="action-quiet" :to="`/paper/sources?project=${project.id}`">
                    重新生成技術報告
                  </RouterLink>
                </template>
                <AppButton v-else :to="`/paper/sources?project=${project.id}`" variant="secondary">
                  生成技術報告
                </AppButton>
              </template>
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
            <AppButton
              :variant="project.status === 'completed' && !needsMapping ? 'secondary' : 'primary'"
              @click="openInWorkflow"
            >
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
  import { loadWorkflowStateFromStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { type Project, useProjectStore } from '@/store/projectStore'
  import { summarizeWorkflowPipeline } from '@/utils/workflow/summarizeWorkflowPipeline'
  import { findBestModel, pickPrimaryMetric, summarizeWorkflowResult } from '@/utils/workflow/summarizeWorkflowResult'

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

  // nodes 與 workflowResult 存在同一份 localStorage 記錄裡，一次讀出來給兩個摘要用
  const workflowState = computed(() => loadWorkflowStateFromStorage(String(route.params.id)))

  const summary = computed(() => summarizeWorkflowResult(workflowState.value?.workflowResult ?? null))

  const primaryMetric = computed(() => pickPrimaryMetric(summary.value))

  const bestModel = computed(() =>
    primaryMetric.value ? findBestModel(summary.value, primaryMetric.value) : null,
  )

  const pipeline = computed(() => summarizeWorkflowPipeline(workflowState.value?.nodes))

  // 全空代表沒有可用的執行紀錄
  const pipelineRows = computed(() => {
    const p = pipeline.value
    // count 只給模型：其他幾類一眼數得完，標一個數字反而多餘
    const rows: Array<{ label: string, values: string[], count?: number }> = []
    if (p.preprocess.length > 0) rows.push({ label: '前處理', values: p.preprocess })
    if (p.featureEngineering.length > 0) rows.push({ label: '特徵工程', values: p.featureEngineering })
    if (p.resampling) rows.push({ label: '重採樣', values: [p.resampling] })
    if (p.validation) rows.push({ label: '驗證', values: [p.validation] })
    if (p.models.length > 0) rows.push({ label: '模型', values: p.models, count: p.models.length })
    return rows
  })

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
    font-size: 18px;
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
    margin-bottom: 4px;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .result-value {
    font-size: 14px;
    color: var(--color-text);
  }

  /* 與流程各列同字級，只用藏青色標示「這一列是答案」 */
  .result-value--model {
    font-weight: 500;
    color: var(--color-ink);
    word-break: break-word;
  }

  .result-metric-hint {
    margin-top: 4px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* 分組靠間距不靠線：列內 4px、列間 20px，差距夠大就讀得出邊界，
     一張卡裡不需要再多五條橫線 */
  .result-row--compact {
    padding: 10px 0;
  }

  .result-count {
    margin-left: 6px;
    color: var(--color-ink-soft);
  }

  /* 一步驟一顆 pill，取代原本用頓號串成一整串的寫法 —— 步驟多的時候那串會黏成一片。
     樣式跟框架庫詳情面板的 .tag-pill 同一套 */
  .pipeline-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .pipeline-pill {
    padding: 3px 10px;
    border-radius: 999px;
    background: color-mix(in oklab, var(--color-ink) 10%, white);
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-strong);
    word-break: break-word;
  }

  .result-empty {
    padding: 10px 0;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .result-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    padding-top: 16px;
    padding-bottom: 16px;
  }

  /* 重新生成會覆蓋既有報告，是低頻動作。與兩顆膠囊同排但不給外框，
     靠「沒有形狀」而不是靠更淡的顏色降聲量——太淡會被誤認成停用 */
  .action-quiet {
    margin-left: 4px;
    font-size: 13px;
    color: var(--color-ink-soft);
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .action-quiet:hover {
    color: var(--color-ink);
    text-decoration: underline;
  }

  /* ── Open workflow button ── */
  .open-workflow-wrap {
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
