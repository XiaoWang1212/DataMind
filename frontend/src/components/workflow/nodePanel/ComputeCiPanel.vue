<template>
  <div class="ci-info">
    <div class="ci-info__header">
      <span class="ci-info__icon">📊</span>
      <div>
        <h4 class="ci-info__title">Bootstrap 信賴區間</h4>
        <p class="ci-info__sub">對每個評估指標計算 95% 信賴區間</p>
      </div>
    </div>

    <div class="ci-info__section">
      <h5 class="ci-info__section-title">這個節點做什麼？</h5>
      <p class="ci-info__text">
        使用 Bootstrap 重抽樣方法，對模型評估指標（AUC、F1、MCC 等）估算 95% 信賴區間，
        讓結果更具統計嚴謹性，適合學術論文或需要量化不確定性的場景。
      </p>
    </div>

    <div class="ci-info__section">
      <h5 class="ci-info__section-title">運作方式</h5>
      <ul class="ci-info__list">
        <li>從測試集以重抽樣方式產生多組樣本</li>
        <li>對每組樣本計算評估指標</li>
        <li>取第 2.5 與 97.5 百分位數作為信賴區間上下界</li>
      </ul>
    </div>

    <div class="ci-info__notice">
      <span class="ci-info__notice-icon">⚠️</span>
      <p>計算時間顯著增加，建議在模型確認後再開啟。</p>
    </div>

    <div class="ci-info__footer">
      <span class="ci-info__footer-icon">⚙️</span>
      <p>
        若要啟用或停用 Compute CI，請至 <strong>Settings</strong> 節點調整。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
  .ci-info {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .ci-info__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .ci-info__icon {
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
  }

  .ci-info__title {
    margin: 0 0 2px;
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
  }

  .ci-info__sub {
    margin: 0;
    font-size: 11px;
    color: #64748b;
  }

  .ci-info__section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ci-info__section-title {
    margin: 0;
    font-size: 12px;
    font-weight: 600;
    color: #334155;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .ci-info__text {
    margin: 0;
    font-size: 12px;
    color: #475569;
    line-height: 1.6;
  }

  .ci-info__list {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: #475569;
    line-height: 1.5;
  }

  .ci-info__notice {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-radius: 8px;
  }

  .ci-info__notice-icon {
    font-size: 14px;
    flex-shrink: 0;
    line-height: 1.5;
  }

  .ci-info__notice p {
    margin: 0;
    font-size: 12px;
    color: #92400e;
    line-height: 1.5;
  }

  .ci-info__footer {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.12);
    border-radius: 8px;
  }

  .ci-info__footer-icon {
    font-size: 14px;
    flex-shrink: 0;
    line-height: 1.5;
  }

  .ci-info__footer p {
    margin: 0;
    font-size: 12px;
    color: #475569;
    line-height: 1.5;
  }

  .ci-info__footer strong {
    color: #005dff;
  }
</style>
