<template>
  <div class="settings">
    <PageHeader subtitle="設定您的研究環境" title="設定" />

    <div class="settings-body enter-stagger">
      <!-- General Settings -->
      <div class="settings-card">
        <div class="card-title">一般設定</div>

        <div class="setting-row">
          <div class="setting-info">
            <div class="setting-name">預設分析逾時</div>
            <div class="setting-desc">分析執行的最長時間</div>
          </div>
          <select v-model="timeout" class="timeout-select">
            <option value="5">5 分鐘</option>
            <option value="10">10 分鐘</option>
            <option value="15">15 分鐘</option>
            <option value="30">30 分鐘</option>
            <option value="60">60 分鐘</option>
          </select>
        </div>

        <div class="setting-divider" />

        <div class="setting-row">
          <div class="setting-info">
            <div class="setting-name">自動儲存提取</div>
            <div class="setting-desc">自動儲存框架提取結果</div>
          </div>
          <button
            :aria-checked="autoSave"
            class="toggle-btn"
            :class="{ 'toggle-btn--on': autoSave }"
            role="switch"
            @click="autoSave = !autoSave"
          >
            <span class="toggle-thumb" />
          </button>
        </div>
      </div>

      <!-- API Configuration -->
      <div class="settings-card">
        <div class="card-title">API 設定</div>

        <div class="api-field">
          <label class="api-label">NLP 服務端點</label>
          <input
            v-model="nlpEndpoint"
            class="api-input"
            placeholder="https://api.your-service.internal"
          >
        </div>

        <div class="api-field">
          <label class="api-label">API 金鑰</label>
          <input
            v-model="apiKey"
            class="api-input"
            placeholder="••••••••••••••••"
            type="password"
          >
        </div>
      </div>

      <!-- Save button -->
      <div class="save-row">
        <AppButton variant="primary" @click="saveSettings">儲存設定</AppButton>
        <span v-if="saved" class="save-hint">
          <v-icon icon="mdi-check-circle-outline" size="14" />
          設定已儲存
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'

  const timeout = ref('10')
  const autoSave = ref(true)
  const nlpEndpoint = ref('https://api.nlp-service.internal')
  const apiKey = ref('')
  const saved = ref(false)

  function saveSettings () {
    saved.value = true
    setTimeout(() => {
      saved.value = false
    }, 2500)
  }
</script>

<style scoped>
  .settings {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* ── Settings card ── */
  .settings-card {
    margin-bottom: 16px;
    padding: 22px 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
    color: var(--color-text);
  }

  .card-title {
    margin-bottom: 20px;
    font-size: 15px;
    font-weight: 500;
    color: var(--color-text);
  }

  /* ── Setting row ── */
  .setting-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 4px 0;
  }

  .setting-divider {
    height: 1px;
    margin: 16px 0;
    background: var(--color-border);
  }

  .setting-info {
    flex: 1;
  }

  .setting-name {
    margin-bottom: 3px;
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text);
  }

  .setting-desc {
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  /* ── Timeout select ── */
  .timeout-select {
    min-width: 110px;
    height: 36px;
    padding: 0 30px 0 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background-color: var(--color-surface);
    font-size: 13px;
    color: var(--color-text);
    outline: none;
    cursor: pointer;
    appearance: auto;
    color-scheme: light;
  }

  .timeout-select:focus {
    border-color: var(--color-ink);
  }

  /* ── Toggle ── */
  .toggle-btn {
    position: relative;
    flex-shrink: 0;
    width: 44px;
    height: 24px;
    border: none;
    border-radius: 999px;
    background: var(--color-border);
    cursor: pointer;
    transition: background-color var(--dur-base) var(--ease-in-out);
  }

  .toggle-btn--on {
    background: var(--color-ink);
  }

  .toggle-thumb {
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--color-surface);
    /* 陰影帶藏青而非純黑，跟 --shadow-* 同一個光源與色調；滑塊小，用更緊的擴散 */
    box-shadow: 0 1px 3px rgba(14, 30, 66, 0.24);
    transition: left var(--dur-base) var(--ease-in-out);
  }

  .toggle-btn--on .toggle-thumb {
    left: 22px;
  }

  /* ── API fields ── */
  .api-field {
    margin-bottom: 16px;
  }

  .api-field:last-child {
    margin-bottom: 0;
  }

  .api-label {
    display: block;
    margin-bottom: 7px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .api-input {
    box-sizing: border-box;
    width: 100%;
    height: 40px;
    padding: 0 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background-color: var(--color-surface-alt);
    font-size: 14px;
    color: var(--color-text);
    outline: none;
    transition: border-color var(--dur-fast) var(--ease-out),
      background-color var(--dur-fast) var(--ease-out);
    color-scheme: light;
  }

  .api-input:focus {
    border-color: var(--color-ink);
    background-color: var(--color-surface);
  }

  /* ── Save ── */
  .save-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .save-hint {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 13px;
    color: var(--color-success-text);
  }
</style>
