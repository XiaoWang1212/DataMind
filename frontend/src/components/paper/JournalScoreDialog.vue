<template>
  <div
    v-if="visible"
    class="journal-score-backdrop"
    @click.self="emit('close')"
  >
    <div class="journal-score-card">
      <header class="journal-score-header">
        <div class="journal-score-header__text">
          <p class="journal-score-eyebrow">期刊評分報告</p>
          <h3 class="journal-score-title">Journal Peer Review Simulation</h3>
        </div>
        <AppButton icon-only title="按 Esc 關閉" variant="ghost" @click="emit('close')">
          <v-icon icon="mdi-close" size="16" />
        </AppButton>
      </header>

      <p v-if="failedJournals.length > 0" class="journal-score-warning">
        <v-icon icon="mdi-alert-outline" size="14" />
        {{ failedJournals.join('、') }} 評分失敗，僅顯示其餘期刊結果
      </p>

      <nav class="journal-score-tabs">
        <button
          v-for="(js, index) in journalScores"
          :key="js.journal"
          class="journal-score-tab"
          :class="{ 'journal-score-tab--active': index === activeIndex }"
          type="button"
          @click="activeIndex = index"
        >
          {{ js.journal }}
        </button>
      </nav>

      <div v-if="activeJournal" class="journal-score-body">
        <div class="journal-score-overview">
          <ScoreRing :font-size="30" :score="activeJournal.overallScore" :size="104" :stroke-width="9" />

          <div class="journal-score-overview__text">
            <p class="journal-score-overview__name">{{ activeJournal.journalFullName }}</p>
            <p v-if="activeJournal.overallComment" class="journal-score-overview__comment">
              {{ activeJournal.overallComment }}
            </p>

            <div class="journal-score-overview__minis">
              <ScoreRing
                v-for="c in activeJournal.criteria.slice(0, 3)"
                :key="c.name"
                :font-size="12"
                :score="c.score"
                :size="40"
                :stroke-width="4"
              />
              <span v-if="activeJournal.criteria.length > 3" class="journal-score-overview__more">
                +{{ activeJournal.criteria.length - 3 }} more
              </span>
            </div>
          </div>
        </div>

        <hr class="journal-score-divider">

        <p class="journal-score-section-title">逐項評分準則</p>

        <ol class="journal-score-criteria">
          <li
            v-for="(criterion, index) in activeJournal.criteria"
            :key="criterion.name"
            class="journal-score-criterion"
          >
            <div class="journal-score-criterion__head">
              <span class="journal-score-criterion__index">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="journal-score-criterion__name">{{ criterion.name }}</span>
            </div>
            <div class="journal-score-criterion__bar-row">
              <div class="journal-score-criterion__bar">
                <div
                  class="journal-score-criterion__bar-fill"
                  :style="{ width: `${criterion.score}%`, background: getScoreColor(criterion.score) }"
                />
              </div>
              <span class="journal-score-criterion__score" :style="{ color: getScoreColor(criterion.score) }">
                {{ criterion.score }}
              </span>
            </div>
            <p class="journal-score-criterion__comment">{{ criterion.comment }}</p>
          </li>
        </ol>

        <hr class="journal-score-divider">

        <p class="journal-score-section-title">修改建議</p>

        <ol class="journal-score-suggestions">
          <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index" class="journal-score-suggestion">
            <span class="journal-score-suggestion__index">
              {{ String(index + 1).padStart(2, '0') }}.
            </span>
            <span class="journal-score-suggestion__text">{{ suggestion }}</span>
          </li>
        </ol>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = defineProps<{
    visible: boolean
    journalScores: JournalScore[]
    failedJournals: string[]
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const activeIndex = ref(0)

  const activeJournal = computed(() => props.journalScores[activeIndex.value] ?? null)

  function onKeydown (event: KeyboardEvent) {
    if (event.key === 'Escape') emit('close')
  }

  watch(() => props.visible, visible => {
    if (visible) {
      activeIndex.value = 0
      window.addEventListener('keydown', onKeydown)
    } else {
      window.removeEventListener('keydown', onKeydown)
    }
  }, { immediate: true })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown)
  })
</script>

<style scoped>
  .journal-score-backdrop {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(18, 30, 58, 0.45);
    z-index: 1000;
  }

  /* 實色白底，不套玻璃：backdrop-filter 疊在深色遮罩前面會把深色一起模糊進來，
     顏色會偏濁。跟 2026-08-15 workflow canvas 同一個判斷 */
  .journal-score-card {
    width: 680px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-float);
  }

  .journal-score-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    padding: 20px 24px 0;
    flex-shrink: 0;
  }

  .journal-score-eyebrow {
    margin: 0 0 4px;
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.01em;
    color: var(--color-ink);
  }

  .journal-score-title {
    margin: 0;
    font-family: var(--font-heading);
    font-size: 22px;
    font-weight: 500;
    color: var(--color-text);
  }

  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 14px 24px 0;
    color: var(--color-warning-text);
    font-size: 12px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .journal-score-tabs {
    display: flex;
    gap: 20px;
    padding: 18px 24px 0;
    border-bottom: 1px solid var(--color-border);
    flex-shrink: 0;
  }

  .journal-score-tab {
    border: none;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 0 0 10px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-ink-soft);
    cursor: pointer;
    transition: color var(--dur-fast) var(--ease-out),
      border-bottom-color var(--dur-fast) var(--ease-out);
  }

  .journal-score-tab--active {
    font-weight: 500;
    color: var(--color-ink);
    border-bottom-color: var(--color-ink);
  }

  .journal-score-body {
    padding: 22px 24px 24px;
    overflow-y: auto;
  }

  .journal-score-overview {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .journal-score-overview__text {
    flex: 1;
    min-width: 0;
  }

  .journal-score-overview__name {
    margin: 0 0 6px;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .journal-score-overview__comment {
    margin: 0 0 12px;
    font-size: 14.5px;
    line-height: 1.6;
    font-weight: 500;
    color: var(--color-text);
  }

  .journal-score-overview__minis {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .journal-score-overview__more {
    font-size: 12px;
    color: var(--color-ink-soft);
  }

  .journal-score-divider {
    margin: 20px 0;
    border: none;
    border-top: 1px solid var(--color-border);
  }

  .journal-score-section-title {
    margin: 0 0 14px;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink);
  }

  .journal-score-criteria {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }

  .journal-score-criterion__head {
    display: flex;
    align-items: baseline;
    gap: 8px;
    margin-bottom: 6px;
  }

  .journal-score-criterion__index {
    font-size: 11px;
    font-weight: 500;
    color: var(--color-ink-soft);
  }

  .journal-score-criterion__name {
    font-size: 13.5px;
    font-weight: 500;
    color: var(--color-text);
  }

  .journal-score-criterion__bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 8px;
  }

  .journal-score-criterion__bar {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: var(--color-border);
    overflow: hidden;
  }

  .journal-score-criterion__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .journal-score-criterion__score {
    flex-shrink: 0;
    font-size: 13px;
    font-weight: 500;
    min-width: 24px;
    text-align: right;
  }

  .journal-score-criterion__comment {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.65;
    color: var(--color-text);
  }

  .journal-score-suggestions {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* 拿掉邊框後靠淡底色分組，比之前太淡看不出來的邊框更容易辨識每一條的範圍 */
  .journal-score-suggestion {
    display: flex;
    gap: 10px;
    padding: 10px 12px;
    border-radius: var(--radius-md);
    background: var(--color-surface-alt);
  }

  .journal-score-suggestion__index {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 500;
    color: var(--color-ink);
  }

  .journal-score-suggestion__text {
    font-size: 13px;
    line-height: 1.65;
    color: var(--color-text);
  }
</style>
