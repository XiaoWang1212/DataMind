<template>
  <div class="style-guide">
    <h1 class="sg-h1">Design tokens 展示頁</h1>
    <p class="sg-note">
      僅在 dev 模式掛路由，用來核對 docs/DESIGN_SYSTEM.md 的 token 是否套對，不會出現在 production build。
    </p>

    <section>
      <h2 class="sg-h2">色彩</h2>
      <div class="sg-swatch-grid">
        <div v-for="swatch in swatches" :key="swatch.name" class="sg-swatch">
          <div class="sg-swatch-color" :style="{ background: swatch.varRef }" />
          <div class="sg-swatch-label">{{ swatch.name }}</div>
          <div class="sg-swatch-var">{{ swatch.varRef }}</div>
        </div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">Workflow 節點分類色（§2.3）</h2>
      <p class="sg-note">
        依 pipeline 角色分五類。全部避開綠／琥珀／紅 —— 那三色留給節點外圈的執行狀態，
        混用會讓「已完成」讀不出來。節點是圓形 + 白色 icon。
      </p>
      <div class="sg-node-grid">
        <div v-for="cat in nodeCategories" :key="cat.name" class="sg-node">
          <div class="sg-node-dot" :style="{ background: cat.varRef }">
            <v-icon icon="mdi-circle-outline" size="24" />
          </div>
          <div>
            <div class="sg-swatch-label">{{ cat.name }}</div>
            <div class="sg-swatch-var">{{ cat.nodes }}</div>
          </div>
        </div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">圓角</h2>
      <div class="sg-row">
        <div class="sg-radius-box" style="border-radius: var(--radius-sm)">sm 8px</div>
        <div class="sg-radius-box" style="border-radius: var(--radius-md)">md 12px</div>
        <div class="sg-radius-box" style="border-radius: var(--radius-lg)">lg 16px</div>
        <div class="sg-radius-box rounded-full">pill</div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">陰影</h2>
      <div class="sg-row">
        <div class="sg-shadow-box" style="box-shadow: var(--shadow-card)">shadow-card</div>
        <div class="sg-shadow-box" style="box-shadow: var(--shadow-float)">shadow-float</div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">按鈕（§7.1 四變體 + §6.2 邊緣反光 hover）</h2>
      <div class="sg-row">
        <AppButton variant="primary">primary</AppButton>
        <AppButton variant="secondary">secondary</AppButton>
        <AppButton variant="ghost">ghost</AppButton>
        <AppButton variant="danger">danger</AppButton>
      </div>
      <div class="sg-row" style="margin-top: 16px">
        <AppButton loading variant="primary">loading</AppButton>
        <AppButton disabled variant="primary">disabled</AppButton>
        <AppButton icon-only variant="secondary">
          <v-icon icon="mdi-plus" size="18" />
        </AppButton>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">狀態顯示（§7.5）</h2>
      <div class="sg-row">
        <StatusBadge status="success">已對應</StatusBadge>
        <StatusBadge status="warning">待確認</StatusBadge>
        <StatusBadge status="danger">未對應</StatusBadge>
        <StatusBadge status="neutral">已略過</StatusBadge>
      </div>
      <div class="sg-row" style="margin-top: 16px">
        <StatusBadge status="success" variant="dot">已對應</StatusBadge>
        <StatusBadge status="warning" variant="dot">待確認</StatusBadge>
        <StatusBadge status="danger" variant="dot">未對應</StatusBadge>
        <StatusBadge status="neutral" variant="dot">已略過</StatusBadge>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">頁首（§3 字級階層）</h2>
      <PageHeader subtitle="副標說明文字，13px" title="頁面標題">
        <template #actions>
          <AppButton variant="secondary">次要動作</AppButton>
          <AppButton variant="primary">主要動作</AppButton>
        </template>
      </PageHeader>
    </section>

    <section>
      <h2 class="sg-h2">字級階層</h2>
      <div class="sg-type-sample" style="font-size: 22px; font-weight: 500;">頁面標題 h1 / 22px / 500</div>
      <div class="sg-type-sample" style="font-size: 18px; font-weight: 500;">區塊標題 h2 / 18px / 500</div>
      <div class="sg-type-sample" style="font-size: 15px; font-weight: 500;">小標 h3 / 15px / 500</div>
      <div class="sg-type-sample" style="font-size: 14px; font-weight: 400;">內文 / 14px / 400</div>
      <div class="sg-type-sample" style="font-size: 13px; font-weight: 400;">次要/說明 / 13px / 400</div>
    </section>

    <section>
      <h2 class="sg-h2">玻璃（§5）</h2>
      <div class="sg-glass-stage">
        <div class="glass-panel sg-glass-demo">glass-panel：浮動面板、彈窗</div>
        <div class="glass-menu sg-glass-demo">glass-menu：下拉選單</div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">載入骨架（§6.2）</h2>
      <div class="sg-skeleton-demo">
        <div class="skeleton-line" style="width: 40%" />
        <div class="skeleton-line" style="width: 70%" />
        <div class="skeleton-line" style="width: 55%" />
      </div>
    </section>

    <section>
      <h2 class="sg-h2">資料表格（§7.4）</h2>
      <TableShell>
        <table class="ds-table">
          <thead>
            <tr><th>欄位</th><th>型別</th><th>狀態</th></tr>
          </thead>
          <tbody>
            <tr>
              <td class="ds-identifier">age</td>
              <td class="ds-identifier">int64</td>
              <td><StatusBadge status="success">已對應</StatusBadge></td>
            </tr>
            <tr>
              <td class="ds-identifier">bmi_score</td>
              <td class="ds-identifier">float64</td>
              <td><StatusBadge status="warning">待確認</StatusBadge></td>
            </tr>
          </tbody>
        </table>
      </TableShell>
    </section>

    <section>
      <h2 class="sg-h2">內容寬度</h2>
      <div class="sg-width-demo" style="max-width: var(--content-measure)">content-measure 760px</div>
      <div class="sg-width-demo" style="max-width: var(--content-max-width)">content-max-width 1280px</div>
      <div class="sg-width-demo" style="max-width: var(--content-max-width-wide)">content-max-width-wide 1680px</div>
    </section>
  </div>
</template>

<script lang="ts" setup>
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import TableShell from '@/components/ui/TableShell.vue'

  interface Swatch { name: string, varRef: string }

  const swatches: Swatch[] = [
    { name: 'ink（品牌藏青）', varRef: 'var(--color-ink)' },
    { name: 'ink-strong', varRef: 'var(--color-ink-strong)' },
    { name: 'ink-soft', varRef: 'var(--color-ink-soft)' },
    { name: 'text', varRef: 'var(--color-text)' },
    { name: 'surface', varRef: 'var(--color-surface)' },
    { name: 'surface-alt', varRef: 'var(--color-surface-alt)' },
    { name: 'page', varRef: 'var(--color-page)' },
    { name: 'border', varRef: 'var(--color-border)' },
    { name: 'border-strong', varRef: 'var(--color-border-strong)' },
    { name: 'success', varRef: 'var(--color-success)' },
    { name: 'success-bg', varRef: 'var(--color-success-bg)' },
    { name: 'warning', varRef: 'var(--color-warning)' },
    { name: 'warning-bg', varRef: 'var(--color-warning-bg)' },
    { name: 'error（danger）', varRef: 'var(--color-error)' },
    { name: 'error-bg', varRef: 'var(--color-error-bg)' },
  ]

  // §2.3：依 pipeline 角色分五類，全部避開綠/琥珀/紅（那三色留給節點外圈的執行狀態）
  const nodeCategories = [
    { name: 'source 資料來源', varRef: 'var(--color-node-source)', nodes: 'File' },
    { name: 'inspect 檢視', varRef: 'var(--color-node-inspect)', nodes: 'Data Table、Distribution' },
    { name: 'transform 轉換', varRef: 'var(--color-node-transform)', nodes: 'Preprocessor、Feature Engineering' },
    { name: 'model 建模', varRef: 'var(--color-node-model)', nodes: 'Settings、Models' },
    { name: 'evaluate 評估', varRef: 'var(--color-node-evaluate)', nodes: 'Test & Score、Feature Importance、Confusion Matrix、Compute CI' },
  ]
</script>

<style scoped>
.style-guide {
  max-width: var(--content-max-width-wide);
  margin: 0 auto;
  padding: 32px;
}

.sg-h1 {
  font-size: 22px;
  font-weight: 500;
  color: var(--color-text);
}

.sg-note {
  font-size: 13px;
  color: var(--color-ink-soft);
  margin-bottom: 24px;
}

.sg-h2 {
  font-size: 18px;
  font-weight: 500;
  color: var(--color-text);
  margin: 32px 0 12px;
}

.sg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-start;
}

.sg-swatch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

.sg-swatch-color {
  height: 56px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
}

.sg-swatch-label {
  font-size: 13px;
  color: var(--color-text);
  margin-top: 6px;
}

.sg-swatch-var {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-ink-soft);
}

.sg-node-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.sg-node {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sg-node-dot {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  color: #fff;
}

.sg-radius-box {
  width: 96px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-alt);
  border: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-ink-soft);
}

.sg-shadow-box {
  width: 160px;
  height: 96px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  font-size: 12px;
  color: var(--color-ink-soft);
}

/* 玻璃要有東西透出來才看得出效果，示範區塊底下先鋪一塊彩色漸層 */
.sg-glass-stage {
  display: flex;
  gap: 16px;
  padding: 24px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(220px circle at 20% 30%, rgba(90, 130, 190, 0.55), transparent 60%),
    radial-gradient(200px circle at 80% 70%, rgba(196, 150, 130, 0.35), transparent 60%),
    linear-gradient(175deg, #eef2f5 0%, #dce3e9 100%);
}

.sg-glass-demo {
  padding: 16px 20px;
  font-size: 14px;
  color: var(--color-text);
}

.sg-skeleton-demo {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 420px;
}

.sg-type-sample {
  margin-bottom: 8px;
  color: var(--color-text);
}

.sg-width-demo {
  background: var(--color-surface-alt);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  margin-bottom: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-ink-soft);
}
</style>
