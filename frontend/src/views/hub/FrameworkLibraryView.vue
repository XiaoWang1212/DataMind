<template>
  <div>
    <!-- Page header -->
    <div class="page-header">
      <h1 class="page-title">框架庫</h1>
      <p class="page-sub">管理您的研究框架集合</p>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="search-wrap">
        <v-icon class="search-icon" icon="mdi-magnify" size="17" />
        <input
          v-model="searchQuery"
          class="search-input"
          placeholder="搜尋框架..."
        >
      </div>
      <RouterLink class="upload-btn" to="/hub/library/extract">
        <v-icon icon="mdi-upload" size="16" />
        上傳論文
      </RouterLink>
    </div>

    <!-- Framework cards -->
    <div class="card-grid">
      <div
        v-for="fw in filteredFrameworks"
        :key="fw.id"
        class="fw-card"
        :class="{ 'fw-card--selected': selectedId === fw.id }"
        @click="selectedId = fw.id"
      >
        <div class="fw-card-top">
          <div class="fw-icon-wrap">
            <v-icon color="#4f46e5" icon="mdi-book-open-outline" size="19" />
          </div>
          <div class="fw-info">
            <div class="fw-title" :title="fw.title">{{ fw.title }}</div>
            <div class="fw-subtitle">{{ fw.subtitle }}</div>
          </div>
        </div>
        <div class="fw-meta">
          <div class="fw-meta-row">
            <v-icon class="meta-icon" icon="mdi-tag-outline" size="13" />
            <span>{{ fw.tag }}</span>
          </div>
          <div class="fw-meta-row">
            <v-icon class="meta-icon" icon="mdi-calendar-outline" size="13" />
            <span>{{ fw.date }}</span>
          </div>
        </div>
        <div class="fw-vars">{{ fw.variables }} 個已定義變數</div>
      </div>
    </div>

    <div v-if="filteredFrameworks.length === 0" class="empty-state">
      查無符合的框架
    </div>
  </div>

  <!-- Detail panel (slide-in from right) -->
  <Transition name="panel">
    <div v-if="selectedFramework" class="detail-panel">
      <!-- Panel header -->
      <div class="panel-header">
        <div class="panel-header-info">
          <div class="panel-title">{{ selectedFramework.title }}</div>
          <div class="panel-tag">{{ selectedFramework.tag }}</div>
        </div>
        <button class="panel-close" @click="selectedId = null">
          <v-icon icon="mdi-close" size="18" />
        </button>
      </div>

      <!-- Panel body (scrollable) -->
      <div class="panel-body">
        <!-- Paper title -->
        <div class="panel-section">
          <div class="panel-section-head">
            <v-icon class="section-icon" icon="mdi-file-document-outline" size="16" />
            <span class="panel-section-label">論文標題</span>
          </div>
          <div class="panel-text-muted">{{ selectedFramework.paperTitle }}</div>
        </div>

        <!-- Description -->
        <div class="panel-section">
          <div class="panel-section-label-plain">描述</div>
          <div class="panel-text-muted">{{ selectedFramework.description }}</div>
        </div>

        <!-- Independent variables -->
        <div class="panel-section">
          <div class="panel-section-head">
            <v-icon class="section-icon" icon="mdi-account-multiple-outline" size="15" />
            <span class="panel-section-label">自變數</span>
          </div>
          <div class="var-list">
            <div v-for="v in selectedFramework.independentVars" :key="v" class="var-item">
              {{ v }}
            </div>
          </div>
        </div>

        <!-- Dependent variables -->
        <div class="panel-section">
          <div class="panel-section-head">
            <v-icon class="section-icon" icon="mdi-target" size="15" />
            <span class="panel-section-label">因變數</span>
          </div>
          <div class="var-list">
            <div v-for="v in selectedFramework.dependentVars" :key="v" class="var-item">
              {{ v }}
            </div>
          </div>
        </div>

        <!-- Research hypotheses -->
        <div class="panel-section">
          <div class="panel-section-label-plain">研究假設</div>
          <div class="hypothesis-list">
            <div
              v-for="(h, i) in selectedFramework.hypotheses"
              :key="i"
              class="hypothesis-item"
            >
              {{ h }}
            </div>
          </div>
        </div>

        <!-- Footer meta -->
        <div class="panel-footer-meta">
          <div class="panel-meta-row">
            <span class="panel-meta-key">建立時間</span>
            <span class="panel-meta-val">{{ selectedFramework.date }}</span>
          </div>
          <div class="panel-meta-row">
            <span class="panel-meta-key">變數</span>
            <span class="panel-meta-val">{{ selectedFramework.variables }} 個已定義</span>
          </div>
        </div>
      </div>

      <!-- Use in project button -->
      <div class="panel-action">
        <RouterLink
          class="use-btn"
          :to="`/hub/projects/new`"
        >
          用於專案
        </RouterLink>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { RouterLink } from 'vue-router'
  import { useFrameworkStore } from '@/store/frameworkStore'

  const store = useFrameworkStore()
  const searchQuery = ref('')
  const selectedId = ref<number | null>(null)

  const filteredFrameworks = computed(() => {
    if (!searchQuery.value) return store.frameworks
    const q = searchQuery.value.toLowerCase()
    return store.frameworks.filter(
      f => f.title.toLowerCase().includes(q) || f.tag.toLowerCase().includes(q),
    )
  })

  const selectedFramework = computed(() =>
    selectedId.value === null ? null : store.frameworks.find(f => f.id === selectedId.value) ?? null,
  )
</script>

<style scoped>
.page-header {
  margin-bottom: 22px;
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

/* ── Toolbar ── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.search-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 11px;
  color: var(--color-secondary);
}

.search-input {
  width: 100%;
  height: 38px;
  padding: 0 14px 0 36px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: var(--color-text);
  outline: none;
  transition: border-color 0.15s;
  color-scheme: light;
}

.search-input::placeholder {
  color: var(--color-secondary);
}

.search-input:focus {
  border-color: var(--color-accent);
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s;
}

.upload-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Cards ── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.fw-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-card:hover {
  border-color: #a5b4fc;
}

.fw-card--selected {
  border: 1.5px solid var(--color-accent);
}

.fw-card-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.fw-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fw-info {
  flex: 1;
  min-width: 0;
}

.fw-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.fw-subtitle {
  font-size: 12px;
  color: var(--color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.fw-meta {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-top: 1px solid #f0f0f0;
  padding-top: 14px;
  margin-bottom: 12px;
}

.fw-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-secondary);
}

.meta-icon {
  color: var(--color-secondary);
  flex-shrink: 0;
}

.fw-vars {
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Empty ── */
.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--color-secondary);
  font-size: 14px;
}

/* ── Detail panel ── */
.detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  background: #ffffff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  z-index: 200;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.06);
}

/* Slide transition */
.panel-enter-active,
.panel-leave-active {
  transition: transform 0.22s ease;
}

.panel-enter-from,
.panel-leave-to {
  transform: translateX(100%);
}

/* ── Panel header ── */
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.panel-header-info {
  flex: 1;
  min-width: 0;
  padding-right: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.3;
}

.panel-tag {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-top: 3px;
}

.panel-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  transition: background 0.12s;
  flex-shrink: 0;
}

.panel-close:hover {
  background: #f5f5f5;
  color: var(--color-secondary);
}

/* ── Panel body ── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px;
}

.panel-section {
  padding: 18px 0;
  border-bottom: 1px solid #f3f3f3;
}

.panel-section:last-child {
  border-bottom: none;
}

.panel-section-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
}

.section-icon {
  color: var(--color-secondary);
}

.panel-section-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-secondary);
}

.panel-section-label-plain {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-secondary);
  margin-bottom: 10px;
}

.panel-text-muted {
  font-size: 13px;
  color: var(--color-secondary);
  line-height: 1.55;
}

/* ── Variables ── */
.var-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-item {
  padding: 9px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'Courier New', 'Roboto Mono', Consolas, monospace;
  color: var(--color-secondary);
  background: #ffffff;
}

/* ── Hypotheses ── */
.hypothesis-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hypothesis-item {
  padding: 8px 12px;
  border-left: 2.5px solid #93c5fd;
  font-size: 13px;
  color: var(--color-secondary);
  line-height: 1.5;
}

/* ── Footer meta ── */
.panel-footer-meta {
  padding: 14px 0;
  border-top: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.panel-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
}

.panel-meta-key {
  color: var(--color-secondary);
}

.panel-meta-val {
  color: var(--color-secondary);
  font-weight: 500;
}

/* ── Action button ── */
.panel-action {
  padding: 16px 20px;
  flex-shrink: 0;
  border-top: 1px solid #f0f0f0;
}

.use-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 46px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 8px;
  text-decoration: none;
  font-size: 15px;
  font-weight: 600;
  transition: background 0.15s;
}

.use-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
