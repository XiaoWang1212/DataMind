<template>
  <div>
    <!-- Back link -->
    <RouterLink to="/hub/projects" class="back-link">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回專案
    </RouterLink>

    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">建立新專案</h1>
      <p class="page-sub">按照步驟設定您的研究專案</p>
    </div>

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
          />
        </div>
        <div class="form-field">
          <label class="form-label">描述（選填）</label>
          <textarea
            v-model="form.description"
            class="form-textarea"
            rows="4"
            placeholder="描述您的研究目標..."
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
              <v-icon icon="mdi-book-open-outline" size="20" color="#4f46e5" />
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
          @dragover.prevent
          @drop.prevent="handleDatasetDrop"
          @click="datasetInput?.click()"
        >
          <v-icon icon="mdi-table-arrow-up" size="48" class="drop-icon" />
          <div class="drop-text">點擊或拖放資料集檔案</div>
          <div class="drop-hint">支援 CSV、Excel（最大 50MB）</div>
          <input ref="datasetInput" type="file" accept=".csv,.xlsx,.xls" hidden @change="handleDatasetChange" />
        </div>
        <div v-if="form.datasetFile" class="file-info">
          <v-icon icon="mdi-file-table-outline" size="18" color="var(--color-accent)" />
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
      <button class="prev-btn" :disabled="currentStep === 0" @click="currentStep--">
        上一步
      </button>
      <button v-if="currentStep < 3" class="next-btn" @click="currentStep++">
        下一步
        <v-icon icon="mdi-chevron-right" size="17" />
      </button>
      <button v-else class="next-btn" @click="executeProject">
        執行分析
        <v-icon icon="mdi-play" size="17" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { saveWorkflowDataFileToStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'

const router = useRouter()
const frameworkStore = useFrameworkStore()
const projectStore = useProjectStore()
const datasetInput = ref<HTMLInputElement | null>(null)
const currentStep = ref(0)

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

function stepCircleClass(i: number): string {
  if (i < currentStep.value) return 'step-circle--done'
  if (i === currentStep.value) return 'step-circle--active'
  return 'step-circle--inactive'
}

function handleDatasetChange(e: Event): void {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) form.value.datasetFile = input.files[0]
}

function handleDatasetDrop(e: DragEvent): void {
  const file = e.dataTransfer?.files[0]
  if (file) form.value.datasetFile = file
}

async function executeProject (): Promise<void> {
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
}
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-secondary);
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: var(--color-ink);
}

.page-header {
  margin-bottom: 28px;
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

/* ── Stepper ── */
.stepper {
  display: flex;
  align-items: flex-start;
  gap: 0;
  margin-bottom: 28px;
  position: relative;
}

.stepper-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  position: relative;
}

.stepper-line {
  position: absolute;
  top: 16px;
  left: calc(100% - 50%);
  width: calc(100% - 44px);
  height: 1px;
  background: #e5e7eb;
  z-index: 0;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.step-circle--active {
  background: var(--color-accent);
  color: #ffffff;
}

.step-circle--done {
  background: var(--color-accent);
  color: #ffffff;
}

.step-circle--inactive {
  background: #ffffff;
  color: var(--color-secondary);
  border: 2px solid #e5e7eb;
}

.step-info {
  flex: 1;
  padding-top: 4px;
}

.step-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-secondary);
}

.step-title--active {
  color: var(--color-ink);
}

.step-sub {
  font-size: 11.5px;
  color: var(--color-secondary);
  margin-top: 2px;
}

/* ── Form card ── */
.form-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 28px;
  margin-bottom: 0;
  color: var(--color-ink);
}

.form-field {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-secondary);
}

.form-input:focus {
  border-color: var(--color-accent);
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-textarea::placeholder {
  color: var(--color-secondary);
}

.form-textarea:focus {
  border-color: var(--color-accent);
}

/* ── Framework select ── */
.fw-select-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.fw-select-card {
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-select-card:hover {
  border-color: #a5b4fc;
}

.fw-select-card--selected {
  border-color: var(--color-accent);
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.fw-select-icon {
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.fw-select-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 4px;
}

.fw-select-tag {
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover {
  border-color: var(--color-accent);
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.drop-icon {
  color: var(--color-secondary);
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: var(--color-secondary);
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: var(--color-secondary);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.file-name {
  font-size: 13px;
  color: var(--color-secondary);
}

/* ── Review ── */
.review-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.review-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 16px;
}

.review-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
  font-size: 13.5px;
}

.review-key {
  width: 120px;
  flex-shrink: 0;
  color: var(--color-secondary);
}

.review-val {
  color: var(--color-ink);
  font-weight: 500;
}

/* ── Footer buttons ── */
.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 28px;
  background: #ffffff;
  color: var(--color-ink);
  border-radius: 0 0 8px 8px;
  border: 1px solid #e8e8e8;
  border-top: 1px solid #f0f0f0;
  margin-top: -1px;
}

.prev-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-secondary);
  padding: 0 8px;
  transition: color 0.12s;
}

.prev-btn:disabled {
  color: #d1d5db;
  cursor: default;
}

.prev-btn:not(:disabled):hover {
  color: var(--color-ink);
}

.next-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 22px;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.next-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
