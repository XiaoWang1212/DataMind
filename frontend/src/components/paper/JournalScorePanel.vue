<!-- frontend/src/components/paper/JournalScorePanel.vue -->
<template>
  <div class="score-panel">
    <div v-if="journalScores.length === 0" class="score-panel-empty">
      <div class="score-panel-empty__icon">
        <v-icon color="#8a6d1a" icon="mdi-star" size="22" />
      </div>
      <p class="score-panel-empty__text">
        點擊「期刊評分」按鈕，以 <strong>JAMIA</strong>、<strong>npj Digital Medicine</strong>、<strong>BMC MIDM</strong> 的審稿標準評估本文
      </p>
      <p class="score-panel-empty__meta">3 個期刊 · 6 項準則 · AI 評分</p>
    </div>

    <div v-else class="score-panel-summary">
      <div class="score-panel-summary__head">
        <ScoreRing :font-size="15" :score="averageScore" :size="40" :stroke-width="4" />
        <span class="score-panel-summary__avg-label">avg</span>
      </div>

      <p class="score-panel-summary__title">評分摘要</p>

      <ul class="score-panel-summary__list">
        <li v-for="js in journalScores" :key="js.journal" class="score-panel-summary__row">
          <div class="score-panel-summary__row-head">
            <span class="score-panel-summary__row-name">{{ js.journal }}</span>
            <span class="score-panel-summary__row-score" :style="{ color: getScoreColor(js.overallScore) }">
              {{ js.overallScore }}
            </span>
          </div>
          <div class="score-panel-summary__bar">
            <div
              class="score-panel-summary__bar-fill"
              :style="{ width: `${js.overallScore}%`, background: getScoreColor(js.overallScore) }"
            />
          </div>
        </li>
      </ul>

      <button class="score-panel-summary__cta" type="button" @click="emit('openReport')">
        查看完整評分報告
        <v-icon icon="mdi-arrow-right" size="14" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import { getScoreColor } from '@/utils/scoreColor'

  const props = defineProps<{
    journalScores: JournalScore[]
    scoring: boolean
  }>()

  const emit = defineEmits<{
    openReport: []
  }>()

  const averageScore = computed(() => {
    if (props.journalScores.length === 0) return 0
    const sum = props.journalScores.reduce((acc, js) => acc + js.overallScore, 0)
    return Math.round(sum / props.journalScores.length)
  })
</script>

<style scoped>
  .score-panel {
    margin-bottom: 12px;
  }

  .score-panel-empty {
    background: #ffffff;
    border: 1px solid #e8ebf1;
    border-radius: 12px;
    padding: 24px 18px;
    text-align: center;
  }

  .score-panel-empty__icon {
    width: 44px;
    height: 44px;
    margin: 0 auto 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #fffbe8;
    border-radius: 10px;
  }

  .score-panel-empty__text {
    margin: 0 0 8px;
    font-size: 12.5px;
    line-height: 1.7;
    color: #4a4f5c;
  }

  .score-panel-empty__text strong {
    color: #1c2130;
  }

  .score-panel-empty__meta {
    margin: 0;
    font-size: 11.5px;
    color: #1058d6;
  }

  .score-panel-summary {
    background: #ffffff;
    border: 1px solid #e8ebf1;
    border-radius: 12px;
    padding: 16px 16px 14px;
  }

  .score-panel-summary__head {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .score-panel-summary__avg-label {
    font-size: 11px;
    color: #6f7480;
  }

  .score-panel-summary__title {
    margin: 0 0 10px;
    font-size: 12.5px;
    font-weight: 700;
    color: #8a6d1a;
  }

  .score-panel-summary__list {
    list-style: none;
    margin: 0 0 12px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .score-panel-summary__row-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 4px;
  }

  .score-panel-summary__row-name {
    font-size: 12px;
    font-weight: 600;
    color: #1c2130;
  }

  .score-panel-summary__row-score {
    font-size: 12.5px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .score-panel-summary__bar {
    height: 5px;
    border-radius: 3px;
    background: #e8ebf1;
    overflow: hidden;
  }

  .score-panel-summary__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .score-panel-summary__cta {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 10px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: none;
    font-size: 12px;
    font-weight: 600;
    color: #4a4f5c;
    cursor: pointer;
  }

  .score-panel-summary__cta:hover {
    border-color: #1058d6;
    color: #1058d6;
  }
</style>
