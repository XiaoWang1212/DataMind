# Consolidate Result Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the "生成論文" (generate paper) button and its downstream navigation from the standalone `ResultsPage.vue` (`/results`) to the Hub's `ResultView.vue` (`/hub/projects/:id/result`), and re-point every entry/exit path in the flow (`/workflow`'s "查看結果" button, `PaperSourcesView.vue`'s back/error navigation) so the whole loop consolidates on the Hub page.

**Architecture:** Four independent, single-file template/script edits — no new components, no data-flow changes. `PaperSourcesView.vue` keeps reading `route.query.project` exactly as before; only the Hub button and the redirect targets change.

**Tech Stack:** Vue 3, Vue Router 4, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-accent` (`#e8a33d`)
- `ResultView.vue`'s `projectId` is `computed(() => route.params.id as string)` — already in scope in the `<script setup>`, template can reference it directly
- `PaperSourcesView.vue`'s `projectId` is `computed(() => route.query.project as string | undefined)` — do not change this; it is unrelated to which page linked into `/paper/sources`
- No unit test framework is configured in `frontend/` — verification is `npm run build` and live browser checks, run from the `frontend/` directory
- Do not add a test framework or write new automated tests as part of this plan
- Do not remove `ResultsPage.vue`, the `/results` route, or any of its other content (metric cards, AI insight card, comparison table) — only the generate-paper button and its dedicated CSS rule are removed

---

### Task 1: `ResultView.vue` — add the "生成論文" button

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue` (template's `page-header` block, plus new CSS rules)

**Interfaces:**
- Consumes: `--color-accent` (already defined), `projectId` (already defined in this file's `<script setup>`), `summary` (already defined, a `ComputedRef<ModelMetricSummary[]>`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the `page-header` template block**

Replace:

```html
    <div v-if="project" class="page-header">
      <h1 class="page-title">{{ project.name }}</h1>
      <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
    </div>
```

With:

```html
    <div v-if="project" class="page-header">
      <div class="page-header-top">
        <div>
          <h1 class="page-title">{{ project.name }}</h1>
          <p class="page-sub">結果總覽 · 框架：{{ project.frameworkName }}</p>
        </div>
        <RouterLink
          v-if="summary.length > 0"
          class="generate-paper-btn"
          :to="`/paper/sources?project=${projectId}`"
        >
          生成論文
        </RouterLink>
      </div>
    </div>
```

- [ ] **Step 2: Add the new CSS rules**

Replace:

```css
.page-header {
  margin-bottom: 24px;
}
```

With:

```css
.page-header {
  margin-bottom: 24px;
}

.page-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.generate-paper-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s;
}

.generate-paper-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
```

(`.page-header { margin-bottom: 24px; }` appears once in the file's `<style scoped>` block — this is the only occurrence.)

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "feat: add generate-paper button to Hub ResultView"
```

---

### Task 2: `ResultsPage.vue` — remove the "生成論文" button

**Files:**
- Modify: `frontend/src/views/ResultsPage.vue` (remove one template block, one CSS rule)

**Interfaces:**
- Consumes: nothing new
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Remove the button from the toolbar**

Replace:

```html
        <v-btn
          class="generate-paper-btn bg-accent"
          color="accent"
          size="small"
          @click="router.push(`/paper/sources?project=${projectId}`)"
        >
          生成論文
        </v-btn>
      </header>
```

With:

```html
      </header>
```

- [ ] **Step 2: Remove the now-unused CSS rule**

Replace:

```css
  .generate-paper-btn {
    margin-left: 12px;
  }

  .toolbar-tab {
```

With:

```css
  .toolbar-tab {
```

- [ ] **Step 3: Verify no leftover references**

Run: `grep -n "generate-paper-btn" frontend/src/views/ResultsPage.vue`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ResultsPage.vue
git commit -m "feat: remove generate-paper button from standalone ResultsPage"
```

---

### Task 3: `WorkflowWorkspace.vue` — redirect "查看結果" to the Hub page

**Files:**
- Modify: `frontend/src/components/workflow/WorkflowWorkspace.vue` (one `@click` handler)

**Interfaces:**
- Consumes: `projectId` (already defined in this file's `<script setup>` as `computed(() => route.query.project as string | undefined)`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Change the button's navigation target**

Replace:

```html
    <button
      v-if="workflowResult"
      class="view-results-btn"
      type="button"
      @click="router.push(`/results?project=${projectId}`)"
    >
      查看結果
    </button>
```

With:

```html
    <button
      v-if="workflowResult"
      class="view-results-btn"
      type="button"
      @click="router.push(`/hub/projects/${projectId}/result`)"
    >
      查看結果
    </button>
```

- [ ] **Step 2: Verify no leftover references**

Run: `grep -n "'/results?project=" frontend/src/components/workflow/WorkflowWorkspace.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/workflow/WorkflowWorkspace.vue
git commit -m "feat: redirect workflow's view-results button to Hub ResultView"
```

---

### Task 4: `PaperSourcesView.vue` — redirect back/error navigation to the Hub page

**Files:**
- Modify: `frontend/src/views/PaperSourcesView.vue` (two `@click` handlers, one line of user-facing text)

**Interfaces:**
- Consumes: `projectId` (already defined in this file's `<script setup>` as `computed(() => route.query.project as string | undefined)`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Update the top-left back button**

Replace:

```html
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.push(`/results?project=${projectId}`)"
        />
```

With:

```html
        <v-btn
          class="back-btn"
          icon="mdi-arrow-left"
          size="small"
          variant="text"
          @click="router.push(`/hub/projects/${projectId}/result`)"
        />
```

- [ ] **Step 2: Update the "no mining results" empty-state text and button**

Replace:

```html
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從 /results 頁面進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/results?project=${projectId}`)">
          回到 /results
        </v-btn>
      </section>
```

With:

```html
      <section v-else-if="!miningResults" class="sources-status">
        <p>找不到這個專案的探勘結果,請先從結果頁進入。</p>
        <v-btn class="bg-accent" color="accent" size="small" @click="router.push(`/hub/projects/${projectId}/result`)">
          回到結果頁
        </v-btn>
      </section>
```

- [ ] **Step 3: Verify no leftover references**

Run: `grep -n "/results?project=" frontend/src/views/PaperSourcesView.vue`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperSourcesView.vue
git commit -m "feat: redirect PaperSourcesView back/error navigation to Hub ResultView"
```

---

### Task 5: Full verification pass

**Files:**
- No file modifications — this task only verifies the state of Tasks 1–4.

**Interfaces:**
- Consumes: the completed state of Tasks 1–4
- Produces: nothing (terminal task)

- [ ] **Step 1: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 2: Live browser check — Hub result page has the button**

Run (from `frontend/`): `npm run dev`. In the Hub, open a project that has a completed workflow run (`/hub/projects/<id>/result`).

Expected: a "生成論文" button appears next to the page title, accent-colored. Click it — expect navigation to `/paper/sources?project=<id>`.

- [ ] **Step 3: Live browser check — no-results project has no button**

Open a Hub project with no workflow result yet (`/hub/projects/<id>/result` showing the "尚未有可用結果" empty state).

Expected: no "生成論文" button is rendered (the empty-state branch never reaches the button's `v-if`).

- [ ] **Step 4: Live browser check — PaperSourcesView back navigation**

From the Hub result page in Step 2, follow through to `/paper/sources`. Click the back arrow.

Expected: navigates back to `/hub/projects/<id>/result`, not `/results`.

- [ ] **Step 5: Live browser check — workflow completion redirect**

Open `/workflow`, run (or resume) a workflow to completion, click "查看結果".

Expected: navigates to `/hub/projects/<id>/result`, not `/results`.

- [ ] **Step 6: Live browser check — ResultsPage.vue no longer has the button**

Open `/results?project=<id>` directly.

Expected: no "生成論文" button in the toolbar; metric cards, AI insight card, and comparison table still render normally for a project with results.

- [ ] **Step 7: Stop the dev server after checking**

Stop the `npm run dev` process started in Step 2.

---

## Plan Self-Review

**Spec coverage:** All four spec sections (A–D) map directly to Tasks 1–4. Task 5 verifies the end-to-end loop described in the spec's "驗證方式" section.

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" phrasing — every step shows complete before/after code.

**Type consistency:** N/A — no new functions, types, or component props introduced; `projectId` is consumed with its existing type in every file (`string` in `ResultView.vue`, `string | undefined` in `WorkflowWorkspace.vue`/`PaperSourcesView.vue`, matching each file's pre-existing declaration).
