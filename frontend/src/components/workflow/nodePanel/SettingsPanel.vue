<template>
  <section class="settings-wizard">

    <!-- ── 步驟頁籤 ── -->
    <div class="wizard-tabs">
      <button
        v-for="(label, i) in STEPS"
        :key="i"
        class="wizard-tab"
        :class="{ 'wizard-tab--active': currentStep === i }"
        :style="{ '--tab-color': `var(--color-node-${STEP_CATEGORIES[i]})` }"
        type="button"
        @click="currentStep = i"
      >
        <span class="wizard-tab__num">{{ i + 1 }}</span>
        <span class="wizard-tab__text">{{ label }}</span>
        <span
          v-if="label === '模型' && props.models.length === 0"
          class="wizard-tab__required"
          title="必須新增至少一個模型"
        >必填</span>
      </button>
    </div>

    <!-- ── Step 0：前處理 ── -->
    <div v-if="currentStep === 0" class="step-body" :style="{ '--step-color': `var(--color-node-${STEP_CATEGORIES[0]})` }">
      <div class="add-bar">
        <CustomSelect
          v-model="newPreprocessType"
          class="type-select"
          :options="preprocessOptions.map(([value, label]) => ({ value, label }))"
          placeholder="選擇步驟類型"
        />
        <AppButton :disabled="!newPreprocessType" variant="secondary" @click="addPreprocessStep">
          新增
        </AppButton>
      </div>

      <div v-if="localPreprocessing.length > 0" class="item-list">
        <div v-for="(step, i) in localPreprocessing" :key="i" class="item-row">
          <div class="item-head">
            <span class="item-idx">{{ i + 1 }}</span>
            <span class="item-name">{{ preprocessStepLabel(step, datasetColumns) }}</span>
            <AppButton
              aria-label="移除"
              icon-only
              title="移除"
              variant="ghost"
              @click="removePreprocessStep(i)"
            >
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
          </div>
          <div
            v-if="step.type === 'fill_na' || step.type === 'knn_impute' || step.type === 'remove_outliers_iqr' || step.type === 'remove_outliers_zscore'"
            class="item-params"
          >
            <template v-if="step.type === 'fill_na'">
              <div v-if="fillNaColumnKind(step, datasetColumns) === 'nominal'" class="param-pair">
                <span class="param-key">strategy</span>
                <span class="param-fixed">眾數（類別型欄位固定使用）</span>
              </div>
              <div v-else class="param-pair">
                <span class="param-key">strategy</span>
                <CustomSelect
                  class="param-select"
                  :model-value="String(step.strategy ?? 'mean')"
                  :options="fillNaColumnKind(step, datasetColumns) === 'numeric'
                    ? [
                      { value: 'mean', label: '均值' },
                      { value: 'median', label: '中位數' },
                    ]
                    : [
                      { value: 'auto', label: '自動（數值用均值／類別用眾數）' },
                      { value: 'mean', label: '均值' },
                      { value: 'median', label: '中位數' },
                      { value: 'mode', label: '眾數' },
                    ]"
                  @update:model-value="patchPreprocessStep(i, 'strategy', $event)"
                />
              </div>
            </template>
            <template v-else-if="step.type === 'knn_impute'">
              <div class="param-pair">
                <span class="param-key">n_neighbors</span>
                <input
                  class="param-num"
                  min="1"
                  type="number"
                  :value="step.n_neighbors ?? 5"
                  @change="patchPreprocessStep(i, 'n_neighbors', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-else-if="step.type === 'remove_outliers_iqr' || step.type === 'remove_outliers_zscore'">
              <div class="param-pair">
                <span class="param-key">threshold</span>
                <input
                  class="param-num"
                  min="0"
                  step="0.1"
                  type="number"
                  :value="step.threshold ?? (step.type === 'remove_outliers_iqr' ? 1.5 : 3)"
                  @change="patchPreprocessStep(i, 'threshold', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
          </div>
        </div>
      </div>
      <p v-else class="empty-hint">尚未加入任何前處理步驟</p>
    </div>

    <!-- ── Step 1：特徵工程 ── -->
    <div v-else-if="currentStep === 1" class="step-body" :style="{ '--step-color': `var(--color-node-${STEP_CATEGORIES[1]})` }">
      <div class="add-bar">
        <CustomSelect
          v-model="newFEType"
          class="type-select"
          :options="featureOptions.map(([value, label]) => ({ value, label }))"
          placeholder="選擇步驟類型"
        />
        <AppButton :disabled="!newFEType" variant="secondary" @click="addFEStep">
          新增
        </AppButton>
      </div>

      <div v-if="localFE.length > 0" class="item-list">
        <div v-for="(step, i) in localFE" :key="i" class="item-row">
          <div class="item-head">
            <span class="item-idx">{{ i + 1 }}</span>
            <span class="item-name">{{ FEATURE_LABELS[step.type as string] ?? step.type }}</span>
            <AppButton
              aria-label="移除"
              icon-only
              title="移除"
              variant="ghost"
              @click="removeFEStep(i)"
            >
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
          </div>
          <div
            v-if="step.type === 'select_relevant_features' || step.type === 'pca'"
            class="item-params"
          >
            <template v-if="step.type === 'select_relevant_features'">
              <div class="param-pair">
                <span class="param-key">k</span>
                <input
                  class="param-num"
                  min="1"
                  type="number"
                  :value="step.k ?? 10"
                  @change="patchFEStep(i, 'k', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-else-if="step.type === 'pca'">
              <div class="param-pair">
                <span class="param-key">n_components</span>
                <input
                  class="param-num"
                  min="1"
                  placeholder="auto"
                  type="number"
                  :value="step.n_components ?? ''"
                  @change="patchFEStep(i, 'n_components', ($event.target as HTMLInputElement).value ? Number(($event.target as HTMLInputElement).value) : undefined)"
                >
              </div>
            </template>
          </div>
        </div>
      </div>
      <p v-else class="empty-hint">尚未加入任何特徵工程步驟</p>
    </div>

    <!-- ── Step 2：模型 ── -->
    <div v-else-if="currentStep === 2" class="step-body" :style="{ '--step-color': `var(--color-node-${STEP_CATEGORIES[2]})` }">
      <div class="add-bar">
        <CustomSelect
          v-model="selectedModel"
          class="type-select"
          :options="availableModels.map(m => ({ value: m, label: m }))"
          :placeholder="props.modelOptionsLoading ? '載入中…' : availableModels.length === 0 ? '已全部加入' : '選擇模型'"
          :disabled="props.modelOptionsLoading || availableModels.length === 0"
        />
        <AppButton :disabled="!selectedModel" variant="secondary" @click="addModel">
          新增
        </AppButton>
      </div>

      <div v-if="props.models.length > 0" class="item-list">
        <div v-for="model in props.models" :key="modelName(model)" class="item-row">
          <div class="item-head">
            <span class="item-idx item-idx--dot" />
            <span class="item-name">{{ modelName(model) }}</span>
            <AppButton
              aria-label="移除"
              icon-only
              title="移除"
              variant="ghost"
              @click="emit('remove-model', modelName(model))"
            >
              <v-icon icon="mdi-close" size="14" />
            </AppButton>
          </div>
        </div>
      </div>
      <p v-else class="empty-hint">尚未加入任何模型</p>
    </div>

    <!-- ── Step 3：驗證方式 ── -->
    <div v-else-if="currentStep === 3" class="step-body" :style="{ '--step-color': `var(--color-node-${STEP_CATEGORIES[3]})` }">
      <div class="validation-methods">
        <div
          v-for="method in VALIDATION_METHODS"
          :key="method.value"
          class="validation-method"
        >
          <label class="validation-method__radio">
            <input
              :checked="localValidation.method === method.value"
              name="validation-method"
              type="radio"
              @change="setValidationMethod(method.value)"
            >
            {{ method.label }}
          </label>

          <div v-if="localValidation.method === method.value" class="validation-method__params">
            <template v-if="method.value === 'k_fold' || method.value === 'group_k_fold'">
              <div class="param-pair">
                <span class="param-key">Number of folds</span>
                <input
                  class="param-num"
                  min="2"
                  type="number"
                  :value="Number(localValidation.n_splits ?? 10)"
                  @change="patchValidation('n_splits', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-if="method.value === 'k_fold'">
              <label class="param-checkbox">
                <input
                  :checked="Boolean(localValidation.stratified ?? true)"
                  type="checkbox"
                  @change="patchValidation('stratified', ($event.target as HTMLInputElement).checked)"
                >
                Stratified
              </label>
            </template>
            <template v-if="method.value === 'group_k_fold'">
              <div class="param-pair">
                <span class="param-key">Group column</span>
                <CustomSelect
                  class="param-select"
                  :disabled="datasetColumns.length === 0"
                  :model-value="String(localValidation.group_column ?? '')"
                  :options="datasetColumns.map(c => ({ value: c.name, label: c.name }))"
                  placeholder="選擇欄位"
                  @update:model-value="patchValidation('group_column', $event)"
                />
              </div>
            </template>
            <template v-if="method.value === 'random_sampling'">
              <div class="param-pair">
                <span class="param-key">Repeat train/test</span>
                <input
                  class="param-num"
                  min="1"
                  type="number"
                  :value="Number(localValidation.n_repeats ?? 10)"
                  @change="patchValidation('n_repeats', Number(($event.target as HTMLInputElement).value))"
                >
              </div>
            </template>
            <template v-if="method.value === 'random_sampling' || method.value === 'test_on_train' || method.value === 'test_on_test'">
              <div class="param-pair">
                <span class="param-key">Training set size (%)</span>
                <input
                  class="param-num"
                  max="99"
                  min="1"
                  type="number"
                  :value="Math.round(Number(localValidation.train_size ?? 0.8) * 100)"
                  @change="patchValidation('train_size', Number(($event.target as HTMLInputElement).value) / 100)"
                >
              </div>
              <label class="param-checkbox">
                <input
                  :checked="Boolean(localValidation.stratified ?? true)"
                  type="checkbox"
                  @change="patchValidation('stratified', ($event.target as HTMLInputElement).checked)"
                >
                Stratified
              </label>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Step 4：信賴區間 ── -->
    <div v-else class="step-body" :style="{ '--step-color': `var(--color-node-${STEP_CATEGORIES[4]})` }">
      <div class="ci-card">
        <div class="ci-card__header">
          <div class="ci-card__info">
            <span class="ci-card__title">Bootstrap 信賴區間</span>
            <span class="ci-card__sub">對每個評估指標計算 95% CI</span>
          </div>
          <button
            class="ci-toggle"
            :class="{ 'ci-toggle--on': props.computeCi }"
            type="button"
            @click="emit('update-compute-ci', !props.computeCi)"
          >
            <span class="ci-toggle__thumb" />
          </button>
        </div>
        <div class="ci-card__desc">
          <p>開啟後，系統將使用 Bootstrap 重抽樣對模型評估指標（如 AUC、F1 等）估算信賴區間。</p>
          <ul>
            <li>結果更具統計意義，適合論文報告</li>
            <li>計算時間顯著增加，建議模型確認後再開啟</li>
          </ul>
        </div>
        <div class="ci-card__status" :class="props.computeCi ? 'ci-card__status--on' : 'ci-card__status--off'">
          {{ props.computeCi ? '已啟用：執行時將計算 Bootstrap CI' : '已停用：不計算信賴區間' }}
        </div>
      </div>
    </div>

    <div class="settings-footer">
      <AppButton variant="secondary" @click="emit('back-node')">
        回 Data Table
      </AppButton>
      <div class="settings-footer__right">
        <AppButton
          v-if="currentStep > 0"
          variant="secondary"
          @click="currentStep -= 1"
        >
          上一步
        </AppButton>
        <AppButton
          :disabled="isPrimaryDisabled"
          variant="primary"
          @click="handlePrimary"
        >
          {{ primaryLabel }}
        </AppButton>
      </div>
    </div>

  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import { FEATURE_LABELS, PREPROCESS_LABELS, VALIDATION_LABELS } from '@/constants/workflowLabels'
  import { expandAutoFillNaSteps, fillNaColumnKind, preprocessStepLabel, splitAutoFillNaStep } from '@/utils/workflow/fillNaColumnSplit'

  type ModelEntry = string | { name?: string; [k: string]: unknown }

  const props = defineProps<{
    preprocessing: Array<Record<string, unknown>>
    featureEngineering: Array<Record<string, unknown>>
    models: Array<ModelEntry>
    computeCi: boolean
    availableModels: string[]
    usedModelNames: string[]
    modelOptionsLoading?: boolean
    validation: Record<string, unknown>
    datasetColumns: Array<{ name: string, type: string, role: string }>
  }>()

  const emit = defineEmits<{
    (e: 'add-model' | 'remove-model', name: string): void
    (e: 'update-preprocessing' | 'update-feature-engineering', steps: Array<Record<string, unknown>>): void
    (e: 'update-compute-ci', value: boolean): void
    (e: 'update-validation', value: Record<string, unknown>): void
    (e: 'continue'): void
    (e: 'back-node'): void
    (e: 'step-change', step: number): void
  }>()

  const STEPS = ['前處理', '特徵工程', '模型', '驗證方式', '信賴區間'] as const
  // 每個 step 對應的節點分類色（見 docs/DESIGN_SYSTEM.md §2.3），
  // 讓 wizard 頁籤跟畫布上真正的節點顏色一致
  const STEP_CATEGORIES = ['transform', 'transform', 'model', 'evaluate', 'evaluate'] as const
  const currentStep = ref(0)

  const LAST_STEP = STEPS.length - 1

  const primaryLabel = computed(() => (currentStep.value < LAST_STEP ? '下一步' : '執行'))
  const isPrimaryDisabled = computed(() => currentStep.value === LAST_STEP && props.models.length === 0)

  function handlePrimary (): void {
    if (currentStep.value < LAST_STEP) {
      currentStep.value += 1
    } else {
      emit('continue')
    }
  }

  watch(currentStep, step => emit('step-change', step), { immediate: true })

  const VALIDATION_METHODS = Object.entries(VALIDATION_LABELS)
    .map(([value, label]) => ({ value, label }))

  const preprocessOptions = computed(() => Object.entries(PREPROCESS_LABELS))
  const featureOptions = computed(() => Object.entries(FEATURE_LABELS))

  // 沒有指定 columns 的 fill_na 步驟（框架匯入的 strategy:"auto"，或使用者手動新增的）
  // 一律依 datasetColumns 的真實型別拆成「數值型補均值／類別型補眾數」兩筆；
  // 已經拆過的步驟因為已有 columns 不會再被動到，函式本身是冪等的。
  function syncPreprocessing (steps: Array<Record<string, unknown>>): void {
    const normalized = expandAutoFillNaSteps(steps, props.datasetColumns)
    localPreprocessing.value = normalized
    if (normalized.length !== steps.length) {
      emit('update-preprocessing', normalized)
    }
  }

  const localPreprocessing = ref<Array<Record<string, unknown>>>([])
  const localFE = ref<Array<Record<string, unknown>>>([...props.featureEngineering])
  const localValidation = ref<Record<string, unknown>>({ ...props.validation })

  watch(
    () => props.preprocessing,
    v => syncPreprocessing(v),
    { deep: true, immediate: true },
  )
  // datasetColumns 通常在進到這個 step 前就確定了，但保留這個 watch
  // 是為了涵蓋「進來時欄位型別還沒就緒」的邊界情況
  watch(
    () => props.datasetColumns,
    () => syncPreprocessing(localPreprocessing.value),
  )
  watch(
    () => props.featureEngineering,
    v => {
      localFE.value = [...v]
    },
    { deep: true },
  )
  watch(
    () => props.validation,
    v => {
      localValidation.value = { ...v }
    },
    { deep: true },
  )

  const newPreprocessType = ref('')
  const newFEType = ref('')
  const selectedModel = ref('')

  const availableModels = computed(() =>
    props.availableModels.filter(m => !props.usedModelNames.includes(m)),
  )

  watch(availableModels, list => {
    if (list.length > 0 && !list.includes(selectedModel.value)) {
      selectedModel.value = list[0] ?? ''
    }
  }, { immediate: true })

  function modelName (m: ModelEntry): string {
    return typeof m === 'string' ? m : String(m.name ?? '')
  }

  // ── 前處理 ──
  function addPreprocessStep (): void {
    if (!newPreprocessType.value) return

    if (newPreprocessType.value === 'fill_na') {
      const split = splitAutoFillNaStep({ type: 'fill_na' }, props.datasetColumns)
      localPreprocessing.value = [...localPreprocessing.value, ...(split ?? [{ type: 'fill_na', strategy: 'mean' }])]
      emit('update-preprocessing', localPreprocessing.value)
      newPreprocessType.value = ''
      return
    }

    const step: Record<string, unknown> = { type: newPreprocessType.value }
    switch (newPreprocessType.value) {
      case 'knn_impute': {
        step.n_neighbors = 5
        break
      }
      case 'remove_outliers_iqr': {
        step.threshold = 1.5
        break
      }
      case 'remove_outliers_zscore': {
        step.threshold = 3
        break
      }
      default: {
        break
      }
    }
    localPreprocessing.value = [...localPreprocessing.value, step]
    emit('update-preprocessing', localPreprocessing.value)
    newPreprocessType.value = ''
  }

  function removePreprocessStep (i: number): void {
    localPreprocessing.value = localPreprocessing.value.filter((_, idx) => idx !== i)
    emit('update-preprocessing', localPreprocessing.value)
  }

  function patchPreprocessStep (i: number, key: string, value: unknown): void {
    localPreprocessing.value = localPreprocessing.value.map((s, idx) =>
      idx === i ? { ...s, [key]: value } : s,
    )
    emit('update-preprocessing', localPreprocessing.value)
  }

  // ── 特徵工程 ──
  function addFEStep (): void {
    if (!newFEType.value) return
    const step: Record<string, unknown> = { type: newFEType.value }
    if (newFEType.value === 'select_relevant_features') step.k = 10
    localFE.value = [...localFE.value, step]
    emit('update-feature-engineering', localFE.value)
    newFEType.value = ''
  }

  function removeFEStep (i: number): void {
    localFE.value = localFE.value.filter((_, idx) => idx !== i)
    emit('update-feature-engineering', localFE.value)
  }

  function patchFEStep (i: number, key: string, value: unknown): void {
    localFE.value = localFE.value.map((s, idx) =>
      idx === i ? { ...s, [key]: value } : s,
    )
    emit('update-feature-engineering', localFE.value)
  }

  // ── 模型 ──
  function addModel (): void {
    if (!selectedModel.value) return
    emit('add-model', selectedModel.value)
    selectedModel.value = ''
  }

  // ── 驗證方式 ──
  function patchValidation (key: string, value: unknown): void {
    localValidation.value = { ...localValidation.value, [key]: value }
    emit('update-validation', localValidation.value)
  }

  function setValidationMethod (method: string): void {
    localValidation.value = { ...localValidation.value, method }
    emit('update-validation', localValidation.value)
  }
</script>

<style scoped>
  .settings-wizard {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* 步驟頁籤 */
  .wizard-tabs {
    flex-shrink: 0;
    display: flex;
    gap: 4px;
    padding: 4px;
    background: color-mix(in oklab, var(--color-ink) 5%, transparent);
    border-radius: var(--radius-md);
  }

  .wizard-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 4px;
    border: none;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--color-ink-soft);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background var(--dur-fast), color var(--dur-fast), box-shadow var(--dur-fast);
  }

  /* 淺色靠白底 + 分類色的字與投影就分得出來，維持原樣 */
  .wizard-tab--active {
    background: var(--color-surface);
    color: var(--tab-color, var(--color-ink));
    font-weight: 500;
    box-shadow: 0 1px 5px color-mix(in oklab, var(--tab-color, var(--color-ink)) 20%, transparent);
  }

  /* 深色的軌道跟 surface 只差一階，光靠底色讀不出作用中是哪一格：
     底色再抬一階、補一圈分類色內描邊、字加粗，三件事一起才夠。
     這三項都不套到淺色——淺色的 surface-alt 跟軌道算出來幾乎同色，反而把層次抹掉 */
  .v-theme--dark .wizard-tab--active {
    background: var(--color-surface-alt);
    font-weight: 700;
    box-shadow:
      inset 0 0 0 1px color-mix(in oklab, var(--tab-color, var(--color-ink)) 55%, transparent),
      0 1px 5px color-mix(in oklab, var(--tab-color, var(--color-ink)) 20%, transparent);
  }

  .wizard-tab__num {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 500;
    flex-shrink: 0;
    background: color-mix(in oklab, var(--color-ink-soft) 14%, transparent);
    color: var(--color-ink-soft);
    transition: background var(--dur-fast), color var(--dur-fast);
  }

  .wizard-tab--active .wizard-tab__num {
    background: var(--tab-color, var(--color-ink));
    color: var(--color-inverted);
  }

  /* 深色比照 IconNode（§2.3）把構造翻面成深底 + 亮號碼。
     淺色沿用原本的白字疊粉彩（1.9:1，已知不足，見附錄） */
  .v-theme--dark .wizard-tab--active .wizard-tab__num {
    background: color-mix(in oklab, var(--tab-color, var(--color-ink)) 24%, var(--color-surface));
    color: color-mix(in oklab, var(--tab-color, var(--color-ink)) 82%, #fff);
    font-weight: 700;
  }

  .wizard-tab__text {
    white-space: nowrap;
  }

  .wizard-tab__required {
    font-size: 9px;
    font-weight: 500;
    color: var(--color-error-text);
    white-space: nowrap;
  }

  /* Step 內容 */
  .step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .add-bar {
    display: flex;
    gap: 6px;
  }

  /* 只保留 add-bar 的 flex 佈局，外觀交給 CustomSelect 自己畫 */
  .type-select {
    flex: 1;
    min-width: 0;
  }

  .item-list {
    display: grid;
    /* 240px 才放得下「缺值填補（數值型）」這種較長的步驟名稱 */
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .item-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px;
    background: color-mix(in oklab, var(--step-color, var(--color-ink)) 10%, transparent);
    border: 1px solid color-mix(in oklab, var(--step-color, var(--color-ink)) 22%, transparent);
    border-radius: var(--radius-md);
    font-size: 13px;
  }

  .item-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .item-idx {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: color-mix(in oklab, var(--step-color, var(--color-ink)) 30%, transparent);
    color: color-mix(in oklab, var(--step-color, var(--color-ink)) 65%, var(--color-ink-strong));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .item-idx--dot {
    background: var(--step-color, var(--color-ink));
  }

  .item-name {
    flex: 1;
    font-weight: 500;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-text);
    min-width: 0;
  }

  .item-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px solid color-mix(in oklab, var(--step-color, var(--color-ink)) 24%, transparent);
  }

  .item-params .param-select {
    flex: 1;
    min-width: 0;
  }

  .param-pair {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: var(--color-ink-soft);
    white-space: nowrap;
  }

  .param-fixed {
    font-size: 13px;
    font-weight: 500;
    line-height: 1.35;
    color: var(--color-text);
    /* key 是 nowrap，值不給收縮空間的話會把整排撐出卡片 */
    min-width: 0;
  }

  .param-num {
    width: 68px;
    height: 30px;
    border: 1px solid color-mix(in oklab, var(--step-color, var(--color-ink)) 24%, transparent);
    border-radius: var(--radius-sm);
    padding: 0 8px;
    font-size: 13px;
    text-align: center;
    outline: none;
    background: var(--color-surface);
    color: var(--color-text);
  }

  .validation-methods {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .validation-method {
    padding: 8px 10px;
    border-radius: var(--radius-sm);
    transition: background var(--dur-fast);
  }

  @media (hover: hover) and (pointer: fine) {
    .validation-method:hover {
      background: color-mix(in oklab, var(--color-ink) 8%, transparent);
    }
  }

  .validation-method__radio {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    /* 不能用 ink：它在深色主題翻成淺藍，內文會變成藍字 */
    color: var(--color-text);
    cursor: pointer;
  }

  .validation-method__radio input[type="radio"] {
    appearance: none;
    width: 15px;
    height: 15px;
    margin: 0;
    flex-shrink: 0;
    border-radius: 50%;
    border: 1.5px solid var(--color-border-strong);
    position: relative;
    cursor: pointer;
    transition: border-color var(--dur-fast);
  }

  .validation-method__radio input[type="radio"]:checked {
    border-color: var(--step-color, var(--color-ink));
  }

  .validation-method__radio input[type="radio"]:checked::after {
    content: "";
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: var(--step-color, var(--color-ink));
  }

  .validation-method__params {
    margin: 8px 0 4px 33px;
    padding-left: 16px;
    border-left: 1.5px solid color-mix(in oklab, var(--step-color, var(--color-ink)) 35%, transparent);
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .param-checkbox {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    color: var(--color-ink-soft);
    cursor: pointer;
  }

  .del-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: none;
    background: none;
    color: var(--color-ink-soft);
    cursor: pointer;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.12s, background 0.12s;
  }

  .del-btn:hover {
    color: var(--color-error);
    background: color-mix(in oklab, var(--color-error) 10%, transparent);
  }

  .empty-hint {
    margin: 0;
    font-size: 12px;
    color: var(--color-ink-soft);
    padding: 6px 0;
  }

  /* compute_ci 卡片 */
  .ci-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: color-mix(in oklab, var(--step-color, var(--color-ink)) 10%, transparent);
    border: 1px solid color-mix(in oklab, var(--step-color, var(--color-ink)) 22%, transparent);
    border-radius: var(--radius-md);
  }

  .ci-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .ci-card__info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .ci-card__title {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-text);
  }

  .ci-card__sub {
    font-size: 11px;
    color: var(--color-ink-soft);
  }

  .ci-card__desc {
    font-size: 12px;
    color: var(--color-ink-soft);
    line-height: 1.55;
  }

  .ci-card__desc p {
    margin: 0 0 6px;
  }

  .ci-card__desc ul {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .ci-card__status {
    font-size: 11px;
    font-weight: 500;
    padding: 5px 10px;
    border-radius: var(--radius-sm);
    text-align: center;
  }

  .ci-card__status--on {
    background: color-mix(in oklab, var(--step-color, var(--color-ink)) 22%, transparent);
    color: color-mix(in oklab, var(--step-color, var(--color-ink)) 65%, var(--color-ink-strong));
  }

  .ci-card__status--off {
    background: color-mix(in oklab, var(--color-ink-soft) 10%, transparent);
    color: var(--color-ink-soft);
  }

  .ci-toggle {
    flex-shrink: 0;
    width: 36px;
    height: 20px;
    border-radius: 999px;
    border: none;
    background: var(--color-border);
    cursor: pointer;
    padding: 2px;
    transition: background var(--dur-base);
    position: relative;
  }

  .ci-toggle--on {
    background: var(--step-color, var(--color-ink));
  }

  .ci-toggle__thumb {
    display: block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--color-surface);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: transform var(--dur-base);
    transform: translateX(0);
  }

  .ci-toggle--on .ci-toggle__thumb {
    transform: translateX(16px);
  }

  .settings-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-top: 12px;
    border-top: 1px solid color-mix(in oklab, var(--color-ink) 10%, transparent);
  }

  .settings-footer__right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

</style>
