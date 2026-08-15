<template>
  <section class="settings-wizard">

    <!-- ── 步驟頁籤 ── -->
    <div class="wizard-tabs">
      <button
        v-for="(label, i) in STEPS"
        :key="i"
        class="wizard-tab"
        :class="{ 'wizard-tab--active': currentStep === i }"
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
    <div v-if="currentStep === 0" class="step-body">
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
            <span class="item-name">{{ PREPROCESS_LABELS[step.type as string] ?? step.type }}</span>
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
              <div class="param-pair">
                <span class="param-key">strategy</span>
                <CustomSelect
                  class="param-select"
                  :model-value="String(step.strategy ?? 'mean')"
                  :options="[
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
    <div v-else-if="currentStep === 1" class="step-body">
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
    <div v-else-if="currentStep === 2" class="step-body">
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

    <!-- ── Step 3：信賴區間 ── -->
    <div v-else class="step-body">
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

  type ModelEntry = string | { name?: string; [k: string]: unknown }

  const props = defineProps<{
    preprocessing: Array<Record<string, unknown>>
    featureEngineering: Array<Record<string, unknown>>
    models: Array<ModelEntry>
    computeCi: boolean
    availableModels: string[]
    usedModelNames: string[]
    modelOptionsLoading?: boolean
  }>()

  const emit = defineEmits<{
    (e: 'add-model' | 'remove-model', name: string): void
    (e: 'update-preprocessing' | 'update-feature-engineering', steps: Array<Record<string, unknown>>): void
    (e: 'update-compute-ci', value: boolean): void
    (e: 'continue'): void
    (e: 'back-node'): void
    (e: 'step-change', step: number): void
  }>()

  const STEPS = ['前處理', '特徵工程', '模型', '信賴區間'] as const
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

  const PREPROCESS_LABELS: Record<string, string> = {
    fill_na: '缺值填補',
    knn_impute: 'KNN 缺值填補',
    iterative_impute: 'MICE 多重插補',
    normalize: 'Min-Max 正規化',
    standardize: 'Z-score 標準化',
    one_hot: 'One-Hot 編碼',
    label_encode: 'Label 編碼',
    drop_columns: '移除欄位',
    remove_outliers_iqr: 'IQR 異常值處理',
    remove_outliers_zscore: 'Z-score 異常值處理',
  }

  const FEATURE_LABELS: Record<string, string> = {
    select_relevant_features: '特徵選擇',
    pca: 'PCA 降維',
    discretize_continuous: '連續→離散',
    continuize_discrete: '離散→連續',
    normalize_features: '特徵正規化',
    remove_sparse_features: '移除稀疏特徵',
  }

  const preprocessOptions = computed(() => Object.entries(PREPROCESS_LABELS))
  const featureOptions = computed(() => Object.entries(FEATURE_LABELS))

  const localPreprocessing = ref<Array<Record<string, unknown>>>([...props.preprocessing])
  const localFE = ref<Array<Record<string, unknown>>>([...props.featureEngineering])

  watch(
    () => props.preprocessing,
    v => {
      localPreprocessing.value = [...v]
    },
    { deep: true },
  )
  watch(
    () => props.featureEngineering,
    v => {
      localFE.value = [...v]
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
    const step: Record<string, unknown> = { type: newPreprocessType.value }
    switch (newPreprocessType.value) {
      case 'fill_na': {
        step.strategy = 'mean'
        break
      }
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
    background: color-mix(in oklab, var(--color-accent) 5%, transparent);
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
    color: var(--color-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background var(--dur-fast), color var(--dur-fast), box-shadow var(--dur-fast);
  }

  .wizard-tab--active {
    background: var(--color-surface);
    color: var(--color-accent);
    font-weight: 500;
    box-shadow: 0 1px 5px color-mix(in oklab, var(--color-accent) 14%, transparent);
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
    background: rgba(100, 116, 139, 0.12);
    color: var(--color-secondary);
    transition: background var(--dur-fast), color var(--dur-fast);
  }

  .wizard-tab--active .wizard-tab__num {
    background: var(--color-accent);
    color: #fff;
  }

  .wizard-tab__text {
    white-space: nowrap;
  }

  .wizard-tab__required {
    font-size: 9px;
    font-weight: 500;
    color: var(--color-error-text);
    background: rgba(239, 68, 68, 0.12);
    border-radius: var(--radius-sm);
    padding: 1px 4px;
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
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
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
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    border-radius: var(--radius-sm);
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
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    color: var(--color-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .item-idx--dot {
    background: color-mix(in oklab, var(--color-accent) 20%, transparent);
  }

  .item-name {
    flex: 1;
    font-weight: 500;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-text);
    min-width: 0;
    word-break: break-word;
  }

  .item-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed color-mix(in oklab, var(--color-accent) 14%, transparent);
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
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .param-num {
    width: 68px;
    height: 30px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 15%, transparent);
    border-radius: var(--radius-sm);
    padding: 0 8px;
    font-size: 13px;
    text-align: center;
    outline: none;
    background: rgba(255, 255, 255, 0.9);
    color: var(--color-text);
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
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
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
    color: var(--color-secondary);
  }

  .ci-card__desc {
    font-size: 12px;
    color: var(--color-secondary);
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
    background: color-mix(in oklab, var(--color-accent) 10%, transparent);
    color: var(--color-accent);
  }

  .ci-card__status--off {
    background: rgba(100, 116, 139, 0.1);
    color: var(--color-secondary);
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
    background: var(--color-accent);
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
    border-top: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
  }

  .settings-footer__right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

</style>
