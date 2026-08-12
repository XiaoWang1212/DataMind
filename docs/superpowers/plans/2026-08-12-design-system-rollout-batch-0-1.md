# 設計系統全站套用 Batch 0–1 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立設計系統共用元件層，並把 Hub、認證、介紹頁全部套上 `docs/DESIGN_SYSTEM.md` 的規範。

**Architecture:** Batch 0 在 `components/ui/` 建五個原語（AppButton、StatusBadge、PageHeader、TableShell、glass class），全部先在 `StyleGuideView` 驗證；Batch 1 拿這些原語逐檔改寫 Hub 十頁、認證四頁、介紹頁，每檔把硬寫 hex 換成語意 token、字重收斂到 400/500、圖示換 outline、浮動層套玻璃。頁面的資訊架構與欄位配置一律維持現狀。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript、Vuetify 4（`utilities: false`）、Tailwind 4（CSS-first `@theme`）、CSS layers、`@mdi/font`。

依據 spec：`docs/superpowers/specs/2026-08-11-design-system-rollout-design.md`
視覺規範：`docs/DESIGN_SYSTEM.md`

Batch 2（Paper）與 Batch 3（Workflow）另行規劃，等這份落地、共用層定型後再寫。

## Global Constraints

- **色彩、圓角一律引用 token，不在元件裡硬寫 hex。** 唯一例外是 §5 玻璃效果的 `rgba(255,255,255,x)` 半透明 tint 與受光邊，那是效果本身的一部分。
- **token 命名以 `styles/tailwind.css` 實際存在的為準。** 設計文件寫 `--color-danger`，程式碼裡是 `--color-error` / `--color-error-bg`，沿用後者。
- **字重只用 400 與 500**，全面清掉 600 / 700 / `bold`。
- **圖示一律 outline 版**（`mdi-account-outline`）；`mdi-plus`、`mdi-close`、`mdi-chevron-*`、`mdi-arrow-*`、`mdi-check`、`mdi-magnify` 這類本身沒有實心／線框變體的純符號維持原樣。
- **同語意全站只用一個圖示。** 本批建立對照表，Task 21 收尾核對。
- **不重設版面。** 資訊架構、欄位配置、功能行為維持現狀，只在明顯違反 §8.2 寬度上限或 §7 元件規格時順手修。
- **每個 task 的 commit 步驟需先取得 user 同意**（專案規約：未確認前不 commit）。
- **驗證指令**（沒有自動化測試，這兩個就是門檻）：
  - `cd frontend && npm run build`（含 `vue-tsc` 型別檢查）
  - `cd frontend && npm run lint`
- **瀏覽器驗證**：`docker compose up -d` 後開 `http://localhost:5173`，設計系統原語看 `/style-guide`。

### 全批共用的 hex → token 對照

盤點各檔後歸納出來的映射。改檔時依「這個色在該處的角色」選，不要只看色碼像不像：

| 現有 hex | 換成 |
|---|---|
| `#ffffff` / `#fff` | `var(--color-surface)` |
| `#f0f0f0` `#f0f1f3` `#f3f3f3` `#f5f5f5` `#f9fafb` `#f3f4f6` `#f7f7f9` | 當背景 → `var(--color-surface-alt)`；當分隔線 → `var(--color-border)` |
| `#e8e8e8` `#e5e7eb` `#e2e4ea` | `var(--color-border)` |
| `#d1d5db` `#cbd5e1` `#c4c9d4` `#b7c2e6` | `var(--color-border-strong)` |
| `#9ca3af` `#94a3b8` | `var(--color-ink-soft)` |
| `#374151` | `var(--color-text)` |
| `#4f46e5` `#3730a3` `#5b21b6` `#2347c5` `#005dff` | `var(--color-ink)`；hover／按下用 `var(--color-ink-strong)` |
| `#e0e7ff` `#dbeafe` `#eef1ff` `#c7d2fe` `#a5b4fc` `#93c5fd` `#fafbff` `#ede9fe` | `color-mix(in oklab, var(--color-ink) N%, white)`，N 依原本深淺取 6/10/16/24 |
| `#16a34a` `#15803d` | 圓點／圖示 `var(--color-success)`；文字 `var(--color-success-text)` |
| `#dcfce7` `#bbf7d0` `#f0fdf4` | `var(--color-success-bg)` |
| `#d97706` `#f59e0b` `#b45309` | 圓點／圖示 `var(--color-warning)`；文字 `var(--color-warning-text)` |
| `#fef3c7` `#fef9c3` `#fffbeb` `#fde68a` | `var(--color-warning-bg)` |
| `#ef4444` `#b91c1c` | 圓點／圖示 `var(--color-error)`；文字 `var(--color-error-text)` |
| `#fecaca` `#fef2f2` `#fee2e2` `#ffd7d7` | `var(--color-error-bg)` |

`--color-success-text` / `--color-warning-text` / `--color-error-text` 目前不存在，Task 2 會補上。

---

## Batch 0：共用層

### Task 1: 邊緣反光 composable 與 AppButton

**Files:**
- Create: `frontend/src/composables/useSpecularHover.ts`
- Create: `frontend/src/components/ui/AppButton.vue`
- Modify: `frontend/src/views/StyleGuideView.vue`

**Interfaces:**
- Produces: `useSpecularHover(target: Ref<HTMLElement | null>): void` — 在元素上維護 `--mx` / `--my` / `--glow` 三個 CSS 變數。
- Produces: `AppButton` props — `variant?: 'primary' | 'secondary' | 'ghost' | 'danger'`（預設 `'primary'`）、`type?: 'button' | 'submit' | 'reset'`（預設 `'button'`）、`disabled?: boolean`、`loading?: boolean`、`iconOnly?: boolean`。預設 slot 放內容。

- [ ] **Step 1: 建立 `useSpecularHover.ts`**

全站只掛一個 `pointermove` listener，用 rAF 節流後更新所有註冊的元素 — 六十幾個按鈕各掛一個 listener 會拖慢滑鼠移動。

```ts
import { onBeforeUnmount, onMounted, type Ref } from 'vue'

// 滑鼠距離按鈕多遠開始亮。貼到邊框時最亮，超過這個距離完全不亮
const PROXIMITY = 90

// 模組層級的註冊表：所有 AppButton 共用一個 listener
const tracked = new Set<HTMLElement>()
let listening = false
let frame = 0
let pointerX = 0
let pointerY = 0

function update (): void {
  frame = 0
  for (const el of tracked) {
    const rect = el.getBoundingClientRect()
    // 滑鼠到矩形的距離，在框內時為 0
    const dx = Math.max(rect.left - pointerX, 0, pointerX - rect.right)
    const dy = Math.max(rect.top - pointerY, 0, pointerY - rect.bottom)
    const distance = Math.hypot(dx, dy)
    const glow = distance > PROXIMITY ? 0 : 1 - distance / PROXIMITY
    el.style.setProperty('--mx', `${pointerX - rect.left}px`)
    el.style.setProperty('--my', `${pointerY - rect.top}px`)
    el.style.setProperty('--glow', glow.toFixed(3))
  }
}

function onPointerMove (event: PointerEvent): void {
  pointerX = event.clientX
  pointerY = event.clientY
  if (frame === 0) {
    frame = requestAnimationFrame(update)
  }
}

// 觸控裝置點一下就會觸發 hover，反光會亮在手指底下不滅；直接不註冊
function supportsHover (): boolean {
  return window.matchMedia('(hover: hover) and (pointer: fine)').matches
}

export function useSpecularHover (target: Ref<HTMLElement | null>): void {
  onMounted(() => {
    if (!target.value || !supportsHover()) {
      return
    }
    tracked.add(target.value)
    if (!listening) {
      window.addEventListener('pointermove', onPointerMove, { passive: true })
      listening = true
    }
  })

  onBeforeUnmount(() => {
    if (target.value) {
      tracked.delete(target.value)
    }
    if (tracked.size === 0 && listening) {
      window.removeEventListener('pointermove', onPointerMove)
      listening = false
      if (frame) {
        cancelAnimationFrame(frame)
        frame = 0
      }
    }
  })
}
```

- [ ] **Step 2: 建立 `components/ui/AppButton.vue`**

反光只走邊框：用 `padding: 1px` + `mask-composite: exclude` 挖掉中間，讓漸層只留在 1px 的邊上。平常 `--glow: 0`，邊框完全透明無殘留（§6.2）。

```vue
<template>
  <button
    ref="root"
    class="app-btn"
    :class="[`app-btn--${variant}`, { 'app-btn--icon-only': iconOnly }]"
    :disabled="disabled || loading"
    :type="type"
  >
    <span v-if="loading" aria-hidden="true" class="app-btn-spinner" />
    <span class="app-btn-body" :class="{ 'app-btn-body--loading': loading }">
      <slot />
    </span>
  </button>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { useSpecularHover } from '@/composables/useSpecularHover'

  withDefaults(defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    type?: 'button' | 'submit' | 'reset'
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(), {
    variant: 'primary',
    type: 'button',
    disabled: false,
    loading: false,
    iconOnly: false,
  })

  const root = ref<HTMLElement | null>(null)
  useSpecularHover(root)
</script>

<style scoped>
  .app-btn {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px 18px;
    border: none;
    border-radius: 999px;
    font-family: inherit;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.2;
    cursor: pointer;
    transition: background-color var(--dur-fast) var(--ease-out),
      color var(--dur-fast) var(--ease-out),
      transform var(--dur-fast) var(--ease-out);
  }

  .app-btn:active:not(:disabled) {
    transform: scale(0.96);
  }

  .app-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .app-btn--icon-only {
    padding: 8px;
    width: 36px;
    height: 36px;
  }

  /* 反光只顯示在 1px 邊框上：外層漸層減掉 content-box，剩下 padding 那圈 */
  .app-btn::after {
    content: '';
    position: absolute;
    inset: 0;
    padding: 1px;
    border-radius: inherit;
    background: radial-gradient(
      110px circle at var(--mx, 50%) var(--my, 50%),
      var(--specular-color),
      transparent 60%
    );
    opacity: var(--glow, 0);
    mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    mask-composite: exclude;
    -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    pointer-events: none;
    /* 刻意不加 transition：--glow 每幀都在變，再疊轉場會讓反光拖在滑鼠後面。
       proximity 本身就是平滑漸變，夠了 */
  }

  /* 深底用白光、淺底用藏青光，否則反光在自己的底色上看不見 */
  .app-btn--primary {
    background: var(--color-ink);
    color: #fff;
    --specular-color: rgba(255, 255, 255, 0.9);
  }

  .app-btn--secondary {
    background: var(--color-surface);
    color: var(--color-ink);
    box-shadow: inset 0 0 0 1px var(--color-border);
    --specular-color: color-mix(in oklab, var(--color-ink) 70%, transparent);
  }

  .app-btn--ghost {
    background: transparent;
    color: var(--color-ink-soft);
    --specular-color: color-mix(in oklab, var(--color-ink) 55%, transparent);
  }

  .app-btn--danger {
    background: var(--color-error-bg);
    color: var(--color-error-text);
    --specular-color: color-mix(in oklab, var(--color-error) 70%, transparent);
  }

  /* 觸控裝置點一下會觸發 hover 並卡在 hover 底色，所以 hover 態一律 gate 起來 */
  @media (hover: hover) and (pointer: fine) {
    .app-btn--primary:hover:not(:disabled) {
      background: var(--color-ink-strong);
    }

    .app-btn--ghost:hover:not(:disabled) {
      color: var(--color-ink);
    }
  }

  /* loading 時內容留在原位只是隱形，避免按鈕寬度跳動 */
  .app-btn-body--loading {
    visibility: hidden;
  }

  .app-btn-spinner {
    position: absolute;
    width: 15px;
    height: 15px;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: app-btn-spin 0.7s linear infinite;
  }

  @keyframes app-btn-spin {
    to { transform: rotate(360deg); }
  }
</style>
```

- [ ] **Step 3: 在 StyleGuideView 用 AppButton 取代手寫的 sg-btn**

把 `views/StyleGuideView.vue` 中「按鈕」那一節的四顆 `<button class="sg-btn …">` 換成 AppButton，並補上 loading、disabled、icon-only 三種狀態，順手刪掉 `.sg-btn*` 的 scoped CSS 與該節標題裡「尚未套邊緣反光 hover」的字樣：

```vue
<section>
  <h2 class="sg-h2">按鈕（§7.1 四變體 + §6.2 邊緣反光 hover）</h2>
  <div class="sg-row">
    <AppButton variant="primary">primary</AppButton>
    <AppButton variant="secondary">secondary</AppButton>
    <AppButton variant="ghost">ghost</AppButton>
    <AppButton variant="danger">danger</AppButton>
  </div>
  <div class="sg-row">
    <AppButton loading variant="primary">loading</AppButton>
    <AppButton disabled variant="primary">disabled</AppButton>
    <AppButton icon-only variant="secondary">
      <v-icon icon="mdi-plus" size="18" />
    </AppButton>
  </div>
</section>
```

- [ ] **Step 4: 型別與 lint 通過**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 5: 瀏覽器驗收**

開 `http://localhost:5173/style-guide`，確認：
1. 滑鼠靠近按鈕（還沒進到按鈕上）反光就開始亮，離開後**邊框完全消失、沒有殘留一圈色**。
2. 反光跟著滑鼠沿邊框跑，按鈕表面底色不變。
3. 按下去有 `scale(0.96)` 的壓下感。
4. loading 那顆的寬度跟 primary 一樣，沒有因為換成 spinner 而縮。
5. 開系統的「減少動態效果」後重載，反光與縮放停止（`main.scss` 的 `prefers-reduced-motion` 已涵蓋）。

- [ ] **Step 6: Commit（需 user 同意）**

```bash
git add frontend/src/composables/useSpecularHover.ts frontend/src/components/ui/AppButton.vue frontend/src/views/StyleGuideView.vue
git commit -m "feat(ui): add AppButton with specular border hover"
```

---

### Task 2: 狀態文字色 token 與 StatusBadge

**Files:**
- Modify: `frontend/src/plugins/vuetify.ts`
- Modify: `frontend/src/styles/tailwind.css`
- Create: `frontend/src/components/ui/StatusBadge.vue`
- Modify: `frontend/src/views/StyleGuideView.vue`

**Interfaces:**
- Produces: token `--color-success-text` `#176B39`、`--color-warning-text` `#8F560A`、`--color-error-text` `#B8342A`。
- Produces: `StatusBadge` props — `status: 'success' | 'warning' | 'danger' | 'neutral'`、`variant?: 'dot' | 'badge'`（預設 `'badge'`）。預設 slot 放文字。

`neutral` 不在 `docs/DESIGN_SYSTEM.md` §7.5 的三態裡，是為了 `MappingTable` 的 `SKIPPED`（已略過）而加 — 它是「使用者主動跳過」，既不是成功也不是警示，用狀態色會誤導語意。Task 21 會把這一態補回設計文件 §7.5。

- [ ] **Step 1: 在 vuetify light theme 補三個文字色**

`plugins/vuetify.ts` 的 `colors` 內，在既有 `'success-bg'` 那組附近加入：

```ts
// docs/DESIGN_SYSTEM.md §2.2：徽章文字疊在對應的 -bg 淺底上時，圓點色的對比不足 4.5:1，
// 所以文字另用更深一階的值
'success-text': '#176B39',
'warning-text': '#8F560A',
'error-text': '#B8342A',
```

- [ ] **Step 2: 在 tailwind 橋接層補對應變數**

`styles/tailwind.css` 的 `@theme static` 內，接在 `--color-error-bg` 之後：

```css
  --color-success-text: rgb(var(--v-theme-success-text));
  --color-warning-text: rgb(var(--v-theme-warning-text));
  --color-error-text: rgb(var(--v-theme-error-text));
```

- [ ] **Step 3: 建立 `components/ui/StatusBadge.vue`**

```vue
<template>
  <span class="status-badge" :class="[`status-badge--${status}`, `status-badge--${variant}`]">
    <span v-if="variant === 'dot'" aria-hidden="true" class="status-badge-dot" />
    <slot />
  </span>
</template>

<script setup lang="ts">
  withDefaults(defineProps<{
    status: 'success' | 'warning' | 'danger' | 'neutral'
    variant?: 'dot' | 'badge'
  }>(), {
    variant: 'badge',
  })
</script>

<style scoped>
  .status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    line-height: 1.4;
    white-space: nowrap;
  }

  .status-badge--badge {
    padding: 3px 10px;
    border-radius: 999px;
  }

  .status-badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* dot 版沒有淺色底襯，文字直接在白底上，用同一組深色文字值即可 */
  .status-badge--success { color: var(--color-success-text); }
  .status-badge--warning { color: var(--color-warning-text); }
  .status-badge--danger { color: var(--color-error-text); }
  .status-badge--neutral { color: var(--color-ink-soft); }

  .status-badge--success .status-badge-dot { background: var(--color-success); }
  .status-badge--warning .status-badge-dot { background: var(--color-warning); }
  .status-badge--danger .status-badge-dot { background: var(--color-error); }
  .status-badge--neutral .status-badge-dot { background: var(--color-ink-soft); }

  .status-badge--badge.status-badge--success { background: var(--color-success-bg); }
  .status-badge--badge.status-badge--warning { background: var(--color-warning-bg); }
  .status-badge--badge.status-badge--danger { background: var(--color-error-bg); }
  .status-badge--badge.status-badge--neutral { background: var(--color-surface-alt); }
</style>
```

- [ ] **Step 4: StyleGuideView 換掉手寫徽章**

把「狀態徽章」那節的 `<span class="sg-badge …">` 換成 StatusBadge，兩種 variant 各列一排，並刪掉 `.sg-badge*` 的 scoped CSS：

```vue
<section>
  <h2 class="sg-h2">狀態顯示（§7.5）</h2>
  <div class="sg-row">
    <StatusBadge status="success">已對應</StatusBadge>
    <StatusBadge status="warning">待確認</StatusBadge>
    <StatusBadge status="danger">未對應</StatusBadge>
    <StatusBadge status="neutral">已略過</StatusBadge>
  </div>
  <div class="sg-row">
    <StatusBadge status="success" variant="dot">已對應</StatusBadge>
    <StatusBadge status="warning" variant="dot">待確認</StatusBadge>
    <StatusBadge status="danger" variant="dot">未對應</StatusBadge>
    <StatusBadge status="neutral" variant="dot">已略過</StatusBadge>
  </div>
</section>
```

- [ ] **Step 5: 型別與 lint 通過**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 6: 瀏覽器驗收**

在 `/style-guide` 用瀏覽器 DevTools 的對比檢查器量三個 badge 的文字對底色，都要 ≥ 4.5:1。圓點色與文字色刻意不同值，確認圓點看起來仍是飽和的實色。

- [ ] **Step 7: Commit（需 user 同意）**

```bash
git add frontend/src/plugins/vuetify.ts frontend/src/styles/tailwind.css frontend/src/components/ui/StatusBadge.vue frontend/src/views/StyleGuideView.vue
git commit -m "feat(ui): add StatusBadge and status text color tokens"
```

---

### Task 3: PageHeader

**Files:**
- Create: `frontend/src/components/ui/PageHeader.vue`
- Modify: `frontend/src/views/StyleGuideView.vue`

**Interfaces:**
- Consumes: 無。
- Produces: `PageHeader` props — `title: string`、`subtitle?: string`；具名 slot `actions`（右側動作區）、`back`（標題左側的返回鈕，Hub 詳情頁會用）。

- [ ] **Step 1: 建立 `components/ui/PageHeader.vue`**

```vue
<template>
  <header class="page-header">
    <div class="page-header-lead">
      <slot name="back" />
      <div>
        <h1 class="page-header-title">{{ title }}</h1>
        <p v-if="subtitle" class="page-header-sub">{{ subtitle }}</p>
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header-actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
  defineProps<{
    title: string
    subtitle?: string
  }>()
</script>

<style scoped>
  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 1.5rem;
  }

  .page-header-lead {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    min-width: 0;
  }

  .page-header-title {
    margin: 0 0 4px;
    font-size: 22px;
    font-weight: 500;
    color: var(--color-text);
  }

  .page-header-sub {
    margin: 0;
    font-size: 13px;
    color: var(--color-ink-soft);
  }

  .page-header-actions {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
</style>
```

- [ ] **Step 2: StyleGuideView 加一節**

```vue
<section>
  <h2 class="sg-h2">頁首（§3 字級階層）</h2>
  <PageHeader subtitle="副標說明文字，13px" title="頁面標題">
    <template #actions>
      <AppButton variant="secondary">次要動作</AppButton>
      <AppButton variant="primary">主要動作</AppButton>
    </template>
  </PageHeader>
</section>
```

- [ ] **Step 3: 型別與 lint 通過**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 4: 瀏覽器驗收**

`/style-guide` 上確認標題 22px/500、副標 13px、動作區靠右且與標題頂端對齊；把視窗縮到 600px 寬，動作區不會把標題擠到換行破版。

- [ ] **Step 5: Commit（需 user 同意）**

```bash
git add frontend/src/components/ui/PageHeader.vue frontend/src/views/StyleGuideView.vue
git commit -m "feat(ui): add PageHeader component"
```

---

### Task 4: TableShell 與 .ds-table

**Files:**
- Create: `frontend/src/components/ui/TableShell.vue`
- Create: `frontend/src/styles/ds-table.css`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/views/StyleGuideView.vue`

**Interfaces:**
- Produces: `TableShell` — 無 props，預設 slot 放 `<table class="ds-table">`。
- Produces: 全域 class `.ds-table`（§7.4 表頭、儲存格、row hover、identifier mono）。

`.ds-table` 放在 `@layer vuetify-final`（`styles/layers.css` 宣告的最後一層），確保套在 Vuetify 元件內的表格時不會被 vuetify-components 蓋掉。

- [ ] **Step 1: 建立 `components/ui/TableShell.vue`**

```vue
<template>
  <div class="table-shell">
    <slot />
  </div>
</template>

<style scoped>
  /* overflow: hidden 讓表格四角吃到容器圓角；欄多時內部橫向捲動 */
  .table-shell {
    overflow: hidden auto;
    border-radius: var(--radius-md);
    background: var(--color-surface);
    box-shadow: var(--shadow-card);
  }
</style>
```

- [ ] **Step 2: 建立 `styles/ds-table.css`**

```css
@layer vuetify-final {
  .ds-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
    color: var(--color-text);
  }

  .ds-table thead th {
    padding: 10px 14px;
    background: var(--color-surface-alt);
    color: var(--color-ink-soft);
    font-size: 12px;
    font-weight: 500;
    text-align: left;
    white-space: nowrap;
  }

  .ds-table tbody td {
    padding: 12px 14px;
    border-top: 1px solid var(--color-border);
  }

  .ds-table tbody tr {
    transition: background-color var(--dur-fast) var(--ease-out);
  }

  .ds-table tbody tr:hover {
    background: var(--color-surface-alt);
  }

  /* 欄位名、type、class 等 identifier 用等寬字（§3） */
  .ds-table .ds-identifier {
    font-family: var(--font-mono);
  }
}
```

- [ ] **Step 3: 在 `main.ts` 引入**

在 `import './styles/main.scss'` 之後加一行：

```ts
import './styles/ds-table.css'
```

- [ ] **Step 4: StyleGuideView 加一節**

```vue
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
```

- [ ] **Step 5: 型別與 lint 通過**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 6: 瀏覽器驗收**

`/style-guide` 上確認：表頭是 `--color-surface-alt` 底、12px、灰字；列 hover 換底色且過場 120ms；表格四角圓角完整沒有被內容切出方角；`age`、`int64` 是等寬字。

- [ ] **Step 7: Commit（需 user 同意）**

```bash
git add frontend/src/components/ui/TableShell.vue frontend/src/styles/ds-table.css frontend/src/main.ts frontend/src/views/StyleGuideView.vue
git commit -m "feat(ui): add TableShell and ds-table styles"
```

---

### Task 5: 玻璃 class 與進場動畫 utility

**Files:**
- Create: `frontend/src/styles/glass.css`
- Create: `frontend/src/styles/motion.css`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/views/StyleGuideView.vue`

**Interfaces:**
- Produces: `.glass-panel`（浮動面板、彈窗）、`.glass-menu`（下拉選單）。兩者都自帶 `-webkit-` 前綴與 `@supports` fallback。
- Produces: `.enter-rise`（§6.2 進場：輕微上移淡入）、`.enter-stagger > *`（子元素依序延遲 40ms，最多五階）、`.skeleton-line`（§6.2 骨架屏）。做成全域 utility 而不是各檔 scoped keyframes — scoped CSS 的 `@keyframes` 不能跨檔共用，Batch 1 有五個檔要用到這幾組動畫。

- [ ] **Step 1: 建立 `styles/glass.css`**

模糊值取 §5.2 的 14px（區間 10–16 的中間），tint 取 0.62 讓文字對比夠。不支援 `backdrop-filter` 時退回接近不透明的純色底。

```css
@layer vuetify-final {
  .glass-panel,
  .glass-menu {
    background: rgba(255, 255, 255, 0.62);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    /* 上緣較亮模擬受光邊 */
    border-top: 1px solid rgba(255, 255, 255, 0.85);
    border-right: 1px solid rgba(255, 255, 255, 0.5);
    border-bottom: 1px solid rgba(255, 255, 255, 0.5);
    border-left: 1px solid rgba(255, 255, 255, 0.5);
  }

  .glass-panel {
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-float);
  }

  .glass-menu {
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-float);
  }

  @supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
    .glass-panel,
    .glass-menu {
      background: rgba(255, 255, 255, 0.96);
    }
  }
}
```

- [ ] **Step 2: 建立 `styles/motion.css`**

```css
@layer vuetify-final {
  .enter-rise {
    animation: enter-rise var(--dur-slow) var(--ease-out) both;
  }

  /* 列表依序進場。總長壓在 250ms 內，超過五個就不再往後延，避免拖沓。
     只用在初次載入就固定下來的列表 — 會因為篩選/排序重新渲染的列表用這個，
     每次操作整串都會重跑一次動畫 */
  .enter-stagger > * {
    animation: enter-rise var(--dur-slow) var(--ease-out) both;
  }

  .enter-stagger > *:nth-child(2) { animation-delay: 40ms; }
  .enter-stagger > *:nth-child(3) { animation-delay: 80ms; }
  .enter-stagger > *:nth-child(4) { animation-delay: 120ms; }
  .enter-stagger > *:nth-child(n + 5) { animation-delay: 160ms; }

  @keyframes enter-rise {
    from { opacity: 0; transform: translateY(7px); }
    to   { opacity: 1; transform: none; }
  }

  /* §6.2：載入用骨架屏而非空白轉圈，維持版面穩定 */
  .skeleton-line {
    height: 1em;
    border-radius: var(--radius-sm);
    background: linear-gradient(
      90deg,
      var(--color-surface-alt) 0%,
      color-mix(in oklab, var(--color-surface-alt) 60%, white) 50%,
      var(--color-surface-alt) 100%
    );
    background-size: 200% 100%;
    /* 等速掃光用 linear：ease 會在兩端頓一下，看起來像卡住。掃快一點也讓載入感覺比較短 */
    animation: skeleton-sweep 1.2s linear infinite;
  }

  @keyframes skeleton-sweep {
    from { background-position: 200% 0; }
    to   { background-position: -200% 0; }
  }
}
```

- [ ] **Step 3: 在 `main.ts` 引入**

接在 `./styles/ds-table.css` 之後：

```ts
import './styles/glass.css'
import './styles/motion.css'
```

- [ ] **Step 4: StyleGuideView 加一節**

玻璃要有東西透出來才看得出效果，所以示範區塊底下先鋪一塊彩色漸層：

```vue
<section>
  <h2 class="sg-h2">玻璃（§5）</h2>
  <div class="sg-glass-stage">
    <div class="glass-panel sg-glass-demo">glass-panel：浮動面板、彈窗</div>
    <div class="glass-menu sg-glass-demo">glass-menu：下拉選單</div>
  </div>
</section>
```

對應 scoped CSS：

```css
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
```

- [ ] **Step 5: 型別與 lint 通過**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 6: 瀏覽器驗收**

`/style-guide` 上確認：背後的彩色漸層有透過玻璃糊出來（不是單純半透明白塊）；上緣邊框比其他三邊亮；文字讀得清楚。用 DevTools 暫時把 `backdrop-filter` 停用，確認 fallback 是近乎不透明的白底而不是糊成一片。重載頁面，確認上面幾節的卡片沒有被 `.enter-rise` 影響（還沒套上去，應該完全沒動）。

- [ ] **Step 7: Commit（需 user 同意）**

```bash
git add frontend/src/styles/glass.css frontend/src/styles/motion.css frontend/src/main.ts frontend/src/views/StyleGuideView.vue
git commit -m "feat(ui): add glass and motion utility styles"
```

---

## Batch 1：Hub、認證、介紹頁

Batch 1 的每個 task 都跑同一份流程：讀檔 → 依該檔對照表改 → build → lint → 指定的瀏覽器檢查 → commit。共同要檢查的十三項寫在 spec 的「每頁的套用清單」，以下每個 task 只列該檔**特有**的待改項。

### Task 6: CustomSelect 套玻璃選單

先做這個，因為多個 Hub 頁面都用到它。

**Files:**
- Modify: `frontend/src/components/common/CustomSelect.vue`

**Interfaces:**
- Consumes: `.glass-menu`（Task 5）。
- Produces: 對外 props 與事件不變，只改視覺。

- [ ] **Step 1: 列出待改項**

該檔現有硬寫值：`#94a3b8`（ink-soft）、`#b45309`（warning-text）、`#cbd5e1`（border-strong）、`#e8e8e8`（border）、`#fff`（surface）。另有：
- 第 374 行 `box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14)` → 選單改用 `.glass-menu`，這行拿掉（`.glass-menu` 自帶 `--shadow-float`）。
- 第 338 行 focus ring 用 `var(--color-accent)` → 改 `var(--color-ink)`。
- 1 處 `font-weight: 600` → 500。
- 1 個原生 `<button>`（觸發器）→ **維持原生 button，不換 AppButton**：它是 select 觸發器不是動作按鈕，換成 pill 會失去輸入框的形態語意。只把它的色值換成 token。

- [ ] **Step 2: 套用改動**

在選單容器的 class 加上 `glass-menu`，移除自己那份 background / border-radius / box-shadow；其餘依上表換 token。

- [ ] **Step 3: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 4: 瀏覽器驗收**

在 `/hub/projects/new` 展開任一下拉，確認：選單是玻璃、背後內容有糊出來；選項文字對比足夠；鍵盤上下鍵與 Enter 選取仍正常；選單沒有被其他元素蓋住（原本 `z-index: 3000` 要保留）。

- [ ] **Step 5: Commit（需 user 同意）**

```bash
git add frontend/src/components/common/CustomSelect.vue
git commit -m "style(select): apply glass menu and design tokens"
```

---

### Task 7: HubSidebar — token 化、修對比、兩版玻璃

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`

**Interfaces:**
- Produces: localStorage key `datamind:sidebar-glass`，值 `'light'` | `'dark'`，預設 `'light'`。切換鈕只在 `import.meta.env.DEV` 顯示。

- [ ] **Step 1: 修掉選中項的對比問題**

現在 `.hub-nav-item--active` 是 `background: var(--color-accent)` + `color: var(--color-text)`。`accent` 在 Phase 1 已從金色改成藏青 `#1A3159`，於是變成深藏青底配近黑字，對比遠低於 4.5:1。改成 §7.2 規定的做法 — 較亮的半透明白底 + Medium 字重 + 藏青文字：

```css
.hub-nav-item--active {
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-ink);
  font-weight: 500;
}
```

- [ ] **Step 2: 其餘 token 化**

- `#9ca3af`（brand-sub、footer 文字）→ `var(--color-ink-soft)`
- `#e5e7eb`（toggle / logout 鈕邊框）→ `var(--color-border)`
- `#f0f0f0`（user、footer 上分隔線）→ `var(--color-border)`
- `#ffffff`（toggle / logout 鈕底）→ `var(--color-surface)`
- `.hub-brand-title` 的 `font-weight: 700` → `500`
- 三顆 orb 與 hover 用的 `var(--color-accent)` → `var(--color-ink)`
- `border-radius: 4px`（兩顆小鈕）→ `var(--radius-sm)`；`border-radius: 7px`（nav item）→ `var(--radius-sm)`
- `transition: … 0.2s ease` / `0.15s` / `0.12s` → `var(--dur-base)` / `var(--dur-fast)` + `var(--ease-in-out)`（寬度）、`var(--ease-out)`（顏色）
- `mdi-logout` → `mdi-logout-variant`？**不改** — MDI 沒有 `mdi-logout-outline`，依 §3.5.1 純符號維持原樣。

- [ ] **Step 3: 寬度與收合動畫對齊 §7.2**

寬度 `210px ↔ 56px` 改成 `220px ↔ 72px`。目前 `hub-brand`、`hub-sidebar-user`、`hub-sidebar-footer`、`hub-nav-label` 是用 `v-if="!collapsed"` 直接從 DOM 移除，寬度轉場時文字會被硬切。改成保留在 DOM 用 opacity 淡出。

**淡出後必須一併關掉互動**：`hub-sidebar-user` 裡有登出鈕，只設 `opacity: 0` 的話它會變成看不見但可點、也可以 Tab 到，這是實際的操作錯誤來源，不只是視覺問題。用 `visibility` 搭配 `transition-behavior: allow-discrete`，讓它在淡出結束的那一刻才真的消失：

```css
.hub-nav-label,
.hub-brand,
.hub-sidebar-user,
.hub-sidebar-footer {
  transition:
    opacity var(--dur-fast) var(--ease-out),
    visibility var(--dur-fast) allow-discrete;
}

.hub-sidebar--collapsed .hub-nav-label,
.hub-sidebar--collapsed .hub-brand,
.hub-sidebar--collapsed .hub-sidebar-user,
.hub-sidebar--collapsed .hub-sidebar-footer {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
}
```

`visibility: hidden` 同時把元素移出無障礙樹與 Tab 順序，`pointer-events: none` 擋掉淡出過程中的誤點。展開時 `visibility` 會立刻變回 `visible`、opacity 才慢慢升，順序是對的。

- [ ] **Step 4: 加入深色玻璃第二版**

在根元素上依 localStorage 值掛 `hub-sidebar--glass-light` 或 `hub-sidebar--glass-dark`，兩版共用同一份結構與動畫，只覆寫顏色：

```ts
const glassVariant = ref<'light' | 'dark'>(
  (localStorage.getItem('datamind:sidebar-glass') as 'light' | 'dark' | null) ?? 'light',
)

// 兩版玻璃並存只是為了在瀏覽器互相對照，定案後刪掉落選的那版與這個切換
const isDev = import.meta.env.DEV

function toggleGlassVariant (): void {
  glassVariant.value = glassVariant.value === 'light' ? 'dark' : 'light'
  localStorage.setItem('datamind:sidebar-glass', glassVariant.value)
}
```

深色版依 §5.2 與 §7.2：

```css
.hub-sidebar--glass-dark {
  background: rgba(16, 32, 66, 0.62);
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 4px 0 24px rgba(14, 30, 66, 0.28);
}

.hub-sidebar--glass-dark .hub-brand-title,
.hub-sidebar--glass-dark .hub-user-name { color: #fff; }

.hub-sidebar--glass-dark .hub-brand-sub,
.hub-sidebar--glass-dark .hub-nav-item,
.hub-sidebar--glass-dark .hub-sidebar-footer { color: rgba(255, 255, 255, 0.72); }

.hub-sidebar--glass-dark .hub-nav-item:hover { background: rgba(255, 255, 255, 0.1); }

.hub-sidebar--glass-dark .hub-nav-item--active {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}

.hub-sidebar--glass-dark .hub-toggle-btn,
.hub-sidebar--glass-dark .hub-logout-btn {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.85);
}

.hub-sidebar--glass-dark .hub-sidebar-user,
.hub-sidebar--glass-dark .hub-sidebar-footer { border-top-color: rgba(255, 255, 255, 0.14); }
```

切換鈕放在側邊欄底部、`v-if="isDev"`：

```vue
<button v-if="isDev" class="hub-glass-toggle" @click="toggleGlassVariant">
  玻璃：{{ glassVariant === 'light' ? '淺' : '深' }}
</button>
```

- [ ] **Step 5: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 6: 瀏覽器驗收**

在 `/hub/dashboard`：
1. 選中的導覽項讀得清楚（這是這個 task 的主要修正）。
2. 收合／展開時文字先淡出、寬度再收，沒有文字被硬切。
3. 收合後寬度 72px，圖示仍置中；**用鍵盤 Tab 一路按過去，不會 focus 到已經淡出的登出鈕與版本文字**。
4. 按底部切換鈕在深／淺兩版間切，重新整理後保持選擇。
5. 深色版每一項文字（含 footer 版本號）對比都足夠。

- [ ] **Step 7: Commit（需 user 同意）**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "style(sidebar): apply design tokens, fix active item contrast, add dark glass variant"
```

---

### Task 8: HubLayout 與 DashboardView 收尾

這兩個檔已有未 commit 的改動，本 task 是驗收 + 補上 PageHeader。

**Files:**
- Modify: `frontend/src/layouts/HubLayout.vue`
- Modify: `frontend/src/views/hub/DashboardView.vue`

- [ ] **Step 1: DashboardView 改用 PageHeader**

把檔案開頭手寫的 `.page-header` / `.page-title` / `.page-sub` 區塊換成：

```vue
<PageHeader subtitle="歡迎回來，這是您的研究概覽。" title="儀表板" />
```

並刪掉對應的三段 scoped CSS。

- [ ] **Step 2: 確認容器寬度**

`.dashboard` 已有 `max-width: var(--content-max-width)`，補 `margin-inline: auto`，否則超寬螢幕下內容會貼左而不是置中（§8.2）。

- [ ] **Step 3: 卡片進場動畫**

用 Task 5 的全域 utility，不要在這裡自己寫 keyframes。在 `.stat-grid` 與 `.action-grid` 兩個容器的 class 上各加 `enter-stagger`：

```vue
<div class="stat-grid enter-stagger">
```

```vue
<div class="action-grid enter-stagger">
```

- [ ] **Step 4: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 5: 瀏覽器驗收**

`/hub/dashboard`：頁面漸層從 HubLayout 透出來（不是純色）；統計數字是藏青 32px；卡片依序淡入且很快結束；把視窗拉到 2000px 寬，內容置中不貼邊。

- [ ] **Step 6: Commit（需 user 同意）**

```bash
git add frontend/src/layouts/HubLayout.vue frontend/src/views/hub/DashboardView.vue
git commit -m "style(hub): apply design system to layout and dashboard"
```

---

### Task 9: FrameworkLibraryView

**Files:**
- Modify: `frontend/src/views/hub/FrameworkLibraryView.vue`

- [ ] **Step 1: 套用改動**

- hex：`#4f46e5` → `var(--color-ink)`；`#e0e7ff` / `#a5b4fc` / `#93c5fd` → `color-mix(in oklab, var(--color-ink) 10~24%, white)`；`#e8e8e8` / `#f0f0f0` / `#f3f3f3` / `#f5f5f5` 依角色 → `var(--color-border)` 或 `var(--color-surface-alt)`；`#ffffff` → `var(--color-surface)`
- 6 處 `font-weight: 600` → 500
- 圖示：`mdi-upload` → `mdi-upload-outline`（全站統一用這個表示上傳）；`mdi-target` 無 outline 變體，維持；`mdi-close`、`mdi-magnify` 屬純符號，不動
- 頁首 → `PageHeader`
- 1 個原生 `<button>` → `AppButton`（依它的角色選 variant）
- 頁面容器補 `max-width: var(--content-max-width); margin-inline: auto`

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/library`：卡片是實色白底 + `--shadow-card`（不是玻璃）；搜尋框、上傳鈕的色系全部是藏青，沒有殘留的靛紫；hover 回饋與 Dashboard 的卡片一致。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/FrameworkLibraryView.vue
git commit -m "style(hub): apply design system to framework library"
```

---

### Task 10: ExtractFrameworkView

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue`

這頁有近期做的 thinking 卡片（漸層光暈），改動時**不要破壞那個效果**，只把它用到的色值換成 token。

- [ ] **Step 1: 套用改動**

- hex：`#3730a3` / `#5b21b6` → `var(--color-ink-strong)`；`#e0e7ff` / `#ede9fe` → `color-mix(in oklab, var(--color-ink) 10~16%, white)`；`#374151` → `var(--color-text)`；`#d1d5db` → `var(--color-border-strong)`；`#e5e7eb` → `var(--color-border)`；`#f3f4f6` / `#f9fafb` → `var(--color-surface-alt)`；`#ef4444` / `#fecaca` / `#fef2f2` → `var(--color-error)` / `var(--color-error-bg)`，錯誤文字用 `var(--color-error-text)`；`#fff` / `#ffffff` → `var(--color-surface)`
- 3 處 `font-weight: 600` → 500
- 圖示：`mdi-file-pdf-box` → `mdi-file-pdf-box`（無 outline 變體，維持）；`mdi-arrow-left`、`mdi-close` 純符號不動
- 頁首 → `PageHeader`，返回鈕放 `#back` slot
- 3 個原生 `<button>` → `AppButton`
- 錯誤訊息區塊改用 `StatusBadge status="danger"` 或維持區塊但換成 error token（依現有版面選，不重排）

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/library/extract`：實際上傳一份 PDF 跑一次提取，確認 thinking 卡片的漸層光暈與兩行輪替動畫沒壞、進度訊息正常、錯誤狀態的紅色是新的 error token。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "style(hub): apply design system to extract framework"
```

---

### Task 11: ProjectsView

**Files:**
- Modify: `frontend/src/views/hub/ProjectsView.vue`

- [ ] **Step 1: 套用改動**

- hex：`#2347c5` → `var(--color-ink)`；`#dbeafe` / `#c7d2fe` → `color-mix(in oklab, var(--color-ink) 10~16%, white)`；`#d97706` / `#f59e0b` → `var(--color-warning)`，文字用 `var(--color-warning-text)`；`#fef3c7` → `var(--color-warning-bg)`；`#c4c9d4` → `var(--color-border-strong)`；`#e8e8e8` / `#f0f0f0` / `#f3f4f6` → `var(--color-border)` 或 `var(--color-surface-alt)`；`#ffffff` → `var(--color-surface)`
- 2 處 `font-weight: 600` → 500
- 專案狀態的色塊 → `StatusBadge`（進行中 → `warning`、已完成 → `success`、其他依現有語意對應；沒有語意的裝飾色一律拿掉）
- 頁首 → `PageHeader`，「建立新專案」放 `#actions` slot 用 `AppButton variant="primary"`
- 容器補寬度上限與 `margin-inline: auto`
- 專案列表容器加 `enter-stagger`（Task 5 的全域 utility）

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/projects`：狀態徽章語意正確（不是拿狀態色當裝飾）；每頁只有一顆 primary 按鈕；列表 hover 換 `--color-surface-alt` 底。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/ProjectsView.vue
git commit -m "style(hub): apply design system to projects list"
```

---

### Task 12: CreateProjectView

**Files:**
- Modify: `frontend/src/views/hub/CreateProjectView.vue`

- [ ] **Step 1: 套用改動**

- hex：`#4f46e5` → `var(--color-ink)`；`#e0e7ff` / `#a5b4fc` → `color-mix(in oklab, var(--color-ink) 10~24%, white)`；`#d1d5db` → `var(--color-border-strong)`；`#e5e7eb` / `#e8e8e8` / `#f0f0f0` / `#f0f1f3` → `var(--color-border)` 或 `var(--color-surface-alt)`；`#f9fafb` → `var(--color-surface-alt)`；`#ffffff` → `var(--color-surface)`
- 5 處 `font-weight: 600` → 500
- 圖示：`mdi-play` → `mdi-play-outline`；`mdi-table-arrow-up` 無 outline 變體，維持；`mdi-arrow-left`、`mdi-chevron-right` 純符號不動
- 頁首 → `PageHeader` + `#back`
- 3 個原生 `<button>` → `AppButton`；表單送出那顆是唯一 primary
- 表單容器寬度用 `var(--content-max-width)`，不要滿版

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/projects/new`：完整建立一個專案，確認上傳資料集、選框架、送出三步都正常；下拉是 Task 6 的玻璃選單；送出中按鈕呈 loading 且寬度不跳。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/CreateProjectView.vue
git commit -m "style(hub): apply design system to create project"
```

---

### Task 13: ProjectDetailView

**Files:**
- Modify: `frontend/src/views/hub/ProjectDetailView.vue`

- [ ] **Step 1: 套用改動**

- hex：`#2347c5` → `var(--color-ink)`；`#dbeafe` → `color-mix(in oklab, var(--color-ink) 10%, white)`；`#d97706` / `#fef3c7` → warning 組；`#e8e8e8` / `#f0f1f3` / `#f3f4f6` → border 或 surface-alt；`#ffffff` → `var(--color-surface)`
- 3 處 `font-weight: 600` → 500
- 圖示：`mdi-table-arrow-right` 無 outline 變體，維持；`mdi-arrow-left` / `mdi-arrow-right` 純符號不動
- 頁首 → `PageHeader` + `#back`
- 1 個原生 `<button>` → `AppButton`
- 專案狀態 → `StatusBadge`
- 第 47 行的 `<v-progress-circular>` → skeleton（§6.2）。用 Task 5 的 `.skeleton-line` 疊三行代替轉圈，行寬做出長短差異，載入時版面高度不跳：

```vue
<div v-if="loading" class="detail-skeleton">
  <div class="skeleton-line" style="width: 40%" />
  <div class="skeleton-line" style="width: 70%" />
  <div class="skeleton-line" style="width: 55%" />
</div>
```

```css
  .detail-skeleton {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
```

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/projects/<id>`：狀態徽章與 ProjectsView 列表上的同一狀態長得一樣（一致性檢查）；前往欄位對應、查看結果的導覽都正常；重載頁面時看到的是骨架屏而不是轉圈，且載入完成後版面沒有明顯跳動。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/ProjectDetailView.vue
git commit -m "style(hub): apply design system to project detail"
```

---

### Task 14: FieldMappingView 與 DatasetPreview

**Files:**
- Modify: `frontend/src/views/hub/FieldMappingView.vue`
- Modify: `frontend/src/components/hub/fieldMapping/DatasetPreview.vue`

- [ ] **Step 1: FieldMappingView 套用改動**

- hex：`#94a3b8` → `var(--color-ink-soft)`；`#b45309` → `var(--color-warning-text)`；`#b91c1c` → `var(--color-error-text)`；`#cbd5e1` → `var(--color-border-strong)`；`#e8e8e8` / `#f0f1f3` → `var(--color-border)` / `var(--color-surface-alt)`；`#fecaca` / `#fef2f2` → `var(--color-error-bg)`；`#fff` / `#ffffff` → `var(--color-surface)`
- 4 處 `font-weight: 600` → 500
- 頁首 → `PageHeader` + `#back`
- 2 個原生 `<button>` → `AppButton`
- 這是資料密集頁，容器寬度用 `var(--content-max-width-wide)`
- 第 37 行 `<v-progress-circular indeterminate size="28" color="accent" />` → skeleton（§6.2）。這裡載入的是對應表，用五行 `.skeleton-line` 模擬表格列，讓載入前後的版面高度接近：

```vue
<div v-if="loading" class="mapping-skeleton">
  <div v-for="n in 5" :key="n" class="skeleton-line" />
</div>
```

```css
  .mapping-skeleton {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 20px;
  }

  .mapping-skeleton .skeleton-line {
    height: 20px;
  }
```

- [ ] **Step 2: DatasetPreview 套用改動**

- `#f0f1f3` → `var(--color-surface-alt)`
- 2 處 `font-weight: 600` → 500
- 它有一個 `<table>` → 包進 `TableShell`、表格加 `class="ds-table"`，欄位名那格加 `class="ds-identifier"`，並刪掉該檔自己那份表頭／儲存格 CSS

- [ ] **Step 3: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 4: 瀏覽器驗收**

`/hub/projects/<id>/mapping`：資料預覽表格是 §7.4 的樣子（灰表頭、列 hover、圓角完整）；欄位名是等寬字；欄位很多時表格內部橫向捲動，頁面本身不橫向捲；重載時對應表區域顯示骨架屏而不是轉圈。

- [ ] **Step 5: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/FieldMappingView.vue frontend/src/components/hub/fieldMapping/DatasetPreview.vue
git commit -m "style(hub): apply design system to field mapping shell and dataset preview"
```

---

### Task 15: MappingTable

**Files:**
- Modify: `frontend/src/components/hub/fieldMapping/MappingTable.vue`

這是全批最密集的一檔：13 種硬寫色、五種狀態、三個按鈕、一個表格。

- [ ] **Step 1: 五種狀態換成 StatusBadge**

現有 `.status-chip--*` 五個 class 對應 `AUTO_MATCHED` / `NEEDS_REVIEW` / `UNMATCHED` / `SKIPPED` / `CONFIRMED`。改成：

| 狀態 | StatusBadge status |
|---|---|
| `AUTO_MATCHED` | `success` |
| `CONFIRMED` | `success` |
| `NEEDS_REVIEW` | `warning` |
| `UNMATCHED` | `danger` |
| `SKIPPED` | `neutral` |

保留現有的 tooltip（`STATUS_HINT`）與 `tabindex` focus 行為 — 把 StatusBadge 包在原本的 tooltip activator 內即可，刪掉 `.status-chip--*` 五段 CSS，但 `.status-chip[tabindex]:focus-visible` 那段 focus ring 要留著，改成套在外層。

- [ ] **Step 2: 表格與其餘 token**

- 表格 → `TableShell` + `class="ds-table"`，欄位名格加 `ds-identifier`，刪掉自己那份表頭／儲存格 CSS
- hex：`#15803d` → `var(--color-success-text)`；`#b45309` → `var(--color-warning-text)`；`#b91c1c` → `var(--color-error-text)`；`#d97706` → `var(--color-warning)`；`#dcfce7` → `var(--color-success-bg)`；`#fee2e2` → `var(--color-error-bg)`；`#fef3c7` / `#fef9c3` → `var(--color-warning-bg)`；`#94a3b8` → `var(--color-ink-soft)`；`#cbd5e1` → `var(--color-border-strong)`；`#e8e8e8` / `#f0f1f3` → `var(--color-border)` / `var(--color-surface-alt)`；`#fff` → `var(--color-surface)`
- 3 處 `font-weight: 600` → 500
- 圖示：`mdi-check`、`mdi-undo-variant` 皆為純符號，維持
- 3 個原生 `<button>`（確認、還原等）→ `AppButton`，破壞性的那顆用 `variant="danger"`
- 狀態改變時給一次性淡入強調（§6.2）：

```css
  .status-cell :deep(.status-badge) {
    animation: status-pop var(--dur-base) var(--ease-out);
  }

  @keyframes status-pop {
    from { opacity: 0.4; transform: scale(0.94); }
    to   { opacity: 1; transform: none; }
  }
```

- [ ] **Step 3: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 4: 瀏覽器驗收**

`/hub/projects/<id>/mapping`：五種狀態各找一列確認顏色與語意對得上（尤其「已略過」是中性灰不是狀態色）；點確認讓狀態從待確認變成已確認，徽章有一次性的輕微強調；tooltip 仍會出現；鍵盤 Tab 到徽章有 focus ring。

- [ ] **Step 5: Commit（需 user 同意）**

```bash
git add frontend/src/components/hub/fieldMapping/MappingTable.vue
git commit -m "style(hub): apply design system to mapping table"
```

---

### Task 16: MappingChatPanel 套玻璃

**Files:**
- Modify: `frontend/src/components/hub/fieldMapping/MappingChatPanel.vue`

- [ ] **Step 1: 套玻璃與 token**

- 面板容器加 `class="glass-panel"`，移除自己那份 background / border / box-shadow
- hex：`#94a3b8` → `var(--color-ink-soft)`；`#b45309` → `var(--color-warning-text)`；`#cbd5e1` → `var(--color-border-strong)`；`#e8e8e8` → `var(--color-border)`；`#eef1ff` → `color-mix(in oklab, var(--color-ink) 8%, white)`；`#fde68a` / `#fffbeb` → `var(--color-warning-bg)`；`#fff` / `#ffffff` → `var(--color-surface)`
- 2 處 `font-weight: 600` → 500
- 1 個原生 `<button>`（送出）→ `AppButton`
- AI 回覆依 §6.2 逐段淡入：每則訊息的根元素加 `enter-rise`（Task 5 的全域 utility）。兩個地雷要避開：
  - **不要**在訊息容器上用 `enter-stagger`，那會在每次新增訊息時讓整串舊訊息重跑動畫。
  - 若 AI 回覆是逐字串流進同一個元素，`enter-rise` 會在每次內容更新時重跑 keyframes、造成閃爍。確認 `enter-rise` 只掛在「訊息氣泡」這層（新增一則才產生一個新元素），不要掛在會被串流更新的內文節點上。

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

在欄位對應頁開對話面板：面板是玻璃且背後的表格有糊出來；訊息文字對比足夠（玻璃上最容易失敗的就是這點）；送出一則訊息，AI 回覆是淡入不是瞬間跳出；捲動訊息時面板不閃爍（`backdrop-filter` 與捲動同時作用的效能檢查）。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/components/hub/fieldMapping/MappingChatPanel.vue
git commit -m "style(hub): apply glass and design tokens to mapping chat panel"
```

---

### Task 17: ResultView

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue`

766 行、10 處 600+ 字重、11 種硬寫色，是頁面中最大的一檔。

- [ ] **Step 1: 套用改動**

- hex：`#16a34a` → `var(--color-success)`，成功文字 `var(--color-success-text)`；`#ef4444` → `var(--color-error)`，錯誤文字 `var(--color-error-text)`；`#ffd7d7` → `var(--color-error-bg)`；`#b7c2e6` → `var(--color-border-strong)`；`#e2e4ea` / `#e8e8e8` → `var(--color-border)`；`#eef1ff` / `#fafbff` → `color-mix(in oklab, var(--color-ink) 6~8%, white)`；`#f0f1f3` / `#f7f7f9` → `var(--color-surface-alt)`；`#ffffff` → `var(--color-surface)`
- 10 處 `font-weight: 600/700` → 500
- 圖示：`mdi-shimmer` 無 outline 變體，維持；`mdi-arrow-left` 純符號不動
- 頁首 → `PageHeader` + `#back`
- 2 個原生 `<button>` → `AppButton`
- 結果表格 → `TableShell` + `ds-table`；模型名、metric id 這類 identifier 加 `ds-identifier`
- 分析跟談面板（AI chat）→ `class="glass-panel"`
- 資料密集頁，容器寬度用 `var(--content-max-width-wide)`

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/projects/<id>/result`：跑過一次工作流的專案要能正常顯示結果；結果表格排序／捲動仍正常；分析跟談面板是玻璃；成功／失敗的模型列顏色語意正確；把視窗拉到 2138px 以上，表格不會無限拉伸。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "style(hub): apply design system to result view"
```

---

### Task 18: SettingsView

**Files:**
- Modify: `frontend/src/views/hub/SettingsView.vue`

- [ ] **Step 1: 套用改動**

- hex：`#16a34a` → `var(--color-success)`，成功提示文字 `var(--color-success-text)`；`#e5e7eb` / `#e8e8e8` → `var(--color-border)`；`#f0f1f3` / `#f9fafb` → `var(--color-surface-alt)`；`#ffffff` → `var(--color-surface)`
- 2 處 `font-weight: 600` → 500
- 圖示：`mdi-check-circle` → `mdi-check-circle-outline`
- 頁首 → `PageHeader`
- 2 個原生 `<button>` → `AppButton`；儲存那顆是唯一 primary
- 儲存成功提示 → `StatusBadge status="success"`

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/hub/settings`：改一個設定並儲存，成功提示用的是新的 success token；表單寬度有上限不滿版。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/views/hub/SettingsView.vue
git commit -m "style(hub): apply design system to settings"
```

---

### Task 19: 認證四頁與 GoogleSignInButton

**Files:**
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/RegisterView.vue`
- Modify: `frontend/src/views/ForgotPasswordView.vue`
- Modify: `frontend/src/views/ResetPasswordView.vue`
- Modify: `frontend/src/components/auth/GoogleSignInButton.vue`

四頁結構相近，一起做，共用同一組對照。

- [ ] **Step 1: 四頁共同的 token 替換**

- `#ffffff` → `var(--color-surface)`
- `#e8e8e8` → `var(--color-border)`
- `#d1d5db`（LoginView）→ `var(--color-border-strong)`
- `#b91c1c` → `var(--color-error-text)`；`#fecaca` / `#fef2f2` → `var(--color-error-bg)`
- `#15803d`（Forgot / Reset）→ `var(--color-success-text)`；`#bbf7d0` / `#f0fdf4` → `var(--color-success-bg)`
- 每頁各 1 處 `font-weight: 600` → 500
- 送出鈕（每頁 1–2 個原生 `<button>`）→ `AppButton variant="primary"`，送出中用 `loading`
- 卡片容器：`--radius-md` + `--shadow-card` + `--color-surface`（登入卡不玻璃化，§5.3 明確排除一般卡片）
- 表單卡片寬度維持現狀，只確認有上限

- [ ] **Step 2: GoogleSignInButton 只做最小改動**

該檔目前沒有硬寫 hex、沒有 600+ 字重。**不換成 AppButton**（Google 品牌規範），只確認它的圓角與旁邊的 AppButton 視覺不打架：若現在是方角而送出鈕是 pill，把它也改成 `border-radius: 999px`。

- [ ] **Step 3: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 4: 瀏覽器驗收**

逐頁走一次：登入（含錯誤密碼看紅色提示）、註冊、忘記密碼（看綠色成功提示）、重設密碼。確認四頁的卡片、輸入框、按鈕長得一致；Google 按鈕與送出鈕並排時不突兀；頁面漸層在登入頁也看得到。

- [ ] **Step 5: Commit（需 user 同意）**

```bash
git add frontend/src/views/LoginView.vue frontend/src/views/RegisterView.vue frontend/src/views/ForgotPasswordView.vue frontend/src/views/ResetPasswordView.vue frontend/src/components/auth/GoogleSignInButton.vue
git commit -m "style(auth): apply design system to auth pages"
```

---

### Task 20: Introduction（介紹頁）

**Files:**
- Modify: `frontend/src/components/Introduction.vue`

該檔沒有硬寫 hex、沒有 600+ 字重，只需處理圖示與 Tailwind class。注意它第 98 行有 `@reference "../styles/tailwind.css"`，改 class 時要維持這個機制可用。

- [ ] **Step 1: 套用改動**

- 圖示：`mdi-star` → `mdi-star-outline`；`mdi-text` → `mdi-text`（無 outline 變體，維持）；`mdi-arrow-top-right` 純符號不動
- 檢查用到的 Tailwind 顏色 class 是否指向舊的 `accent`，若有改成 `ink`
- 若有按鈕，換成 `AppButton`

- [ ] **Step 2: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 3: 瀏覽器驗收**

`/tutorial`：版面沒跑掉，圖示是線框版。

- [ ] **Step 4: Commit（需 user 同意）**

```bash
git add frontend/src/components/Introduction.vue
git commit -m "style(intro): switch to outline icons and design tokens"
```

---

### Task 21: Batch 1 收尾

**Files:**
- Modify: `docs/DESIGN_SYSTEM.md`
- Create: `docs/superpowers/plans/assets/2026-08-12-batch-1-changes.md`

- [ ] **Step 1: 圖示一致性核對**

跑一次盤點，確認同語意沒有用到不同圖示：

```bash
cd frontend/src && grep -rhoE 'mdi-[a-z0-9-]+' --include='*.vue' \
  views/hub views/LoginView.vue views/RegisterView.vue views/ForgotPasswordView.vue \
  views/ResetPasswordView.vue components/hub components/auth components/common \
  components/Introduction.vue layouts | sort | uniq -c | sort -rn
```

檢查清單：上傳只用 `mdi-upload-outline`、新增只用 `mdi-plus`、刪除只用 `mdi-delete-outline`、編輯只用 `mdi-pencil-outline`。有不一致就統一，並把結果記進 §3.5。

- [ ] **Step 2: 殘留硬寫色掃描**

```bash
cd frontend/src && grep -rnE '#[0-9a-fA-F]{3,8}\b' --include='*.vue' \
  views/hub views/LoginView.vue views/RegisterView.vue views/ForgotPasswordView.vue \
  views/ResetPasswordView.vue components/hub components/auth components/common layouts
```

預期只剩玻璃效果的 `rgba(255,255,255,x)` 與深色玻璃的 `rgba(16,32,66,x)`。其他都要換成 token。

- [ ] **Step 3: 字重殘留掃描**

```bash
cd frontend/src && grep -rnE 'font-weight: *(600|700|800|bold)' --include='*.vue' \
  views/hub views/LoginView.vue views/RegisterView.vue views/ForgotPasswordView.vue \
  views/ResetPasswordView.vue components/hub components/auth components/common layouts
```

預期 0 筆。

- [ ] **Step 4: 更新設計系統文件**

- §7.5 補上 `neutral` 第四態，說明它用於「使用者主動略過」這類非狀態語意，色值用 `--color-ink-soft` / `--color-surface-alt`。
- §3.5.2 更新遷移現況：Hub、認證、介紹頁已完成，剩 Paper 與 Workflow。
- §6.2 已改寫：specular 邊緣反光實測後放棄（1px 邊框上的效果太細微，看不出來），改成底色加深一階 + 抬起 1px，四變體共用。`useSpecularHover.ts` 一併刪除。
- §7.2 暫不改寫 — 等 user 在瀏覽器選定深／淺版本後，Task 22 再處理。

- [ ] **Step 5: 寫 Batch 1 變更清單**

在 `docs/superpowers/plans/assets/2026-08-12-batch-1-changes.md` 列出：每一頁改了什麼、哪些頁面要重點檢查、已知未處理的項目。這份給 user 驗收時對照用。

- [ ] **Step 6: 全站 build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 7: Commit（需 user 同意）**

```bash
git add docs/DESIGN_SYSTEM.md docs/superpowers/plans/assets/2026-08-12-batch-1-changes.md
git commit -m "docs: update design system after batch 1 rollout"
```

---

### Task 22: 側邊欄玻璃定案（需 user 決定後才執行）

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`
- Modify: `docs/DESIGN_SYSTEM.md`

這個 task 卡在 user 的決定上，不要在還沒得到答覆前執行。

- [ ] **Step 1: 取得 user 的選擇**

請 user 在 `/hub/dashboard` 用側邊欄底部的切換鈕看過深／淺兩版，選一個。

- [ ] **Step 2: 刪掉落選的那版**

移除落選版的所有 CSS、`glassVariant` ref、`toggleGlassVariant`、localStorage 讀寫、`isDev` 判斷與切換鈕。保留的那版把 class 收回根元素上的固定樣式，不再需要變體 class。

- [ ] **Step 3: 改寫 §7.2**

把 `docs/DESIGN_SYSTEM.md` §7.2 的側邊欄規格改成定案版本的實際數值（底色 tint、邊框、選中態、寬度 220↔72），並從附錄「待驗證／未定案項目」拿掉「側邊欄深色／淺色」那條。

- [ ] **Step 4: build 與 lint**

Run: `cd frontend && npm run build && npm run lint`
Expected: 兩者皆 0 error。

- [ ] **Step 5: 瀏覽器驗收**

`/hub/dashboard`：側邊欄只剩定案那版，切換鈕消失，收合展開與選中態都正常。

- [ ] **Step 6: Commit（需 user 同意）**

```bash
git add frontend/src/components/hub/HubSidebar.vue docs/DESIGN_SYSTEM.md
git commit -m "style(sidebar): settle on final glass variant"
```

---

## Batch 1 完成後

交付 `docs/superpowers/plans/assets/2026-08-12-batch-1-changes.md` 給 user 驗收。通過後再依當時的共用層實際樣貌，寫 Batch 2（Paper）的計畫。
