# Workflow Color Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the project's `--color-*` design tokens to the 17 files that make up the standalone `/workflow → /results → /paper/sources` flow, replacing the old `#005dff`/`#2563eb` CTA blues with accent, text greys with ink/secondary, white/near-white backgrounds with surface, and unifying duplicate status-color hex values — the fourth and final batch of the color rollout.

**Architecture:** Pure CSS value swaps inside each file's existing `<style scoped>` block (plus a handful of inline `fill`/`color` attributes in `<template>` markup and SVG) — no logic changes anywhere. Each task replaces one file's entire style block (and any inline template color attributes) in a single edit, following the same approach used in the prior three color-application batches.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-secondary` (`#334155`), `--color-accent` (`#e8a33d`), `--color-surface` (`#ffffff`), `--color-ink` (`#1c2130`), `--color-inverted` (`#f1f5f9`)
- Substitution rules (apply verbatim, no exceptions except where explicitly noted per-file below):
  - `#005dff` → `var(--color-accent)`; `rgba(0, 93, 255, X)` → `color-mix(in oklab, var(--color-accent) N%, transparent)` where N = X × 100 (e.g. `rgba(0, 93, 255, 0.1)` → `color-mix(in oklab, var(--color-accent) 10%, transparent)`), except where the rgba is composited directly over a white/surface background (not transparent) — those use `color-mix(in oklab, var(--color-accent) N%, var(--color-surface))` instead, called out per-occurrence below
  - `#2563eb` → `var(--color-accent)`; `rgba(59, 130, 246, X)` → same `color-mix` pattern as above
  - `#0f172a`, `#1e293b`, `#1f2937`, `#1c2130`, `#20232a`, `#1f2532`, `#1f2430`, `#192235`, `#15181e`, `#242424` → `var(--color-ink)`
  - `#475569`, `#64748b`, `#94a3b8`, `#6b7280`, `#6f7480`, `#5f6571`, `#3a3f4a`, and `#334155` (only when used as a text `color`, never as a background) → `var(--color-secondary)`
  - `#ffffff`, `#fff`, `#f8fafc`, `#f9fbff`, `#f8fbff`, `#f7f9ff`, `#fafbff`, `#f0f2f5` → `var(--color-surface)`
  - Success green `#10b981` / `#18a836` → literal hex `#16a34a` (not a token — unifies with the value already established in the prior batch)
  - Error red `#b91c1c` → literal hex `#ef4444` (not a token — unifies with the value already established in the prior batch; occurrences already at `#ef4444` need no change)
- **Never touch:** neutral border/divider colors (`rgba(148, 163, 184, *)`, `#e2e8f0`, `#cbd5e1`, `#ced3e9`, `#d8dbe3`, `#d7d9df`, `#dedfe4`, `#e4e4e8`, `#e8ebf1`, `#e8ebf2`, `#e8ebf1`); `IconNode.vue`'s node-type palette (`.node-purple`, `.node-yellow`, `.node-pending`, and the `LABEL_ACCENTS` map — including its `#005dff` entry, which stays literal); decorative indigo functional-icon blocks (`#4f46e5`, `#e0e7ff`, and their rgba tints `rgba(238, 242, 255, *)` / `rgba(224, 231, 255, *)`); the add/remove flash-overlay colors in `IconNode.vue` (`#06b6d4`, `#ef4444` — already correct, leave as literal); `ComputeCiPanel.vue`'s warning amber (`#92400e` and its `rgba(245, 158, 11, *)` background/border); `ResultsPage.vue`/`PaperSourcesView.vue`'s `--line`/`--line-soft` neutral border variables
- No unit test framework is configured in `frontend/` — verification is `npm run build`, `grep`, and (for the final task) live browser checks, run from the `frontend/` directory
- Do not add a test framework or write new automated tests as part of this plan
- `frontend/src/components/WorkflowBuilder.vue` is out of scope (confirmed unreferenced by any route or import — dead code)

---

### Task 1: `WorkflowPage.vue`

**Files:**
- Modify: `frontend/src/views/WorkflowPage.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.workflow-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: #f9fbff;
}

.workflow-page__main {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
}

.workflow-page__workspace {
  height: 100%;
  overflow: hidden;
}
</style>
```

With:

```css
<style scoped>
.workflow-page {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background-color: var(--color-surface);
}

.workflow-page__main {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
  overflow: hidden;
}

.workflow-page__workspace {
  height: 100%;
  overflow: hidden;
}
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#f9fbff" frontend/src/views/WorkflowPage.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/WorkflowPage.vue
git commit -m "feat: apply color tokens to WorkflowPage"
```

---

### Task 2: `ResultsPage.vue`

**Files:**
- Modify: `frontend/src/views/ResultsPage.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-primary`, `--color-surface`, `--color-accent`, `--color-ink`, `--color-secondary`, `--color-inverted` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .results-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    --brand-soft: #ebf2ff;
    --good: #18a836;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    position: relative;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .results-main {
    flex: 1;
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: auto;
  }

  .results-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
    animation: slide-in 0.45s ease both;
  }

  .back-btn {
    color: #1f2430;
  }

  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

  .generate-paper-btn {
    margin-left: 12px;
  }

  .toolbar-tab {
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: #5f6571;
    cursor: pointer;
    background: transparent;
    transition: all 0.2s ease;
  }

  .toolbar-tab--active {
    background: #ffffff;
    color: #192235;
    box-shadow: 0 1px 3px rgba(20, 38, 84, 0.12);
  }

  .metric-grid {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
    animation: reveal-up 0.42s ease both;
  }

  .metric-card:nth-child(2) {
    animation-delay: 0.05s;
  }

  .metric-card:nth-child(3) {
    animation-delay: 0.1s;
  }

  .metric-card:nth-child(4) {
    animation-delay: 0.15s;
  }

  .metric-card--accent .metric-value {
    color: var(--good);
  }

  .metric-title {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    color: #20232a;
  }

  .metric-value {
    margin: 8px 0 2px;
    font-size: 36px;
    font-weight: 700;
    line-height: 1.05;
  }

  .metric-hint {
    margin: 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .insight-card {
    margin-top: 12px;
    border-radius: 14px;
    color: #f7f9ff;
    padding: 14px 16px;
    background: linear-gradient(102deg, #4f86f0 0%, #4554df 100%);
    animation: reveal-up 0.5s ease both;
    animation-delay: 0.12s;
  }

  .insight-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .insight-icon-wrap {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.2);
  }

  .insight-title {
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
    font-weight: 700;
  }

  .insight-text {
    margin: 8px 0 10px;
    font-size: 13px;
    color: rgba(248, 251, 255, 0.93);
    line-height: 1.45;
  }

  .insight-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .insight-tag {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    background: rgba(255, 255, 255, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.35);
  }

  .comparison-card {
    margin-top: 12px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: #ffffff;
    overflow: hidden;
    animation: reveal-up 0.55s ease both;
    animation-delay: 0.18s;
  }

  .comparison-head {
    padding: 14px 18px;
    border-bottom: 1px solid var(--line-soft);
  }

  .comparison-head h3 {
    margin: 0;
    font-size: 29px;
  }

  .comparison-head p {
    margin: 3px 0 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .table-wrap {
    overflow: auto;
  }

  .result-table {
    width: 100%;
    min-width: 680px;
    border-collapse: collapse;
  }

  .result-table th,
  .result-table td {
    padding: 11px 18px;
    text-align: left;
    border-bottom: 1px solid var(--line-soft);
    font-size: 12px;
    white-space: nowrap;
  }

  .result-table th {
    font-weight: 700;
    color: #2a2f39;
    background: #fafbff;
  }

  .result-table tbody tr:last-child td {
    border-bottom: none;
  }

  .model-name {
    font-weight: 700;
    color: #1f2532;
  }

  .score-best {
    color: var(--good);
    font-weight: 700;
  }

  @keyframes reveal-up {
    from {
      opacity: 0;
      transform: translateY(10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1260px) {
    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 920px) {
    .results-page {
      display: block;
      padding: 12px;
    }

    .results-main {
      margin-top: 10px;
      border-radius: 12px;
      padding: 12px;
    }

    .insight-title,
    .comparison-head h3,
    .metric-value {
      font-size: clamp(20px, 4.2vw, 30px);
    }
  }

  @media (max-width: 640px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .results-toolbar {
      align-items: flex-start;
      gap: 8px;
      flex-direction: column;
    }

    .toolbar-tabs {
      width: 100%;
      justify-content: space-between;
    }

    .toolbar-tab {
      flex: 1;
      justify-content: center;
    }

    .result-table {
      min-width: 620px;
    }
  }
</style>
```

With:

```css
<style scoped>
  .results-page {
    --page-bg: var(--color-primary);
    --card-bg: var(--color-surface);
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: var(--color-ink);
    --text-secondary: var(--color-secondary);
    --brand: var(--color-accent);
    --brand-soft: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
    --good: #16a34a;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    position: relative;
    background:
      radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
      var(--page-bg);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .results-main {
    flex: 1;
    min-width: 0;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: var(--card-bg);
    padding: 12px 20px 18px;
    overflow: auto;
  }

  .results-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
    animation: slide-in 0.45s ease both;
  }

  .back-btn {
    color: var(--color-ink);
  }

  .toolbar-tabs {
    border-radius: 10px;
    padding: 4px;
    background: #e8ebf2;
    display: inline-flex;
    gap: 4px;
  }

  .generate-paper-btn {
    margin-left: 12px;
  }

  .toolbar-tab {
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
    color: var(--color-secondary);
    cursor: pointer;
    background: transparent;
    transition: all 0.2s ease;
  }

  .toolbar-tab--active {
    background: var(--color-surface);
    color: var(--color-ink);
    box-shadow: 0 1px 3px rgba(20, 38, 84, 0.12);
  }

  .metric-grid {
    margin-top: 16px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 14px;
    animation: reveal-up 0.42s ease both;
  }

  .metric-card:nth-child(2) {
    animation-delay: 0.05s;
  }

  .metric-card:nth-child(3) {
    animation-delay: 0.1s;
  }

  .metric-card:nth-child(4) {
    animation-delay: 0.15s;
  }

  .metric-card--accent .metric-value {
    color: var(--good);
  }

  .metric-title {
    margin: 0;
    font-size: 12px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .metric-value {
    margin: 8px 0 2px;
    font-size: 36px;
    font-weight: 700;
    line-height: 1.05;
  }

  .metric-hint {
    margin: 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .insight-card {
    margin-top: 12px;
    border-radius: 14px;
    color: var(--color-inverted);
    padding: 14px 16px;
    background: linear-gradient(102deg, var(--color-accent) 0%, color-mix(in oklab, var(--color-accent) 70%, var(--color-ink)) 100%);
    animation: reveal-up 0.5s ease both;
    animation-delay: 0.12s;
  }

  .insight-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .insight-icon-wrap {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.2);
  }

  .insight-title {
    margin: 0;
    font-size: 30px;
    line-height: 1.1;
    font-weight: 700;
  }

  .insight-text {
    margin: 8px 0 10px;
    font-size: 13px;
    color: rgba(248, 251, 255, 0.93);
    line-height: 1.45;
  }

  .insight-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .insight-tag {
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    background: rgba(255, 255, 255, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.35);
  }

  .comparison-card {
    margin-top: 12px;
    border: 1px solid var(--line);
    border-radius: 14px;
    background: var(--color-surface);
    overflow: hidden;
    animation: reveal-up 0.55s ease both;
    animation-delay: 0.18s;
  }

  .comparison-head {
    padding: 14px 18px;
    border-bottom: 1px solid var(--line-soft);
  }

  .comparison-head h3 {
    margin: 0;
    font-size: 29px;
  }

  .comparison-head p {
    margin: 3px 0 0;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .table-wrap {
    overflow: auto;
  }

  .result-table {
    width: 100%;
    min-width: 680px;
    border-collapse: collapse;
  }

  .result-table th,
  .result-table td {
    padding: 11px 18px;
    text-align: left;
    border-bottom: 1px solid var(--line-soft);
    font-size: 12px;
    white-space: nowrap;
  }

  .result-table th {
    font-weight: 700;
    color: var(--color-ink);
    background: var(--color-surface);
  }

  .result-table tbody tr:last-child td {
    border-bottom: none;
  }

  .model-name {
    font-weight: 700;
    color: var(--color-ink);
  }

  .score-best {
    color: var(--good);
    font-weight: 700;
  }

  @keyframes reveal-up {
    from {
      opacity: 0;
      transform: translateY(10px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateY(-8px);
    }

    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 1260px) {
    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 920px) {
    .results-page {
      display: block;
      padding: 12px;
    }

    .results-main {
      margin-top: 10px;
      border-radius: 12px;
      padding: 12px;
    }

    .insight-title,
    .comparison-head h3,
    .metric-value {
      font-size: clamp(20px, 4.2vw, 30px);
    }
  }

  @media (max-width: 640px) {
    .metric-grid {
      grid-template-columns: 1fr;
    }

    .results-toolbar {
      align-items: flex-start;
      gap: 8px;
      flex-direction: column;
    }

    .toolbar-tabs {
      width: 100%;
      justify-content: space-between;
    }

    .toolbar-tab {
      flex: 1;
      justify-content: center;
    }

    .result-table {
      min-width: 620px;
    }
  }
</style>
```

Note: `.toolbar-tabs`'s `background: #e8ebf2;` is intentionally unchanged — it's a neutral tab-track grey, not covered by any substitution rule.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#e4e4e8\|#15181e\|#6f7480\|#1058d6\|#ebf2ff\|#18a836\|#d7d9df\|#dedfe4\|#f3f4f8\|#eff1f6\|#1f2430\|#5f6571\|#192235\|#20232a\|#4f86f0\|#4554df\|#2a2f39\|#fafbff\|#1f2532" frontend/src/views/ResultsPage.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ResultsPage.vue
git commit -m "feat: apply color tokens to ResultsPage"
```

---

### Task 3: `PaperSourcesView.vue`

**Files:**
- Modify: `frontend/src/views/PaperSourcesView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-primary`, `--color-surface`, `--color-accent`, `--color-ink`, `--color-secondary` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .sources-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    min-height: calc(100vh - 64px);
    display: flex;
    padding: 16px;
    background: linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .sources-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 24px;
    overflow: auto;
  }

  .sources-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: #1f2430;
  }

  .sources-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: #1c2130;
  }

  .sources-topic {
    margin: 14px 2px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status {
    margin: 20px 2px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status--error {
    color: #b91c1c;
  }

  .candidate-list {
    list-style: none;
    margin: 14px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .candidate-card {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--card-bg);
  }

  .candidate-select {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
  }

  .candidate-body {
    flex: 1;
    min-width: 0;
  }

  .candidate-title {
    margin: 0 0 4px;
    font-size: 13.5px;
    font-weight: 700;
    color: #1c2130;
  }

  .candidate-meta {
    margin: 0 0 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .candidate-abstract {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: #3a3f4a;
  }

  .sources-actions {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
</style>
```

With:

```css
<style scoped>
  .sources-page {
    --page-bg: var(--color-primary);
    --card-bg: var(--color-surface);
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: var(--color-ink);
    --text-secondary: var(--color-secondary);
    min-height: calc(100vh - 64px);
    display: flex;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
      var(--page-bg);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .sources-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: var(--card-bg);
    padding: 12px 20px 24px;
    overflow: auto;
  }

  .sources-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0 2px 10px;
    border-bottom: 1px solid var(--line-soft);
  }

  .back-btn {
    color: var(--color-ink);
  }

  .sources-title {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .sources-topic {
    margin: 14px 2px 0;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status {
    margin: 20px 2px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .sources-status--error {
    color: #ef4444;
  }

  .candidate-list {
    list-style: none;
    margin: 14px 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .candidate-card {
    border: 1px solid var(--line);
    border-radius: 12px;
    background: var(--card-bg);
  }

  .candidate-select {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 14px 16px;
    cursor: pointer;
  }

  .candidate-body {
    flex: 1;
    min-width: 0;
  }

  .candidate-title {
    margin: 0 0 4px;
    font-size: 13.5px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .candidate-meta {
    margin: 0 0 6px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .candidate-abstract {
    margin: 0;
    font-size: 12.5px;
    line-height: 1.6;
    color: var(--color-secondary);
  }

  .sources-actions {
    margin-top: 18px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#e4e4e8\|#15181e\|#6f7480\|#d7d9df\|#dedfe4\|#f3f4f8\|#eff1f6\|#1f2430\|#1c2130\|#b91c1c\|#3a3f4a" frontend/src/views/PaperSourcesView.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/PaperSourcesView.vue
git commit -m "feat: apply color tokens to PaperSourcesView"
```

---

### Task 4: `UploadDialog.vue`

**Files:**
- Modify: `frontend/src/components/workflow/UploadDialog.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-surface`, `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .upload-dialog-backdrop {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(8px);
  }

  .upload-dialog-card {
    width: min(560px, calc(100% - 32px));
    border-radius: 20px;
    background: #ffffff;
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .upload-dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .upload-dialog-close {
    border: none;
    background: rgba(243, 244, 246, 0.9);
    width: 36px;
    height: 36px;
    border-radius: 999px;
    color: #1f2937;
    font-size: 18px;
    cursor: pointer;
  }

  .upload-dialog-card h3 {
    margin: 0;
    font-size: 20px;
  }

  .upload-dialog-card p {
    margin: 6px 0 0;
    color: #475569;
    font-size: 14px;
    line-height: 1.6;
  }

  .upload-dropzone {
    min-height: 210px;
    padding: 28px 20px;
    border: 2px dashed rgba(148, 163, 184, 0.8);
    border-radius: 18px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: rgba(236, 246, 255, 0.68);
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .upload-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.12);
  }

  .upload-dropzone__icon {
    font-size: 28px;
    color: #2563eb;
  }

  .upload-dropzone__text {
    font-size: 18px;
    color: #1f2937;
    font-weight: 600;
  }

  .upload-dropzone__browse {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 22px;
    border-radius: 999px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-dropzone__file {
    font-size: 13px;
    color: #475569;
  }

  .upload-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
</style>
```

With:

```css
<style scoped>
  .upload-dialog-backdrop {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(15, 23, 42, 0.45);
    backdrop-filter: blur(8px);
  }

  .upload-dialog-card {
    width: min(560px, calc(100% - 32px));
    border-radius: 20px;
    background: var(--color-surface);
    box-shadow: 0 24px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .upload-dialog-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
  }

  .upload-dialog-close {
    border: none;
    background: rgba(243, 244, 246, 0.9);
    width: 36px;
    height: 36px;
    border-radius: 999px;
    color: var(--color-ink);
    font-size: 18px;
    cursor: pointer;
  }

  .upload-dialog-card h3 {
    margin: 0;
    font-size: 20px;
  }

  .upload-dialog-card p {
    margin: 6px 0 0;
    color: var(--color-secondary);
    font-size: 14px;
    line-height: 1.6;
  }

  .upload-dropzone {
    min-height: 210px;
    padding: 28px 20px;
    border: 2px dashed rgba(148, 163, 184, 0.8);
    border-radius: 18px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    background: rgba(236, 246, 255, 0.68);
    transition: border-color 0.2s ease, background 0.2s ease;
  }

  .upload-dropzone--active {
    border-color: var(--color-accent);
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
  }

  .upload-dropzone__icon {
    font-size: 28px;
    color: var(--color-accent);
  }

  .upload-dropzone__text {
    font-size: 18px;
    color: var(--color-ink);
    font-weight: 600;
  }

  .upload-dropzone__browse {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 22px;
    border-radius: 999px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-dropzone__file {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .upload-dialog-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
</style>
```

Note: `.upload-dropzone`'s idle-state `background: rgba(236, 246, 255, 0.68);` is intentionally unchanged — a distinct pale-blue wash, not the named CTA rgba pattern. `.upload-dropzone__browse`'s `color: #fff;` stays literal (white text on an accent-colored button, not a white background).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#ffffff\|#1f2937\|#475569\|#2563eb" frontend/src/components/workflow/UploadDialog.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/UploadDialog.vue
git commit -m "feat: apply color tokens to UploadDialog"
```

---

### Task 5: `IconNode.vue`

**Files:**
- Modify: `frontend/src/components/workflow/IconNode.vue` (two targeted snippets in `<style scoped>` — the node-type color palette in this file is explicitly out of scope, see Global Constraints)

**Interfaces:**
- Consumes: `--color-ink`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit the node label text color**

Replace:

```css
  .icon-node-label {
    min-height: 32px;
    text-align: center;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 600;
    color: #242424;
    white-space: pre-line;
  }
```

With:

```css
  .icon-node-label {
    min-height: 32px;
    text-align: center;
    font-size: 13px;
    line-height: 1.2;
    font-weight: 600;
    color: var(--color-ink);
    white-space: pre-line;
  }
```

- [ ] **Step 2: Edit the highlighted-node ring's default fallback color**

Replace:

```css
  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, #005dff);
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }

  @keyframes highlight-pulse {
    0%, 100% { box-shadow: 0 0 0 3px var(--highlight-color, #005dff); }
    50% { box-shadow: 0 0 0 6px var(--highlight-color, #005dff); }
  }
```

With:

```css
  .node-highlighted {
    box-shadow: 0 0 0 4px var(--highlight-color, var(--color-accent));
    animation: highlight-pulse 1.4s ease-in-out infinite;
  }

  @keyframes highlight-pulse {
    0%, 100% { box-shadow: 0 0 0 3px var(--highlight-color, var(--color-accent)); }
    50% { box-shadow: 0 0 0 6px var(--highlight-color, var(--color-accent)); }
  }
```

Note: `LABEL_ACCENTS` (in `<script setup>`), `.node-yellow`, `.node-pending`, `.node-purple` (including its `#005dff` gradient stop), and the `#fff`/`rgba(255,255,255,*)` icon/spinner foreground colors are all intentionally unchanged — see Global Constraints and spec section E.

- [ ] **Step 3: Verify no leftover old color values (outside the excluded node-type palette)**

Run: `grep -n "#242424" frontend/src/components/workflow/IconNode.vue`
Expected: no output.

Run: `grep -n "#005dff" frontend/src/components/workflow/IconNode.vue`
Expected: exactly 2 matches — both inside `LABEL_ACCENTS`/`.node-purple` (the excluded node-type palette), confirming the highlighted-ring fallback was changed but the node-type palette was not.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/IconNode.vue
git commit -m "feat: apply color tokens to IconNode (node-type palette excluded)"
```

---

### Task 6: `WorkflowCanvas.vue`

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowCanvas.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-surface`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .canvas {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding-top: 6px;
    min-height: 0;
    min-width: 0;
    box-sizing: border-box;

    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .flow-area {
    flex: 1;
    min-height: 300px;
    min-width: 0;
    border: none;
    border-radius: 12px;
    background-color: #f8fbff;
    background-image: radial-gradient(
      rgba(0, 93, 255, 0.08) 0.9px,
      transparent 0.9px
    );
    background-size: 14px 14px;
    overflow: auto;
    padding-top: 6px;
  }

  /* 拖曳時顯示手掌游標 */
  :deep(.vue-flow__pane) {
    cursor: grab;
  }

  :deep(.vue-flow__pane.dragging) {
    cursor: grabbing;
  }

  /* 可點的節點顯示手指；模型節點停用互動、顯示預設箭頭 */
  :deep(.vue-flow__node) {
    cursor: pointer;
  }

  :deep(.vue-flow__node.node-non-interactive) {
    cursor: default;
  }

  :deep(.vue-flow__edge-path) {
    stroke: #005dff;
    stroke-width: 2.4;
  }

  @media (max-width: 1024px) {
    /* 平板：畫布高度加高，避免節點擠在一起 */
    .flow-area {
      min-height: 360px;
    }
  }

  @media (max-width: 768px) {
    /* 手機：外層邊距縮小、圓角縮小、高度再拉高 */
    .canvas {
      padding: 2px 0;
    }

    .flow-area {
      min-height: 420px;
      border-radius: 10px;
    }
  }
</style>
```

With:

```css
<style scoped>
  .canvas {
    background: transparent;
    border: none;
    border-radius: 12px;
    padding-top: 6px;
    min-height: 0;
    min-width: 0;
    box-sizing: border-box;

    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .flow-area {
    flex: 1;
    min-height: 300px;
    min-width: 0;
    border: none;
    border-radius: 12px;
    background-color: var(--color-surface);
    background-image: radial-gradient(
      color-mix(in oklab, var(--color-accent) 8%, transparent) 0.9px,
      transparent 0.9px
    );
    background-size: 14px 14px;
    overflow: auto;
    padding-top: 6px;
  }

  /* 拖曳時顯示手掌游標 */
  :deep(.vue-flow__pane) {
    cursor: grab;
  }

  :deep(.vue-flow__pane.dragging) {
    cursor: grabbing;
  }

  /* 可點的節點顯示手指；模型節點停用互動、顯示預設箭頭 */
  :deep(.vue-flow__node) {
    cursor: pointer;
  }

  :deep(.vue-flow__node.node-non-interactive) {
    cursor: default;
  }

  :deep(.vue-flow__edge-path) {
    stroke: var(--color-accent);
    stroke-width: 2.4;
  }

  @media (max-width: 1024px) {
    /* 平板：畫布高度加高，避免節點擠在一起 */
    .flow-area {
      min-height: 360px;
    }
  }

  @media (max-width: 768px) {
    /* 手機：外層邊距縮小、圓角縮小、高度再拉高 */
    .canvas {
      padding: 2px 0;
    }

    .flow-area {
      min-height: 420px;
      border-radius: 10px;
    }
  }
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#f8fbff\|#005dff" frontend/src/components/workflow/WorkflowCanvas.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/WorkflowCanvas.vue
git commit -m "feat: apply color tokens to WorkflowCanvas"
```

---

### Task 7: `WorkflowOptionsPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowOptionsPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .setting-area {
    flex: 1;
    border: none;
    border-radius: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: transparent;
  }

  .panel-header {
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(0, 93, 255, 0.1);
    background: transparent;
  }

  .panel-header h3 {
    margin: 0 0 2px;
    font-size: 16px;
    color: #0f172a;
  }

  .panel-header p {
    margin: 0;
    font-size: 13px;
    color: #6b7280;
  }

  .panel-body {
    flex: 1;
    min-height: 0;
    overflow: visible;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 4px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 10px;
  }

  .form-row label {
    font-size: 13px;
    font-weight: 600;
    color: #374151;
  }

  .form-row input,
  .form-row select {
    border: 1px solid rgba(0, 93, 255, 0.2);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
    outline: none;
    background: rgba(255, 255, 255, 0.5);
  }

  /* 隱藏原生 select 箭頭，換成自訂 chevron */
  .form-row select {
    appearance: none;
    -webkit-appearance: none;
    padding-right: 32px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23005DFF' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    cursor: pointer;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed rgba(0, 93, 255, 0.28);
    border-radius: 16px;
    background: rgba(0, 93, 255, 0.04);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__title {
    font-size: 14px;
    font-weight: 700;
  }

  .upload-card__desc {
    margin: 0;
    color: #475569;
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-card__input-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .upload-card__info {
    color: #0f172a;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.13);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: #2563eb;
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }

  .upload-modal-line2 {
    color: #475569;
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: #475569;
  }

  .upload-modal-error {
    color: #b91c1c;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    color: #1f2937;
    font-size: 16px;
    font-weight: 700;
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: #475569;
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .upload-modal-chart-card {
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: #f8fafc;
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #475569;
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: 1.2fr 3fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: #2563eb;
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: #0f172a;
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
  }

  .upload-modal-preview-table table {
    width: 100%;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
  }

  .upload-modal-preview-table th {
    background: #f8fafc;
    color: #0f172a;
  }

  .details__summary {
    user-select: none;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 13px;
    background: rgba(0, 93, 255, 0.06);
    border-bottom: 1px solid rgba(0, 93, 255, 0.12);
  }

  .details__content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .preview-box {
    margin-top: 6px;
    border: 1px solid rgba(0, 93, 255, 0.16);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.28);
    overflow: auto;
  }

  .preview-box table {
    width: 100%;
    border-collapse: collapse;
  }

  .preview-box th,
  .preview-box td {
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
    padding: 6px 8px;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-box th {
    background: rgba(160, 192, 232, 0.35);
    font-weight: 700;
  }

  .hint {
    font-size: 13px;
    color: #6b7280;
  }

  .actions {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    padding: 10px 0 14px;
  }

  .btn {
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-primary {
    background: #005dff;
    color: #fff;
    font-weight: 700;
  }

  .btn-primary:hover {
    background: #004fd8;
  }

  @media (max-width: 768px) {
    /* 手機：改為單欄表單，避免標籤與輸入框擠壓 */
    .setting-area {
      padding: 12px 14px 16px;
    }

    .panel-header h3 {
      font-size: 15px;
    }

    .panel-header p {
      font-size: 12px;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 6px;
    }

    .form-row label {
      font-size: 12px;
    }

    .form-row input,
    .form-row select {
      font-size: 12px;
      padding: 8px 9px;
    }

    .details__summary {
      font-size: 12px;
      padding: 9px 10px;
    }

    .actions {
      padding: 8px 0 12px;
    }

    .btn {
      width: 100%;
    }
  }

</style>
```

With:

```css
<style scoped>
  .setting-area {
    flex: 1;
    border: none;
    border-radius: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow: visible;
    padding: 14px 18px 0;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }

  .panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    background: transparent;
  }

  .panel-header {
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    background: transparent;
  }

  .panel-header h3 {
    margin: 0 0 2px;
    font-size: 16px;
    color: var(--color-ink);
  }

  .panel-header p {
    margin: 0;
    font-size: 13px;
    color: var(--color-secondary);
  }

  .panel-body {
    flex: 1;
    min-height: 0;
    overflow: visible;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 4px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 140px 1fr;
    align-items: center;
    gap: 10px;
  }

  .form-row label {
    font-size: 13px;
    font-weight: 600;
    color: var(--color-secondary);
  }

  .form-row input,
  .form-row select {
    border: 1px solid color-mix(in oklab, var(--color-accent) 20%, transparent);
    border-radius: 8px;
    padding: 7px 10px;
    font-size: 13px;
    outline: none;
    background: rgba(255, 255, 255, 0.5);
  }

  /* 隱藏原生 select 箭頭，換成自訂 chevron */
  .form-row select {
    appearance: none;
    -webkit-appearance: none;
    padding-right: 32px;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23E8A33D' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    cursor: pointer;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed color-mix(in oklab, var(--color-accent) 28%, transparent);
    border-radius: 16px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__title {
    font-size: 14px;
    font-weight: 700;
  }

  .upload-card__desc {
    margin: 0;
    color: var(--color-secondary);
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-card__input-row {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .upload-card__info {
    color: var(--color-ink);
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: var(--color-accent);
    background: color-mix(in oklab, var(--color-accent) 13%, transparent);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: var(--color-accent);
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .upload-modal-line2 {
    color: var(--color-secondary);
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .upload-modal-error {
    color: #ef4444;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    color: var(--color-ink);
    font-size: 16px;
    font-weight: 700;
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .upload-modal-chart-card {
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: var(--color-surface);
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: 1.2fr 3fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: var(--color-ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--color-accent);
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: var(--color-ink);
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
  }

  .upload-modal-preview-table table {
    width: 100%;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
  }

  .upload-modal-preview-table th {
    background: var(--color-surface);
    color: var(--color-ink);
  }

  .details__summary {
    user-select: none;
    padding: 10px 12px;
    font-weight: 600;
    font-size: 13px;
    background: color-mix(in oklab, var(--color-accent) 6%, transparent);
    border-bottom: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
  }

  .details__content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .preview-box {
    margin-top: 6px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 16%, transparent);
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.28);
    overflow: auto;
  }

  .preview-box table {
    width: 100%;
    border-collapse: collapse;
  }

  .preview-box th,
  .preview-box td {
    border-bottom: 1px solid #f0f2f5;
    text-align: left;
    padding: 6px 8px;
    font-size: 12px;
    white-space: nowrap;
  }

  .preview-box th {
    background: rgba(160, 192, 232, 0.35);
    font-weight: 700;
  }

  .hint {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .actions {
    flex-shrink: 0;
    display: flex;
    justify-content: flex-end;
    padding: 10px 0 14px;
  }

  .btn {
    border: none;
    border-radius: 10px;
    padding: 8px 16px;
    cursor: pointer;
    font-size: 13px;
  }

  .btn-primary {
    background: var(--color-accent);
    color: #fff;
    font-weight: 700;
  }

  .btn-primary:hover {
    background: color-mix(in oklab, var(--color-accent) 85%, black);
  }

  @media (max-width: 768px) {
    /* 手機：改為單欄表單，避免標籤與輸入框擠壓 */
    .setting-area {
      padding: 12px 14px 16px;
    }

    .panel-header h3 {
      font-size: 15px;
    }

    .panel-header p {
      font-size: 12px;
    }

    .form-row {
      grid-template-columns: 1fr;
      gap: 6px;
    }

    .form-row label {
      font-size: 12px;
    }

    .form-row input,
    .form-row select {
      font-size: 12px;
      padding: 8px 9px;
    }

    .details__summary {
      font-size: 12px;
      padding: 9px 10px;
    }

    .actions {
      padding: 8px 0 12px;
    }

    .btn {
      width: 100%;
    }
  }

</style>
```

Note: `.form-row input, .form-row select`'s `background: rgba(255, 255, 255, 0.5);`, `.preview-box`'s `background: rgba(255, 255, 255, 0.28);`, and `.preview-box th`'s `background: rgba(160, 192, 232, 0.35);` are intentionally unchanged — semi-transparent glass-panel overlays not covered by any named substitution rule. `.upload-modal-button`'s and `.btn-primary`'s `color: #fff;` stay literal (button text on an accent-colored background, not a white background).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "rgba(0, 93, 255\|#0f172a\|#6b7280\|#374151\|%23005DFF\|#2563eb\|rgba(59, 130, 246\|#1f2937\|#475569\|#b91c1c\|#f8fafc\|#005dff\|#004fd8" frontend/src/components/workflow/WorkflowOptionsPanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/WorkflowOptionsPanel.vue
git commit -m "feat: apply color tokens to WorkflowOptionsPanel"
```

---

### Task 8: `WorkflowWorkspace.vue`

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-surface`, `--color-accent`, `--color-ink` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .workspace {
    position: relative;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: auto;
    border-radius: 16px 16px 0 0;
    background-color: #f9fbff;
    background-image: radial-gradient(rgba(0, 93, 255, 0.035) 0.8px, transparent 0.8px);
    background-size: 16px 16px;
  }

  .workspace-canvas {
    flex: 1;
    min-height: 520px;
    width: 100%;
  }

  .demo-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0;
  }

  .demo-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .demo-btn:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .execute-workflow-btn {
    position: absolute;
    top: 14px;
    right: 120px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }

  .json-upload-btn {
    position: absolute;
    top: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .json-upload-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }

  .paper-upload-btn {
    position: absolute;
    top: 14px;
    right: 230px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(0, 93, 255, 0.18);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #005dff;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .paper-upload-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .gemini-upload-btn {
    position: absolute;
    top: 14px;
    right: 340px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 130px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(99, 102, 241, 0.3);
    background: rgba(238, 242, 255, 0.85);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #4f46e5;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .gemini-upload-btn:hover:not(:disabled) {
    background: rgba(224, 231, 255, 0.95);
  }

  .gemini-upload-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .workflow-result {
    position: absolute;
    top: 62px;
    right: 14px;
    z-index: 5;
    width: min(430px, calc(100% - 32px));
    max-height: 500px;
    overflow: auto;
    padding: 16px;
    background: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.32);
    border-radius: 16px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
    color: #0f172a;
  }

  .workflow-error {
    margin-bottom: 10px;
    color: #b91c1c;
    font-size: 13px;
    font-weight: 600;
  }

  .options-drawer {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.45);
    background: rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(16px);
    box-shadow: 0 -8px 18px rgba(15, 23, 42, 0.05);
    will-change: height, transform;
    transition: height 260ms cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    /* 安全上限：實際高度由 useDrawerDrag 精確控制各段大小，
       這裡固定用 full 段（90vh）當唯一上限，避免用分段 class
       卡高度時，收合到比自己上限還小的段落會被瞬間夾住而不是平滑動畫 */
    max-height: 90vh;
  }

  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    /* 永遠保留捲軸空間（兩側等寬），避免捲軸出現/消失時內容寬度跳動、且左右留白對稱 */
    scrollbar-gutter: stable both-edges;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .drawer-content-wrapper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .options-drawer__scroll::-webkit-scrollbar {
    width: 8px;
    height: 8px;
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.72);
    border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(6px);
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.85);
  }

  .options-drawer__bar {
    width: 52px;
    height: 5px;
    border-radius: 999px;
    background: rgba(0, 93, 255, 0.26);
    margin: 0 auto;
    cursor: grab;
  }

  .options-drawer__bar:active {
    cursor: grabbing;
  }

  .options-drawer__drag-zone {
    padding: 12px 0 0;
    cursor: grab;
    touch-action: none;
  }

  .options-drawer__drag-zone:active {
    cursor: grabbing;
  }

  @media (max-width: 768px) {
    .workspace {
      border-radius: 12px;
    }

    .options-drawer {
      border-top-left-radius: 12px;
      border-top-right-radius: 12px;
    }

    .options-drawer__drag-zone {
      padding: 14px 0 8px;
    }
  }

  .slide-up-enter-active,
  .slide-up-leave-active {
    transition: transform 0.22s ease, opacity 0.22s ease;
  }

  .slide-up-enter-from,
  .slide-up-leave-to {
    transform: translateY(100%);
    opacity: 0;
  }

  .slide-up-enter-to,
  .slide-up-leave-from {
    transform: translateY(0);
    opacity: 1;
  }

  .drawer-content-enter-active,
  .drawer-content-leave-active {
    transition: opacity 180ms ease, transform 180ms ease;
  }

  .drawer-content-enter-from,
  .drawer-content-leave-to {
    opacity: 0;
    transform: translateY(8px);
  }

  .drawer-content-enter-to,
  .drawer-content-leave-from {
    opacity: 1;
    transform: translateY(0);
  }
</style>
```

With:

```css
<style scoped>
  .workspace {
    position: relative;
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: auto;
    border-radius: 16px 16px 0 0;
    background-color: var(--color-surface);
    background-image: radial-gradient(color-mix(in oklab, var(--color-accent) 3.5%, transparent) 0.8px, transparent 0.8px);
    background-size: 16px 16px;
  }

  .workspace-canvas {
    flex: 1;
    min-height: 520px;
    width: 100%;
  }

  .demo-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: var(--color-accent);
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0;
  }

  .demo-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .demo-btn:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .execute-workflow-btn {
    position: absolute;
    top: 14px;
    right: 120px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: var(--color-accent);
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn {
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: var(--color-accent);
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .view-results-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }

  .json-upload-btn {
    position: absolute;
    top: 14px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: var(--color-accent);
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .json-upload-btn:hover {
    background: rgba(255, 255, 255, 0.92);
  }

  .paper-upload-btn {
    position: absolute;
    top: 14px;
    right: 230px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 92px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: var(--color-accent);
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .paper-upload-btn:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.92);
  }

  .gemini-upload-btn {
    position: absolute;
    top: 14px;
    right: 340px;
    z-index: 5;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 130px;
    height: 36px;
    border-radius: 999px;
    border: 1.5px solid rgba(99, 102, 241, 0.3);
    background: rgba(238, 242, 255, 0.85);
    backdrop-filter: blur(8px);
    font-size: 13px;
    color: #4f46e5;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
    user-select: none;
    padding: 0 14px;
  }

  .gemini-upload-btn:hover:not(:disabled) {
    background: rgba(224, 231, 255, 0.95);
  }

  .gemini-upload-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .workflow-result {
    position: absolute;
    top: 62px;
    right: 14px;
    z-index: 5;
    width: min(430px, calc(100% - 32px));
    max-height: 500px;
    overflow: auto;
    padding: 16px;
    background: var(--color-surface);
    border: 1px solid rgba(148, 163, 184, 0.32);
    border-radius: 16px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
    color: var(--color-ink);
  }

  .workflow-error {
    margin-bottom: 10px;
    color: #ef4444;
    font-size: 13px;
    font-weight: 600;
  }

  .options-drawer {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 10;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.45);
    background: rgba(255, 255, 255, 0.45);
    backdrop-filter: blur(16px);
    box-shadow: 0 -8px 18px rgba(15, 23, 42, 0.05);
    will-change: height, transform;
    transition: height 260ms cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    /* 安全上限：實際高度由 useDrawerDrag 精確控制各段大小，
       這裡固定用 full 段（90vh）當唯一上限，避免用分段 class
       卡高度時，收合到比自己上限還小的段落會被瞬間夾住而不是平滑動畫 */
    max-height: 90vh;
  }

  .options-drawer__scroll {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
    /* 永遠保留捲軸空間（兩側等寬），避免捲軸出現/消失時內容寬度跳動、且左右留白對稱 */
    scrollbar-gutter: stable both-edges;
    overscroll-behavior: contain;
    padding-bottom: 16px;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.72) transparent;
  }

  .drawer-content-wrapper {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .options-drawer__scroll::-webkit-scrollbar {
    width: 8px;
    height: 8px;
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-track {
    background: transparent;
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.72);
    border-radius: 999px;
    border: 2px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(6px);
  }

  .options-drawer__scroll::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.85);
  }

  .options-drawer__bar {
    width: 52px;
    height: 5px;
    border-radius: 999px;
    background: color-mix(in oklab, var(--color-accent) 26%, transparent);
    margin: 0 auto;
    cursor: grab;
  }

  .options-drawer__bar:active {
    cursor: grabbing;
  }

  .options-drawer__drag-zone {
    padding: 12px 0 0;
    cursor: grab;
    touch-action: none;
  }

  .options-drawer__drag-zone:active {
    cursor: grabbing;
  }

  @media (max-width: 768px) {
    .workspace {
      border-radius: 12px;
    }

    .options-drawer {
      border-top-left-radius: 12px;
      border-top-right-radius: 12px;
    }

    .options-drawer__drag-zone {
      padding: 14px 0 8px;
    }
  }

  .slide-up-enter-active,
  .slide-up-leave-active {
    transition: transform 0.22s ease, opacity 0.22s ease;
  }

  .slide-up-enter-from,
  .slide-up-leave-to {
    transform: translateY(100%);
    opacity: 0;
  }

  .slide-up-enter-to,
  .slide-up-leave-from {
    transform: translateY(0);
    opacity: 1;
  }

  .drawer-content-enter-active,
  .drawer-content-leave-active {
    transition: opacity 180ms ease, transform 180ms ease;
  }

  .drawer-content-enter-from,
  .drawer-content-leave-to {
    opacity: 0;
    transform: translateY(8px);
  }

  .drawer-content-enter-to,
  .drawer-content-leave-from {
    opacity: 1;
    transform: translateY(0);
  }
</style>
```

Note: `.gemini-upload-btn` (and its hover/disabled states) is entirely unchanged — indigo decorative functional-icon color, excluded per Global Constraints. `.options-drawer`, `.options-drawer__scroll`, and their scrollbar rules keep their `rgba(255, 255, 255, *)` glass-panel values unchanged (not covered by any substitution rule).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#f9fbff\|rgba(0, 93, 255\|#005dff\|#ffffff\|#0f172a\|#b91c1c" frontend/src/components/workflow/WorkflowWorkspace.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: apply color tokens to WorkflowWorkspace"
```

---

### Task 9: `ComputeCiPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .ci-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* ── 有結果：header ── */
  .ci-panel__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .ci-panel__icon {
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
  }

  .ci-panel__title {
    margin: 0 0 2px;
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
  }

  .ci-panel__sub {
    margin: 0;
    font-size: 11px;
    color: #64748b;
  }

  /* ── 模型區塊 ── */
  .ci-model-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    background: rgba(0, 93, 255, 0.03);
    border: 1px solid rgba(0, 93, 255, 0.1);
    border-radius: 8px;
  }

  .ci-model-block__name {
    font-size: 12px;
    font-weight: 700;
    color: #005dff;
  }

  /* ── Split ── */
  .ci-split {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ci-split__label {
    font-size: 11px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  /* ── 表格 ── */
  .ci-table {
    display: flex;
    flex-direction: column;
    gap: 1px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 6px;
    overflow: hidden;
  }

  .ci-table__header,
  .ci-table__row {
    display: grid;
    grid-template-columns: 1.6fr 1fr 1fr 1fr;
    font-size: 11px;
    padding: 4px 8px;
  }

  .ci-table__header {
    font-weight: 600;
    color: #94a3b8;
    background: #f8fafc;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  .ci-table__header span:not(:first-child) {
    text-align: center;
  }

  .ci-table__row {
    background: #fff;
  }

  .ci-table__row:nth-child(even) {
    background: #f8fafc;
  }

  .ci-table__metric {
    color: #334155;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ci-table__num {
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: #64748b;
  }

  .ci-table__num--val {
    font-weight: 700;
    color: #1e293b;
  }

  .ci-table__num--lo,
  .ci-table__num--hi {
    color: #94a3b8;
  }

  /* ── 無結果：靜態介紹 ── */
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
    font-size: 12px;
    color: #92400e;
    line-height: 1.5;
  }

  .ci-info__notice p,
  .ci-info__footer p {
    margin: 0;
  }

  .ci-info__footer {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.12);
    border-radius: 8px;
    font-size: 12px;
    color: #475569;
    line-height: 1.5;
  }

  .ci-info__footer strong {
    color: #005dff;
  }
</style>
```

With:

```css
<style scoped>
  .ci-panel {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  /* ── 有結果：header ── */
  .ci-panel__header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
  }

  .ci-panel__icon {
    font-size: 22px;
    line-height: 1;
    flex-shrink: 0;
  }

  .ci-panel__title {
    margin: 0 0 2px;
    font-size: 14px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .ci-panel__sub {
    margin: 0;
    font-size: 11px;
    color: var(--color-secondary);
  }

  /* ── 模型區塊 ── */
  .ci-model-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 10px;
    background: color-mix(in oklab, var(--color-accent) 3%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    border-radius: 8px;
  }

  .ci-model-block__name {
    font-size: 12px;
    font-weight: 700;
    color: var(--color-accent);
  }

  /* ── Split ── */
  .ci-split {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ci-split__label {
    font-size: 11px;
    font-weight: 600;
    color: var(--color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }

  /* ── 表格 ── */
  .ci-table {
    display: flex;
    flex-direction: column;
    gap: 1px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 6px;
    overflow: hidden;
  }

  .ci-table__header,
  .ci-table__row {
    display: grid;
    grid-template-columns: 1.6fr 1fr 1fr 1fr;
    font-size: 11px;
    padding: 4px 8px;
  }

  .ci-table__header {
    font-weight: 600;
    color: var(--color-secondary);
    background: var(--color-surface);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  }

  .ci-table__header span:not(:first-child) {
    text-align: center;
  }

  .ci-table__row {
    background: var(--color-surface);
  }

  .ci-table__row:nth-child(even) {
    background: var(--color-surface);
  }

  .ci-table__metric {
    color: var(--color-secondary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ci-table__num {
    text-align: center;
    font-variant-numeric: tabular-nums;
    color: var(--color-secondary);
  }

  .ci-table__num--val {
    font-weight: 700;
    color: var(--color-ink);
  }

  .ci-table__num--lo,
  .ci-table__num--hi {
    color: var(--color-secondary);
  }

  /* ── 無結果：靜態介紹 ── */
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
    color: var(--color-ink);
  }

  .ci-info__sub {
    margin: 0;
    font-size: 11px;
    color: var(--color-secondary);
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
    color: var(--color-secondary);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .ci-info__text {
    margin: 0;
    font-size: 12px;
    color: var(--color-secondary);
    line-height: 1.6;
  }

  .ci-info__list {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 12px;
    color: var(--color-secondary);
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
    font-size: 12px;
    color: #92400e;
    line-height: 1.5;
  }

  .ci-info__notice p,
  .ci-info__footer p {
    margin: 0;
  }

  .ci-info__footer {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
    border-radius: 8px;
    font-size: 12px;
    color: var(--color-secondary);
    line-height: 1.5;
  }

  .ci-info__footer strong {
    color: var(--color-accent);
  }
</style>
```

Note: `.ci-info__notice`'s `rgba(245, 158, 11, *)` background/border and `color: #92400e;` are intentionally unchanged — the excluded warning amber status color.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#1e293b\|#64748b\|rgba(0, 93, 255\|#005dff\|#94a3b8\|#f8fafc\|#334155\|#475569" frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue`
Expected: no output.

Run: `grep -n "#92400e" frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue`
Expected: exactly 1 match, inside `.ci-info__notice` — confirms the warning amber is untouched.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/ComputeCiPanel.vue
git commit -m "feat: apply color tokens to ComputeCiPanel"
```

---

### Task 10: `DataTablePanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DataTablePanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .data-table-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 14px;
    position: relative;
  }

  .data-table-loading-overlay {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12px;
    padding: 24px;
    border-radius: 16px;
    border: 1px dashed rgba(96, 165, 250, 0.7);
    background: rgba(255, 255, 255, 0.88);
    color: #005dff;
    font-size: 14px;
    z-index: 10;
  }

  .data-table-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .data-table-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .data-table-file {
    flex-shrink: 0;
    margin-left: auto;
    color: #475569;
    font-size: 13px;
  }

  .data-table-empty {
    padding: 20px;
    border-radius: 12px;
    background: #f8fafc;
    color: #475569;
  }

  .data-table-summary,
  .data-table-summary-inline {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }

  .data-table-summary {
    margin-bottom: 12px;
  }

  .data-table-summary-inline {
    flex: 1 1 auto;
    min-width: 0;
    white-space: nowrap;
  }

  .data-table-guide {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: #005dff;
    font-size: 13px;
    line-height: 1.4;
  }

  .data-table-guide strong {
    color: #005dff;
  }

  .data-table-guide--ready {
    color: #10b981;
  }

  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 0;
    border-radius: 12px;
    border: 1px solid rgba(0, 93, 255, 0.12);
    background: #ffffff;
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }

  .column-settings-title {
    flex-shrink: 0;
    padding: 10px 12px;
    font-size: 13px;
    color: #475569;
    font-weight: 600;
  }

  .column-settings-body {
    overflow-y: auto;
    flex: 1;
    min-height: 0;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    scrollbar-color: rgba(148, 163, 184, 0.5) transparent;
  }

  .column-settings-body::-webkit-scrollbar {
    width: 6px;
  }

  .column-settings-body::-webkit-scrollbar-track {
    background: transparent;
  }

  .column-settings-body::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.5);
  }

  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 10px 12px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), #ffffff 70%);
    flex-shrink: 0;
  }

  .column-settings-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }

  .column-settings-table th:nth-child(1),
  .column-settings-table td:nth-child(1) {
    width: 37%;
  }

  .column-settings-table th:nth-child(2),
  .column-settings-table td:nth-child(2) {
    width: 26%;
  }

  .column-settings-table th:nth-child(3),
  .column-settings-table td:nth-child(3) {
    width: 22%;
  }

  .column-settings-table th:nth-child(4),
  .column-settings-table td:nth-child(4) {
    width: 15%;
  }

  .column-settings-table thead th {
    position: sticky;
    top: 0;
    background: #f8fafc;
    font-weight: 600;
    z-index: 1;
  }

  .column-settings-table th,
  .column-settings-table td {
    padding: 10px 8px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    text-align: left;
    font-size: 13px;
    color: #0f172a;
  }

  .column-name-input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid rgba(0, 93, 255, 0.35);
    border-radius: 8px;
    background: #f8fafc;
    font-size: 13px;
    color: #0f172a;
  }

  .values-cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .btn-reset,
  .btn-apply {
    min-width: 88px;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-reset {
    background: #f8fafc;
    color: #0f172a;
    border: 1px solid rgba(0, 93, 255, 0.18);
  }

  .btn-apply {
    background: #005dff;
    color: #fff;
  }

  .btn-apply--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .column-settings-table select {
    width: 100%;
    padding: 8px 30px 8px 10px;
    border: 1px solid rgba(0, 93, 255, 0.35);
    border-radius: 8px;
    background-color: #fff;
    font-size: 13px;
    color: #0f172a;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    /* 補上下拉箭頭，明確表示這是可點的下拉選單 */
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23005DFF' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  .column-settings-table select:hover {
    border-color: #005dff;
  }

  .column-settings-table select:focus {
    border-color: #005dff;
    box-shadow: 0 0 0 3px rgba(0, 93, 255, 0.15);
    outline: none;
  }

  /* Role 欄引導：下拉選單右下角的灰色「tap here」漣漪圈 */
  .role-select-wrap {
    position: relative;
  }

  .tap-hint {
    position: absolute;
    right: -7px;
    bottom: -7px;
    width: 24px;
    height: 24px;
    pointer-events: none;
    z-index: 2;
  }

  /* 點過 Role 選單後，圈圈淡出消失，而不是瞬間不見 */
  .tap-hint-fade-leave-active {
    transition: opacity 0.3s ease;
  }

  .tap-hint-fade-leave-to {
    opacity: 0;
  }

  .tap-hint__dot {
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: rgba(100, 116, 139, 0.7);
  }

  .tap-hint__ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2.5px solid rgba(100, 116, 139, 0.85);
    opacity: 0;
    animation: tap-ripple 2.4s ease-out infinite;
  }

  .tap-hint__ring--delay {
    animation-delay: 1.2s;
  }

  /* 從中間點的邊緣(scale 0.75 = 點的大小)往外擴 */
  @keyframes tap-ripple {
    0% {
      transform: scale(0.75);
      opacity: 0.9;
    }
    100% {
      transform: scale(1.5);
      opacity: 0;
    }
  }

  /* 未選 target 前，Role 下拉維持靜態高亮，把動效留給漣漪圈 */
  .role-select--attention {
    border-color: #94a3b8;
  }

  @media (prefers-reduced-motion: reduce) {
    .tap-hint__ring {
      animation: none;
      opacity: 0.5;
    }
  }

  .target-row td,
  .target-cell {
    background: rgba(0, 93, 255, 0.1);
  }

  .target-row {
    background: transparent;
  }

  .loader {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0, 93, 255, 0.25);
    border-top-color: #005dff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
```

With:

```css
<style scoped>
  .data-table-panel {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    gap: 14px;
    position: relative;
  }

  .data-table-loading-overlay {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12px;
    padding: 24px;
    border-radius: 16px;
    border: 1px dashed rgba(96, 165, 250, 0.7);
    background: rgba(255, 255, 255, 0.88);
    color: var(--color-accent);
    font-size: 14px;
    z-index: 10;
  }

  .data-table-body {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }

  .data-table-header {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .data-table-file {
    flex-shrink: 0;
    margin-left: auto;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .data-table-empty {
    padding: 20px;
    border-radius: 12px;
    background: var(--color-surface);
    color: var(--color-secondary);
  }

  .data-table-summary,
  .data-table-summary-inline {
    display: flex;
    gap: 14px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .data-table-summary {
    margin-bottom: 12px;
  }

  .data-table-summary-inline {
    flex: 1 1 auto;
    min-width: 0;
    white-space: nowrap;
  }

  .data-table-guide {
    flex: 1 1 auto;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--color-accent);
    font-size: 13px;
    line-height: 1.4;
  }

  .data-table-guide strong {
    color: var(--color-accent);
  }

  .data-table-guide--ready {
    color: #16a34a;
  }

  .data-table-column-settings {
    display: flex;
    flex-direction: column;
    padding: 0;
    border-radius: 12px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
    background: var(--color-surface);
    flex: 1 1 380px;
    min-height: 380px;
    overflow: hidden;
  }

  .column-settings-title {
    flex-shrink: 0;
    padding: 10px 12px;
    font-size: 13px;
    color: var(--color-secondary);
    font-weight: 600;
  }

  .column-settings-body {
    overflow-y: auto;
    flex: 1;
    min-height: 0;
    overscroll-behavior: contain;
    scrollbar-width: thin;
    scrollbar-color: rgba(148, 163, 184, 0.5) transparent;
  }

  .column-settings-body::-webkit-scrollbar {
    width: 6px;
  }

  .column-settings-body::-webkit-scrollbar-track {
    background: transparent;
  }

  .column-settings-body::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: rgba(148, 163, 184, 0.5);
  }

  .column-settings-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    padding: 10px 12px;
    border-top: 1px solid rgba(148, 163, 184, 0.12);
    background: linear-gradient(180deg, rgba(255, 255, 255, 0), var(--color-surface) 70%);
    flex-shrink: 0;
  }

  .column-settings-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
  }

  .column-settings-table th:nth-child(1),
  .column-settings-table td:nth-child(1) {
    width: 37%;
  }

  .column-settings-table th:nth-child(2),
  .column-settings-table td:nth-child(2) {
    width: 26%;
  }

  .column-settings-table th:nth-child(3),
  .column-settings-table td:nth-child(3) {
    width: 22%;
  }

  .column-settings-table th:nth-child(4),
  .column-settings-table td:nth-child(4) {
    width: 15%;
  }

  .column-settings-table thead th {
    position: sticky;
    top: 0;
    background: var(--color-surface);
    font-weight: 600;
    z-index: 1;
  }

  .column-settings-table th,
  .column-settings-table td {
    padding: 10px 8px;
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
    text-align: left;
    font-size: 13px;
    color: var(--color-ink);
  }

  .column-name-input {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 35%, transparent);
    border-radius: 8px;
    background: var(--color-surface);
    font-size: 13px;
    color: var(--color-ink);
  }

  .values-cell {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .btn-reset,
  .btn-apply {
    min-width: 88px;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-reset {
    background: var(--color-surface);
    color: var(--color-ink);
    border: 1px solid color-mix(in oklab, var(--color-accent) 18%, transparent);
  }

  .btn-apply {
    background: var(--color-accent);
    color: #fff;
  }

  .btn-apply--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .column-settings-table select {
    width: 100%;
    padding: 8px 30px 8px 10px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 35%, transparent);
    border-radius: 8px;
    background-color: var(--color-surface);
    font-size: 13px;
    color: var(--color-ink);
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    /* 補上下拉箭頭，明確表示這是可點的下拉選單 */
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24'%3E%3Cpath fill='%23E8A33D' d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    transition: border-color 0.12s, box-shadow 0.12s;
  }

  .column-settings-table select:hover {
    border-color: var(--color-accent);
  }

  .column-settings-table select:focus {
    border-color: var(--color-accent);
    box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-accent) 15%, transparent);
    outline: none;
  }

  /* Role 欄引導：下拉選單右下角的灰色「tap here」漣漪圈 */
  .role-select-wrap {
    position: relative;
  }

  .tap-hint {
    position: absolute;
    right: -7px;
    bottom: -7px;
    width: 24px;
    height: 24px;
    pointer-events: none;
    z-index: 2;
  }

  /* 點過 Role 選單後，圈圈淡出消失，而不是瞬間不見 */
  .tap-hint-fade-leave-active {
    transition: opacity 0.3s ease;
  }

  .tap-hint-fade-leave-to {
    opacity: 0;
  }

  .tap-hint__dot {
    position: absolute;
    inset: 3px;
    border-radius: 50%;
    background: rgba(100, 116, 139, 0.7);
  }

  .tap-hint__ring {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 2.5px solid rgba(100, 116, 139, 0.85);
    opacity: 0;
    animation: tap-ripple 2.4s ease-out infinite;
  }

  .tap-hint__ring--delay {
    animation-delay: 1.2s;
  }

  /* 從中間點的邊緣(scale 0.75 = 點的大小)往外擴 */
  @keyframes tap-ripple {
    0% {
      transform: scale(0.75);
      opacity: 0.9;
    }
    100% {
      transform: scale(1.5);
      opacity: 0;
    }
  }

  /* 未選 target 前，Role 下拉維持靜態高亮，把動效留給漣漪圈 */
  .role-select--attention {
    border-color: #94a3b8;
  }

  @media (prefers-reduced-motion: reduce) {
    .tap-hint__ring {
      animation: none;
      opacity: 0.5;
    }
  }

  .target-row td,
  .target-cell {
    background: color-mix(in oklab, var(--color-accent) 10%, transparent);
  }

  .target-row {
    background: transparent;
  }

  .loader {
    width: 16px;
    height: 16px;
    border: 2px solid color-mix(in oklab, var(--color-accent) 25%, transparent);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
```

Note: `#94a3b8` and `rgba(100, 116, 139, *)` are intentionally unchanged in this file — `.btn-apply--disabled`'s and `.role-select--attention`'s uses are neutral disabled/attention-state greys (not brand text), and `rgba(100, 116, 139, *)`/`rgba(148, 163, 184, *)` are the same neutral-grey family used elsewhere as excluded borders, just applied here as decorative "tap hint" ripple colors. This distinction (opaque hex as text color converts; the same grey family used as a translucent border/background/state indicator does not) applies consistently in later tasks too.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#005dff\|#475569\|#f8fafc\|#10b981\|rgba(0, 93, 255\|#ffffff\|#0f172a\|%23005DFF" frontend/src/components/workflow/nodePanel/DataTablePanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DataTablePanel.vue
git commit -m "feat: apply color tokens to DataTablePanel"
```

---

### Task 11: `DistributionPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/DistributionPanel.vue` (template SVG `fill` attributes, plus the entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit the SVG bar-chart `fill` attributes in the template**

Replace:

```html
                  <rect
                    fill="#2563eb"
                    :height="
                      Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                    rx="6"
                    :width="Math.max(24, 280 / chart.counts.length - 8)"
                    :x="12 + idx * (300 / chart.counts.length)"
                    :y="
                      150 -
                        Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                  />
                  <text
                    fill="#475569"
                    font-size="10"
                    text-anchor="middle"
                    :x="
                      12 +
                        idx * (300 / chart.counts.length) +
                        Math.max(24, 280 / chart.counts.length - 8) / 2
                    "
                    y="165"
                  >
                    {{ item.label }}
                  </text>
                  <text
                    fill="#0f172a"
                    font-size="10"
                    text-anchor="middle"
                    :x="
                      12 +
                        idx * (300 / chart.counts.length) +
                        Math.max(24, 280 / chart.counts.length - 8) / 2
                    "
                    :y="
                      140 -
                        Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                  >
                    {{ item.count }}
                  </text>
```

With:

```html
                  <rect
                    fill="var(--color-accent)"
                    :height="
                      Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                    rx="6"
                    :width="Math.max(24, 280 / chart.counts.length - 8)"
                    :x="12 + idx * (300 / chart.counts.length)"
                    :y="
                      150 -
                        Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                  />
                  <text
                    fill="var(--color-secondary)"
                    font-size="10"
                    text-anchor="middle"
                    :x="
                      12 +
                        idx * (300 / chart.counts.length) +
                        Math.max(24, 280 / chart.counts.length - 8) / 2
                    "
                    y="165"
                  >
                    {{ item.label }}
                  </text>
                  <text
                    fill="var(--color-ink)"
                    font-size="10"
                    text-anchor="middle"
                    :x="
                      12 +
                        idx * (300 / chart.counts.length) +
                        Math.max(24, 280 / chart.counts.length - 8) / 2
                    "
                    :y="
                      140 -
                        Math.max(4, Math.round((item.count / chart.maxCount) * 110))
                    "
                  >
                    {{ item.count }}
                  </text>
```

- [ ] **Step 2: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .distribution-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .distribution-panel--full {
    flex: 1;
    min-height: 0;
  }

  .distribution-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .distribution-title {
    font-weight: 700;
    font-size: 16px;
  }

  .distribution-file {
    flex-shrink: 0;
    margin-left: auto;
    color: #475569;
    font-size: 13px;
  }

  .distribution-empty {
    padding: 24px;
    border-radius: 12px;
    background: #f8fafc;
    color: #475569;
  }

  .distribution-summary {
    display: flex;
    gap: 14px;
    color: #475569;
    font-size: 13px;
  }

  .distribution-chart-grid {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .distribution-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .distribution-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .distribution-chart-grid--full {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    align-content: start;
    flex: 1 1 380px;
    min-height: 380px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .distribution-chart-grid--full .distribution-chart-card {
    flex: none;
    min-width: 0;
  }

  .distribution-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    border-radius: 16px;
    background: rgba(248, 250, 252, 0.9);
    color: #475569;
    font-size: 14px;
  }

  .distribution-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    padding: 12px;
    border-radius: 16px;
    background: white;
    border: 1px solid rgba(148, 163, 184, 0.16);
    scroll-snap-align: start;
    overflow-wrap: anywhere;
  }

  .distribution-chart-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
    color: #475569;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    -webkit-line-clamp: 2;
  }

  .distribution-chart-title.expanded {
    -webkit-line-clamp: unset;
    white-space: normal;
  }

  .distribution-title-toggle {
    border: none;
    background: transparent;
    color: #2563eb;
    font-size: 12px;
    padding: 0;
    margin-bottom: 8px;
    cursor: pointer;
    text-align: left;
  }

  .distribution-chart-subtitle {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 10px;
  }

  .distribution-chart-meta {
    display: flex;
    justify-content: space-between;
    color: #64748b;
    font-size: 12px;
    margin-bottom: 8px;
  }

  .distribution-chart-plot {
    background: #f8fafc;
    border-radius: 12px;
    padding: 10px;
  }
</style>
```

With:

```css
<style scoped>
  .distribution-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .distribution-panel--full {
    flex: 1;
    min-height: 0;
  }

  .distribution-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .distribution-title {
    font-weight: 700;
    font-size: 16px;
  }

  .distribution-file {
    flex-shrink: 0;
    margin-left: auto;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .distribution-empty {
    padding: 24px;
    border-radius: 12px;
    background: var(--color-surface);
    color: var(--color-secondary);
  }

  .distribution-summary {
    display: flex;
    gap: 14px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .distribution-chart-grid {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .distribution-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .distribution-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .distribution-chart-grid--full {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    align-content: start;
    flex: 1 1 380px;
    min-height: 380px;
    overflow-y: auto;
    overflow-x: hidden;
  }

  .distribution-chart-grid--full .distribution-chart-card {
    flex: none;
    min-width: 0;
  }

  .distribution-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    border-radius: 16px;
    background: rgba(248, 250, 252, 0.9);
    color: var(--color-secondary);
    font-size: 14px;
  }

  .distribution-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    padding: 12px;
    border-radius: 16px;
    background: var(--color-surface);
    border: 1px solid rgba(148, 163, 184, 0.16);
    scroll-snap-align: start;
    overflow-wrap: anywhere;
  }

  .distribution-chart-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
    color: var(--color-secondary);
    display: -webkit-box;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    -webkit-line-clamp: 2;
  }

  .distribution-chart-title.expanded {
    -webkit-line-clamp: unset;
    white-space: normal;
  }

  .distribution-title-toggle {
    border: none;
    background: transparent;
    color: var(--color-accent);
    font-size: 12px;
    padding: 0;
    margin-bottom: 8px;
    cursor: pointer;
    text-align: left;
  }

  .distribution-chart-subtitle {
    font-size: 12px;
    color: var(--color-secondary);
    margin-bottom: 10px;
  }

  .distribution-chart-meta {
    display: flex;
    justify-content: space-between;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 8px;
  }

  .distribution-chart-plot {
    background: var(--color-surface);
    border-radius: 12px;
    padding: 10px;
  }
</style>
```

- [ ] **Step 3: Verify no leftover old color values**

Run: `grep -n "#475569\|#f8fafc\|#2563eb\|#64748b\|fill=\"#\|background: white" frontend/src/components/workflow/nodePanel/DistributionPanel.vue`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/DistributionPanel.vue
git commit -m "feat: apply color tokens to DistributionPanel"
```

---

### Task 12: `FeatureEngineeringPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .feature-engineering-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: #475569;
  }

  .steps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: #1e293b;
    min-width: 0;
    word-break: break-word;
  }

  .step-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed #e2e8f0;
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    color: #0f172a;
    font-weight: 500;
  }

  .empty-hint {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

With:

```css
<style scoped>
  .feature-engineering-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .steps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    background: var(--color-surface);
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-ink);
    min-width: 0;
    word-break: break-word;
  }

  .step-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed #e2e8f0;
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    color: var(--color-ink);
    font-weight: 500;
  }

  .empty-hint {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
```

Note: `.step-index`'s `background: #e0e7ff; color: #4f46e5;` is intentionally unchanged — the excluded indigo step-number badge (see Global Constraints).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#475569\|#f8fafc\|#1e293b\|#64748b\|#0f172a\|#6b7280" frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue`
Expected: no output.

Run: `grep -n "#4f46e5" frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue`
Expected: exactly 1 match, inside `.step-index`.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureEngineeringPanel.vue
git commit -m "feat: apply color tokens to FeatureEngineeringPanel"
```

---

### Task 13: `FeatureImportancePanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .feature-importance-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 0 0 16px;
  }

  /* 控制列：模型｜下拉  fold｜下拉，label 在下拉左邊、兩組並排 */
  .fi-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .fi-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .fi-field__label {
    font-size: 13px;
    color: #475569;
    white-space: nowrap;
  }

  .fi-select {
    width: 160px;
  }

  /* 表格沿用 Test & Score 的圓角卡片樣式，維持結果面板一致 */
  .fi-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
  }

  .fi-row {
    display: grid;
    grid-template-columns: 1fr 140px;
    gap: 0;
    align-items: center;
  }

  .fi-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .fi-row:not(.fi-row--header):hover {
    background: rgba(0, 93, 255, 0.035);
  }

  .fi-row--header {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
  }

  .fi-row--header .fi-cell {
    padding: 8px 14px;
  }

  .fi-cell {
    padding: 11px 14px;
    color: #0f172a;
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
  }

  .fi-cell--feature {
    color: #1e293b;
  }

  .fi-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

With:

```css
<style scoped>
  .feature-importance-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 0 0 16px;
  }

  /* 控制列：模型｜下拉  fold｜下拉，label 在下拉左邊、兩組並排 */
  .fi-controls {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }

  .fi-field {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .fi-field__label {
    font-size: 13px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .fi-select {
    width: 160px;
  }

  /* 表格沿用 Test & Score 的圓角卡片樣式，維持結果面板一致 */
  .fi-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: var(--color-surface);
  }

  .fi-row {
    display: grid;
    grid-template-columns: 1fr 140px;
    gap: 0;
    align-items: center;
  }

  .fi-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .fi-row:not(.fi-row--header):hover {
    background: color-mix(in oklab, var(--color-accent) 3.5%, transparent);
  }

  .fi-row--header {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-secondary);
    background: var(--color-surface);
  }

  .fi-row--header .fi-cell {
    padding: 8px 14px;
  }

  .fi-cell {
    padding: 11px 14px;
    color: var(--color-ink);
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
  }

  .fi-cell--feature {
    color: var(--color-ink);
  }

  .fi-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#475569\|#ffffff\|rgba(0, 93, 255\|#f8fafc\|#0f172a\|#1e293b\|#6b7280" frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/FeatureImportancePanel.vue
git commit -m "feat: apply color tokens to FeatureImportancePanel"
```

---

### Task 14: `PreprocessorPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .preprocessor-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: #475569;
  }

  .steps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: #1e293b;
    min-width: 0;
    word-break: break-word;
  }

  .step-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed #e2e8f0;
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    color: #0f172a;
    font-weight: 500;
  }

  .empty-hint {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

With:

```css
<style scoped>
  .preprocessor-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 4px 0;
  }

  .step-count {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .steps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .step-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    background: var(--color-surface);
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    font-size: 13px;
  }

  .step-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .step-index {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #e0e7ff;
    color: #4f46e5;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .step-label {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-ink);
    min-width: 0;
    word-break: break-word;
  }

  .step-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed #e2e8f0;
  }

  .param-row {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .param-val {
    font-size: 13px;
    color: var(--color-ink);
    font-weight: 500;
  }

  .empty-hint {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
```

Note: `.step-index`'s `background: #e0e7ff; color: #4f46e5;` is intentionally unchanged — the excluded indigo step-number badge (see Global Constraints).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#475569\|#f8fafc\|#1e293b\|#64748b\|#0f172a\|#6b7280" frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue`
Expected: no output.

Run: `grep -n "#4f46e5" frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue`
Expected: exactly 1 match, inside `.step-index`.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/PreprocessorPanel.vue
git commit -m "feat: apply color tokens to PreprocessorPanel"
```

---

### Task 15: `SettingsPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/SettingsPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .settings-wizard {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* 步驟頁籤 */
  .wizard-tabs {
    flex-shrink: 0;
    display: flex;
    gap: 4px;
    padding: 4px;
    background: rgba(0, 93, 255, 0.05);
    border-radius: 12px;
  }

  .wizard-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 4px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  }

  .wizard-tab--active {
    background: #fff;
    color: #005dff;
    font-weight: 700;
    box-shadow: 0 1px 5px rgba(0, 93, 255, 0.14);
  }

  .wizard-tab__num {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    background: rgba(100, 116, 139, 0.12);
    color: #64748b;
    transition: background 0.15s, color 0.15s;
  }

  .wizard-tab--active .wizard-tab__num {
    background: #005dff;
    color: #fff;
  }

  .wizard-tab__text {
    white-space: nowrap;
  }

  .wizard-tab__required {
    font-size: 9px;
    font-weight: 700;
    color: #ef4444;
    background: rgba(239, 68, 68, 0.12);
    border-radius: 6px;
    padding: 1px 4px;
    white-space: nowrap;
  }

  /* Step 內容 */
  .step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .add-bar {
    display: flex;
    gap: 6px;
  }

  /* 只保留 add-bar 的 flex 佈局，外觀交給 CustomSelect 自己畫 */
  .type-select {
    flex: 1;
    min-width: 0;
  }

  .add-btn {
    height: 32px;
    padding: 0 14px;
    border: none;
    border-radius: 8px;
    background: #005dff;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
    transition: opacity 0.12s;
  }

  .add-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .add-btn:not(:disabled):hover {
    opacity: 0.82;
  }

  .item-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .item-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.1);
    border-radius: 8px;
    font-size: 13px;
  }

  .item-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .item-idx {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: rgba(0, 93, 255, 0.12);
    color: #005dff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .item-idx--dot {
    background: rgba(0, 93, 255, 0.2);
  }

  .item-name {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: #1e293b;
    min-width: 0;
    word-break: break-word;
  }

  .item-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed rgba(0, 93, 255, 0.14);
  }

  .item-params .param-select {
    flex: 1;
    min-width: 0;
  }

  .param-pair {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: #64748b;
    white-space: nowrap;
  }

  .param-num {
    width: 68px;
    height: 30px;
    border: 1px solid rgba(0, 93, 255, 0.15);
    border-radius: 6px;
    padding: 0 8px;
    font-size: 13px;
    text-align: center;
    outline: none;
    background: rgba(255, 255, 255, 0.9);
    color: #0f172a;
  }

  .del-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: none;
    background: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.12s, background 0.12s;
  }

  .del-btn:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
  }

  .empty-hint {
    margin: 0;
    font-size: 12px;
    color: #94a3b8;
    padding: 6px 0;
  }

  /* compute_ci 卡片 */
  .ci-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: rgba(0, 93, 255, 0.04);
    border: 1px solid rgba(0, 93, 255, 0.12);
    border-radius: 10px;
  }

  .ci-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .ci-card__info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .ci-card__title {
    font-size: 13px;
    font-weight: 700;
    color: #1e293b;
  }

  .ci-card__sub {
    font-size: 11px;
    color: #64748b;
  }

  .ci-card__desc {
    font-size: 12px;
    color: #475569;
    line-height: 1.55;
  }

  .ci-card__desc p {
    margin: 0 0 6px;
  }

  .ci-card__desc ul {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .ci-card__status {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 6px;
    text-align: center;
  }

  .ci-card__status--on {
    background: rgba(0, 93, 255, 0.1);
    color: #005dff;
  }

  .ci-card__status--off {
    background: rgba(100, 116, 139, 0.1);
    color: #64748b;
  }

  .ci-toggle {
    flex-shrink: 0;
    width: 36px;
    height: 20px;
    border-radius: 999px;
    border: none;
    background: #e2e8f0;
    cursor: pointer;
    padding: 2px;
    transition: background 0.2s;
    position: relative;
  }

  .ci-toggle--on {
    background: #005dff;
  }

  .ci-toggle__thumb {
    display: block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #fff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s;
    transform: translateX(0);
  }

  .ci-toggle--on .ci-toggle__thumb {
    transform: translateX(16px);
  }

  .settings-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-top: 12px;
    border-top: 1px solid rgba(0, 93, 255, 0.1);
  }

  .settings-footer__right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .btn-continue {
    min-width: 88px;
    padding: 10px 14px;
    border: none;
    border-radius: 10px;
    background: #2563eb;
    color: #fff;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-continue--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .btn-back {
    min-width: 88px;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: #fff;
    color: #475569;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-back:hover {
    background: #f1f5f9;
  }
</style>
```

With:

```css
<style scoped>
  .settings-wizard {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* 步驟頁籤 */
  .wizard-tabs {
    flex-shrink: 0;
    display: flex;
    gap: 4px;
    padding: 4px;
    background: color-mix(in oklab, var(--color-accent) 5%, transparent);
    border-radius: 12px;
  }

  .wizard-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 4px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--color-secondary);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, color 0.15s, box-shadow 0.15s;
  }

  .wizard-tab--active {
    background: var(--color-surface);
    color: var(--color-accent);
    font-weight: 700;
    box-shadow: 0 1px 5px color-mix(in oklab, var(--color-accent) 14%, transparent);
  }

  .wizard-tab__num {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink: 0;
    background: rgba(100, 116, 139, 0.12);
    color: var(--color-secondary);
    transition: background 0.15s, color 0.15s;
  }

  .wizard-tab--active .wizard-tab__num {
    background: var(--color-accent);
    color: #fff;
  }

  .wizard-tab__text {
    white-space: nowrap;
  }

  .wizard-tab__required {
    font-size: 9px;
    font-weight: 700;
    color: #ef4444;
    background: rgba(239, 68, 68, 0.12);
    border-radius: 6px;
    padding: 1px 4px;
    white-space: nowrap;
  }

  /* Step 內容 */
  .step-body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .add-bar {
    display: flex;
    gap: 6px;
  }

  /* 只保留 add-bar 的 flex 佈局，外觀交給 CustomSelect 自己畫 */
  .type-select {
    flex: 1;
    min-width: 0;
  }

  .add-btn {
    height: 32px;
    padding: 0 14px;
    border: none;
    border-radius: 8px;
    background: var(--color-accent);
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
    transition: opacity 0.12s;
  }

  .add-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .add-btn:not(:disabled):hover {
    opacity: 0.82;
  }

  .item-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 8px;
    align-items: stretch;
  }

  .item-row {
    display: flex;
    flex-direction: column;
    gap: 8px;
    height: 100%;
    box-sizing: border-box;
    padding: 10px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
    border-radius: 8px;
    font-size: 13px;
  }

  .item-head {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .item-idx {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: color-mix(in oklab, var(--color-accent) 12%, transparent);
    color: var(--color-accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 700;
    flex-shrink: 0;
  }

  .item-idx--dot {
    background: color-mix(in oklab, var(--color-accent) 20%, transparent);
  }

  .item-name {
    flex: 1;
    font-weight: 600;
    font-size: 13px;
    line-height: 1.3;
    color: var(--color-ink);
    min-width: 0;
    word-break: break-word;
  }

  .item-params {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: auto;
    padding-top: 8px;
    border-top: 1px dashed color-mix(in oklab, var(--color-accent) 14%, transparent);
  }

  .item-params .param-select {
    flex: 1;
    min-width: 0;
  }

  .param-pair {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .param-key {
    font-size: 12px;
    color: var(--color-secondary);
    white-space: nowrap;
  }

  .param-num {
    width: 68px;
    height: 30px;
    border: 1px solid color-mix(in oklab, var(--color-accent) 15%, transparent);
    border-radius: 6px;
    padding: 0 8px;
    font-size: 13px;
    text-align: center;
    outline: none;
    background: rgba(255, 255, 255, 0.9);
    color: var(--color-ink);
  }

  .del-btn {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: none;
    background: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.12s, background 0.12s;
  }

  .del-btn:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
  }

  .empty-hint {
    margin: 0;
    font-size: 12px;
    color: #94a3b8;
    padding: 6px 0;
  }

  /* compute_ci 卡片 */
  .ci-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 12px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    border: 1px solid color-mix(in oklab, var(--color-accent) 12%, transparent);
    border-radius: 10px;
  }

  .ci-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .ci-card__info {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .ci-card__title {
    font-size: 13px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .ci-card__sub {
    font-size: 11px;
    color: var(--color-secondary);
  }

  .ci-card__desc {
    font-size: 12px;
    color: var(--color-secondary);
    line-height: 1.55;
  }

  .ci-card__desc p {
    margin: 0 0 6px;
  }

  .ci-card__desc ul {
    margin: 0;
    padding-left: 16px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .ci-card__status {
    font-size: 11px;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 6px;
    text-align: center;
  }

  .ci-card__status--on {
    background: color-mix(in oklab, var(--color-accent) 10%, transparent);
    color: var(--color-accent);
  }

  .ci-card__status--off {
    background: rgba(100, 116, 139, 0.1);
    color: var(--color-secondary);
  }

  .ci-toggle {
    flex-shrink: 0;
    width: 36px;
    height: 20px;
    border-radius: 999px;
    border: none;
    background: #e2e8f0;
    cursor: pointer;
    padding: 2px;
    transition: background 0.2s;
    position: relative;
  }

  .ci-toggle--on {
    background: var(--color-accent);
  }

  .ci-toggle__thumb {
    display: block;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: var(--color-surface);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    transition: transform 0.2s;
    transform: translateX(0);
  }

  .ci-toggle--on .ci-toggle__thumb {
    transform: translateX(16px);
  }

  .settings-footer {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding-top: 12px;
    border-top: 1px solid color-mix(in oklab, var(--color-accent) 10%, transparent);
  }

  .settings-footer__right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .btn-continue {
    min-width: 88px;
    padding: 10px 14px;
    border: none;
    border-radius: 10px;
    background: var(--color-accent);
    color: #fff;
    font-size: 13px;
    cursor: pointer;
  }

  .btn-continue--disabled {
    background: #94a3b8;
    cursor: not-allowed;
  }

  .btn-back {
    min-width: 88px;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    background: var(--color-surface);
    color: var(--color-secondary);
    font-size: 13px;
    cursor: pointer;
  }

  .btn-back:hover {
    background: #f1f5f9;
  }
</style>
```

Note: `#94a3b8` (`.del-btn`, `.empty-hint`, `.btn-continue--disabled`) and `rgba(100, 116, 139, *)` (`.wizard-tab__num`, `.ci-card__status--off`) are intentionally unchanged — the same neutral-grey exception established in Task 10. `.wizard-tab__required`'s error red (`#ef4444`/`rgba(239, 68, 68, *)`) and `.del-btn:hover`'s error red are already at the canonical value and need no change. `.ci-toggle`'s track `#e2e8f0`, `.btn-back`'s border `#cbd5e1` and hover background `#f1f5f9` stay — neutral borders/tints not covered by any substitution rule. `.add-btn`/`.btn-continue`'s `color: #fff;` and `.wizard-tab--active .wizard-tab__num`'s `color: #fff;` stay literal (button/badge text on an accent-colored background).

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "rgba(0, 93, 255\|#64748b\|#005dff\|#1e293b\|#475569\|#2563eb" frontend/src/components/workflow/nodePanel/SettingsPanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/SettingsPanel.vue
git commit -m "feat: apply color tokens to SettingsPanel"
```

---

### Task 16: `TestScorePanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/TestScorePanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .workflow-summary {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0 0 16px;
  }

  .workflow-summary h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: #0f172a;
  }

  .summary-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: #ffffff;
  }

  .table-row {
    display: grid;
    grid-template-columns: 180px repeat(auto-fit, minmax(80px, 1fr));
    gap: 0;
    align-items: center;
  }

  /* 分隔線掛在 row 上（不是 cell）：cell 的 border 會被 grid 的欄間切斷成一段一段 */
  .table-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .table-row:not(.table-row--header):hover {
    background: rgba(0, 93, 255, 0.035);
  }

  .table-row--header {
    font-size: 12px;
    font-weight: 600;
    color: #475569;
    background: #f8fafc;
  }

  /* 標題列比資料列矮：它只是欄位標籤，不需要跟資料列一樣的呼吸空間 */
  .table-row--header .table-cell {
    padding: 8px 14px;
  }

  .table-cell {
    padding: 11px 14px;
    color: #0f172a;
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: left;
  }

  /* tabular-nums：讓同一欄的分數逐位對齊，比置中好比較。
     metric 表頭也套這條，標題才會跟底下那一整欄的數字切齊 */
  .table-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* 該 metric 表現最好的模型。這是 leaderboard 真正要回答的問題，
     不用逐格比對小數點就看得出誰贏 */
  .table-cell--best {
    font-weight: 700;
  }

  /* 最左欄：模型名 + split 名兩行堆疊，靠左 */
  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 2px;
    align-items: flex-start;
    background: transparent;
  }

  .model-name {
    font-weight: 600;
    color: #1e293b;
    font-size: 13px;
  }

  .model-split {
    font-size: 11px;
    font-weight: 400;
    color: #94a3b8;
  }

  .summary-empty {
    color: #6b7280;
    font-size: 13px;
  }
</style>
```

With:

```css
<style scoped>
  .workflow-summary {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 0 0 16px;
  }

  .workflow-summary h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .summary-table {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(148, 163, 184, 0.22);
    border-radius: 12px;
    overflow: hidden;
    background: var(--color-surface);
  }

  .table-row {
    display: grid;
    grid-template-columns: 180px repeat(auto-fit, minmax(80px, 1fr));
    gap: 0;
    align-items: center;
  }

  /* 分隔線掛在 row 上（不是 cell）：cell 的 border 會被 grid 的欄間切斷成一段一段 */
  .table-row:not(:last-child) {
    border-bottom: 1px solid rgba(148, 163, 184, 0.16);
  }

  .table-row:not(.table-row--header):hover {
    background: color-mix(in oklab, var(--color-accent) 3.5%, transparent);
  }

  .table-row--header {
    font-size: 12px;
    font-weight: 600;
    color: var(--color-secondary);
    background: var(--color-surface);
  }

  /* 標題列比資料列矮：它只是欄位標籤，不需要跟資料列一樣的呼吸空間 */
  .table-row--header .table-cell {
    padding: 8px 14px;
  }

  .table-cell {
    padding: 11px 14px;
    color: var(--color-ink);
    font-size: 13px;
    min-width: 0;
    word-break: break-word;
    background: transparent;
    text-align: left;
  }

  /* tabular-nums：讓同一欄的分數逐位對齊，比置中好比較。
     metric 表頭也套這條，標題才會跟底下那一整欄的數字切齊 */
  .table-cell--num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  /* 該 metric 表現最好的模型。這是 leaderboard 真正要回答的問題，
     不用逐格比對小數點就看得出誰贏 */
  .table-cell--best {
    font-weight: 700;
  }

  /* 最左欄：模型名 + split 名兩行堆疊，靠左 */
  .table-cell--model {
    display: flex;
    flex-direction: column;
    gap: 2px;
    align-items: flex-start;
    background: transparent;
  }

  .model-name {
    font-weight: 600;
    color: var(--color-ink);
    font-size: 13px;
  }

  .model-split {
    font-size: 11px;
    font-weight: 400;
    color: var(--color-secondary);
  }

  .summary-empty {
    color: var(--color-secondary);
    font-size: 13px;
  }
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#0f172a\|#ffffff\|rgba(0, 93, 255\|#475569\|#f8fafc\|#1e293b\|#94a3b8\|#6b7280" frontend/src/components/workflow/nodePanel/TestScorePanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/TestScorePanel.vue
git commit -m "feat: apply color tokens to TestScorePanel"
```

---

### Task 17: `WorkflowFileUploadPanel.vue`

**Files:**
- Modify: `frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-accent`, `--color-ink`, `--color-secondary`, `--color-surface` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed rgba(0, 93, 255, 0.28);
    border-radius: 16px;
    background: rgba(0, 93, 255, 0.04);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__desc {
    margin: 0;
    color: #475569;
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: #2563eb;
    background: rgba(59, 130, 246, 0.13);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: #2563eb;
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }

  .upload-modal-line2 {
    color: #475569;
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: #2563eb;
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: #475569;
  }

  .upload-modal-note {
    margin-top: 6px;
    color: #475569;
    font-size: 12px;
    line-height: 1.4;
  }

  .upload-modal-error {
    color: #b91c1c;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
    color: #1f2937;
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: #475569;
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .upload-modal-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .upload-modal-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .upload-modal-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: #f8fafc;
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    color: #0f172a;
  }

  .upload-modal-chart-subtitle {
    margin-top: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: #475569;
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: minmax(75px, 1.4fr) 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: #0f172a;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: #2563eb;
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: #0f172a;
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
    background: #ffffff;
    color: #0f172a;
  }

  .upload-modal-preview-table table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
    color: #0f172a;
  }

  .upload-modal-preview-table th {
    background: #f8fafc;
    color: #0f172a;
  }

  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }
</style>
```

With:

```css
<style scoped>
  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }

  .upload-card {
    padding: 18px;
    border: 1px dashed color-mix(in oklab, var(--color-accent) 28%, transparent);
    border-radius: 16px;
    background: color-mix(in oklab, var(--color-accent) 4%, transparent);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .upload-card__desc {
    margin: 0;
    color: var(--color-secondary);
    font-size: 13px;
    line-height: 1.5;
  }

  .upload-modal-dropzone {
    border: 2px dashed rgba(148, 163, 184, 0.9);
    border-radius: 18px;
    min-height: 220px;
    padding: 28px;
    display: grid;
    place-items: center;
    text-align: center;
    gap: 14px;
    transition:
      border-color 0.2s ease,
      background 0.2s ease;
  }

  .upload-modal-dropzone--active {
    border-color: var(--color-accent);
    background: color-mix(in oklab, var(--color-accent) 13%, transparent);
  }

  .upload-modal-icon {
    font-size: 32px;
    color: var(--color-accent);
  }

  .upload-modal-line1 {
    font-size: 18px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .upload-modal-line2 {
    color: var(--color-secondary);
    font-size: 14px;
  }

  .upload-modal-button {
    border: none;
    border-radius: 999px;
    padding: 10px 22px;
    background: var(--color-accent);
    color: #fff;
    cursor: pointer;
    font-size: 14px;
  }

  .upload-modal-file {
    font-size: 13px;
    color: var(--color-secondary);
  }

  .upload-modal-note {
    margin-top: 6px;
    color: var(--color-secondary);
    font-size: 12px;
    line-height: 1.4;
  }

  .upload-modal-error {
    color: #ef4444;
    font-size: 13px;
    text-align: center;
  }

  .upload-modal-preview {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .upload-modal-preview-header {
    font-size: 16px;
    font-weight: 700;
    color: var(--color-ink);
  }

  .upload-modal-preview-summary {
    display: flex;
    gap: 16px;
    color: var(--color-secondary);
    font-size: 13px;
  }

  .upload-modal-chart-grid {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
    scroll-snap-type: x proximity;
  }

  .upload-modal-chart-grid::-webkit-scrollbar {
    height: 10px;
  }

  .upload-modal-chart-grid::-webkit-scrollbar-thumb {
    background: rgba(148, 163, 184, 0.7);
    border-radius: 999px;
  }

  .upload-modal-chart-card {
    flex: 0 0 320px;
    min-width: 320px;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 18px;
    padding: 16px;
    background: var(--color-surface);
  }

  .upload-modal-chart-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 8px;
    color: var(--color-ink);
  }

  .upload-modal-chart-subtitle {
    margin-top: 6px;
    color: var(--color-secondary);
    font-size: 12px;
  }

  .upload-modal-chart-meta {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    color: var(--color-secondary);
    font-size: 12px;
    margin-bottom: 14px;
  }

  .upload-modal-chart-bars {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .upload-modal-chart-bar-row {
    display: grid;
    grid-template-columns: minmax(75px, 1.4fr) 1fr auto;
    gap: 10px;
    align-items: center;
  }

  .upload-modal-chart-bar-label {
    font-size: 12px;
    color: var(--color-ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
  }

  .upload-modal-chart-bar-track {
    height: 10px;
    border-radius: 999px;
    background: #e2e8f0;
    overflow: hidden;
  }

  .upload-modal-chart-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: var(--color-accent);
  }

  .upload-modal-chart-bar-value {
    font-size: 12px;
    color: var(--color-ink);
    text-align: right;
  }

  .upload-modal-preview-table {
    max-height: 220px;
    overflow: auto;
    border: 1px solid rgba(148, 163, 184, 0.24);
    border-radius: 14px;
    background: var(--color-surface);
    color: var(--color-ink);
  }

  .upload-modal-preview-table table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
  }

  .upload-modal-preview-table th,
  .upload-modal-preview-table td {
    padding: 10px 12px;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9);
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
    color: var(--color-ink);
  }

  .upload-modal-preview-table th {
    background: var(--color-surface);
    color: var(--color-ink);
  }

  .workflow-file-upload-panel {
    font-family:
      "Noto Sans TC", "Microsoft JhengHei", "Apple LiGothic", sans-serif;
  }
</style>
```

Note: the duplicated `.workflow-file-upload-panel` rule (appears both at the top and bottom of the block) is pre-existing and out of scope — only colors change, no structural cleanup.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "rgba(0, 93, 255\|#475569\|#2563eb\|rgba(59, 130, 246\|#1f2937\|#b91c1c\|#f8fafc\|#0f172a\|#64748b\|#ffffff" frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/nodePanel/WorkflowFileUploadPanel.vue
git commit -m "feat: apply color tokens to WorkflowFileUploadPanel"
```

---

### Task 18: Full verification pass

**Files:**
- No file modifications — this task only verifies the 17 files touched by Tasks 1–17.

**Interfaces:**
- Consumes: the completed state of Tasks 1–17
- Produces: nothing (terminal task)

- [ ] **Step 1: Grep for leftover old-palette hex values across the whole Workflow area**

Run (from the repo root):

```bash
grep -rn "#005dff\|#2563eb\|#0f172a\|#1e293b\|#1f2937\|#20232a\|#1f2532\|#1f2430\|#192235\|#15181e\|#242424\|#475569\|#64748b\|#6b7280\|#6f7480\|#5f6571\|#3a3f4a\|#f9fbff\|#f8fbff\|#f7f9ff\|#fafbff\|#f0f2f5\|#18a836\|#10b981\|#b91c1c" frontend/src/views/WorkflowPage.vue frontend/src/views/ResultsPage.vue frontend/src/views/PaperSourcesView.vue frontend/src/components/workflow/
```

Expected: no output. (`#94a3b8`, `rgba(100, 116, 139, *)`, `rgba(148, 163, 184, *)`, and the `IconNode.vue`/`ComputeCiPanel.vue`/`.gemini-upload-btn` exclusions are deliberately not in this grep — see Global Constraints.)

- [ ] **Step 2: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 3: Live browser check — `/workflow`**

Run (from `frontend/`): `npm run dev`. Open `/workflow`.

Expected, checked via devtools `getComputedStyle`:
- The canvas background and edge lines use the accent color, not blue
- Clicking a node opens the bottom drawer; its buttons (add/continue/back) and active step tab are accent-colored, not blue
- The floating toolbar buttons (demo/execute/view-results/upload) are accent-colored; the Gemini upload button stays indigo
- Node icons on the canvas keep their original purple/yellow/pending colors (unchanged from before this batch)

- [ ] **Step 4: Live browser check — `/results?project=<id>`**

Navigate to `/results?project=<id>` for a project with a completed workflow run (or trigger one from `/workflow` first).

Expected: the "生成論文" button and metric-card accents are the accent color; the AI-insight card uses an accent-based gradient instead of the old blue-purple gradient; table header background and body text resolve to ink/surface tokens.

- [ ] **Step 5: Live browser check — `/paper/sources?project=<id>`**

Navigate to `/paper/sources?project=<id>`.

Expected: candidate cards' title/abstract text use ink/secondary tokens; the "確認並生成論文" button is accent-colored; the outer page glow matches the same accent-tinted pattern used on `/paper`.

- [ ] **Step 6: Stop the dev server after checking**

Stop the `npm run dev` process started in Step 3.

- [ ] **Step 7: Commit (if any fixes were needed during verification)**

If Steps 1–5 required any fixes, stage and commit them:

```bash
git add -A
git commit -m "fix: address verification findings in workflow color application"
```

If no fixes were needed, skip this step — Tasks 1–17 already committed everything.

---

## Plan Self-Review

**Spec coverage:** Every section of `docs/superpowers/specs/2026-07-30-workflow-color-application-design.md` maps to a task — 段落 A (CTA/accent) and 段落 B (text colors) are covered across Tasks 1–17 (every file with `#005dff`/`#2563eb` or grey text got its accent/ink/secondary substitutions); 段落 C (white/near-white → surface, `ResultsPage.vue`/`PaperSourcesView.vue` page-var restructuring) is covered by Tasks 2–3; 段落 D (`ResultsPage.vue` insight-card gradient) is covered by Task 2; 段落 E (`IconNode.vue` node-type palette exclusion) is covered by Task 5; 段落 F (status-color dedup) is covered across Tasks 2–3 (error red) and Task 10 (success green). The non-goals (neutral borders, decorative indigo, flash-overlay colors, `ComputeCiPanel.vue` warning amber) are called out as explicit exceptions in Global Constraints and reiterated per-task where they appear. Task 18 verifies the whole batch.

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" phrasing anywhere — every task shows the complete before/after CSS (or template) block. Clean.

**Type consistency:** N/A for this plan (pure CSS value substitution, no functions/types/signatures introduced or consumed across tasks).

