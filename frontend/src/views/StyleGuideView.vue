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
          <div class="sg-swatch-hex">{{ swatch.hex }}</div>
        </div>
      </div>
    </section>

    <section>
      <h2 class="sg-h2">Workflow 節點分類色（§2.3）</h2>
      <p class="sg-note">
        依 pipeline 角色分五類，比照 Orange Data Mining 的六類配色大致順序（橘/藍/紫/綠/紅）指派，
        低飽和大地色系。節點是圓形淺底 + 深色 icon + 細邊框，選中/完成用綠色勾勾徽章疊在右下角。
      </p>
      <div class="sg-node-grid">
        <div v-for="cat in nodeCategories" :key="cat.name" class="sg-node">
          <div class="sg-node-dot sg-node-dot--bordered" :style="{ background: cat.varRef }">
            <v-icon color="var(--color-ink-strong)" icon="mdi-circle-outline" size="24" />
            <span class="sg-node-badge">
              <v-icon icon="mdi-check" size="13" />
            </span>
          </div>
          <div>
            <div class="sg-swatch-label">{{ cat.name }}</div>
            <div class="sg-swatch-var">{{ cat.hex }}</div>
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
      <h2 class="sg-h2">按鈕（§7.1 四變體 + §6.2 共用 hover）</h2>
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
      <h2 class="sg-h2">下拉選單（§5.3）</h2>
      <div class="sg-on-card">
        <CustomSelect
          v-model="selectValue"
          aria-label="範例下拉選單"
          :options="selectOptions"
          placeholder="選擇對應欄位"
        />
      </div>
    </section>

    <section>
      <h2 class="sg-h2">對話氣泡（§2.2）</h2>
      <div class="glass-panel sg-chat">
        <div class="sg-bubble sg-bubble--assistant">
          我可以協助調整左側的欄位對應，請直接以文字說明您的需求。
        </div>
        <div class="sg-bubble sg-bubble--user">年齡對應到 pt_age</div>
        <div class="sg-bubble sg-bubble--assistant">好的，已將「年齡」對應到 pt_age。</div>
        <div class="sg-bubble sg-bubble--assistant sg-bubble--muted">思考中…</div>
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
  import { ref } from 'vue'
  import CustomSelect from '@/components/common/CustomSelect.vue'
  import AppButton from '@/components/ui/AppButton.vue'
  import PageHeader from '@/components/ui/PageHeader.vue'
  import StatusBadge from '@/components/ui/StatusBadge.vue'
  import TableShell from '@/components/ui/TableShell.vue'

  const selectValue = ref('')
  const selectOptions = [
    { value: 'pt_age', label: 'pt_age', hint: '整數 · 18–92' },
    { value: 'braden_total', label: 'braden_total', hint: '整數 · 6–23' },
    { value: 'bmi_score', label: 'bmi_score', hint: '浮點數' },
    { value: 'gender', label: 'gender', hint: '類別', disabled: true },
  ]

  // hex 值抄自 vuetify.ts 的 light theme colors，兩邊改動時要一起同步
  interface Swatch { name: string, varRef: string, hex: string }

  const swatches: Swatch[] = [
    { name: 'ink（品牌藏青）', varRef: 'var(--color-ink)', hex: '#1A3159' },
    { name: 'ink-strong', varRef: 'var(--color-ink-strong)', hex: '#12244A' },
    { name: 'ink-soft', varRef: 'var(--color-ink-soft)', hex: '#626B7E' },
    { name: 'text', varRef: 'var(--color-text)', hex: '#1C2130' },
    { name: 'surface', varRef: 'var(--color-surface)', hex: '#FFFFFF' },
    { name: 'surface-alt', varRef: 'var(--color-surface-alt)', hex: '#F1F4F8' },
    { name: 'page', varRef: 'var(--color-page)', hex: '#E4E9ED' },
    { name: 'border', varRef: 'var(--color-border)', hex: '#E4E6E8' },
    { name: 'border-strong', varRef: 'var(--color-border-strong)', hex: '#D3D8DC' },
    { name: 'success', varRef: 'var(--color-success)', hex: '#3B9A7F' },
    { name: 'success-bg', varRef: 'var(--color-success-bg)', hex: '#DCEAE5' },
    { name: 'warning', varRef: 'var(--color-warning)', hex: '#BC8836' },
    { name: 'warning-bg', varRef: 'var(--color-warning-bg)', hex: '#EFE7D7' },
    { name: 'error（danger）', varRef: 'var(--color-error)', hex: '#D7445C' },
    { name: 'error-bg', varRef: 'var(--color-error-bg)', hex: '#F2DEE2' },
    // 只能當圖形填色，不能當文字（見 utils/scoreColor.ts）
    { name: 'score-low（評分填色）', varRef: 'var(--color-score-low)', hex: '#FFD000' },
  ]

  // §2.3：依 pipeline 角色分五類，比照 Orange 的六類配色大致順序（橘/藍/紫/綠/紅）指派
  const nodeCategories = [
    { name: 'source 資料來源', varRef: 'var(--color-node-source)', hex: '#D2A596', nodes: 'File、Data Table' },
    { name: 'transform 轉換', varRef: 'var(--color-node-transform)', hex: '#8EB8D1', nodes: 'Preprocessor、Feature Engineering' },
    { name: 'visualize 視覺化', varRef: 'var(--color-node-visualize)', hex: '#A9AED6', nodes: 'Distribution' },
    { name: 'model 建模', varRef: 'var(--color-node-model)', hex: '#85BDBC', nodes: 'Settings、Models' },
    { name: 'evaluate 評估', varRef: 'var(--color-node-evaluate)', hex: '#CFA3B6', nodes: 'Test & Score、Feature Importance、Confusion Matrix、Compute CI' },
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

.sg-swatch-var,
.sg-swatch-hex {
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
  position: relative;
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  color: #fff;
}

/* 淺色分類色跟頁面底色對比不足時的保險，不管色票怎麼調都通用 */
.sg-node-dot--bordered {
  border: 1.5px solid rgba(18, 36, 74, 0.16);
}

/* outline 風格：白底＋綠框＋綠勾，不管節點本身是什麼色都能跟它分開，見 IconNode.vue */
.sg-node-badge {
  position: absolute;
  right: -2px;
  bottom: -2px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 19px;
  height: 19px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1.5px solid var(--color-success);
  color: var(--color-success);
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

/* 下拉選單實際都開在白卡上，要在同樣的背景下看才準 */
.sg-on-card {
  max-width: 320px;
  padding: 20px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.sg-chat {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 420px;
  padding: 16px;
}

.sg-bubble {
  max-width: 88%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  line-height: 1.55;
}

.sg-bubble--user {
  align-self: flex-end;
  background: var(--color-chat-user);
  color: var(--color-inverted);
}

.sg-bubble--assistant {
  align-self: flex-start;
  background: var(--color-chat-system);
  box-shadow:
    0 1px 2px rgba(14, 30, 66, 0.1),
    0 6px 16px rgba(14, 30, 66, 0.07);
  color: var(--color-text);
}

.sg-bubble--muted {
  color: color-mix(in srgb, var(--color-ink-soft) 70%, var(--color-ink-strong));
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
