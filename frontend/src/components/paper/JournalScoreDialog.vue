<template>
  <div
    v-if="visible"
    class="journal-score-backdrop"
    @click.self="emit('close')"
  >
    <div class="journal-score-card">
      <header class="journal-score-header">
        <h3>期刊評分結果</h3>
        <button
          class="journal-score-close"
          type="button"
          @click="emit('close')"
        >
          ×
        </button>
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
        <div class="journal-score-overall">
          <span class="journal-score-overall__name">{{ activeJournal.journalFullName }}</span>
          <span class="journal-score-overall__value">{{ activeJournal.overallScore }}<small>/100</small></span>
        </div>

        <ul class="journal-score-criteria">
          <li
            v-for="criterion in activeJournal.criteria"
            :key="criterion.name"
            class="journal-score-criterion"
          >
            <div class="journal-score-criterion__head">
              <span class="journal-score-criterion__name">{{ criterion.name }}</span>
              <span class="journal-score-criterion__score">{{ criterion.score }}</span>
            </div>
            <p class="journal-score-criterion__comment">{{ criterion.comment }}</p>
          </li>
        </ul>

        <div class="journal-score-suggestions">
          <p class="journal-score-suggestions__title">修改建議</p>
          <ul>
            <li v-for="(suggestion, index) in activeJournal.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed, ref, watch } from 'vue'

  const props = defineProps<{
    visible: boolean
    journalScores: JournalScore[]
    failedJournals: string[]
  }>()

  const emit = defineEmits<{
    close: []
  }>()

  const activeIndex = ref(0)

  watch(() => props.visible, visible => {
    if (visible) activeIndex.value = 0
  })

  const activeJournal = computed(() => props.journalScores[activeIndex.value] ?? null)
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
    width: 640px;
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
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid #e8ebf1;
  }

  .journal-score-header h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-close {
    border: none;
    background: none;
    font-size: 20px;
    line-height: 1;
    color: #6f7480;
    cursor: pointer;
  }

  .journal-score-warning {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 12px 20px 0;
    padding: 8px 12px;
    border-radius: 8px;
    background: #fff4e5;
    color: #9a5b00;
    font-size: 12px;
  }

  .journal-score-tabs {
    display: flex;
    gap: 6px;
    padding: 14px 20px 0;
    border-bottom: 1px solid #e8ebf1;
  }

  .journal-score-tab {
    border: none;
    background: none;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 600;
    color: #6f7480;
    cursor: pointer;
    border-bottom: 2px solid transparent;
  }

  .journal-score-tab--active {
    color: #1058d6;
    border-bottom-color: #1058d6;
  }

  .journal-score-body {
    padding: 18px 20px 20px;
    overflow-y: auto;
  }

  .journal-score-overall {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .journal-score-overall__name {
    font-size: 12.5px;
    color: #6f7480;
  }

  .journal-score-overall__value {
    font-size: 26px;
    font-weight: 700;
    color: #1058d6;
  }

  .journal-score-overall__value small {
    font-size: 13px;
    font-weight: 500;
    color: #6f7480;
  }

  .journal-score-criteria {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .journal-score-criterion {
    border: 1px solid #e8ebf1;
    border-radius: 10px;
    padding: 10px 12px;
  }

  .journal-score-criterion__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .journal-score-criterion__name {
    font-size: 12.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-criterion__score {
    font-size: 12.5px;
    font-weight: 700;
    color: #1058d6;
  }

  .journal-score-criterion__comment {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }

  .journal-score-suggestions {
    margin-top: 16px;
    padding-top: 14px;
    border-top: 1px solid #e8ebf1;
  }

  .journal-score-suggestions__title {
    margin: 0 0 8px;
    font-size: 12.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .journal-score-suggestions ul {
    margin: 0;
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .journal-score-suggestions li {
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }
</style>
