<template>
  <div
    v-if="visible"
    class="journal-score-backdrop"
    @click.self="emit('close')"
  >
    <div class="journal-score-card">
      <header class="journal-score-header">
        <div class="journal-score-header__text">
          <p class="journal-score-eyebrow" :style="{ color: activeAccent.text }">期刊評分報告</p>
          <h3 class="journal-score-title">Journal Peer Review Simulation</h3>
        </div>
        <button class="journal-score-esc" type="button" @click="emit('close')">ESC</button>
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
          :style="index === activeIndex
            ? { color: getJournalAccent(js.journal).text, borderBottomColor: getJournalAccent(js.journal).main }
            : undefined"
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

        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">逐項評分準則</p>

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

        <p class="journal-score-section-title" :style="{ color: activeAccent.text }">修改建議</p>

        <ol class="journal-score-suggestions">
          <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index" class="journal-score-suggestion">
            <span class="journal-score-suggestion__index" :style="{ color: activeAccent.text }">
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
  import { getJournalAccent } from '@/utils/journalTheme'
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
  const activeAccent = computed(() => getJournalAccent(activeJournal.value?.journal ?? ''))

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
    background: rgba(20, 22, 30, 0.45);
    z-index: 1000;
  }

  .journal-score-card {
    width: 680px;
    max-width: calc(100vw - 32px);
    max-height: calc(100vh - 64px);
    display: flex;
    flex-direction: column;
    background: #ffffff;
    border-radius: 14px;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
    overflow: hidden;
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
    font-weight: 700;
    letter-spacing: 0.04em;
  }

  .journal-score-title {
    margin: 0;
    font-family: 'Noto Serif TC', Georgia, 'Times New Roman', serif;
    font-size: 22px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-esc {
    flex-shrink: 0;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: none;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
    color: #8a8f9c;
    cursor: pointer;
  }

  .journal-score-esc:hover {
    border-color: #b7bcc7;
    color: #4a4f5c;
  }

  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 14px 24px 0;
    padding: 8px 12px;
    border-radius: 8px;
    background: #fff4e5;
    color: #9a5b00;
    font-size: 12px;
    flex-shrink: 0;
  }

  .journal-score-tabs {
    display: flex;
    gap: 20px;
    padding: 18px 24px 0;
    border-bottom: 1px solid #e8ebf1;
    flex-shrink: 0;
  }

  .journal-score-tab {
    border: none;
    border-bottom: 2px solid transparent;
    background: none;
    padding: 0 0 10px;
    font-size: 13px;
    font-weight: 600;
    color: #8a8f9c;
    cursor: pointer;
  }

  .journal-score-tab--active {
    font-weight: 700;
    color: #1c2130;
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
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #8a8f9c;
  }

  .journal-score-overview__comment {
    margin: 0 0 12px;
    font-size: 14.5px;
    line-height: 1.6;
    font-weight: 600;
    color: #1c2130;
  }

  .journal-score-overview__minis {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .journal-score-overview__more {
    font-size: 12px;
    color: #8a8f9c;
  }

  .journal-score-divider {
    margin: 20px 0;
    border: none;
    border-top: 1px solid #e8ebf1;
  }

  .journal-score-section-title {
    margin: 0 0 14px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
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
    font-weight: 700;
    color: #b7bcc7;
  }

  .journal-score-criterion__name {
    font-size: 13.5px;
    font-weight: 700;
    color: #1c2130;
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
    background: #e8ebf1;
    overflow: hidden;
  }

  .journal-score-criterion__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .journal-score-criterion__score {
    flex-shrink: 0;
    font-size: 13px;
    font-weight: 700;
    min-width: 24px;
    text-align: right;
  }

  .journal-score-criterion__comment {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.65;
    color: #4a4f5c;
  }

  .journal-score-suggestions {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .journal-score-suggestion {
    display: flex;
    gap: 10px;
    border: 1px solid #e8ebf1;
    border-radius: 10px;
    padding: 12px 14px;
  }

  .journal-score-suggestion__index {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 700;
  }

  .journal-score-suggestion__text {
    font-size: 12.5px;
    line-height: 1.65;
    color: #3a3f4a;
  }
</style>
