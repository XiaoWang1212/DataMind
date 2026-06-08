<template>
  <div>
    <!-- Back link -->
    <RouterLink to="/hub/library" class="back-link">
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
          @dragover.prevent="isDragOver = true"
          @dragleave="isDragOver = false"
          @drop.prevent="handleDrop"
          @click="fileInput?.click()"
        >
          <v-icon icon="mdi-upload-outline" size="48" class="drop-icon" />
          <div class="drop-text">點擊上傳或拖放檔案</div>
          <div class="drop-hint">僅限 PDF 檔案（最大 10MB）</div>
          <input ref="fileInput" type="file" accept=".pdf" hidden @change="handleFileChange" />
        </div>
        <div v-if="selectedFile" class="file-info">
          <v-icon icon="mdi-file-pdf-box" size="18" color="#ef4444" />
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
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular indeterminate color="#2347c5" size="20" width="2" />
          <span>正在提取框架...</span>
        </div>
      </div>

      <!-- Result panel -->
      <div class="panel">
        <div class="panel-label">已提取框架</div>
        <div class="result-zone">
          <div v-if="!extractedData" class="result-placeholder">
            提取完成後，框架詳細資料將顯示於此
          </div>
          <template v-else>
            <div class="result-field">
              <div class="result-field-label">框架名稱</div>
              <div class="result-field-value">{{ extractedData.name }}</div>
            </div>
            <div class="result-field">
              <div class="result-field-label">方法論</div>
              <div class="result-field-value">{{ extractedData.method }}</div>
            </div>
            <div class="result-field">
              <div class="result-field-label">已識別變數</div>
              <div class="result-field-value">{{ extractedData.variables }} 個</div>
            </div>
            <button class="save-btn" @click="saveFramework">儲存框架</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'

const fileInput = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const isDragOver = ref(false)
const extracting = ref(false)
const extractedData = ref<{ name: string; method: string; variables: number } | null>(null)

function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) selectedFile.value = input.files[0]
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file && file.type === 'application/pdf') selectedFile.value = file
}

function startExtract() {
  extracting.value = true
  extractedData.value = null
  setTimeout(() => {
    extracting.value = false
    extractedData.value = {
      name: selectedFile.value?.name.replace('.pdf', '') ?? '未命名框架',
      method: 'CNN 卷積神經網絡',
      variables: 12,
    }
  }, 2000)
}

function saveFramework() {
  alert('框架已儲存至框架庫！')
  extractedData.value = null
  selectedFile.value = null
}
</script>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
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
  color: #111827;
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
  border-color: #2347c5;
  background: #f0f4ff;
}

.drop-icon {
  color: #9ca3af;
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: #9ca3af;
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
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: #9ca3af;
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
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.extract-btn:hover {
  background: #1b3ca0;
}

.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: #6b7280;
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
  color: #9ca3af;
  font-size: 13.5px;
  margin: auto;
  text-align: center;
}

.result-field-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.result-field-value {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
}

.save-btn {
  margin-top: 4px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: #1b3ca0;
}
</style>
