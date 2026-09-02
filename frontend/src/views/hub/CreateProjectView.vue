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
      <p v-if="currentStep === 0 && stepError" class="step-error">{{ stepError }}</p>

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
            <div v-if="form.frameworkId === fw.id" class="fw-select-check">
              <v-icon icon="mdi-check-bold" size="13" />
            </div>
            <div class="fw-select-icon">
              <v-icon icon="mdi-book-open-outline" size="20" />
            </div>
            <div class="fw-select-name">{{ fw.title }}</div>
            <div class="fw-select-tag">{{ fw.tag }}</div>
          </div>
          <div
            class="fw-select-card"
            :class="{ 'fw-select-card--selected': form.frameworkId === NO_FRAMEWORK_ID }"
            @click="form.frameworkId = NO_FRAMEWORK_ID"
          >
            <div class="fw-select-icon">
              <v-icon icon="mdi-book-off-outline" size="20" />
            </div>
            <div class="fw-select-name">不使用框架</div>
            <div class="fw-select-tag">跳過欄位對齊，直接進工作區</div>
          </div>
        </div>
        <p v-if="stepError" class="step-error">{{ stepError }}</p>
      </template>

      <!-- Step 3: Upload Dataset -->
      <template v-if="currentStep === 2">
        <FileDropZone
          v-model="form.datasetFile"
          accept=".csv,.xlsx,.xls"
          accept-label="CSV、Excel"
          file-icon="mdi-file-table-outline"
          hint="支援 CSV、Excel（最大 50MB）"
          icon="mdi-table-arrow-up"
          text="點擊或拖放資料集檔案"
        />
        <p v-if="stepError" class="step-error">{{ stepError }}</p>
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
            <span class="review-val">{{ frameworkReviewLabel }}</span>
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
      <AppButton :disabled="currentStep === 0" variant="ghost" @click="goBack">
        上一步
      </AppButton>
      <AppButton v-if="currentStep < 3" variant="primary" @click="goNext">
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
  import { computed, ref, watch } from 'vue'
  import { RouterLink, useRoute, useRouter } from 'vue-router'
  import FileDropZone from '@/components/common/FileDropZone.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { saveWorkflowDataFileToStorage } from '@/composables/workflow/useWorkflowStorage'
  import { useFrameworkStore } from '@/store/frameworkStore'
  import { useProjectStore } from '@/store/projectStore'

  const route = useRoute()
  const router = useRouter()
  const frameworkStore = useFrameworkStore()
  const projectStore = useProjectStore()
  const currentStep = ref(0)
  const submitting = ref(false)
  const stepError = ref<string | null>(null)

  // 跟「尚未選擇」的預設 null 區分開，選了才會跳過欄位對齊
  const NO_FRAMEWORK_ID = -1

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

  // 從框架庫「用於專案」帶 query 進來時，預選同一個框架（使用者仍可在步驟 2 改選）。
  // frameworks 通常在導覽進來前就載入了，但用 watch + immediate 一併涵蓋直接用網址進入、
  // 這個 view 比 loadFrameworks() 先掛載完成的情況。
  const requestedFrameworkId = (() => {
    const raw = route.query.frameworkId
    const parsed = Number(Array.isArray(raw) ? raw[0] : raw)
    return Number.isFinite(parsed) ? parsed : null
  })()

  watch(
    () => frameworkStore.frameworks,
    frameworks => {
      if (
        requestedFrameworkId !== null
        && form.value.frameworkId === null
        && frameworks.some(f => f.id === requestedFrameworkId)
      ) {
        form.value.frameworkId = requestedFrameworkId
      }
    },
    { immediate: true },
  )

  const selectedFramework = computed(() =>
    frameworkStore.frameworks.find(f => f.id === form.value.frameworkId) ?? null,
  )

  const frameworkReviewLabel = computed(() => {
    if (form.value.frameworkId === NO_FRAMEWORK_ID) return '不使用框架'
    return selectedFramework.value?.title || '（未選擇）'
  })

  function stepCircleClass (i: number): string {
    if (i < currentStep.value) return 'step-circle--done'
    if (i === currentStep.value) return 'step-circle--active'
    return 'step-circle--inactive'
  }

  // 只驗證「往前走」會需要的那一步，回頭看已經填過的步驟不擋
  function validateStep (i: number): string | null {
    if (i === 0 && !form.value.name.trim()) return '請輸入專案名稱'
    if (i === 1 && form.value.frameworkId === null) return '請選擇一個框架，或選擇不使用框架'
    if (i === 2 && !form.value.datasetFile) return '請上傳資料集檔案'
    return null
  }

  function goNext (): void {
    const error = validateStep(currentStep.value)
    if (error) {
      stepError.value = error
      return
    }
    stepError.value = null
    currentStep.value++
  }

  function goBack (): void {
    stepError.value = null
    currentStep.value--
  }

  // 使用者補上欄位後，錯誤提示要立刻消失，不用等他再按一次下一步
  watch(() => [form.value.name, form.value.frameworkId, form.value.datasetFile], () => {
    if (stepError.value && !validateStep(currentStep.value)) {
      stepError.value = null
    }
  })

  async function executeProject (): Promise<void> {
    submitting.value = true
    try {
      // sentinel 只在這個 view 內部有意義，存進資料庫/activeContext 一律還原成 null
      const noFramework = form.value.frameworkId === NO_FRAMEWORK_ID
      const frameworkId = noFramework ? null : form.value.frameworkId

      const project = await projectStore.addProject({
        name: form.value.name || '未命名專案',
        description: form.value.description,
        frameworkId,
        datasetName: form.value.datasetFile?.name ?? '',
        variables: selectedFramework.value?.variables ?? 0,
      })

      projectStore.setActiveContext({
        projectId: project.id,
        datasetFile: form.value.datasetFile,
        frameworkId,
      })

      // 先寫進 IndexedDB：activeContext 只活在記憶體裡，
      // 使用者在對齊頁按重新整理就會遺失。
      // useWorkflowStorage 的 projectId 參數是字串，而 Project.id 是數字。
      if (form.value.datasetFile) {
        await saveWorkflowDataFileToStorage(form.value.datasetFile, String(project.id))
      }

      // 沒有框架就沒有變數清單可對，欄位對齊頁會直接報錯，所以整段跳過
      // 用 replace 而不是 push：專案已經建立成功，瀏覽器上一頁不該讓使用者跳回建立表單
      router.replace(
        noFramework
          ? `/workflow?project=${project.id}`
          : `/hub/projects/${project.id}/mapping`,
      )
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

  .step-error {
    margin: 14px 0 0;
    font-size: 13px;
    color: var(--color-error-text);
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
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  /* 跟框架庫的 .fw-card 同一套 */
  .fw-select-card {
    position: relative;
    padding: 16px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: transform var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  .fw-select-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in oklab, var(--color-ink) 24%, var(--color-surface));
    box-shadow: var(--shadow-card);
  }

  /* 只換邊框顏色在一排卡片裡掃視時看不出選了哪張，
     改用底色、邊框、圖示底座、角落勾號四個訊號 */
  .fw-select-card--selected {
    border: 2px solid var(--color-ink);
    /* 邊框從 1px 變 2px，補回差的那 1px 才不會把旁邊的卡擠位 */
    padding: 15px;
    background: color-mix(in oklab, var(--color-ink) 7%, var(--color-surface));
    box-shadow: 0 4px 14px color-mix(in oklab, var(--color-ink) 18%, transparent);
  }

  .fw-select-card--selected:hover {
    border-color: var(--color-ink-strong);
  }

  .fw-select-card--selected .fw-select-icon {
    background: var(--color-ink);
    color: var(--color-surface);
  }

  .fw-select-check {
    position: absolute;
    top: -7px;
    right: -7px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 9999px;
    background: var(--color-ink);
    color: var(--color-surface);
  }

  .fw-select-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    margin-bottom: 10px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 10%, var(--color-surface));
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
