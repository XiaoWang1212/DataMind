# Color Theme Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the project's blue/cyan color scheme with the new palette (cream primary, slate secondary, amber accent, white surface, plus chat-bubble and text tokens for the upcoming chat feature), and make Vuetify the single source of truth for color with Tailwind referencing it.

**Architecture:** Define the new palette once in Vuetify's `light` theme (`frontend/src/plugins/vuetify.ts`); Tailwind's `@theme` block (`frontend/src/styles/tailwind.css`) references the resulting `--v-theme-*` CSS variables for `primary`/`secondary`/`accent`, matching the pattern already used for `background`/`surface`. Chat-bubble and text tokens (`chat-system`, `chat-user`, `ink`, `inverted`) are plain Tailwind constants since no Vuetify component consumes them. Existing usages of the old color scale classes and `color="primary"` are migrated to the new tokens.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Color values (exact, from spec): `primary #f6f5f2`, `secondary #334155`, `accent #e8a33d`, `surface #ffffff`, `chat-system #fbead0`, `chat-user #12213b`, `ink #1c2130`, `inverted #f1f5f9`
- No unit test framework is configured in `frontend/` — verification is `npm run build` (runs `vue-tsc --build --force` then `vite build`) run from the `frontend/` directory, plus `grep` checks for removed/added identifiers
- Out of scope: page-local `<style scoped>` palettes (e.g. `PaperPage.vue`'s `--brand`/`--page-bg`), dark mode activation, chart coloring logic — do not touch these
- Do not add a test framework or write new automated tests as part of this plan; the project doesn't have one and adding one is out of scope

---

### Task 1: Vuetify theme colors

**Files:**
- Modify: `frontend/src/plugins/vuetify.ts:12-16`

**Interfaces:**
- Consumes: none
- Produces: Vuetify CSS variables `--v-theme-primary`, `--v-theme-secondary`, `--v-theme-accent`, `--v-theme-background`, `--v-theme-surface` resolving to the new palette. Task 2 and Task 4 rely on these existing.

- [ ] **Step 1: Edit `frontend/src/plugins/vuetify.ts`**

Replace:

```ts
export default createVuetify({
  theme: {
    defaultTheme: 'light',
    utilities: false,
  },
```

With:

```ts
export default createVuetify({
  theme: {
    defaultTheme: 'light',
    utilities: false,
    themes: {
      light: {
        colors: {
          primary: '#f6f5f2',
          secondary: '#334155',
          accent: '#e8a33d',
          background: '#f6f5f2',
          surface: '#ffffff',
        },
      },
    },
  },
```

- [ ] **Step 2: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 3: Start the dev server and visually confirm**

Run (from `frontend/`): `npm run dev`
Open the app in a browser. Expected: page background is now cream/off-white (`#f6f5f2`) instead of the previous default white/blue Vuetify theme. Stop the dev server after checking.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/plugins/vuetify.ts
git commit -m "feat: define new Vuetify theme colors (primary/secondary/accent/surface)"
```

---

### Task 2: Tailwind token migration

**Files:**
- Modify: `frontend/src/styles/tailwind.css:15-31`

**Interfaces:**
- Consumes: `--v-theme-primary`, `--v-theme-secondary`, `--v-theme-accent` from Task 1
- Produces: Tailwind utility tokens `bg-primary`/`text-primary`, `bg-secondary`/`text-secondary`, `bg-accent`/`text-accent`, `bg-chat-system`, `bg-chat-user`, `bg-ink`/`text-ink`, `bg-inverted`/`text-inverted`. Task 3 and Task 4 rely on `bg-primary`, `bg-secondary`, `text-ink`, `text-inverted` existing. Removes `bg-primary-100`, `bg-primary-900`, `bg-secondary-100` through `bg-secondary-800` — Task 3 relies on these being gone (it replaces the remaining usages).

- [ ] **Step 1: Edit `frontend/src/styles/tailwind.css`**

Replace:

```css
  --color-background: rgb(var(--v-theme-background));
  --color-surface: rgb(var(--v-theme-surface));
  --color-success: rgb(var(--v-theme-success));
  --color-info: rgb(var(--v-theme-info));
  --color-warning: rgb(var(--v-theme-warning));
  --color-error: rgb(var(--v-theme-error));

  --color-primary-100: #a7e0ff;
  --color-primary-900: #003256;
  --color-secondary-100: #92f7ff;
  --color-secondary-200: #57f0ff;
  --color-secondary-300: #10e3fb;
  --color-secondary-400: #00c1da;
  --color-secondary-500: #009fbd;
  --color-secondary-600: #0087a4;
  --color-secondary-700: #097088;
  --color-secondary-800: #0d5d73;
```

With:

```css
  --color-background: rgb(var(--v-theme-background));
  --color-surface: rgb(var(--v-theme-surface));
  --color-success: rgb(var(--v-theme-success));
  --color-info: rgb(var(--v-theme-info));
  --color-warning: rgb(var(--v-theme-warning));
  --color-error: rgb(var(--v-theme-error));
  --color-primary: rgb(var(--v-theme-primary));
  --color-secondary: rgb(var(--v-theme-secondary));
  --color-accent: rgb(var(--v-theme-accent));

  --color-chat-system: #fbead0;
  --color-chat-user: #12213b;
  --color-ink: #1c2130;
  --color-inverted: #f1f5f9;
```

- [ ] **Step 2: Verify old scale tokens are gone**

Run: `grep -n "color-primary-\|color-secondary-[0-9]" frontend/src/styles/tailwind.css`
Expected: no output (no matches).

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0. (This step will fail until Task 3 also migrates `Introduction.vue`'s references to the removed classes — if it fails here with errors pointing at `Introduction.vue`, that's expected and resolved in Task 3, not a bug in this task. Tailwind v4 doesn't error on unknown utility classes at build time, so `npm run build` should still pass; this step is a safety net.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/tailwind.css
git commit -m "refactor: point Tailwind primary/secondary/accent tokens at Vuetify theme"
```

---

### Task 3: Migrate `Introduction.vue` off the old color scale

**Files:**
- Modify: `frontend/src/components/Introduction.vue:104-115`

**Interfaces:**
- Consumes: `bg-primary`, `bg-secondary/10` Tailwind utilities from Task 2
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `frontend/src/components/Introduction.vue`**

Replace:

```
.hero-card {
  @apply md:col-span-2 md:py-4 sm:pr-30 w-full bg-primary-100 dark:bg-primary-900
}

.v-card-subtitle {
  @apply text-wrap line-clamp-2 leading-[1.2];
  --v-medium-emphasis-opacity: .8;
}

.feature-card {
  @apply flex items-center [&>.v-card-item]:w-full bg-secondary-100;
  @apply dark:bg-linear-to-r dark:from-secondary-800 dark:to-secondary-600 dark:text-white;

  .v-card-item {
```

With:

```
.hero-card {
  @apply md:col-span-2 md:py-4 sm:pr-30 w-full bg-primary
}

.v-card-subtitle {
  @apply text-wrap line-clamp-2 leading-[1.2];
  --v-medium-emphasis-opacity: .8;
}

.feature-card {
  @apply flex items-center [&>.v-card-item]:w-full bg-secondary/10;

  .v-card-item {
```

- [ ] **Step 2: Verify no old classes remain**

Run: `grep -n "primary-100\|primary-900\|secondary-100\|secondary-800\|secondary-600" frontend/src/components/Introduction.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Introduction.vue
git commit -m "refactor: migrate Introduction.vue off removed color-scale classes"
```

---

### Task 4: Swap `color="primary"` to `color="accent"` on interactive elements

**Files:**
- Modify: `frontend/src/components/HelloWorld.vue:48`
- Modify: `frontend/src/views/PaperPage.vue:21`
- Modify: `frontend/src/components/WorkflowBuilder.vue:12` and `:29`
- Modify: `frontend/src/views/PaperSourcesView.vue:23` and `:67`
- Modify: `frontend/src/components/paper/InsertChartDialog.vue:59`
- Modify: `frontend/src/views/ResultsPage.vue:31` and `:45`

**Interfaces:**
- Consumes: `accent` color from the Vuetify theme (Task 1)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `frontend/src/components/HelloWorld.vue`**

Replace:

```
      <v-btn
        class="upload-btn"
        color="primary"
        prepend-icon="mdi-folder-plus-outline"
        rounded="pill"
```

With:

```
      <v-btn
        class="upload-btn"
        color="accent"
        prepend-icon="mdi-folder-plus-outline"
        rounded="pill"
```

- [ ] **Step 2: Edit `frontend/src/views/PaperPage.vue`**

Replace:

```
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              color="primary"
              :disabled="!projectId"
              :loading="saving"
```

With:

```
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              color="accent"
              :disabled="!projectId"
              :loading="saving"
```

- [ ] **Step 3: Edit `frontend/src/components/WorkflowBuilder.vue` (button)**

Replace:

```
        block
        class="new-btn"
        color="primary"
        prepend-icon="mdi-plus"
      >新增</v-btn>
```

With:

```
        block
        class="new-btn"
        color="accent"
        prepend-icon="mdi-plus"
      >新增</v-btn>
```

- [ ] **Step 4: Edit `frontend/src/components/WorkflowBuilder.vue` (avatar)**

Replace:

```
      <div class="user-box">
        <v-avatar color="primary" size="44">
          <v-icon icon="mdi-account" />
        </v-avatar>
```

With:

```
      <div class="user-box">
        <v-avatar color="accent" size="44">
          <v-icon icon="mdi-account" />
        </v-avatar>
```

- [ ] **Step 5: Edit `frontend/src/views/PaperSourcesView.vue` (results link)**

Replace:

```
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
        <v-btn color="primary" size="small" @click="router.push(`/results?project=${projectId}`)">
          回到 /results
        </v-btn>
```

With:

```
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
        <v-btn color="accent" size="small" @click="router.push(`/results?project=${projectId}`)">
          回到 /results
        </v-btn>
```

- [ ] **Step 6: Edit `frontend/src/views/PaperSourcesView.vue` (generate button)**

Replace:

```
          <div class="sources-actions">
            <v-btn
              color="primary"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
```

With:

```
          <div class="sources-actions">
            <v-btn
              color="accent"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
```

- [ ] **Step 7: Edit `frontend/src/components/paper/InsertChartDialog.vue`**

Replace:

```
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="primary" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
```

With:

```
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="accent" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
```

- [ ] **Step 8: Edit `frontend/src/views/ResultsPage.vue` (generate paper button)**

Replace:

```
        <v-btn
          class="generate-paper-btn"
          color="primary"
          size="small"
          @click="router.push(`/paper/sources?project=${projectId}`)"
```

With:

```
        <v-btn
          class="generate-paper-btn"
          color="accent"
          size="small"
          @click="router.push(`/paper/sources?project=${projectId}`)"
```

- [ ] **Step 9: Edit `frontend/src/views/ResultsPage.vue` (empty-state button)**

Replace:

```
      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn color="primary" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
```

With:

```
      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn color="accent" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
```

- [ ] **Step 10: Verify no `color="primary"` usages remain**

Run: `grep -rn 'color="primary"' frontend/src`
Expected: no output.

- [ ] **Step 11: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/components/HelloWorld.vue frontend/src/views/PaperPage.vue frontend/src/components/WorkflowBuilder.vue frontend/src/views/PaperSourcesView.vue frontend/src/components/paper/InsertChartDialog.vue frontend/src/views/ResultsPage.vue
git commit -m "refactor: use accent color for primary CTAs instead of Vuetify primary"
```

---

### Task 5: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: all tokens and migrations from Tasks 1-4
- Produces: nothing

- [ ] **Step 1: Run a clean full build**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 2: Run lint**

Run (from `frontend/`): `npm run lint`
Expected: exits 0, no errors (warnings pre-existing and unrelated to this change are acceptable; any new errors on files touched in Tasks 1-4 must be fixed).

- [ ] **Step 3: Manual visual check**

Run (from `frontend/`): `npm run dev`
Open the app and check:
- Page background is cream (`#f6f5f2`) across `HomePage`, `PaperPage`, `WorkflowPage`, `ResultsPage`
- Cards/dialogs render on a white (`#ffffff`) surface, visibly distinct from the cream page background
- The 9 buttons/elements migrated in Task 4 render in amber (`#e8a33d`), not pale/invisible
- `Introduction.vue`'s hero card and feature card render with the new cream/secondary tint, no visual breakage
Stop the dev server after checking.

- [ ] **Step 4: Confirm no leftover old-palette references**

Run: `grep -rn "#a7e0ff\|#003256\|#92f7ff\|#57f0ff\|#10e3fb\|#00c1da\|#009fbd\|#0087a4\|#097088\|#0d5d73" frontend/src`
Expected: no output.

---

### Task 6: Add explicit `bg-accent` class to accent-colored CTAs

> Added after live browser verification during Task 5 found that `frontend/src/plugins/vuetify.ts` has `theme.utilities: false` (present since project init, not part of this plan) — this disables Vuetify's own generation of `.bg-{color}`/`.text-{color}` classes, which is what the `color` prop on `v-btn`/`v-avatar` relies on for a solid background fill. Confirmed via browser devtools: `--v-theme-accent` resolves correctly, but no `.bg-accent` CSS rule exists anywhere on the page, so `color="accent"` from Task 4 has zero visual effect (matching `color="primary"` having had zero visual effect before Task 4 — this was already broken, Task 4 didn't regress it). Tailwind CSS v4 only generates a utility for a class name if that literal string appears in scanned source — this is why `.bg-primary` exists (used literally in `Introduction.vue`) but `.bg-accent` didn't (never appeared as a literal class string anywhere). Adding an explicit `class="bg-accent"` alongside the existing `color="accent"` prop on each of the 9 elements makes Tailwind generate and apply the real fill, while keeping the `color` prop for Vuetify's other theme-color-driven effects (ripple, focus ring) that aren't gated by `utilities: false`.

**Files:**
- Modify: `frontend/src/components/HelloWorld.vue:47`
- Modify: `frontend/src/views/PaperPage.vue:20-21`
- Modify: `frontend/src/components/WorkflowBuilder.vue:11-12` and `:29`
- Modify: `frontend/src/views/PaperSourcesView.vue:23` and `:66-67`
- Modify: `frontend/src/components/paper/InsertChartDialog.vue:59`
- Modify: `frontend/src/views/ResultsPage.vue:30-31` and `:45`

**Interfaces:**
- Consumes: `bg-accent` Tailwind utility (generated on demand once the literal class string is present in source; token defined in Task 2)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `frontend/src/components/HelloWorld.vue`**

Replace:

```
      <v-btn
        class="upload-btn"
        color="accent"
        prepend-icon="mdi-folder-plus-outline"
        rounded="pill"
```

With:

```
      <v-btn
        class="upload-btn bg-accent"
        color="accent"
        prepend-icon="mdi-folder-plus-outline"
        rounded="pill"
```

- [ ] **Step 2: Edit `frontend/src/views/PaperPage.vue`**

Replace:

```
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              color="accent"
              :disabled="!projectId"
              :loading="saving"
```

With:

```
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="!projectId"
              :loading="saving"
```

- [ ] **Step 3: Edit `frontend/src/components/WorkflowBuilder.vue` (button)**

Replace:

```
        block
        class="new-btn"
        color="accent"
        prepend-icon="mdi-plus"
      >新增</v-btn>
```

With:

```
        block
        class="new-btn bg-accent"
        color="accent"
        prepend-icon="mdi-plus"
      >新增</v-btn>
```

- [ ] **Step 4: Edit `frontend/src/components/WorkflowBuilder.vue` (avatar)**

Replace:

```
      <div class="user-box">
        <v-avatar color="accent" size="44">
          <v-icon icon="mdi-account" />
        </v-avatar>
```

With:

```
      <div class="user-box">
        <v-avatar class="bg-accent" color="accent" size="44">
          <v-icon icon="mdi-account" />
        </v-avatar>
```

- [ ] **Step 5: Edit `frontend/src/views/PaperSourcesView.vue` (results link)**

Replace:

```
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
        <v-btn color="accent" size="small" @click="router.push(`/results?project=${projectId}`)">
          回到 /results
        </v-btn>
```

With:

```
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/results?project=${projectId}`)">
          回到 /results
        </v-btn>
```

- [ ] **Step 6: Edit `frontend/src/views/PaperSourcesView.vue` (generate button)**

Replace:

```
          <div class="sources-actions">
            <v-btn
              color="accent"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
```

With:

```
          <div class="sources-actions">
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="selectedIds.length === 0 || generating"
              @click="handleGenerate"
```

- [ ] **Step 7: Edit `frontend/src/components/paper/InsertChartDialog.vue`**

Replace:

```
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn color="accent" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
```

With:

```
        <v-spacer />
        <v-btn variant="text" @click="emit('update:modelValue', false)">取消</v-btn>
        <v-btn class="bg-accent" color="accent" :disabled="chartSeries.length === 0" @click="handleInsert">插入</v-btn>
      </v-card-actions>
```

- [ ] **Step 8: Edit `frontend/src/views/ResultsPage.vue` (generate paper button)**

Replace:

```
        <v-btn
          class="generate-paper-btn"
          color="accent"
          size="small"
          @click="router.push(`/paper/sources?project=${projectId}`)"
```

With:

```
        <v-btn
          class="generate-paper-btn bg-accent"
          color="accent"
          size="small"
          @click="router.push(`/paper/sources?project=${projectId}`)"
```

- [ ] **Step 9: Edit `frontend/src/views/ResultsPage.vue` (empty-state button)**

Replace:

```
      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn color="accent" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
```

With:

```
      <section v-else-if="!workflowResult" class="empty-state">
        <p>尚無結果。請先在 workflow 頁面完成執行。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push('/workflow')">
          前往 Workflow
        </v-btn>
```

- [ ] **Step 10: Verify no leftover bare `color="accent"` without a sibling `bg-accent` class**

Run: `grep -rn 'color="accent"' frontend/src`
Expected: exactly 9 matches (same 9 locations as Task 4), each on a line that also has (or is adjacent to, within the same tag, a `class` attribute containing) `bg-accent`. Manually confirm all 9 by eye against the list above.

- [ ] **Step 11: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 12: Commit**

```bash
git add frontend/src/components/HelloWorld.vue frontend/src/views/PaperPage.vue frontend/src/components/WorkflowBuilder.vue frontend/src/views/PaperSourcesView.vue frontend/src/components/paper/InsertChartDialog.vue frontend/src/views/ResultsPage.vue
git commit -m "fix: add explicit bg-accent class so accent CTAs render (Vuetify utilities disabled)"
```
