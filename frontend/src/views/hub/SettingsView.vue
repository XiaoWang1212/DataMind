<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">設定</h1>
      <p class="page-sub">設定您的研究環境</p>
    </div>

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
          class="toggle-btn"
          :class="{ 'toggle-btn--on': autoSave }"
          @click="autoSave = !autoSave"
          role="switch"
          :aria-checked="autoSave"
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
        />
      </div>

      <div class="api-field">
        <label class="api-label">API 金鑰</label>
        <input
          v-model="apiKey"
          class="api-input"
          type="password"
          placeholder="••••••••••••••••"
        />
      </div>
    </div>

    <!-- Save button -->
    <div class="save-row">
      <button class="save-btn" @click="saveSettings">儲存設定</button>
      <div v-if="saved" class="save-msg">
        <v-icon icon="mdi-check-circle" size="16" color="#16a34a" />
        設定已儲存
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const timeout = ref('10')
const autoSave = ref(true)
const nlpEndpoint = ref('https://api.nlp-service.internal')
const apiKey = ref('')
const saved = ref(false)

function saveSettings() {
  saved.value = true
  setTimeout(() => { saved.value = false }, 2500)
}
</script>

<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Settings card ── */
.settings-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
  margin-bottom: 16px;
  color: var(--color-text);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 20px;
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
  background: #f0f1f3;
  margin: 16px 0;
}

.setting-info {
  flex: 1;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-accent);
  margin-bottom: 3px;
}

.setting-desc {
  font-size: 12.5px;
  color: var(--color-secondary);
}

/* ── Timeout select ── */
.timeout-select {
  height: 36px;
  padding: 0 30px 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: var(--color-text);
  outline: none;
  cursor: pointer;
  appearance: auto;
  min-width: 110px;
  color-scheme: light;
}

.timeout-select:focus {
  border-color: var(--color-accent);
}

/* ── Toggle ── */
.toggle-btn {
  width: 44px;
  height: 24px;
  border-radius: 99px;
  border: none;
  cursor: pointer;
  background: #e5e7eb;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-btn--on {
  background: var(--color-accent);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
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
  font-size: 13px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.api-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 13.5px;
  color: var(--color-text);
  background-color: #f9fafb;
  outline: none;
  box-sizing: border-box;
  font-family: 'Roboto Mono', monospace;
  transition: border-color 0.15s;
  color-scheme: light;
}

.api-input:focus {
  border-color: var(--color-accent);
  background-color: #ffffff;
}

/* ── Save ── */
.save-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.save-btn {
  height: 40px;
  padding: 0 24px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.save-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: #16a34a;
  font-weight: 500;
}
</style>
