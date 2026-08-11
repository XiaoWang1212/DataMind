<template>
  <div>
    <!-- Back link -->
    <RouterLink class="back-link" to="/hub/library">
      <v-icon icon="mdi-arrow-left" size="15" />
      返回框架庫
    </RouterLink>

    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">從論文提取框架</h1>
      <p class="page-sub">上傳研究論文以自動提取方法論</p>
    </div>

    <!-- Content panels -->
    <div class="panels">
      <!-- Upload panel -->
      <div class="panel">
        <div class="panel-label">上傳論文</div>
        <div
          class="drop-zone"
          :class="{ 'drop-zone--over': isDragOver }"
          @click="fileInput?.click()"
          @dragleave="isDragOver = false"
          @dragover.prevent="isDragOver = true"
          @drop.prevent="handleDrop"
        >
          <v-icon class="drop-icon" icon="mdi-upload-outline" size="48" />
          <div class="drop-text">點擊上傳或拖放檔案</div>
          <div class="drop-hint">僅限 PDF 檔案（最大 10MB）</div>
          <input
            ref="fileInput"
            accept=".pdf"
            hidden
            type="file"
            @change="handleFileChange"
          >
        </div>
        <div v-if="selectedFile" class="file-info">
          <v-icon color="#ef4444" icon="mdi-file-pdf-box" size="18" />
          <span class="file-name">{{ selectedFile.name }}</span>
          <button class="file-remove" @click="selectedFile = null">
            <v-icon icon="mdi-close" size="15" />
          </button>
        </div>
        <button
          v-if="selectedFile && !extracting"
          class="extract-btn"
          @click="startExtract"
        >
          開始提取
        </button>
      </div>

      <!-- Result panel -->
      <div class="panel">
        <div class="panel-label">已提取框架</div>
        <div class="result-zone">
          <div v-if="extractError" class="result-error">{{ extractError }}</div>
          <div v-else-if="!extractedData" class="result-placeholder">
            提取完成後，框架詳細資料將顯示於此
          </div>
          <template v-else>
            <div class="result-field">
              <div class="result-field-label">框架名稱</div>
              <div class="result-field-value">{{ extractedData.name }}</div>
            </div>
            <div v-if="extractedData.targetCol" class="result-field">
              <div class="result-field-label">目標欄位</div>
              <div class="result-field-value">{{ extractedData.targetCol }}</div>
            </div>
            <div v-if="extractedData.models.length > 0" class="result-field">
              <div class="result-field-label">模型（{{ extractedData.models.length }} 個）</div>
              <div class="result-tag-list">
                <span v-for="m in extractedData.models" :key="m" class="result-tag">{{ m }}</span>
              </div>
            </div>
            <div v-if="extractedData.preprocessing.length > 0" class="result-field">
              <div class="result-field-label">前處理步驟（{{ extractedData.preprocessing.length }} 個）</div>
              <div class="result-tag-list">
                <span v-for="s in extractedData.preprocessing" :key="s" class="result-tag result-tag--gray">{{ s }}</span>
              </div>
            </div>
            <div v-if="extractedData.featureEngineering.length > 0" class="result-field">
              <div class="result-field-label">特徵工程（{{ extractedData.featureEngineering.length }} 個）</div>
              <div class="result-tag-list">
                <span v-for="s in extractedData.featureEngineering" :key="s" class="result-tag result-tag--gray">{{ s }}</span>
              </div>
            </div>
            <div v-if="extractedData.metrics.length > 0" class="result-field">
              <div class="result-field-label">評估指標</div>
              <div class="result-tag-list">
                <span v-for="m in extractedData.metrics" :key="m" class="result-tag result-tag--indigo">{{ m }}</span>
              </div>
            </div>
            <button class="save-btn" @click="saveFramework">儲存框架</button>
          </template>
        </div>
      </div>

      <!-- Thinking card (extraction in progress) — spans both columns -->
      <div v-if="extracting" class="thinking-card">
        <div class="thinking-header">
          <span class="thinking-dot" />
          AI 正在思考
        </div>
        <p v-if="previousLine" class="thinking-line thinking-line--prev">{{ previousLine }}</p>
        <Transition mode="out-in" name="thinking-swap">
          <p :key="currentLine" class="thinking-line thinking-line--current">{{ currentLine }}</p>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { streamAnalyzeWorkflowFromPdf } from '@/api/gemini'
  import { useFrameworkStore } from '@/store/frameworkStore'

  interface ExtractedFramework {
    name: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const router = useRouter()
  const store = useFrameworkStore()
  const fileInput = ref<HTMLInputElement | null>(null)
  const selectedFile = ref<File | null>(null)
  const isDragOver = ref(false)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const currentLine = ref('')
  const previousLine = ref('')

  function stripMarkdownAsterisks (text: string): string {
    return text.replace(/\*\*?/g, '')
  }

  function handleFileChange (e: Event): void {
    const input = e.target as HTMLInputElement
    if (input.files?.[0]) selectedFile.value = input.files[0]
  }

  function handleDrop (e: DragEvent): void {
    isDragOver.value = false
    const file = e.dataTransfer?.files[0]
    if (file && file.type === 'application/pdf') selectedFile.value = file
  }

  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    currentLine.value = ''
    previousLine.value = ''

    const file = selectedFile.value
    const baseName = file.name.replace(/\.[^.]+$/, '')

    try {
      await streamAnalyzeWorkflowFromPdf(
        { file, title: baseName },
        {
          onThought: text => {
            previousLine.value = currentLine.value
            currentLine.value = stripMarkdownAsterisks(text)
          },
          onResult: result => {
            const models = (Array.isArray(result.models) ? result.models : []).map((m: unknown) =>
              typeof m === 'string' ? m : String((m as Record<string, unknown>).name ?? ''),
            )
            const preprocessing = (Array.isArray(result.preprocessing) ? result.preprocessing : []).map(
              (s: unknown) => String((s as Record<string, unknown>).type ?? s),
            )
            const featureEngineering = (Array.isArray(result.featureEngineering) ? result.featureEngineering : []).map(
              (s: unknown) => String((s as Record<string, unknown>).type ?? s),
            )

            rawWorkflowJson.value = result
            extractedData.value = {
              name: baseName,
              models,
              preprocessing,
              featureEngineering,
              targetCol: String(result.target_col ?? result.targetCol ?? ''),
              metrics: Array.isArray(result.metrics) ? result.metrics.map(String) : [],
            }
          },
          onError: message => {
            extractError.value = message
          },
        },
      )
    } catch (error) {
      extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
    } finally {
      extracting.value = false
    }
  }

  async function saveFramework (): Promise<void> {
    if (!extractedData.value) return
    const d = extractedData.value
    await store.addFramework({
      title: d.name,
      subtitle: d.models.join('、') || '未命名方法',
      tag: d.models[0] ?? 'AI 提取',
      variables: d.preprocessing.length + d.featureEngineering.length,
      paperTitle: d.name,
      description: `目標欄位：${d.targetCol || '未知'}。評估指標：${d.metrics.join(', ') || '未知'}。`,
      independentVars: [...d.preprocessing, ...d.featureEngineering],
      dependentVars: d.targetCol ? [d.targetCol] : [],
      hypotheses: [],
      workflowJson: rawWorkflowJson.value ?? undefined,
    })
    extractedData.value = null
    rawWorkflowJson.value = null
    selectedFile.value = null
    router.push('/hub/library')
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

/* ── Panels ── */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.panel-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 12px;
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
  background: #ffffff;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover,
.drop-zone--over {
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

/* ── File info ── */
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
  flex: 1;
  font-size: 13px;
  color: var(--color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-secondary);
  display: flex;
  align-items: center;
  padding: 0;
}

.file-remove:hover {
  color: #ef4444;
}

.extract-btn {
  margin-top: 14px;
  width: 100%;
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

.extract-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.thinking-card {
  position: relative;
  grid-column: 1 / -1;
  margin-top: 6px;
  border-radius: 12px;
  padding: 16px 18px;
  background: color-mix(in oklab, var(--color-accent) 4%, var(--color-surface));
  overflow: hidden;
  min-height: 3.4em;
}

.thinking-card::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 1.5px;
  border-radius: 12px;
  background: linear-gradient(
    120deg,
    var(--color-accent),
    color-mix(in oklab, var(--color-accent) 55%, var(--color-ink)),
    var(--color-accent)
  );
  background-size: 300% 300%;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: thinking-gradient-move 3s ease infinite;
}

@keyframes thinking-gradient-move {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-accent);
  margin-bottom: 8px;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: thinking-pulse 1.2s ease-in-out infinite;
}

@keyframes thinking-pulse {
  0%, 100% { opacity: .3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.15); }
}

.thinking-line {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--color-secondary);
  white-space: pre-wrap;
}

.thinking-line--prev {
  font-size: 12.5px;
  color: color-mix(in oklab, var(--color-secondary) 55%, var(--color-surface));
  margin-bottom: 4px;
}

.thinking-swap-enter-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.thinking-swap-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

/* ── Result zone ── */
.result-zone {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  min-height: 200px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-placeholder {
  color: var(--color-secondary);
  font-size: 13.5px;
  margin: auto;
  text-align: center;
}

.result-error {
  color: #ef4444;
  font-size: 13px;
  font-weight: 500;
  padding: 10px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 7px;
}

.result-field-label {
  font-size: 12px;
  color: var(--color-secondary);
  margin-bottom: 6px;
}

.result-field-value {
  font-size: 14px;
  color: var(--color-ink);
  font-weight: 500;
}

/* ── Tags ── */
.result-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.result-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: #e0e7ff;
  color: #3730a3;
}

.result-tag--gray {
  background: #f3f4f6;
  color: #374151;
}

.result-tag--indigo {
  background: #ede9fe;
  color: #5b21b6;
}

.save-btn {
  margin-top: 4px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
