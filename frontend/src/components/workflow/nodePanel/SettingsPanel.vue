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
        <select v-model="newPreprocessType" class="type-select">
          <option disabled value="">選擇步驟類型</option>
          <option v-for="[k, v] in preprocessOptions" :key="k" :value="k">{{ v }}</option>
        </select>
        <button class="add-btn" :disabled="!newPreprocessType" type="button" @click="addPreprocessStep">
          新增
        </button>
      </div>

      <div v-if="localPreprocessing.length > 0" class="item-list">
        <div v-for="(step, i) in localPreprocessing" :key="i" class="item-row">
          <span class="item-idx">{{ i + 1 }}</span>
          <span class="item-name">{{ PREPROCESS_LABELS[step.type as string] ?? step.type }}</span>
          <div class="item-params">
            <template v-if="step.type === 'fill_na'">
              <select
                class="param-select"
                :value="step.strategy ?? 'mean'"
                @change="patchPreprocessStep(i, 'strategy', ($event.target as HTMLSelectElement).value)"
              >
                <option value="mean">均值</option>
                <option value="median">中位數</option>
                <option value="mode">眾數</option>
              </select>
            </template>
            <template v-else-if="step.type === 'knn_impute'">
              <div class="param-pair">
                <span class="param-key">鄰居數</span>
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
                <span class="param-key">閾值</span>
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
          <button class="del-btn" title="移除" type="button" @click="removePreprocessStep(i)">✕</button>
        </div>
      </div>
      <p v-else class="empty-hint">尚未加入任何前處理步驟</p>
    </div>

    <!-- ── Step 1：特徵工程 ── -->
    <div v-else-if="currentStep === 1" class="step-body">
      <div class="add-bar">
        <select v-model="newFEType" class="type-select">
          <option disabled value="">選擇步驟類型</option>
          <option v-for="[k, v] in featureOptions" :key="k" :value="k">{{ v }}</option>
        </select>
        <button class="add-btn" :disabled="!newFEType" type="button" @click="addFEStep">
          新增
        </button>
      </div>

      <div v-if="localFE.length > 0" class="item-list">
        <div v-for="(step, i) in localFE" :key="i" class="item-row">
          <span class="item-idx">{{ i + 1 }}</span>
          <span class="item-name">{{ FEATURE_LABELS[step.type as string] ?? step.type }}</span>
          <div class="item-params">
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
                <span class="param-key">維度</span>
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
          <button class="del-btn" title="移除" type="button" @click="removeFEStep(i)">✕</button>
        </div>
      </div>
      <p v-else class="empty-hint">尚未加入任何特徵工程步驟</p>
    </div>

    <!-- ── Step 2：模型 ── -->
    <div v-else-if="currentStep === 2" class="step-body">
      <div class="add-bar">
        <select
          v-model="selectedModel"
          class="type-select"
          :disabled="props.modelOptionsLoading || availableModels.length === 0"
        >
          <option disabled value="">
            {{ props.modelOptionsLoading ? '載入中…' : availableModels.length === 0 ? '已全部加入' : '選擇模型' }}
          </option>
          <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
        </select>
        <button class="add-btn" :disabled="!selectedModel" type="button" @click="addModel">
          新增
        </button>
      </div>

      <div v-if="props.models.length > 0" class="item-list">
        <div v-for="model in props.models" :key="modelName(model)" class="item-row">
          <span class="item-idx item-idx--dot" />
          <span class="item-name">{{ modelName(model) }}</span>
          <div class="item-params" />
          <button class="del-btn" title="移除" type="button" @click="emit('remove-model', modelName(model))">✕</button>
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
      <button
        class="btn-continue"
        :class="{ 'btn-continue--disabled': props.models.length === 0 }"
        :disabled="props.models.length === 0"
        type="button"
        @click="emit('continue')"
      >
        繼續
      </button>
    </div>

  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue'

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
    (e: 'step-change', step: number): void
  }>()

  const STEPS = ['前處理', '特徵工程', '模型', '信賴區間'] as const
  const currentStep = ref(0)

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
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* 步驟頁籤 */
  .wizard-tabs {
    display: flex;
    gap: 4px;
    padding: 4px;
    background: rgba(0, 93, 255, 0.05);
    border-radius: 12px;
  }

  .wizard-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 4px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  }

  .wizard-tab--active {
    background: #fff;
    color: #005dff;
    font-weight: 700;
    box-shadow: 0 1px 5px rgba(0, 93, 255, 0.14);
  }

  .wizard-tab__num {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    background: rgba(100, 116, 139, 0.12);
    color: #64748b;
    transition: background 0.15s, color 0.15s;
  }

  .wizard-tab--active .wizard-tab__num {
    background: #005dff;
    color: #fff;
  }

  .wizard-tab__text {
    white-space: nowrap;
  }

  .wizard-tab__required {
    font-size: 9px;
    font-weight: 700;
    color: #ef4444;
    background: rgba(239, 68, 68, 0.12);
    border-radius: 6px;
    padding: 1px 4px;
    white-space: nowrap;
  }

  /* Step 內容 */
  .step-body {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .add-bar {
    display: flex;
    gap: 6px;
  }

  .type-select {
    flex: 1;
    height: 32px;
    border: 1px solid rgba(0, 93, 255, 0.18);
    border-radius: 8px;
    padding: 0 28px 0 8px;
    font-size: 12px;
    background-color: rgba(255, 255, 255, 0.9);
    color: #0f172a;
    outline: none;
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24'%3E%3Cpath fill='%23005DFF' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 6px center;
  }

  .type-select:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .add-btn {
    height: 32px;
    padding: 0 14px;
    border: none;
    border-radius: 8px;
    background: #005dff;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
    transition: opacity 0.12s;
  }

  .add-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .add-btn:not(:disabled):hover {
    opacity: 0.82;
  }

  .item-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .item-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.1);
    border-radius: 8px;
    font-size: 12px;
  }

  .item-idx {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(0, 93, 255, 0.12);
    color: #005dff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .item-idx--dot {
    background: rgba(0, 93, 255, 0.2);
  }

  .item-name {
    flex: 1;
    font-weight: 500;
    color: #1e293b;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .item-params {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .param-select {
    height: 26px;
    border: 1px solid rgba(0, 93, 255, 0.15);
    border-radius: 6px;
    padding: 0 6px;
    font-size: 11px;
    background: rgba(255, 255, 255, 0.9);
    color: #0f172a;
    outline: none;
  }

  .param-pair {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .param-key {
    font-size: 10px;
    color: #64748b;
    white-space: nowrap;
  }

  .param-num {
    width: 54px;
    height: 26px;
    border: 1px solid rgba(0, 93, 255, 0.15);
    border-radius: 6px;
    padding: 0 6px;
    font-size: 11px;
    text-align: center;
    outline: none;
    background: rgba(255, 255, 255, 0.9);
    color: #0f172a;
  }

  .del-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: none;
    background: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.12s, background 0.12s;
  }

  .del-btn:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
  }

  .empty-hint {
    margin: 0;
    font-size: 12px;
    color: #94a3b8;
    padding: 6px 0;
  }

  /* compute_ci 卡片 */
  .ci-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.12);
    border-radius: 10px;
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
    font-weight: 700;
    color: #1e293b;
  }

  .ci-card__sub {
    font-size: 11px;
    color: #64748b;
  }

  .ci-card__desc {
    font-size: 12px;
    color: #475569;
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
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 6px;
    text-align: center;
  }

  .ci-card__status--on {
    background: rgba(0, 93, 255, 0.1);
    color: #005dff;
  }

  .ci-card__status--off {
    background: rgba(100, 116, 139, 0.1);
    color: #64748b;
  }

  .ci-toggle {
    flex-shrink: 0;
    width: 36px;
    height: 20px;
    border-radius: 999px;
    border: none;
    background: #e2e8f0;
    cursor: pointer;
    padding: 2px;
    transition: background 0.2s;
    position: relative;
  }

  .ci-toggle--on {
    background: #005dff;
  }

  .ci-toggle__thumb {
    display: block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s;
    transform: translateX(0);
  }

  .ci-toggle--on .ci-toggle__thumb {
    transform: translateX(16px);
  }

  .settings-footer {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 10px;
    padding-top: 4px;
  }

  .btn-continue {
    min-width: 88px;
    padding: 10px 14px;
    border: none;
    border-radius: 10px;
    background: #2563eb;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-continue--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }
</style>
