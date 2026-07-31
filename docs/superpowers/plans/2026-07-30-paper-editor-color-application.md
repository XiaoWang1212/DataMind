# Paper Editor Color Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the project's `--color-*` design tokens (defined in `frontend/src/styles/tailwind.css`) to the paper editor area's hardcoded colors — `PaperPage.vue`'s local CSS variables and decorative background, `PaperEditor.vue`'s toolbar/text colors, and `InsertChartDialog.vue`'s on-screen (non-exported) text colors.

**Architecture:** Pure CSS value swaps in existing `<style scoped>` blocks — no structural, template, or script changes. `PaperPage.vue`'s local CSS custom properties (`--brand`, `--text-secondary`, etc.) are consumed by `ModeSwitch.vue` via `var(--brand, fallback)`, so redefining their values in `PaperPage.vue` cascades automatically; `ModeSwitch.vue` itself is not touched.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-secondary` (`#334155`), `--color-accent` (`#e8a33d`), `--color-surface` (`#ffffff`), `--color-ink` (`#1c2130`)
- No unit test framework is configured in `frontend/` — verification is `npm run build` and live browser `getComputedStyle` checks, run from the `frontend/` directory
- **Never touch:** `frontend/src/components/paper/charts/BarChart.vue`, `frontend/src/components/paper/charts/RadarChart.vue`, `frontend/src/components/paper/charts/chartColors.ts`, or the SVG-string-building code inside `InsertChartDialog.vue`'s `handleInsert()` function (including its `fill="#4a4f5c"` literal) — these values get serialized into standalone exported SVG images with no access to the app's CSS custom properties; converting them to `var()` would silently break exported chart images. This project has hit this exact bug before.
- **Never touch:** `frontend/src/components/paper/CitationPopover.vue` (any part of it), and in `frontend/src/components/paper/PaperEditor.vue` specifically the `.citation-mark` / `.citation-mark:hover` rules (`#fdf0a8` / `#fae57e`) — these are the intentional "yellow highlighter" citation theme, kept independent of the brand palette
- **Never touch:** `--line` / `--line-soft` in `PaperPage.vue` (`#d8dbe3` / `#e8ebf1`), or any border-color declarations in `PaperEditor.vue` — neutral structural dividers, not brand color
- Do not touch `frontend/src/components/paper/ModeSwitch.vue` — it inherits its colors via CSS custom property cascade from `PaperPage.vue` and needs no direct edit
- Do not add a test framework or write new automated tests as part of this plan

---

### Task 1: `PaperPage.vue` local variables and background

**Files:**
- Modify: `frontend/src/views/PaperPage.vue:154-187`

**Interfaces:**
- Consumes: `--color-primary`, `--color-surface`, `--color-ink`, `--color-secondary`, `--color-accent` (already defined in `frontend/src/styles/tailwind.css`)
- Produces: `PaperPage.vue`'s local `--brand` and `--text-secondary` custom properties now resolve to `var(--color-accent)` / `var(--color-secondary)` — `ModeSwitch.vue` (unmodified) picks this up automatically via its existing `var(--brand, #1058d6)` / `var(--text-secondary, #6f7480)` references

- [ ] **Step 1: Edit `.paper-page` and `.paper-main` in `frontend/src/views/PaperPage.vue`**

Replace:

```css
  .paper-page {
    --page-bg: #e4e4e8;
    --card-bg: #ffffff;
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: #15181e;
    --text-secondary: #6f7480;
    --brand: #1058d6;
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background:
      radial-gradient(circle at 8% 12%, rgba(99, 146, 238, 0.18) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, rgba(88, 157, 255, 0.16) 0%, transparent 30%),
      linear-gradient(180deg, #d7d9df 0%, #dedfe4 100%);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background:
      radial-gradient(circle, #cdd0d8 1px, transparent 1px) 0 0 / 18px 18px,
      linear-gradient(180deg, #f3f4f8 0%, #eff1f6 100%);
    padding: 12px 20px 18px;
    overflow: hidden;
  }
```

With:

```css
  .paper-page {
    --page-bg: var(--color-primary);
    --card-bg: var(--color-surface);
    --line: #d8dbe3;
    --line-soft: #e8ebf1;
    --text-main: var(--color-ink);
    --text-secondary: var(--color-secondary);
    --brand: var(--color-accent);
    min-height: calc(100vh - 64px);
    display: flex;
    gap: 0;
    padding: 16px;
    background: var(--color-primary);
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
    color: var(--text-main);
  }

  .paper-main {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    border: 1px solid var(--line);
    border-radius: 0 12px 12px 0;
    background: var(--color-surface);
    padding: 12px 20px 18px;
    overflow: hidden;
  }
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#e4e4e8\|#d7d9df\|#dedfe4\|#cdd0d8\|#f3f4f8\|#eff1f6\|#15181e\|#1058d6" frontend/src/views/PaperPage.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: apply color tokens to PaperPage background and local variables"
```

---

### Task 2: `PaperEditor.vue` toolbar and text colors

**Files:**
- Modify: `frontend/src/components/paper/PaperEditor.vue:207-241`

**Interfaces:**
- Consumes: `--color-surface`, `--color-ink` (already defined in `frontend/src/styles/tailwind.css`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `.editor-toolbar` background**

Replace:

```css
  .editor-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: #f7f8fb;
  }
```

With:

```css
  .editor-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px;
    padding: 6px 8px;
    border: 1px solid #d8dbe3;
    border-radius: 8px;
    background: var(--color-surface);
  }
```

- [ ] **Step 2: Edit editor content text colors**

Replace:

```css
  :deep(.editor-content) {
    font-size: 13.5px;
    line-height: 1.9;
    color: #2a2f3a;
  }

  :deep(.editor-content .ProseMirror) {
    outline: none;
  }

  :deep(.editor-content h1),
  :deep(.editor-content h2),
  :deep(.editor-content h3) {
    margin: 0 0 10px;
    font-weight: 700;
    color: #1c2130;
  }
```

With:

```css
  :deep(.editor-content) {
    font-size: 13.5px;
    line-height: 1.9;
    color: var(--color-ink);
  }

  :deep(.editor-content .ProseMirror) {
    outline: none;
  }

  :deep(.editor-content h1),
  :deep(.editor-content h2),
  :deep(.editor-content h3) {
    margin: 0 0 10px;
    font-weight: 700;
    color: var(--color-ink);
  }
```

- [ ] **Step 3: Verify no leftover old color values, and that the citation-mark colors are untouched**

Run: `grep -n "#f7f8fb\|#2a2f3a\|color: #1c2130" frontend/src/components/paper/PaperEditor.vue`
Expected: no output.

Run: `grep -n "fdf0a8\|fae57e" frontend/src/components/paper/PaperEditor.vue`
Expected: 2 matches (the `.citation-mark` and `.citation-mark:hover` rules), completely unchanged from before this task.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/paper/PaperEditor.vue
git commit -m "feat: apply color tokens to PaperEditor toolbar and text"
```

---

### Task 3: `InsertChartDialog.vue` on-screen text colors

**Files:**
- Modify: `frontend/src/components/paper/InsertChartDialog.vue:164-193`

**Interfaces:**
- Consumes: `--color-secondary` (already defined in `frontend/src/styles/tailwind.css`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `.empty-hint` and `.picker-label`**

Replace:

```css
  .empty-hint {
    font-size: 13px;
    color: #6f7480;
    padding: 12px 0;
  }
```

With:

```css
  .empty-hint {
    font-size: 13px;
    color: var(--color-secondary);
    padding: 12px 0;
  }
```

Replace:

```css
  .picker-label {
    margin: 0 0 4px;
    font-size: 12px;
    font-weight: 700;
    color: #4a4f5c;
  }
```

With:

```css
  .picker-label {
    margin: 0 0 4px;
    font-size: 12px;
    font-weight: 700;
    color: var(--color-secondary);
  }
```

- [ ] **Step 2: Verify the exported-SVG code path is untouched**

Run: `grep -n "#4a4f5c" frontend/src/components/paper/InsertChartDialog.vue`
Expected: exactly 1 match, inside the `legendMarkup` template literal in `handleInsert()` (the `fill="#4a4f5c"` used for exported chart legend text) — this line must NOT have been changed by this task; only the two CSS rules in Step 1 were in scope.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/paper/InsertChartDialog.vue
git commit -m "feat: apply color tokens to InsertChartDialog on-screen text"
```

---

### Task 4: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: the changes from Tasks 1-3
- Produces: nothing

- [ ] **Step 1: Run a clean full build**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 2: Live browser check — PaperPage and PaperEditor**

Run (from `frontend/`): `npm run dev`. Open `/paper`.

In the browser devtools console:
```js
getComputedStyle(document.querySelector('.paper-page')).backgroundColor
// expect: "rgb(246, 245, 242)" (primary)
getComputedStyle(document.querySelector('.paper-main')).backgroundColor
// expect: "rgb(255, 255, 255)" (surface)
getComputedStyle(document.querySelector('.editor-toolbar')).backgroundColor
// expect: "rgb(255, 255, 255)" (surface) — only visible once in edit mode, click 編輯 first
```

Visually confirm: the page background is cream, the editor card area is white, body/heading text renders in dark ink (not visually different from before, since `#1c2130`/`#2a2f3a` were already close to `--color-ink`, but now token-driven).

- [ ] **Step 3: Live browser check — ModeSwitch inherits the new accent automatically**

While still on `/paper`, click 編輯 to enter edit mode (the switch pill moves to the "編輯" side).

```js
getComputedStyle(document.querySelector('.mode-switch .pill')).backgroundColor
// expect: "rgb(232, 163, 61)" (accent) — even though ModeSwitch.vue itself was never edited
```

- [ ] **Step 4: Live browser check — citation highlight and CitationPopover are unaffected**

Click on a citation marker (`[n]`) in the view-mode article body. Expected: the `CitationPopover` card appears with its original pale-yellow background and gold/brown text — visually unchanged from before this plan.

```js
getComputedStyle(document.querySelector('.citation-popover-card')).backgroundColor
// expect: "rgb(255, 251, 232)" (#fffbe8, unchanged)
```

- [ ] **Step 5: Live browser check — insert-chart dialog and exported chart image**

Click the chart-insert icon in the editor toolbar (requires edit mode and a `projectId` with workflow results — if no such project is available in this environment, skip to Step 6 and note it in your report). In the opened dialog, confirm the "模型"/"指標" labels and any empty-state hint render in the new secondary-slate color rather than the old muted grey (visually verify via `getComputedStyle` on `.picker-label`). Select a model/metric, insert the chart, and confirm the inserted chart image in the article still shows visible gridlines, axis labels, and a legend — exactly as before this plan (proving the SVG-export path was not accidentally converted to `var()`).

- [ ] **Step 6: Confirm no leftover old-palette references across the three files**

Run: `grep -rn "#e4e4e8\|#d7d9df\|#dedfe4\|#cdd0d8\|#f3f4f8\|#eff1f6\|#15181e\|#1058d6\|#f7f8fb\|#2a2f3a" frontend/src/views/PaperPage.vue frontend/src/components/paper/PaperEditor.vue frontend/src/components/paper/InsertChartDialog.vue`
Expected: no output.

Stop the dev server after checking.
