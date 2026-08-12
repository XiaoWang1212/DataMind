<!-- frontend/src/components/paper/JournalScorePanel.vue -->
<template>
  <div class="score-panel">
    <div v-if="journalScores.length === 0" class="score-panel-empty">
      <div class="score-panel-empty__icon">
        <v-icon color="var(--color-warning-text)" icon="mdi-star" size="22" />
      </div>
      <p class="score-panel-empty__text">
        點擊「期刊評分」按鈕，以 <strong>JAMIA</strong>、<strong>npj Digital Medicine</strong>、<strong>BMC MIDM</strong> 的審稿標準評估本文
      </p>
      <p class="score-panel-empty__meta">3 個期刊 · 6 項準則 · AI 評分</p>
    </div>

    <div v-else class="score-panel-summary">
      <div class="score-panel-summary__head">
        <ScoreRing :score="averageScore" :size="40" :stroke-width="4" />
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

      <AppButton class="score-panel-summary__cta" variant="secondary" @click="emit('openReport')">
        查看完整評分報告
        <v-icon icon="mdi-arrow-right" size="14" />
      </AppButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { JournalScore } from '@/api/arxiv'
  import { computed } from 'vue'
  import ScoreRing from '@/components/paper/ScoreRing.vue'
  import AppButton from '@/components/ui/AppButton.vue'
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
    margin-bottom: 0;
  }

  .score-panel-empty {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
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
    background: var(--color-warning-bg);
    border-radius: var(--radius-md);
  }

  .score-panel-empty__text {
    margin: 0 0 8px;
    font-size: 12.5px;
    line-height: 1.7;
    color: var(--color-text);
  }

  .score-panel-empty__text strong {
    color: var(--color-text);
  }

  .score-panel-empty__meta {
    margin: 0;
    font-size: 11.5px;
    color: var(--color-ink);
  }

  .score-panel-summary {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
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
    color: var(--color-ink-soft);
  }

  .score-panel-summary__title {
    margin: 0 0 10px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--color-warning-text);
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
    font-weight: 500;
    color: var(--color-text);
  }

  .score-panel-summary__row-score {
    font-size: 12.5px;
    font-weight: 500;
    flex-shrink: 0;
  }

  .score-panel-summary__bar {
    height: 5px;
    border-radius: 3px;
    background: var(--color-border);
    overflow: hidden;
  }

  .score-panel-summary__bar-fill {
    height: 100%;
    border-radius: 3px;
  }

  .score-panel-summary__cta.app-btn {
    width: 100%;
  }
</style>
