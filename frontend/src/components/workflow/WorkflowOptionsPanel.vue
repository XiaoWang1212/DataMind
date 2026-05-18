<template>
  <!-- 抽屜內容容器：由 Workspace 控制顯示/隱藏 -->
  <section class="setting-area">
    <!-- 有選到節點時才渲染內容 -->
    <div v-if="selectedNode" class="panel">
      <!-- 標題區：顯示目前節點名稱與說明 -->
      <div class="panel-header">
        <h3>{{ selectedNode.data.label.replace(/\n/g, " ") }}</h3>
        <p>{{ selectedNode.data.description }}</p>
      </div>

      <div class="panel-body">
        <!-- Data Table 節點：顯示資料預覽（資料來源為上一頁已上傳結果） -->
        <template v-if="selectedNode.id === 'dataTable'">
          <div class="form-row">
            <label for="preview-rows">預覽筆數</label>
            <input
              id="preview-rows"
              v-model.number="localConfig.previewRows"
              min="1"
              type="number"
            >
          </div>

          <div class="preview-box" :style="previewBoxStyle">
            <table>
              <thead>
                <tr>
                  <th v-for="header in PREVIEW_HEADERS" :key="header">
                    {{ header }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in previewRows" :key="rowIndex">
                  <td
                    v-for="(cell, cellIndex) in row"
                    :key="`${rowIndex}-${cellIndex}`"
                  >
                    {{ cell }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- File 節點：顯示上傳區塊 -->
        <template v-if="selectedNode.id === 'file'">
          <WorkflowFileUploadPanel
            :file-name="fileName"
            @update:file-name="(value) => (localConfig.fileName = value)"
          />
        </template>

        <!-- 非 Data Table 節點：依 fields 動態渲染一般表單 -->
        <template v-else>
          <div v-if="isModelNode" class="upload-card">
            <div class="upload-card__title">模型檔案上傳</div>
            <p class="upload-card__desc">
              請上傳模型權重或設定檔，檔案會與該模型節點綁定。
            </p>
            <div v-if="localConfig.fileName" class="upload-card__info">
              已上傳：{{ localConfig.fileName }}
            </div>
          </div>

          <div
            v-for="field in selectedNode.data.fields"
            :key="field.key"
            class="form-row"
          >
            <label :for="field.key">{{ field.label }}</label>

            <input
              v-if="field.type === 'text'"
              :id="field.key"
              v-model="localConfig[field.key]"
              type="text"
            >

            <input
              v-else-if="field.type === 'number'"
              :id="field.key"
              v-model.number="localConfig[field.key]"
              min="0"
              type="number"
            >

            <select v-else :id="field.key" v-model="localConfig[field.key]">
              <option
                v-for="option in field.options ?? []"
                :key="option"
                :value="option"
              >
                {{ option }}
              </option>
            </select>
          </div>
        </template>

        <!-- Model 節點：額外資訊放在可收合區塊 -->
        <details
          v-if="selectedNode.id.startsWith('model')"
          class="details"
          open
        >
          <summary class="details__summary">模型參數</summary>
          <div class="details__content">
            <!-- modelMore 節點：列出已收合的模型 -->
            <template v-if="selectedNode.id === 'modelMore'">
              <div class="hint">
                已收合模型：Support Vector Machine、Naive Bayes、K-Nearest
                Neighbors ...
              </div>
            </template>
            <!-- 其餘模型節點：沒有額外參數時顯示提示 -->
            <template v-else-if="selectedNode.data.fields.length === 0">
              <div class="hint">此模型目前沒有額外參數</div>
            </template>
          </div>
        </details>
      </div>

      <!-- 操作按鈕：固定在面板底部 -->
      <div class="actions">
        <button class="btn btn-primary" type="button" @click="save">
          儲存設定
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { ConfigValue, SimpleNode } from '@/types/workflow'
  import { computed, reactive, watch } from 'vue'
  import {
    PREVIEW_HEADERS,
    PREVIEW_SOURCE_ROWS,
  } from '@/constants/workflowData'
  import WorkflowFileUploadPanel from './nodePanel/WorkflowFileUploadPanel.vue'

  // 父層傳入目前選取節點
  const props = defineProps<{ selectedNode: SimpleNode | null }>()

  // 將設定變更回傳給父層
  const emit = defineEmits<{
    (
      e: 'update-config',
      payload: { nodeId: string, config: Record<string, ConfigValue> },
    ): void
    (e: 'open-upload'): void
  }>()

  // localConfig：面板內可編輯的暫存設定，按下「儲存設定」才同步給父層
  const localConfig = reactive<Record<string, ConfigValue>>({})

  const isModelNode = computed(() =>
    props.selectedNode?.id.startsWith('model'),
  )

  const fileName = computed(() =>
    typeof localConfig.fileName === 'string' ? localConfig.fileName : '',
  )

  // 預覽列數的高度計算常數
  const PREVIEW_HEADER_HEIGHT = 34
  const PREVIEW_ROW_HEIGHT = 31
  const PREVIEW_MAX_HEIGHT = 360

  // 根據「預覽筆數」切片示意資料
  const previewRows = computed(() => {
    const count = Math.max(1, Number(localConfig.previewRows ?? 5))
    return PREVIEW_SOURCE_ROWS.slice(0, count)
  })

  // 讓可視高度隨預覽筆數動態調整
  const previewBoxStyle = computed(() => {
    const count = Math.max(1, Number(localConfig.previewRows ?? 5))
    const dynamicHeight = PREVIEW_HEADER_HEIGHT + count * PREVIEW_ROW_HEIGHT
    return {
      maxHeight: `${Math.min(PREVIEW_MAX_HEIGHT, dynamicHeight)}px`,
    }
  })

  // 當切換節點時，把該節點 config 複製到本地表單狀態
  watch(
    () => props.selectedNode,
    node => {
      // 先清空舊資料，避免欄位殘留
      for (const key of Object.keys(localConfig)) delete localConfig[key]
      if (!node) {
        return
      }
      Object.assign(localConfig, node.data.config)
    },
    { immediate: true },
  )

  // 儲存：把本地表單值回傳給父層更新對應節點
  function save () {
    if (!props.selectedNode) return
    emit('update-config', {
      nodeId: props.selectedNode.id,
      config: { ...localConfig },
    })
  }
</script>

<style scoped>
  .setting-area {
    border: none;
    border-radius: 0;
    height: 100%;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: transparent;
  }

  .panel-header {
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(0, 93, 255, 0.1);
    background: transparent;
  }

  .panel-header h3 {
    margin: 0 0 2px;
    font-size: 16px;
    color: #0f172a;
  }

  .panel-header p {
    margin: 0;
    font-size: 13px;
    color: #6b7280;
  }

  .panel-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 4px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 10px;
  }

  .form-row label {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
  }

  .form-row input,
  .form-row select {
    border: 1px solid rgba(0, 93, 255, 0.2);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
    outline: none;
    background: rgba(255, 255, 255, 0.5);
  }

  /* 隱藏原生 select 箭頭，換成自訂 chevron */
  .form-row select {
    appearance: none;
    -webkit-appearance: none;
    padding-right: 32px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23005DFF' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    cursor: pointer;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed rgba(0, 93, 255, 0.28);
    border-radius: 16px;
    background: rgba(0, 93, 255, 0.04);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__title {
    font-size: 14px;
    font-weight: 700;
  }

  .upload-card__desc {
    margin: 0;
    color: #475569;
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-card__input-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .upload-card__info {
    color: #0f172a;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.13);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: #2563eb;
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }

  .upload-modal-line2 {
    color: #475569;
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: #475569;
  }

  .upload-modal-error {
    color: #b91c1c;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: #475569;
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .upload-modal-chart-card {
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: #f8fafc;
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #475569;
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: 1.2fr 3fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: #2563eb;
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: #0f172a;
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
  }

  .upload-modal-preview-table table {
    width: 100%;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
  }

  .upload-modal-preview-table th {
    background: #f8fafc;
    color: #0f172a;
  }

  .details__summary {
    user-select: none;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 13px;
    background: rgba(0, 93, 255, 0.06);
    border-bottom: 1px solid rgba(0, 93, 255, 0.12);
  }

  .details__content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .preview-box {
    margin-top: 6px;
    border: 1px solid rgba(0, 93, 255, 0.16);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.28);
    overflow: auto;
  }

  .preview-box table {
    width: 100%;
    border-collapse: collapse;
  }

  .preview-box th,
  .preview-box td {
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
    padding: 6px 8px;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-box th {
    background: rgba(160, 192, 232, 0.35);
    font-weight: 700;
  }

  .hint {
    font-size: 13px;
    color: #6b7280;
  }

  .actions {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    padding: 10px 0 14px;
  }

  .btn {
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-primary {
    background: #005dff;
    color: #fff;
    font-weight: 700;
  }

  .btn-primary:hover {
    background: #004fd8;
  }

  @media (max-width: 768px) {
    /* 手機：改為單欄表單，避免標籤與輸入框擠壓 */
    .setting-area {
      padding: 12px 14px 16px;
    }

    .panel-header h3 {
      font-size: 15px;
    }

    .panel-header p {
      font-size: 12px;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 6px;
    }

    .form-row label {
      font-size: 12px;
    }

    .form-row input,
    .form-row select {
      font-size: 12px;
      padding: 8px 9px;
    }

    .details__summary {
      font-size: 12px;
      padding: 9px 10px;
    }

    .actions {
      padding: 8px 0 12px;
    }

    .btn {
      width: 100%;
    }
  }
</style>
