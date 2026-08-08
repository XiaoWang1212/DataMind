# Frontend UX Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three concrete UX bugs: the Hub sidebar's hover state is nearly invisible, the paper editor forces a "取消"/"儲存" click to leave edit mode even with zero changes, and the paper editor toolbar visibly shifts when those two buttons appear/disappear.

**Architecture:** Three independent, small CSS/logic fixes in two existing files — no new components, no new dependencies. `HubSidebar.vue` gets a higher-contrast hover color. `PaperPage.vue` gets a `hasChanges` computed that conditionally unlocks the view/edit switch, plus a template restructure so the action buttons reserve layout space via `visibility` instead of being added/removed from the DOM via `v-if`.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-accent` (`#e8a33d`), `--color-surface` (`#ffffff`)
- No unit test framework is configured in `frontend/` — verification is `npm run build`, `grep`, and live browser `getComputedStyle`/`getBoundingClientRect` checks, run from the `frontend/` directory
- Out of scope — do not touch: any other hover effect outside `HubSidebar.vue`; the existing "has unsaved changes" lock behavior itself (still required when there ARE changes); adding a route-leave confirmation guard; the broader "readability and design polish" initiative (deferred to its own future round)
- Do not add a test framework or write new automated tests as part of this plan

---

### Task 1: Sidebar hover contrast

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue:113-115` and `:139-141`

**Interfaces:**
- Consumes: `--color-accent`, `--color-surface` CSS variables (already defined in `frontend/src/styles/tailwind.css`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `.hub-toggle-btn:hover`**

Replace:

```css
.hub-toggle-btn:hover {
  background: var(--color-primary);
}
```

With:

```css
.hub-toggle-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}
```

- [ ] **Step 2: Edit `.hub-nav-item:hover`**

Replace:

```css
.hub-nav-item:hover {
  background: var(--color-primary);
}
```

With:

```css
.hub-nav-item:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "fix: raise sidebar hover contrast so it's visible against the white sidebar"
```

---

### Task 2: Paper editor toolbar — unlock view on no changes, fix layout shift

**Files:**
- Modify: `frontend/src/views/PaperPage.vue:16-31` (template)
- Modify: `frontend/src/views/PaperPage.vue:63-96` (script — add `hasChanges` computed)
- Modify: `frontend/src/views/PaperPage.vue:208-213` (style — add `.edit-actions` rules)

**Interfaces:**
- Consumes: existing `report`, `savedSnapshot`, `mode` from this same file (unchanged)
- Produces: `hasChanges` computed (`ComputedRef<boolean>`) — used only within this file, not consumed by other tasks

- [ ] **Step 1: Add the `hasChanges` computed**

In the `<script setup>` block, replace:

```ts
  const popoverCitation = computed(() =>
    report.value.citations.find(c => c.id === activeCitationId.value) ?? null,
  )
  const popoverIndex = computed(() =>
    report.value.citations.findIndex(c => c.id === activeCitationId.value) + 1,
  )

  let savedSnapshot: PaperReport = mockPaperReport
```

With:

```ts
  const popoverCitation = computed(() =>
    report.value.citations.find(c => c.id === activeCitationId.value) ?? null,
  )
  const popoverIndex = computed(() =>
    report.value.citations.findIndex(c => c.id === activeCitationId.value) + 1,
  )

  let savedSnapshot: PaperReport = mockPaperReport

  const hasChanges = computed(() =>
    JSON.stringify(toRaw(report.value)) !== JSON.stringify(savedSnapshot),
  )
```

- [ ] **Step 2: Update the template — unlock `ModeSwitch` when there are no changes, and reserve layout space for the action buttons**

Replace:

```html
        <div class="toolbar-actions">
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
          <template v-if="mode === 'edit'">
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="!projectId"
              :loading="saving"
              size="small"
              @click="save"
            >
              儲存
            </v-btn>
          </template>
        </div>
```

With:

```html
        <div class="toolbar-actions">
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit' && hasChanges" />
          <div class="edit-actions" :class="{ 'edit-actions--hidden': mode !== 'edit' }">
            <v-btn size="small" variant="text" @click="cancelEdit">取消</v-btn>
            <v-btn
              class="bg-accent"
              color="accent"
              :disabled="!projectId"
              :loading="saving"
              size="small"
              @click="save"
            >
              儲存
            </v-btn>
          </div>
        </div>
```

- [ ] **Step 3: Add CSS for `.edit-actions`**

In the `<style scoped>` block, replace:

```css
  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }
```

With:

```css
  .toolbar-actions {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-left: auto;
  }

  .edit-actions {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .edit-actions--hidden {
    visibility: hidden;
    pointer-events: none;
  }
```

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "fix: allow leaving paper edit mode without saving when unchanged, and stop toolbar layout shift"
```

---

### Task 3: Fix `hasChanges` snapshot timing

> Added after Task 2's implementer found, via live browser testing with direct Vue internal-state inspection, that the `hasChanges` computed as originally specified is unreliable: Tiptap normalizes the editor's JSON content (fills in default node attributes) the moment `PaperEditor` mounts — which happens on page load, not on entering edit mode — silently growing `report.value.content` beyond what `savedSnapshot` captured moments earlier in `onMounted`, before `PaperEditor` had a chance to mount. Because `savedSnapshot` is only ever a snapshot of "the last saved-to-server state" (correct for `cancelEdit()`'s revert behavior, which must not change), comparing live content against it conflates "Tiptap's one-time normalization noise" with "the user actually typed something," making `hasChanges` effectively true most of the time regardless of real edits. Separately, `toRaw(report.value)` in the comparison strips Vue's reactive proxy before `JSON.stringify` reads nested properties, meaning the computed never re-tracks nested content mutations (typing) as a dependency in the first place — it was only "working" in prior manual spot checks by coincidence of when it happened to first evaluate.
>
> Fix: track a *separate* snapshot — `editEntrySnapshot` — captured fresh every time `mode` transitions to `'edit'` (by which point Tiptap's mount-time normalization has long settled), and compare `hasChanges` against that instead of `savedSnapshot`. Drop `toRaw()` so `JSON.stringify` reads through the reactive proxy and properly tracks nested changes. `savedSnapshot` and `cancelEdit()`'s revert-to-last-saved behavior are completely unchanged.

**Files:**
- Modify: `frontend/src/views/PaperPage.vue:63-100` (script)

**Interfaces:**
- Consumes: existing `report`, `mode`, `savedSnapshot` from this same file (unchanged)
- Produces: `hasChanges` computed now compares against `editEntrySnapshot` instead of `savedSnapshot` — no change to what later tasks (Task 4, verification) observe from the outside; the `:locked` template binding in `PaperPage.vue` is unchanged (still reads `hasChanges`)

- [ ] **Step 1: Add `watch` to the Vue imports**

Replace:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
```

With:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw, watch } from 'vue'
```

- [ ] **Step 2: Replace the `hasChanges` computed with a fresh-per-edit-session snapshot**

Replace:

```ts
  let savedSnapshot: PaperReport = mockPaperReport

  const hasChanges = computed(() =>
    JSON.stringify(toRaw(report.value)) !== JSON.stringify(savedSnapshot),
  )
```

With:

```ts
  let savedSnapshot: PaperReport = mockPaperReport
  let editEntrySnapshot: PaperReport | null = null

  const hasChanges = computed(() =>
    JSON.stringify(report.value) !== JSON.stringify(editEntrySnapshot),
  )

  watch(mode, newMode => {
    if (newMode === 'edit') {
      editEntrySnapshot = structuredClone(toRaw(report.value))
    }
  })
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Browser verification of the actual fix**

Run (from `frontend/`): `npm run dev`. Open `/paper`.

1. Wait a moment after the page finishes loading (let Tiptap's initial mount-time normalization settle) — do NOT type anything.
2. Click 編輯 (enter edit mode).
3. Click 檢視 (view). Expected: it switches to view mode immediately (this is the scenario that was broken before this fix — it should now work reliably, not just on a lucky first try).
4. Click 編輯 again, type a character into the editor body, then click 檢視. Expected: nothing happens (stays locked) — the mode switch is still disabled.
5. Click 取消. Expected: reverts to view mode, editor content reverts to what it was before step 4's typing.
6. Click 編輯 again (without typing anything this time). Click 檢視. Expected: switches to view mode immediately — this is the specific case that was broken (stuck locked after a Cancel) — it must now work.

If you have live browser tooling available, perform this sequence for real and inspect `document.querySelectorAll('.mode-switch-btn')[0].disabled` at each step to confirm the true underlying state, not just visual appearance. If you cannot drive a browser interactively, state that clearly — the controller will independently verify this sequence afterward.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "fix: re-baseline hasChanges snapshot on each edit-mode entry, fixing stuck-locked view switch"
```

---

### Task 4: Revert the no-changes-unlock feature, keep the layout-shift fix

> Added after Task 3's implementer found, via live browser testing with direct Vue internal-state inspection, that the `hasChanges`/`editEntrySnapshot` approach still doesn't fully work: Tiptap normalizes the document JSON not only on mount (Task 2's finding) but *also* the first time `PaperEditor`'s `editable` prop flips from `false` to `true` — which races against the `watch(mode, ...)` snapshot capture and beats it, leaving the very first edit-mode entry on a fresh page load permanently stuck locked even with zero typing. A robust fix would require exposing Tiptap's live document state from `PaperEditor.vue` directly (reading `editor.getJSON()` after its own normalization settles, rather than round-tripping through the `v-model`/`report.value` chain) — which means touching a file explicitly out of scope for this plan. Given two fix attempts have both left a real gap, the decision is to revert the no-changes-unlock feature entirely and keep only the layout-shift fix (Task 2's other deliverable, which works correctly and is unaffected by this issue) and the sidebar hover fix (Task 1). `ModeSwitch` goes back to being unconditionally locked while `mode === 'edit'` — the pre-existing behavior of requiring an explicit "取消" or "儲存" click to leave edit mode, regardless of whether anything changed.

**Files:**
- Modify: `frontend/src/views/PaperPage.vue:17` (template)
- Modify: `frontend/src/views/PaperPage.vue:63-107` (script)

**Interfaces:**
- Consumes: nothing new
- Produces: nothing consumed by later tasks — `hasChanges`, `editEntrySnapshot`, and the `mode` watcher are removed entirely; `savedSnapshot` and `cancelEdit()` are unaffected (unchanged from their original, pre-Task-2 behavior)

- [ ] **Step 1: Revert the `ModeSwitch` `:locked` binding**

Replace:

```html
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit' && hasChanges" />
```

With:

```html
          <ModeSwitch v-model="mode" :disabled="loading" :locked="mode === 'edit'" />
```

- [ ] **Step 2: Remove `watch` from the Vue import list**

Replace:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw, watch } from 'vue'
```

With:

```ts
  import type { PaperReport } from '@/constants/reportData'
  import { computed, onMounted, ref, toRaw } from 'vue'
```

- [ ] **Step 3: Remove `hasChanges`, `editEntrySnapshot`, and the `mode` watcher**

Replace:

```ts
  let savedSnapshot: PaperReport = mockPaperReport
  let editEntrySnapshot: PaperReport | null = null

  const hasChanges = computed(() =>
    JSON.stringify(report.value) !== JSON.stringify(editEntrySnapshot),
  )

  watch(mode, newMode => {
    if (newMode === 'edit') {
      editEntrySnapshot = structuredClone(toRaw(report.value))
    }
  })
```

With:

```ts
  let savedSnapshot: PaperReport = mockPaperReport
```

- [ ] **Step 4: Verify no leftover references**

Run: `grep -n "hasChanges\|editEntrySnapshot" frontend/src/views/PaperPage.vue`
Expected: no output.

- [ ] **Step 5: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors (in particular, no "unused variable" lint-as-error or TS error from the removed `watch`/`toRaw`/`computed` usages — `toRaw` and `computed` are still used elsewhere in the file for `savedSnapshot`'s consumers and the other computeds, so their imports stay; only `watch` should be fully removed).

- [ ] **Step 6: Browser sanity check**

Run (from `frontend/`): `npm run dev`. Open `/paper`. Click 編輯 without typing anything, then click 檢視. Expected: nothing happens — the switch is locked, exactly like before Task 2 ever ran. Click 取消 instead. Expected: returns to view mode. Confirm the Cancel/Save buttons still don't shift the `ModeSwitch` position when they appear/disappear (Task 2's layout-shift fix must still hold).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "revert: drop no-changes-unlock feature, keep layout-shift fix

Two fix attempts (re-baselining the change-detection snapshot) both
left a real gap due to Tiptap's document normalization racing against
Vue's reactivity timing on the editable-prop toggle. A robust fix
needs PaperEditor.vue to expose its live Tiptap state directly, which
is out of scope here. Reverting to the original always-locked
behavior; the layout-shift fix and sidebar hover fix are unaffected
and remain."
```

---

### Task 5: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: the changes from Tasks 1 and 2
- Produces: nothing

- [ ] **Step 1: Run a clean full build**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 2: Sidebar hover — manual and computed-style check**

Run (from `frontend/`): `npm run dev`
Open any `/hub/*` route. Hover over a non-active sidebar nav item and the collapse toggle button. Expected: a visibly distinct light amber tint appears, clearly different from the white sidebar background — not the near-invisible previous state.

In the browser devtools console, with the mouse held over a nav item (or by adding/removing the `:hover` pseudo-class via devtools' "Force state" if scripting a real hover is inconvenient):
```js
getComputedStyle(document.querySelector('.hub-nav-item:hover')).backgroundColor
// expect: NOT "rgb(255, 255, 255)" and NOT "rgb(246, 245, 242)" — a visibly tinted color
```

- [ ] **Step 3: Paper editor — mode lock check (post-revert behavior)**

> Note: the original no-changes-unlock feature was reverted in Task 4 after two fix attempts both left real gaps (see Task 4's rationale above). This step now verifies the reverted, original behavior instead.

Navigate to `/paper` (with a `?project=` query param for an existing project if available, otherwise the mock report still renders). Click "編輯" to enter edit mode without typing anything. Click "檢視" in the mode switch. Expected: **nothing happens** — the switch stays locked in edit mode (matches the pre-Task-2 behavior; this is intentional, not a bug). Click "取消" instead. Expected: returns to view mode.

Re-enter edit mode and type/change something in the editor body. Click "檢視" again. Expected: still nothing happens (locked) — only "取消" or "儲存" can leave, same as above.

- [ ] **Step 4: Paper editor — layout shift check**

While on `/paper` in edit mode with no changes made, in the browser devtools console:
```js
document.querySelector('.mode-switch').getBoundingClientRect().left
```
Note the value. Toggle to view mode, then back to edit mode, running the same command each time. Expected: the value is identical in all three states (view, edit-no-changes, edit-with-changes) — the switch never moves horizontally regardless of whether the "取消"/"儲存" buttons are visible.

Stop the dev server after checking.

- [ ] **Step 5: Confirm no leftover references to the old hover color on these elements**

Run: `grep -n "hover" frontend/src/components/hub/HubSidebar.vue`
Expected: both `.hub-toggle-btn:hover` and `.hub-nav-item:hover` blocks show `color-mix(in oklab, var(--color-accent) 12%, var(--color-surface))`, not `var(--color-primary)`.
