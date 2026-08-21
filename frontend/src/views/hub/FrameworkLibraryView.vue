<template>
  <div class="library">
    <PageHeader subtitle="管理您的研究框架集合" title="框架庫" />

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
        <v-icon icon="mdi-upload-outline" size="16" />
        上傳論文
      </RouterLink>
    </div>

    <!-- Framework cards -->
    <div class="card-grid enter-stagger">
      <div
        v-for="fw in filteredFrameworks"
        :key="fw.id"
        class="fw-card"
        :class="{ 'fw-card--selected': selectedId === fw.id }"
        @click="selectedId = fw.id"
      >
        <div class="fw-card-top">
          <div class="fw-icon-wrap">
            <v-icon icon="mdi-book-open-outline" size="19" />
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
          <div v-if="!isEditingTitle" class="panel-title-row">
            <div class="panel-title">{{ selectedFramework.title }}</div>
            <button class="panel-title-edit-btn" title="編輯名稱" @click="startEditingTitle">
              <v-icon icon="mdi-pencil-outline" size="14" />
            </button>
          </div>
          <div v-else class="panel-title-edit-wrap">
            <input
              ref="titleInputRef"
              v-model="titleDraft"
              class="panel-title-input"
              maxlength="255"
              @blur="commitTitleEdit"
              @keydown="handleTitleKeydown"
            >
            <div v-if="titleError" class="panel-title-error">{{ titleError }}</div>
          </div>
          <div class="panel-tag">{{ selectedFramework.tag }}</div>
        </div>
        <AppButton class="panel-close" icon-only variant="ghost" @click="selectedId = null">
          <v-icon icon="mdi-close" size="18" />
        </AppButton>
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
  import { computed, nextTick, ref, watch } from 'vue'
  import { RouterLink } from 'vue-router'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
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

  const isEditingTitle = ref(false)
  const isSavingTitle = ref(false)
  const titleDraft = ref('')
  const titleError = ref<string | null>(null)
  const titleInputRef = ref<HTMLInputElement | null>(null)

  watch(selectedId, () => {
    isEditingTitle.value = false
    isSavingTitle.value = false
    titleError.value = null
  })

  function startEditingTitle () {
    if (!selectedFramework.value) return
    titleDraft.value = selectedFramework.value.title
    titleError.value = null
    isEditingTitle.value = true
    nextTick(() => {
      titleInputRef.value?.focus()
      titleInputRef.value?.select()
    })
  }

  function cancelEditingTitle () {
    // Ignore cancel while a save is in flight so the pending request's
    // success/failure handling (including any error message) still has an
    // edit state to land on instead of being silently discarded.
    if (isSavingTitle.value) return
    isEditingTitle.value = false
    titleError.value = null
  }

  async function commitTitleEdit () {
    // Guard against concurrent invocations (e.g. Enter followed immediately
    // by blur) — while a save is already in flight, do nothing and let the
    // in-flight call own the edit state and any resulting error.
    if (isSavingTitle.value) return
    if (!isEditingTitle.value || !selectedFramework.value) return

    const trimmed = titleDraft.value.trim()
    if (trimmed === selectedFramework.value.title) {
      isEditingTitle.value = false
      titleError.value = null
      return
    }
    if (!trimmed) {
      titleError.value = '名稱不可為空'
      return
    }

    const frameworkId = selectedFramework.value.id
    isSavingTitle.value = true
    try {
      await store.renameFramework(frameworkId, trimmed)
      isEditingTitle.value = false
      titleError.value = null
    } catch (error) {
      console.error('更新框架名稱失敗', error)
      titleError.value = '儲存失敗，請重試'
    } finally {
      isSavingTitle.value = false
    }
  }

  function handleTitleKeydown (event: KeyboardEvent) {
    if (event.key === 'Enter') {
      event.preventDefault()
      commitTitleEdit()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancelEditingTitle()
    }
  }
</script>

<style scoped>
  .library {
    max-width: var(--content-max-width);
    margin-inline: auto;
  }

  /* ── Toolbar ── */
  .toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .search-wrap {
    position: relative;
    display: flex;
    flex: 1;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 14px;
    color: var(--color-ink-soft);
  }

  .search-input {
    width: 100%;
    height: 38px;
    padding: 0 16px 0 38px;
    border: 1px solid var(--color-border-strong);
    border-radius: 999px;
    background-color: var(--color-surface);
    font-size: 14px;
    color: var(--color-text);
    outline: none;
    color-scheme: light;
    transition: border-color var(--dur-fast) var(--ease-out);
  }

  .search-input::placeholder {
    color: var(--color-ink-soft);
  }

  .search-input:focus {
    border-color: var(--color-ink);
  }

  /* 導向提取頁的連結，外觀比照 AppButton primary */
  .upload-btn {
    display: flex;
    align-items: center;
    gap: 7px;
    height: 38px;
    padding: 0 18px;
    border-radius: 999px;
    background: var(--color-ink);
    color: var(--color-surface);
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
    text-decoration: none;
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .upload-btn:hover {
    background: var(--color-ink-strong);
  }

  /* ── Cards ── */
  .card-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
  }

  .fw-card {
    display: flex;
    flex-direction: column;
    padding: 18px 20px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-surface);
    cursor: pointer;
    transition: transform var(--dur-fast) var(--ease-out),
      border-color var(--dur-fast) var(--ease-out),
      box-shadow var(--dur-fast) var(--ease-out);
  }

  .fw-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in oklab, var(--color-ink) 24%, white);
    box-shadow: var(--shadow-card);
  }

  .fw-card--selected {
    border: 1.5px solid var(--color-ink);
  }

  .fw-card-top {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
  }

  /* 從品牌色推導底色，不另外引入游離色碼 */
  .fw-icon-wrap {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: var(--radius-sm);
    background: color-mix(in oklab, var(--color-ink) 10%, white);
    color: var(--color-ink);
  }

  .fw-info {
    flex: 1;
    min-width: 0;
  }

  .fw-title {
    overflow: hidden;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.3;
    color: var(--color-text);
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .fw-subtitle {
    margin-top: 4px;
    font-size: 12px;
    line-height: 1.4;
    color: var(--color-ink-soft);
  }

  .fw-meta {
    display: flex;
    flex-direction: column;
    gap: 7px;
    margin-bottom: 12px;
    padding-top: 14px;
    border-top: 1px solid var(--color-border);
  }

  .fw-meta-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .meta-icon {
    flex-shrink: 0;
    color: var(--color-ink-soft);
  }

  .fw-vars {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* ── Empty ── */
  .empty-state {
    padding: 48px;
    font-size: 14px;
    color: var(--color-ink-soft);
    text-align: center;
  }

  /* ── Detail panel ── */
  .detail-panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 200;
    display: flex;
    flex-direction: column;
    width: 380px;
    border-left: 1px solid var(--color-border);
    background: var(--color-surface);
    box-shadow: var(--shadow-float);
  }

  /* Slide transition */
  .panel-enter-active,
  .panel-leave-active {
    transition: transform var(--dur-base) var(--ease-in-out);
  }

  .panel-enter-from,
  .panel-leave-to {
    transform: translateX(100%);
  }

  /* ── Panel header ── */
  .panel-header {
    display: flex;
    flex-shrink: 0;
    align-items: flex-start;
    justify-content: space-between;
    padding: 22px 20px 16px;
    border-bottom: 1px solid var(--color-border);
  }

  .panel-header-info {
    flex: 1;
    min-width: 0;
    padding-right: 12px;
  }

  .panel-title {
    font-size: 18px;
    font-weight: 500;
    line-height: 1.3;
    color: var(--color-text);
  }

  .panel-tag {
    margin-top: 3px;
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .panel-title-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .panel-title-edit-btn {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border: none;
    border-radius: 5px;
    background: none;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .panel-title-edit-btn:hover {
    background: var(--color-surface-alt);
  }

  .panel-title-edit-wrap {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .panel-title-input {
    width: 100%;
    padding: 0 0 2px;
    border: none;
    border-bottom: 1.5px solid var(--color-accent);
    outline: none;
    font-family: inherit;
    font-size: 18px;
    font-weight: 500;
    line-height: 1.3;
    color: var(--color-text);
  }

  .panel-title-error {
    font-size: 12px;
    color: var(--color-error-text);
  }

  .panel-close {
    flex-shrink: 0;
  }

  /* ── Panel body ── */
  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 0 20px;
  }

  .panel-section {
    padding: 18px 0;
    border-bottom: 1px solid var(--color-border);
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
    color: var(--color-ink-soft);
  }

  .panel-section-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .panel-section-label-plain {
    margin-bottom: 10px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .panel-text-muted {
    font-size: 13px;
    line-height: 1.55;
    color: var(--color-ink-soft);
  }

  /* ── Variables ── */
  .var-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .var-item {
    padding: 9px 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  /* ── Hypotheses ── */
  .hypothesis-item {
    padding: 8px 12px;
    border-left: 2.5px solid color-mix(in oklab, var(--color-ink) 24%, white);
    font-size: 13px;
    line-height: 1.5;
    color: var(--color-ink-soft);
  }

  .hypothesis-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* ── Footer meta ── */
  .panel-footer-meta {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 4px;
    padding: 14px 0;
    border-top: 1px solid var(--color-border);
  }

  .panel-meta-row {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
  }

  .panel-meta-key {
    color: var(--color-ink-soft);
  }

  .panel-meta-val {
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  /* ── Action button ── */
  .panel-action {
    flex-shrink: 0;
    padding: 16px 20px;
    border-top: 1px solid var(--color-border);
  }

  /* 導向建立專案頁的連結，外觀比照 AppButton primary */
  .use-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 46px;
    border-radius: 999px;
    background: var(--color-ink);
    color: var(--color-surface);
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .use-btn:hover {
    background: var(--color-ink-strong);
  }
</style>
