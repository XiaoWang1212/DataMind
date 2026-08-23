<template>
  <div>
    <PageHeader subtitle="上傳研究論文以自動提取方法論" title="從論文提取框架">
      <template #back>
        <RouterLink class="back-link" to="/hub/library">
          <v-icon icon="mdi-arrow-left" size="15" />
          返回框架庫
        </RouterLink>
      </template>
    </PageHeader>

    <!-- Content panels -->
    <div class="panels">
      <!-- Upload panel -->
      <div class="panel">
        <div class="panel-label">上傳論文</div>
        <FileDropZone
          accept=".pdf"
          accept-label="PDF"
          file-icon="mdi-file-pdf-box"
          hint="僅限 PDF 檔案（最大 10MB）"
          icon="mdi-upload-outline"
          :model-value="selectedFile"
          text="點擊上傳或拖放檔案"
          @update:model-value="onFileChange"
        />
        <AppButton
          v-if="selectedFile && !extracting"
          class="extract-btn"
          :variant="extractedData ? 'secondary' : 'primary'"
          @click="startExtract"
        >
          {{ extractedData ? '重新提取' : '開始提取' }}
        </AppButton>
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
            <div v-if="extractedData.processNarrative" class="result-field">
              <div class="result-field-label">研究流程</div>
              <p class="result-field-narrative">{{ extractedData.processNarrative }}</p>
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
            <AppButton class="save-btn" variant="primary" @click="saveFramework">儲存框架</AppButton>
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
  import FileDropZone from '@/components/common/FileDropZone.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import { useFrameworkStore } from '@/store/frameworkStore'

  interface ExtractedFramework {
    name: string
    processNarrative: string
    models: string[]
    preprocessing: string[]
    featureEngineering: string[]
    targetCol: string
    metrics: string[]
  }

  const router = useRouter()
  const store = useFrameworkStore()
  const selectedFile = ref<File | null>(null)
  const extracting = ref(false)
  const extractError = ref<string | null>(null)
  const extractedData = ref<ExtractedFramework | null>(null)
  const rawWorkflowJson = ref<Record<string, unknown> | null>(null)
  const currentLine = ref('')
  const previousLine = ref('')
  let abortController: AbortController | null = null

  function stripMarkdownAsterisks (text: string): string {
    return text.replace(/\*\*?/g, '')
  }

  function onFileChange (file: File | null): void {
    // 移除檔案時要一併中止進行中的提取，維持原本 removeFile 的行為
    if (!file && extracting.value) abortController?.abort()
    selectedFile.value = file
  }

  async function startExtract (): Promise<void> {
    if (!selectedFile.value) return
    extracting.value = true
    extractedData.value = null
    extractError.value = null
    currentLine.value = ''
    previousLine.value = ''
    abortController = new AbortController()

    const file = selectedFile.value
    const baseName = file.name.replace(/\.[^.]+$/, '')

    try {
      await streamAnalyzeWorkflowFromPdf(
        { file, title: baseName, signal: abortController.signal },
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
              processNarrative: String(result.process_narrative ?? ''),
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
      if (error instanceof DOMException && error.name === 'AbortError') {
        // User cancelled by removing the file — not a failure, no message to show.
      } else {
        extractError.value = error instanceof Error ? error.message : 'AI 分析失敗，請確認 PDF 是否正確'
      }
    } finally {
      extracting.value = false
      abortController = null
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
      description: d.processNarrative || `目標欄位：${d.targetCol || '未知'}。評估指標：${d.metrics.join(', ') || '未知'}。`,
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
/* 標題左側的返回鈕。PageHeader 的 lead 是 flex-start 對齊，補 margin 讓它與 22px 標題視覺齊平 */
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-ink-soft);
  text-decoration: none;
  white-space: nowrap;
  transition: color var(--dur-fast) var(--ease-out);
}

.back-link:hover {
  color: var(--color-text);
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
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 12px;
}

.extract-btn {
  margin-top: 14px;
  width: 100%;
  height: 40px;
}

.thinking-card {
  position: relative;
  grid-column: 1 / -1;
  margin-top: 6px;
  border-radius: var(--radius-md);
  padding: 16px 18px;
  background: color-mix(in oklab, var(--color-ink) 4%, var(--color-surface));
  overflow: hidden;
  min-height: 3.4em;
}

/* 兩端淡、中段濃的藍色漸層，掃動時濃淡差夠大才看得出在動，
   原本用近黑色調兩端太接近，動畫等於沒動 */
.thinking-card::before {
  content: '';
  position: absolute;
  inset: 0;
  padding: 2px;
  border-radius: var(--radius-md);
  background: linear-gradient(
    120deg,
    color-mix(in oklab, var(--color-ink-vivid) 20%, transparent),
    color-mix(in oklab, var(--color-ink-vivid) 75%, transparent),
    color-mix(in oklab, var(--color-ink-vivid) 20%, transparent)
  );
  background-size: 300% 300%;
  -webkit-mask: linear-gradient(white 0 0) content-box, linear-gradient(white 0 0);
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
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ink);
  margin-bottom: 8px;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-ink);
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
  color: var(--color-ink-soft);
  white-space: pre-wrap;
}

.thinking-line--prev {
  font-size: 12px;
  color: color-mix(in oklab, var(--color-ink-soft) 55%, var(--color-surface));
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
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  min-height: 200px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-placeholder {
  color: var(--color-ink-soft);
  font-size: 13px;
  margin: auto;
  text-align: center;
}

/* 邊框從 error 調出來而不是直接用 -bg，否則會跟自己的底色同色而看不見 */
.result-error {
  color: var(--color-error-text);
  font-size: 13px;
  font-weight: 500;
  padding: 10px 12px;
  background: var(--color-error-bg);
  border: 1px solid color-mix(in oklab, var(--color-error) 25%, transparent);
  border-radius: var(--radius-sm);
}

.result-field-label {
  font-size: 12px;
  color: var(--color-ink-soft);
  margin-bottom: 6px;
}

.result-field-value {
  font-size: 14px;
  color: var(--color-text);
  font-weight: 500;
}

.result-field-narrative {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-text);
  white-space: pre-wrap;
}

/* ── Tags ── */
.result-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* 三種標籤原本是三個色系，改成同一支藏青的三個深淺 — 這些分類沒有狀態語意，不該各佔一個顏色 */
.result-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: color-mix(in oklab, var(--color-ink) 10%, white);
  color: var(--color-ink-strong);
}

.result-tag--gray {
  background: var(--color-surface-alt);
  color: var(--color-text);
}

.result-tag--indigo {
  background: color-mix(in oklab, var(--color-ink) 16%, white);
  color: var(--color-ink-strong);
}

.save-btn {
  margin-top: 4px;
  height: 40px;
}
</style>
