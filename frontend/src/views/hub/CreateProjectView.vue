<template>
  <div class="create-project">
    <PageHeader subtitle="按照步驟設定您的研究專案" title="建立新專案">
      <template #back>
        <RouterLink class="back-link" to="/hub/projects">
          <v-icon icon="mdi-arrow-left" size="15" />
          返回專案
        </RouterLink>
      </template>
    </PageHeader>

    <!-- Stepper -->
    <div class="stepper">
      <div v-for="(step, i) in steps" :key="i" class="stepper-item">
        <div class="step-circle" :class="stepCircleClass(i)">
          {{ i + 1 }}
        </div>
        <div class="step-info">
          <div class="step-title" :class="{ 'step-title--active': currentStep === i }">
            {{ step.title }}
          </div>
          <div class="step-sub">{{ step.sub }}</div>
        </div>
        <div v-if="i < steps.length - 1" class="stepper-line" />
      </div>
    </div>

    <!-- Form card -->
    <div class="form-card">
      <!-- Step 1: Project Settings -->
      <template v-if="currentStep === 0">
        <div class="form-field">
          <label class="form-label">專案名稱</label>
          <input
            v-model="form.name"
            class="form-input"
            placeholder="例如：客戶流失分析"
          >
        </div>
        <div class="form-field">
          <label class="form-label">描述（選填）</label>
          <textarea
            v-model="form.description"
            class="form-textarea"
            placeholder="描述您的研究目標..."
            rows="4"
          />
        </div>
      </template>

      <!-- Step 2: Select Framework -->
      <template v-if="currentStep === 1">
        <div class="fw-select-grid">
          <div
            v-for="fw in frameworkStore.frameworks"
            :key="fw.id"
            class="fw-select-card"
            :class="{ 'fw-select-card--selected': form.frameworkId === fw.id }"
            @click="form.frameworkId = fw.id"
          >
            <div class="fw-select-icon">
              <v-icon icon="mdi-book-open-outline" size="20" />
            </div>
            <div class="fw-select-name">{{ fw.title }}</div>
            <div class="fw-select-tag">{{ fw.tag }}</div>
          </div>
        </div>
      </template>

      <!-- Step 3: Upload Dataset -->
      <template v-if="currentStep === 2">
        <div
          class="drop-zone"
          @click="datasetInput?.click()"
          @dragover.prevent
          @drop.prevent="handleDatasetDrop"
        >
          <v-icon class="drop-icon" icon="mdi-table-arrow-up" size="48" />
          <div class="drop-text">點擊或拖放資料集檔案</div>
          <div class="drop-hint">支援 CSV、Excel（最大 50MB）</div>
          <input
            ref="datasetInput"
            accept=".csv,.xlsx,.xls"
            hidden
            type="file"
            @change="handleDatasetChange"
          >
        </div>
        <div v-if="form.datasetFile" class="file-info">
          <v-icon icon="mdi-file-table-outline" size="18" />
          <span class="file-name">{{ form.datasetFile.name }}</span>
        </div>
      </template>

      <!-- Step 4: Review & Execute -->
      <template v-if="currentStep === 3">
        <div class="review-section">
          <div class="review-title">專案摘要</div>
          <div class="review-row">
            <span class="review-key">專案名稱</span>
            <span class="review-val">{{ form.name || '（未填寫）' }}</span>
          </div>
          <div class="review-row">
            <span class="review-key">描述</span>
            <span class="review-val">{{ form.description || '（無）' }}</span>
          </div>
          <div class="review-row">
            <span class="review-key">選擇框架</span>
            <span class="review-val">{{ selectedFramework?.title || '（未選擇）' }}</span>
          </div>
          <div class="review-row">
            <span class="review-key">資料集</span>
            <span class="review-val">{{ form.datasetFile?.name || '（未上傳）' }}</span>
          </div>
        </div>
      </template>
    </div>

    <!-- Footer buttons -->
    <div class="form-footer">
      <AppButton :disabled="currentStep === 0" variant="ghost" @click="currentStep--">
        上一步
      </AppButton>
      <AppButton v-if="currentStep < 3" variant="secondary" @click="currentStep++">
        下一步
        <v-icon icon="mdi-chevron-right" size="17" />
      </AppButton>
      <AppButton v-else :loading="submitting" variant="primary" @click="executeProject">
        執行分析
        <v-icon icon="mdi-play-outline" size="17" />
      </AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { saveWorkflowDataFileToStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'

  const router = useRouter()
  const frameworkStore = useFrameworkStore()
  const projectStore = useProjectStore()
  const datasetInput = ref<HTMLInputElement | null>(null)
  const currentStep = ref(0)
  const submitting = ref(false)

  const steps = [
    { title: '專案設定', sub: '基本資訊' },
    { title: '選擇框架', sub: '選擇研究框架' },
    { title: '上傳資料集', sub: '對應您的資料' },
    { title: '審閱並執行', sub: '確認並執行' },
  ]

  const form = ref({
    name: '',
    description: '',
    frameworkId: null as number | null,
    datasetFile: null as File | null,
  })

  const selectedFramework = computed(() =>
    frameworkStore.frameworks.find(f => f.id === form.value.frameworkId) ?? null,
  )

  function stepCircleClass (i: number): string {
    if (i < currentStep.value) return 'step-circle--done'
    if (i === currentStep.value) return 'step-circle--active'
    return 'step-circle--inactive'
  }

  function handleDatasetChange (e: Event): void {
    const input = e.target as HTMLInputElement
    if (input.files?.[0]) form.value.datasetFile = input.files[0]
  }

  function handleDatasetDrop (e: DragEvent): void {
    const file = e.dataTransfer?.files[0]
    if (file) form.value.datasetFile = file
  }

  async function executeProject (): Promise<void> {
    submitting.value = true
    try {
      const project = await projectStore.addProject({
        name: form.value.name || '未命名專案',
        description: form.value.description,
        frameworkId: form.value.frameworkId,
        datasetName: form.value.datasetFile?.name ?? '',
        variables: selectedFramework.value?.variables ?? 0,
      })

      projectStore.setActiveContext({
        projectId: project.id,
        datasetFile: form.value.datasetFile,
        frameworkId: form.value.frameworkId,
      })

      // 先寫進 IndexedDB：activeContext 只活在記憶體裡，
      // 使用者在對齊頁按重新整理就會遺失。
      // useWorkflowStorage 的 projectId 參數是字串，而 Project.id 是數字。
      if (form.value.datasetFile) {
        await saveWorkflowDataFileToStorage(form.value.datasetFile, String(project.id))
      }

      router.push(`/hub/projects/${project.id}/mapping`)
    } finally {
      submitting.value = false
    }
  }
</script>

<style scoped>
  .create-project {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* 對齊 22px 標題的第一行 */
  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-top: 3px;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-ink-soft);
    text-decoration: none;
    transition: color var(--dur-fast) var(--ease-out);
  }

  .back-link:hover {
    color: var(--color-text);
  }

  /* ── Stepper ── */
  .stepper {
    position: relative;
    display: flex;
    align-items: flex-start;
    gap: 0;
    margin-bottom: 28px;
  }

  .stepper-item {
    position: relative;
    display: flex;
    flex: 1;
    align-items: flex-start;
    gap: 10px;
  }

  .stepper-line {
    position: absolute;
    top: 16px;
    left: calc(100% - 50%);
    z-index: 0;
    width: calc(100% - 44px);
    height: 1px;
    background: var(--color-border);
  }

  .step-circle {
    position: relative;
    z-index: 1;
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    font-size: 13px;
    font-weight: 500;
  }

  .step-circle--active,
  .step-circle--done {
    background: var(--color-ink);
    color: var(--color-surface);
  }

  .step-circle--inactive {
    border: 2px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-ink-soft);
  }

  .step-info {
    flex: 1;
    padding-top: 4px;
  }

  .step-title {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .step-title--active {
    color: var(--color-text);
  }

  .step-sub {
    margin-top: 2px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* ── Form card ── */
  /* 卡片與頁尾按鈕列拼成同一塊，圓角只留在整組的外緣 */
  .form-card {
    padding: 28px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    background: var(--color-surface);
    color: var(--color-text);
  }

  .form-field {
    margin-bottom: 20px;
  }

  .form-label {
    display: block;
    margin-bottom: 7px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .form-input {
    box-sizing: border-box;
    width: 100%;
    height: 40px;
    padding: 0 12px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-sm);
    outline: none;
    background-color: var(--color-surface);
    color: var(--color-text);
    color-scheme: light;
    font-size: 14px;
    transition: border-color var(--dur-fast) var(--ease-out);
  }

  .form-input::placeholder {
    color: var(--color-ink-soft);
  }

  .form-input:focus {
    border-color: var(--color-ink);
  }

  .form-textarea {
    box-sizing: border-box;
    width: 100%;
    padding: 10px 12px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-sm);
    outline: none;
    background-color: var(--color-surface);
    color: var(--color-text);
    color-scheme: light;
    font-family: inherit;
    font-size: 14px;
    resize: vertical;
    transition: border-color var(--dur-fast) var(--ease-out);
  }

  .form-textarea::placeholder {
    color: var(--color-ink-soft);
  }

  .form-textarea:focus {
    border-color: var(--color-ink);
  }

  /* ── Framework select ── */
  .fw-select-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .fw-select-card {
    padding: 16px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: border-color var(--dur-fast) var(--ease-out),
      background-color var(--dur-fast) var(--ease-out);
  }

  .fw-select-card:hover {
    border-color: color-mix(in oklab, var(--color-ink) 24%, white);
  }

  .fw-select-card--selected {
    border-color: var(--color-ink);
    background: color-mix(in oklab, var(--color-ink) 6%, white);
  }

  .fw-select-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    margin-bottom: 10px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 10%, white);
    color: var(--color-ink);
  }

  .fw-select-name {
    margin-bottom: 4px;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .fw-select-tag {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* ── Drop zone ── */
  .drop-zone {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 48px 24px;
    border: 2px dashed var(--color-border-strong);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: border-color var(--dur-fast) var(--ease-out),
      background-color var(--dur-fast) var(--ease-out);
  }

  .drop-zone:hover {
    border-color: var(--color-ink);
    background: color-mix(in oklab, var(--color-ink) 6%, white);
  }

  .drop-icon {
    margin-bottom: 4px;
    color: var(--color-ink-soft);
  }

  .drop-text {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .drop-hint {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .file-info {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    padding: 10px 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface-alt);
    color: var(--color-ink);
  }

  .file-name {
    font-size: 13px;
    color: var(--color-text);
  }

  /* ── Review ── */
  .review-section {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .review-title {
    margin-bottom: 16px;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text);
  }

  .review-row {
    display: flex;
    padding: 12px 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 14px;
  }

  .review-key {
    flex-shrink: 0;
    width: 120px;
    color: var(--color-ink-soft);
  }

  .review-val {
    font-weight: 500;
    color: var(--color-text);
  }

  /* ── Footer buttons ── */
  .form-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: -1px;
    padding: 18px 28px;
    border: 1px solid var(--color-border);
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    background: var(--color-surface);
    color: var(--color-text);
  }
</style>
