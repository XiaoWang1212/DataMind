# Hub Content Color Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the project's `--color-*` design tokens to the 8 Hub page-content views under `frontend/src/views/hub/`: the shared CTA blue becomes accent, text greys become ink/secondary, `ResultView.vue`'s chat bubbles get the first real use of the `chat-user`/`chat-system` tokens, and duplicate status-color hex values get unified.

**Architecture:** Pure CSS value swaps inside each file's existing `<style scoped>` block — no template or script changes anywhere. Each task replaces one file's entire style block in a single edit (the files are short enough that this is simpler and less error-prone than many small find/replace edits).

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-secondary` (`#334155`), `--color-accent` (`#e8a33d`), `--color-surface` (`#ffffff`), `--color-ink` (`#1c2130`), `--color-chat-system` (`#fbead0`), `--color-chat-user` (`#12213b`), `--color-inverted` (`#f1f5f9`)
- Substitution rules (apply verbatim, no exceptions except where explicitly noted per-file below):
  - `#111827` → `var(--color-ink)`
  - `#9ca3af` → `var(--color-secondary)`
  - `#6b7280` → `var(--color-secondary)`
  - `#374151` → `var(--color-secondary)`
  - `#2347c5` → `var(--color-accent)`
  - `#1b3ca0` (the hover state of `#2347c5`) → `color-mix(in oklab, var(--color-accent) 85%, black)`
  - `#f0f4ff` (the light-blue selected/hover background paired with `#2347c5`) → `color-mix(in oklab, var(--color-accent) 12%, var(--color-surface))`
- **Exception — do not convert to accent:** `.badge--completed`'s text color. This status badge intentionally stays blue (a status color, independent of the brand accent), it just gets unified to one hex value: `#2347c5` literal (not a token). `ProjectsView.vue`'s `.badge--completed` is already `#2347c5` (no change needed there); `ProjectDetailView.vue`'s `.badge--completed` is `#1d4ed8` and must change to the literal hex `#2347c5` (not `var(--color-accent)`).
- **Status color hex unification (not brand tokens, just literal hex merges):** `#18a836` → `#16a34a` (success, `ResultView.vue` only); `#b91c1c` → `#ef4444` (error, `ExtractFrameworkView.vue`); `#d64545` → `#ef4444` (error, `ResultView.vue`, 3 occurrences)
- **Never touch:** neutral border/divider colors (`#e8e8e8`, `#e5e7eb`, `#e2e4ea`, `#f0f0f0`, `#f0f1f3`, `#f3f3f3`, `#d1d5db`, `#c4c9d4`), decorative icon swatch colors (`#4f46e5`, `#c7d2fe`, `#e0e7ff`, `#f59e0b`, `#fed7aa`, `#a5b4fc`, `#93c5fd`, `#3730a3`, `#ede9fe`, `#5b21b6`), `.progress-bar`'s `#f59e0b` fill, `.badge--running`'s `#fef3c7`/`#d97706`, `.badge--draft`'s background/text, plain white card/panel backgrounds (`#ffffff`), `#fafafa`, `#f9fafb`, `#f5f5f5`, `#f7f7f9`, `#fafbff`, `#eef1ff`, `#b7c2e6`, `#fef2f2`/`#fecaca` (error-box background/border, only the text color unifies)
- No unit test framework is configured in `frontend/` — verification is `npm run build` and live browser `getComputedStyle` checks, run from the `frontend/` directory
- Do not add a test framework or write new automated tests as part of this plan

---

### Task 1: `DashboardView.vue`

**Files:**
- Modify: `frontend/src/views/hub/DashboardView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── Stats ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 22px 18px;
}

.stat-label {
  font-size: 12.5px;
  color: #9ca3af;
  margin-bottom: 10px;
  font-weight: 400;
}

.stat-number {
  font-size: 42px;
  font-weight: 700;
  color: #111827;
  line-height: 1;
  margin-bottom: 12px;
  letter-spacing: -1px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #9ca3af;
}

/* ── Actions ── */
.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.action-card {
  background: #ffffff;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
}

.action-card:hover {
  border-color: #a5b4fc;
  background: #fafafa;
}

.action-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon-wrap--blue {
  background: #c7d2fe;
}

.action-icon-wrap--orange {
  background: #fed7aa;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 3px;
}

.action-desc {
  font-size: 12.5px;
  color: #9ca3af;
  line-height: 1.45;
}

/* ── Activity ── */
.activity-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
}

.activity-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #111827;
}

.activity-title {
  font-size: 15px;
  font-weight: 600;
}

.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
  border-bottom: 1px solid #f0f0f0;
}

.activity-item--last {
  border-bottom: none;
  padding-bottom: 0;
}

.activity-name {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  margin-bottom: 4px;
}

.activity-status {
  font-size: 12.5px;
  color: #9ca3af;
}

.activity-time {
  font-size: 12.5px;
  color: #9ca3af;
  white-space: nowrap;
  margin-left: 24px;
}
</style>
```

With:

```css
<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Stats ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.stat-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 22px 18px;
}

.stat-label {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-bottom: 10px;
  font-weight: 400;
}

.stat-number {
  font-size: 42px;
  font-weight: 700;
  color: var(--color-ink);
  line-height: 1;
  margin-bottom: 12px;
  letter-spacing: -1px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Actions ── */
.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}

.action-card {
  background: #ffffff;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  padding: 20px 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
}

.action-card:hover {
  border-color: #a5b4fc;
  background: #fafafa;
}

.action-icon-wrap {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.action-icon-wrap--blue {
  background: #c7d2fe;
}

.action-icon-wrap--orange {
  background: #fed7aa;
}

.action-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 3px;
}

.action-desc {
  font-size: 12.5px;
  color: var(--color-secondary);
  line-height: 1.45;
}

/* ── Activity ── */
.activity-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
}

.activity-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: var(--color-ink);
}

.activity-title {
  font-size: 15px;
  font-weight: 600;
}

.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0;
  border-bottom: 1px solid #f0f0f0;
}

.activity-item--last {
  border-bottom: none;
  padding-bottom: 0;
}

.activity-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-ink);
  margin-bottom: 4px;
}

.activity-status {
  font-size: 12.5px;
  color: var(--color-secondary);
}

.activity-time {
  font-size: 12.5px;
  color: var(--color-secondary);
  white-space: nowrap;
  margin-left: 24px;
}
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af" frontend/src/views/hub/DashboardView.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/DashboardView.vue
git commit -m "feat: apply color tokens to DashboardView"
```

---

### Task 2: `ProjectsView.vue`

**Files:**
- Modify: `frontend/src/views/hub/ProjectsView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.page-header {
  margin-bottom: 22px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── New button ── */
.new-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  margin-bottom: 18px;
  transition: background 0.15s;
}

.new-btn:hover {
  background: #1b3ca0;
}

/* ── Project list ── */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.project-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 22px;
  text-decoration: none;
  transition: border-color 0.15s;
}

.project-card:hover {
  border-color: #c7d2fe;
}

.project-main {
  flex: 1;
  min-width: 0;
}

.project-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.project-name {
  font-size: 14.5px;
  font-weight: 600;
  color: #111827;
}

/* ── Badges ── */
.badge {
  font-size: 11.5px;
  font-weight: 500;
  padding: 2px 9px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #2347c5;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: #6b7280;
}

/* ── Meta ── */
.project-meta {
  font-size: 12.5px;
  color: #6b7280;
  margin-bottom: 5px;
}

.project-date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: #9ca3af;
}

.date-icon {
  color: #9ca3af;
}

/* ── Progress ── */
.progress-wrap {
  margin-top: 10px;
}

.progress-label-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.progress-label {
  font-size: 12px;
  color: #6b7280;
}

.progress-pct {
  font-size: 12px;
  color: #6b7280;
}

.progress-track {
  height: 5px;
  background: #f0f0f0;
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #f59e0b;
  border-radius: 99px;
  transition: width 0.3s;
}

.project-arrow {
  color: #c4c9d4;
  flex-shrink: 0;
  margin-left: 16px;
}
</style>
```

With:

```css
<style scoped>
.page-header {
  margin-bottom: 22px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── New button ── */
.new-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  margin-bottom: 18px;
  transition: background 0.15s;
}

.new-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Project list ── */
.project-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.project-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 22px;
  text-decoration: none;
  transition: border-color 0.15s;
}

.project-card:hover {
  border-color: #c7d2fe;
}

.project-main {
  flex: 1;
  min-width: 0;
}

.project-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.project-name {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-ink);
}

/* ── Badges ── */
.badge {
  font-size: 11.5px;
  font-weight: 500;
  padding: 2px 9px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #2347c5;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: var(--color-secondary);
}

/* ── Meta ── */
.project-meta {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-bottom: 5px;
}

.project-date {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: var(--color-secondary);
}

.date-icon {
  color: var(--color-secondary);
}

/* ── Progress ── */
.progress-wrap {
  margin-top: 10px;
}

.progress-label-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.progress-label {
  font-size: 12px;
  color: var(--color-secondary);
}

.progress-pct {
  font-size: 12px;
  color: var(--color-secondary);
}

.progress-track {
  height: 5px;
  background: #f0f0f0;
  border-radius: 99px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #f59e0b;
  border-radius: 99px;
  transition: width 0.3s;
}

.project-arrow {
  color: #c4c9d4;
  flex-shrink: 0;
  margin-left: 16px;
}
</style>
```

Note: `.badge--completed`'s `color: #2347c5;` is intentionally unchanged (per Global Constraints exception — stays literal hex, not accent).

- [ ] **Step 2: Verify no leftover old color values (excluding the intentional `.badge--completed` exception)**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#1b3ca0" frontend/src/views/hub/ProjectsView.vue`
Expected: no output.

Run: `grep -n "#2347c5" frontend/src/views/hub/ProjectsView.vue`
Expected: exactly 1 match, inside `.badge--completed` — confirms the exception is intact and no other `#2347c5` remains.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/ProjectsView.vue
git commit -m "feat: apply color tokens to ProjectsView"
```

---

### Task 3: `FrameworkLibraryView.vue`

**Files:**
- Modify: `frontend/src/views/hub/FrameworkLibraryView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.page-header {
  margin-bottom: 22px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.search-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 11px;
  color: #9ca3af;
}

.search-input {
  width: 100%;
  height: 38px;
  padding: 0 14px 0 36px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: #111827;
  outline: none;
  transition: border-color 0.15s;
  color-scheme: light;
}

.search-input::placeholder {
  color: #9ca3af;
}

.search-input:focus {
  border-color: #2347c5;
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s;
}

.upload-btn:hover {
  background: #1b3ca0;
}

/* ── Cards ── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.fw-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-card:hover {
  border-color: #a5b4fc;
}

.fw-card--selected {
  border: 1.5px solid #2347c5;
}

.fw-card-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.fw-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fw-info {
  flex: 1;
  min-width: 0;
}

.fw-title {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.fw-subtitle {
  font-size: 12px;
  color: #9ca3af;
  margin-top: 4px;
  line-height: 1.4;
}

.fw-meta {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-top: 1px solid #f0f0f0;
  padding-top: 14px;
  margin-bottom: 12px;
}

.fw-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #6b7280;
}

.meta-icon {
  color: #9ca3af;
  flex-shrink: 0;
}

.fw-vars {
  font-size: 12px;
  color: #9ca3af;
}

/* ── Empty ── */
.empty-state {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}

/* ── Detail panel ── */
.detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  background: #ffffff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  z-index: 200;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.06);
}

/* Slide transition */
.panel-enter-active,
.panel-leave-active {
  transition: transform 0.22s ease;
}

.panel-enter-from,
.panel-leave-to {
  transform: translateX(100%);
}

/* ── Panel header ── */
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.panel-header-info {
  flex: 1;
  min-width: 0;
  padding-right: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  line-height: 1.3;
}

.panel-tag {
  font-size: 12.5px;
  color: #9ca3af;
  margin-top: 3px;
}

.panel-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  cursor: pointer;
  color: #9ca3af;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  transition: background 0.12s;
  flex-shrink: 0;
}

.panel-close:hover {
  background: #f5f5f5;
  color: #374151;
}

/* ── Panel body ── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px;
}

.panel-section {
  padding: 18px 0;
  border-bottom: 1px solid #f3f3f3;
}

.panel-section:last-child {
  border-bottom: none;
}

.panel-section-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
}

.section-icon {
  color: #6b7280;
}

.panel-section-label {
  font-size: 13.5px;
  font-weight: 600;
  color: #374151;
}

.panel-section-label-plain {
  font-size: 13.5px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 10px;
}

.panel-text-muted {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.55;
}

/* ── Variables ── */
.var-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-item {
  padding: 9px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'Courier New', 'Roboto Mono', Consolas, monospace;
  color: #374151;
  background: #ffffff;
}

/* ── Hypotheses ── */
.hypothesis-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hypothesis-item {
  padding: 8px 12px;
  border-left: 2.5px solid #93c5fd;
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
}

/* ── Footer meta ── */
.panel-footer-meta {
  padding: 14px 0;
  border-top: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.panel-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
}

.panel-meta-key {
  color: #9ca3af;
}

.panel-meta-val {
  color: #374151;
  font-weight: 500;
}

/* ── Action button ── */
.panel-action {
  padding: 16px 20px;
  flex-shrink: 0;
  border-top: 1px solid #f0f0f0;
}

.use-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 46px;
  background: #2347c5;
  color: #ffffff;
  border-radius: 8px;
  text-decoration: none;
  font-size: 15px;
  font-weight: 600;
  transition: background 0.15s;
}

.use-btn:hover {
  background: #1b3ca0;
}
</style>
```

With:

```css
<style scoped>
.page-header {
  margin-bottom: 22px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.search-wrap {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 11px;
  color: var(--color-secondary);
}

.search-input {
  width: 100%;
  height: 38px;
  padding: 0 14px 0 36px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: var(--color-ink);
  outline: none;
  transition: border-color 0.15s;
  color-scheme: light;
}

.search-input::placeholder {
  color: var(--color-secondary);
}

.search-input:focus {
  border-color: var(--color-accent);
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 7px;
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s;
}

.upload-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Cards ── */
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.fw-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-card:hover {
  border-color: #a5b4fc;
}

.fw-card--selected {
  border: 1.5px solid var(--color-accent);
}

.fw-card-top {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.fw-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.fw-info {
  flex: 1;
  min-width: 0;
}

.fw-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.fw-subtitle {
  font-size: 12px;
  color: var(--color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.fw-meta {
  display: flex;
  flex-direction: column;
  gap: 7px;
  border-top: 1px solid #f0f0f0;
  padding-top: 14px;
  margin-bottom: 12px;
}

.fw-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-secondary);
}

.meta-icon {
  color: var(--color-secondary);
  flex-shrink: 0;
}

.fw-vars {
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Empty ── */
.empty-state {
  text-align: center;
  padding: 48px;
  color: var(--color-secondary);
  font-size: 14px;
}

/* ── Detail panel ── */
.detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 380px;
  background: #ffffff;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  z-index: 200;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.06);
}

/* Slide transition */
.panel-enter-active,
.panel-leave-active {
  transition: transform 0.22s ease;
}

.panel-enter-from,
.panel-leave-to {
  transform: translateX(100%);
}

/* ── Panel header ── */
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 22px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.panel-header-info {
  flex: 1;
  min-width: 0;
  padding-right: 12px;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-ink);
  line-height: 1.3;
}

.panel-tag {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-top: 3px;
}

.panel-close {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  transition: background 0.12s;
  flex-shrink: 0;
}

.panel-close:hover {
  background: #f5f5f5;
  color: var(--color-secondary);
}

/* ── Panel body ── */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 20px;
}

.panel-section {
  padding: 18px 0;
  border-bottom: 1px solid #f3f3f3;
}

.panel-section:last-child {
  border-bottom: none;
}

.panel-section-head {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 10px;
}

.section-icon {
  color: var(--color-secondary);
}

.panel-section-label {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-secondary);
}

.panel-section-label-plain {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-secondary);
  margin-bottom: 10px;
}

.panel-text-muted {
  font-size: 13px;
  color: var(--color-secondary);
  line-height: 1.55;
}

/* ── Variables ── */
.var-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.var-item {
  padding: 9px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'Courier New', 'Roboto Mono', Consolas, monospace;
  color: var(--color-secondary);
  background: #ffffff;
}

/* ── Hypotheses ── */
.hypothesis-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hypothesis-item {
  padding: 8px 12px;
  border-left: 2.5px solid #93c5fd;
  font-size: 13px;
  color: var(--color-secondary);
  line-height: 1.5;
}

/* ── Footer meta ── */
.panel-footer-meta {
  padding: 14px 0;
  border-top: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
}

.panel-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
}

.panel-meta-key {
  color: var(--color-secondary);
}

.panel-meta-val {
  color: var(--color-secondary);
  font-weight: 500;
}

/* ── Action button ── */
.panel-action {
  padding: 16px 20px;
  flex-shrink: 0;
  border-top: 1px solid #f0f0f0;
}

.use-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 46px;
  background: var(--color-accent);
  color: #ffffff;
  border-radius: 8px;
  text-decoration: none;
  font-size: 15px;
  font-weight: 600;
  transition: background 0.15s;
}

.use-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
```

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#374151\|#2347c5\|#1b3ca0" frontend/src/views/hub/FrameworkLibraryView.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/FrameworkLibraryView.vue
git commit -m "feat: apply color tokens to FrameworkLibraryView"
```

---

### Task 4: `CreateProjectView.vue`

**Files:**
- Modify: `frontend/src/views/hub/CreateProjectView.vue` (entire `<style scoped>` block, plus one inline Vuetify icon `color` prop in the template)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit the template's icon color prop**

Replace:

```html
        <div v-if="form.datasetFile" class="file-info">
          <v-icon icon="mdi-file-table-outline" size="18" color="#2347c5" />
          <span class="file-name">{{ form.datasetFile.name }}</span>
        </div>
```

With:

```html
        <div v-if="form.datasetFile" class="file-info">
          <v-icon icon="mdi-file-table-outline" size="18" color="var(--color-accent)" />
          <span class="file-name">{{ form.datasetFile.name }}</span>
        </div>
```

- [ ] **Step 2: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── Stepper ── */
.stepper {
  display: flex;
  align-items: flex-start;
  gap: 0;
  margin-bottom: 28px;
  position: relative;
}

.stepper-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  position: relative;
}

.stepper-line {
  position: absolute;
  top: 16px;
  left: calc(100% - 50%);
  width: calc(100% - 44px);
  height: 1px;
  background: #e5e7eb;
  z-index: 0;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.step-circle--active {
  background: #2347c5;
  color: #ffffff;
}

.step-circle--done {
  background: #2347c5;
  color: #ffffff;
}

.step-circle--inactive {
  background: #ffffff;
  color: #9ca3af;
  border: 2px solid #e5e7eb;
}

.step-info {
  flex: 1;
  padding-top: 4px;
}

.step-title {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
}

.step-title--active {
  color: #111827;
}

.step-sub {
  font-size: 11.5px;
  color: #9ca3af;
  margin-top: 2px;
}

/* ── Form card ── */
.form-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 28px;
  margin-bottom: 0;
  color: #111827;
}

.form-field {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: #111827;
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-input:focus {
  border-color: #2347c5;
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: #111827;
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-textarea::placeholder {
  color: #9ca3af;
}

.form-textarea:focus {
  border-color: #2347c5;
}

/* ── Framework select ── */
.fw-select-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.fw-select-card {
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-select-card:hover {
  border-color: #a5b4fc;
}

.fw-select-card--selected {
  border-color: #2347c5;
  background: #f0f4ff;
}

.fw-select-icon {
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.fw-select-name {
  font-size: 13.5px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 4px;
}

.fw-select-tag {
  font-size: 12px;
  color: #6b7280;
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover {
  border-color: #2347c5;
  background: #f0f4ff;
}

.drop-icon {
  color: #9ca3af;
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: #9ca3af;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.file-name {
  font-size: 13px;
  color: #374151;
}

/* ── Review ── */
.review-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.review-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 16px;
}

.review-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
  font-size: 13.5px;
}

.review-key {
  width: 120px;
  flex-shrink: 0;
  color: #9ca3af;
}

.review-val {
  color: #111827;
  font-weight: 500;
}

/* ── Footer buttons ── */
.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 28px;
  background: #ffffff;
  color: #111827;
  border-radius: 0 0 8px 8px;
  border: 1px solid #e8e8e8;
  border-top: 1px solid #f0f0f0;
  margin-top: -1px;
}

.prev-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: #6b7280;
  padding: 0 8px;
  transition: color 0.12s;
}

.prev-btn:disabled {
  color: #d1d5db;
  cursor: default;
}

.prev-btn:not(:disabled):hover {
  color: #111827;
}

.next-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 22px;
  height: 40px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.next-btn:hover {
  background: #1b3ca0;
}
</style>
```

With:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-secondary);
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: var(--color-ink);
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Stepper ── */
.stepper {
  display: flex;
  align-items: flex-start;
  gap: 0;
  margin-bottom: 28px;
  position: relative;
}

.stepper-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  flex: 1;
  position: relative;
}

.stepper-line {
  position: absolute;
  top: 16px;
  left: calc(100% - 50%);
  width: calc(100% - 44px);
  height: 1px;
  background: #e5e7eb;
  z-index: 0;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.step-circle--active {
  background: var(--color-accent);
  color: #ffffff;
}

.step-circle--done {
  background: var(--color-accent);
  color: #ffffff;
}

.step-circle--inactive {
  background: #ffffff;
  color: var(--color-secondary);
  border: 2px solid #e5e7eb;
}

.step-info {
  flex: 1;
  padding-top: 4px;
}

.step-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-secondary);
}

.step-title--active {
  color: var(--color-ink);
}

.step-sub {
  font-size: 11.5px;
  color: var(--color-secondary);
  margin-top: 2px;
}

/* ── Form card ── */
.form-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 28px;
  margin-bottom: 0;
  color: var(--color-ink);
}

.form-field {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-input::placeholder {
  color: var(--color-secondary);
}

.form-input:focus {
  border-color: var(--color-accent);
}

.form-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 14px;
  color: var(--color-ink);
  background-color: #ffffff;
  outline: none;
  box-sizing: border-box;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.15s;
  color-scheme: light;
}

.form-textarea::placeholder {
  color: var(--color-secondary);
}

.form-textarea:focus {
  border-color: var(--color-accent);
}

/* ── Framework select ── */
.fw-select-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.fw-select-card {
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.fw-select-card:hover {
  border-color: #a5b4fc;
}

.fw-select-card--selected {
  border-color: var(--color-accent);
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.fw-select-icon {
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: #e0e7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.fw-select-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 4px;
}

.fw-select-tag {
  font-size: 12px;
  color: var(--color-secondary);
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover {
  border-color: var(--color-accent);
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.drop-icon {
  color: var(--color-secondary);
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: var(--color-secondary);
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: var(--color-secondary);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.file-name {
  font-size: 13px;
  color: var(--color-secondary);
}

/* ── Review ── */
.review-section {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.review-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 16px;
}

.review-row {
  display: flex;
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
  font-size: 13.5px;
}

.review-key {
  width: 120px;
  flex-shrink: 0;
  color: var(--color-secondary);
}

.review-val {
  color: var(--color-ink);
  font-weight: 500;
}

/* ── Footer buttons ── */
.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 28px;
  background: #ffffff;
  color: var(--color-ink);
  border-radius: 0 0 8px 8px;
  border: 1px solid #e8e8e8;
  border-top: 1px solid #f0f0f0;
  margin-top: -1px;
}

.prev-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-secondary);
  padding: 0 8px;
  transition: color 0.12s;
}

.prev-btn:disabled {
  color: #d1d5db;
  cursor: default;
}

.prev-btn:not(:disabled):hover {
  color: var(--color-ink);
}

.next-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 22px;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.next-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
```

- [ ] **Step 3: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#374151\|#2347c5\|#1b3ca0\|#f0f4ff" frontend/src/views/hub/CreateProjectView.vue`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/CreateProjectView.vue
git commit -m "feat: apply color tokens to CreateProjectView"
```

---

### Task 5: `ExtractFrameworkView.vue`

**Files:**
- Modify: `frontend/src/views/hub/ExtractFrameworkView.vue` (template's `v-progress-circular` color prop, and the entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit the template's progress-circular color prop**

Replace:

```html
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular color="#2347c5" indeterminate size="20" width="2" />
          <span>正在提取框架...</span>
        </div>
```

With:

```html
        <div v-if="extracting" class="extracting-indicator">
          <v-progress-circular color="var(--color-accent)" indeterminate size="20" width="2" />
          <span>正在提取框架...</span>
        </div>
```

- [ ] **Step 2: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── Panels ── */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.panel-label {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 12px;
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: #ffffff;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover,
.drop-zone--over {
  border-color: #2347c5;
  background: #f0f4ff;
}

.drop-icon {
  color: #9ca3af;
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: #9ca3af;
}

/* ── File info ── */
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: #374151;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: #9ca3af;
  display: flex;
  align-items: center;
  padding: 0;
}

.file-remove:hover {
  color: #ef4444;
}

.extract-btn {
  margin-top: 14px;
  width: 100%;
  height: 40px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.extract-btn:hover {
  background: #1b3ca0;
}

.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: #6b7280;
}

/* ── Result zone ── */
.result-zone {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  min-height: 200px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-placeholder {
  color: #9ca3af;
  font-size: 13.5px;
  margin: auto;
  text-align: center;
}

.result-error {
  color: #b91c1c;
  font-size: 13px;
  font-weight: 500;
  padding: 10px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 7px;
}

.result-field-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.result-field-value {
  font-size: 14px;
  color: #111827;
  font-weight: 500;
}

/* ── Tags ── */
.result-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.result-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: #e0e7ff;
  color: #3730a3;
}

.result-tag--gray {
  background: #f3f4f6;
  color: #374151;
}

.result-tag--indigo {
  background: #ede9fe;
  color: #5b21b6;
}

.save-btn {
  margin-top: 4px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: #1b3ca0;
}
</style>
```

With:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-secondary);
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: var(--color-ink);
}

.page-header {
  margin-bottom: 28px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Panels ── */
.panels {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.panel-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 12px;
}

/* ── Drop zone ── */
.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: #ffffff;
  transition: border-color 0.15s, background 0.15s;
}

.drop-zone:hover,
.drop-zone--over {
  border-color: var(--color-accent);
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
}

.drop-icon {
  color: var(--color-secondary);
  margin-bottom: 4px;
}

.drop-text {
  font-size: 14px;
  color: var(--color-secondary);
  font-weight: 500;
}

.drop-hint {
  font-size: 12.5px;
  color: var(--color-secondary);
}

/* ── File info ── */
.file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 10px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
}

.file-name {
  flex: 1;
  font-size: 13px;
  color: var(--color-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-secondary);
  display: flex;
  align-items: center;
  padding: 0;
}

.file-remove:hover {
  color: #ef4444;
}

.extract-btn {
  margin-top: 14px;
  width: 100%;
  height: 40px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.extract-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.extracting-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  font-size: 13px;
  color: var(--color-secondary);
}

/* ── Result zone ── */
.result-zone {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  min-height: 200px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-placeholder {
  color: var(--color-secondary);
  font-size: 13.5px;
  margin: auto;
  text-align: center;
}

.result-error {
  color: #ef4444;
  font-size: 13px;
  font-weight: 500;
  padding: 10px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 7px;
}

.result-field-label {
  font-size: 12px;
  color: var(--color-secondary);
  margin-bottom: 6px;
}

.result-field-value {
  font-size: 14px;
  color: var(--color-ink);
  font-weight: 500;
}

/* ── Tags ── */
.result-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.result-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: #e0e7ff;
  color: #3730a3;
}

.result-tag--gray {
  background: #f3f4f6;
  color: #374151;
}

.result-tag--indigo {
  background: #ede9fe;
  color: #5b21b6;
}

.save-btn {
  margin-top: 4px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}
</style>
```

Note: `.result-tag`, `.result-tag--gray`, `.result-tag--indigo` are decorative categorical tag colors (indigo/gray/purple) — left untouched per Global Constraints (decorative, not brand/CTA/text-grey).

- [ ] **Step 3: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#374151\|#2347c5\|#1b3ca0\|#f0f4ff\|#b91c1c" frontend/src/views/hub/ExtractFrameworkView.vue`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/ExtractFrameworkView.vue
git commit -m "feat: apply color tokens to ExtractFrameworkView, unify error hex"
```

---

### Task 6: `SettingsView.vue`

**Files:**
- Modify: `frontend/src/views/hub/SettingsView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

/* ── Settings card ── */
.settings-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
  margin-bottom: 16px;
  color: #111827;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 20px;
}

/* ── Setting row ── */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0;
}

.setting-divider {
  height: 1px;
  background: #f0f1f3;
  margin: 16px 0;
}

.setting-info {
  flex: 1;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: #2347c5;
  margin-bottom: 3px;
}

.setting-desc {
  font-size: 12.5px;
  color: #9ca3af;
}

/* ── Timeout select ── */
.timeout-select {
  height: 36px;
  padding: 0 30px 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: #111827;
  outline: none;
  cursor: pointer;
  appearance: auto;
  min-width: 110px;
  color-scheme: light;
}

.timeout-select:focus {
  border-color: #2347c5;
}

/* ── Toggle ── */
.toggle-btn {
  width: 44px;
  height: 24px;
  border-radius: 99px;
  border: none;
  cursor: pointer;
  background: #e5e7eb;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-btn--on {
  background: #2347c5;
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.toggle-btn--on .toggle-thumb {
  left: 22px;
}

/* ── API fields ── */
.api-field {
  margin-bottom: 16px;
}

.api-field:last-child {
  margin-bottom: 0;
}

.api-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 7px;
}

.api-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 13.5px;
  color: #111827;
  background-color: #f9fafb;
  outline: none;
  box-sizing: border-box;
  font-family: 'Roboto Mono', monospace;
  transition: border-color 0.15s;
  color-scheme: light;
}

.api-input:focus {
  border-color: #2347c5;
  background-color: #ffffff;
}

/* ── Save ── */
.save-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.save-btn {
  height: 40px;
  padding: 0 24px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: #1b3ca0;
}

.save-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: #16a34a;
  font-weight: 500;
}
</style>
```

With:

```css
<style scoped>
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

/* ── Settings card ── */
.settings-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
  margin-bottom: 16px;
  color: var(--color-ink);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 20px;
}

/* ── Setting row ── */
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0;
}

.setting-divider {
  height: 1px;
  background: #f0f1f3;
  margin: 16px 0;
}

.setting-info {
  flex: 1;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-accent);
  margin-bottom: 3px;
}

.setting-desc {
  font-size: 12.5px;
  color: var(--color-secondary);
}

/* ── Timeout select ── */
.timeout-select {
  height: 36px;
  padding: 0 30px 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  background-color: #ffffff;
  font-size: 13.5px;
  color: var(--color-ink);
  outline: none;
  cursor: pointer;
  appearance: auto;
  min-width: 110px;
  color-scheme: light;
}

.timeout-select:focus {
  border-color: var(--color-accent);
}

/* ── Toggle ── */
.toggle-btn {
  width: 44px;
  height: 24px;
  border-radius: 99px;
  border: none;
  cursor: pointer;
  background: #e5e7eb;
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle-btn--on {
  background: var(--color-accent);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  transition: left 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.toggle-btn--on .toggle-thumb {
  left: 22px;
}

/* ── API fields ── */
.api-field {
  margin-bottom: 16px;
}

.api-field:last-child {
  margin-bottom: 0;
}

.api-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-secondary);
  margin-bottom: 7px;
}

.api-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  border-radius: 7px;
  font-size: 13.5px;
  color: var(--color-ink);
  background-color: #f9fafb;
  outline: none;
  box-sizing: border-box;
  font-family: 'Roboto Mono', monospace;
  transition: border-color 0.15s;
  color-scheme: light;
}

.api-input:focus {
  border-color: var(--color-accent);
  background-color: #ffffff;
}

/* ── Save ── */
.save-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.save-btn {
  height: 40px;
  padding: 0 24px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.save-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.save-msg {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: #16a34a;
  font-weight: 500;
}
</style>
```

Note: `.save-msg`'s `color: #16a34a` is already the canonical success hex (unchanged) — this file needs no status-color unification.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af\|#374151\|#2347c5\|#1b3ca0" frontend/src/views/hub/SettingsView.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/SettingsView.vue
git commit -m "feat: apply color tokens to SettingsView"
```

---

### Task 7: `ProjectDetailView.vue`

**Files:**
- Modify: `frontend/src/views/hub/ProjectDetailView.vue` (template's `v-progress-circular` color prop, and the entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: The `v-progress-circular color="#d97706"` on the "running" state (line 48) is a warning/status color, not the CTA blue — leave it unchanged.** No edit needed for this element; confirming it here so it is not mistakenly touched in Step 2.

- [ ] **Step 2: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 24px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.badge {
  font-size: 12.5px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #1d4ed8;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: #6b7280;
}

.page-header {
  margin-bottom: 22px;
}

.framework-link {
  font-size: 13px;
  color: #2347c5;
}

/* ── Panels ── */
.detail-panels {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}

.results-card,
.info-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 20px;
}

/* ── Results ── */
.result-row {
  padding: 14px 0;
}

.result-divider {
  height: 1px;
  background: #f0f1f3;
}

.result-label {
  font-size: 12.5px;
  color: #9ca3af;
  margin-bottom: 6px;
}

.result-value {
  font-size: 14px;
  color: #111827;
}

.result-value.large {
  font-size: 30px;
  font-weight: 700;
}

.view-result-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-top: 14px;
  font-size: 13.5px;
  font-weight: 500;
  color: #2347c5;
  text-decoration: none;
}

.view-result-btn:hover {
  color: #1b3ca0;
}

/* ── Running state ── */
.running-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 0;
}

.running-text {
  font-size: 14px;
  color: #6b7280;
}

/* ── Draft state ── */
.draft-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  font-size: 14px;
  color: #9ca3af;
}

/* ── Open workflow button ── */
.open-workflow-wrap {
  padding-top: 20px;
  margin-top: 4px;
  border-top: 1px solid #f0f1f3;
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: #1b3ca0;
}

/* ── Project info ── */
.info-row {
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 4px;
}

.info-value {
  font-size: 13.5px;
  color: #111827;
  font-weight: 500;
}

/* ── Not found ── */
.not-found {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}
</style>
```

With:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-secondary);
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: var(--color-ink);
}

.page-header {
  margin-bottom: 24px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0;
}

.badge {
  font-size: 12.5px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 99px;
}

.badge--completed {
  background: #dbeafe;
  color: #2347c5;
}

.badge--running {
  background: #fef3c7;
  color: #d97706;
}

.badge--draft {
  background: #f3f4f6;
  color: var(--color-secondary);
}

.page-header {
  margin-bottom: 22px;
}

.framework-link {
  font-size: 13px;
  color: var(--color-accent);
}

/* ── Panels ── */
.detail-panels {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 20px;
  align-items: start;
}

.results-card,
.info-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 22px 24px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
  margin-bottom: 20px;
}

/* ── Results ── */
.result-row {
  padding: 14px 0;
}

.result-divider {
  height: 1px;
  background: #f0f1f3;
}

.result-label {
  font-size: 12.5px;
  color: var(--color-secondary);
  margin-bottom: 6px;
}

.result-value {
  font-size: 14px;
  color: var(--color-ink);
}

.result-value.large {
  font-size: 30px;
  font-weight: 700;
}

.view-result-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding-top: 14px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--color-accent);
  text-decoration: none;
}

.view-result-btn:hover {
  color: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Running state ── */
.running-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 0;
}

.running-text {
  font-size: 14px;
  color: var(--color-secondary);
}

/* ── Draft state ── */
.draft-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  font-size: 14px;
  color: var(--color-secondary);
}

/* ── Open workflow button ── */
.open-workflow-wrap {
  padding-top: 20px;
  margin-top: 4px;
  border-top: 1px solid #f0f1f3;
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

/* ── Project info ── */
.info-row {
  padding: 12px 0;
  border-bottom: 1px solid #f0f1f3;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 12px;
  color: var(--color-secondary);
  margin-bottom: 4px;
}

.info-value {
  font-size: 13.5px;
  color: var(--color-ink);
  font-weight: 500;
}

/* ── Not found ── */
.not-found {
  text-align: center;
  padding: 48px;
  color: var(--color-secondary);
  font-size: 14px;
}
</style>
```

Note: `.badge--completed`'s color changed from `#1d4ed8` to the literal hex `#1d4ed8` → `#2347c5` (unifying with `ProjectsView.vue`'s `.badge--completed`, per Global Constraints — stays hardcoded hex, not a token).

- [ ] **Step 3: Verify no leftover old color values (including the `#1d4ed8` unification)**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#1b3ca0\|#1d4ed8" frontend/src/views/hub/ProjectDetailView.vue`
Expected: no output.

Run: `grep -n "#2347c5" frontend/src/views/hub/ProjectDetailView.vue`
Expected: exactly 1 match, inside `.badge--completed`.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/hub/ProjectDetailView.vue
git commit -m "feat: apply color tokens to ProjectDetailView, unify badge--completed hex"
```

---

### Task 8: `ResultView.vue`

**Files:**
- Modify: `frontend/src/views/hub/ResultView.vue` (entire `<style scoped>` block)

**Interfaces:**
- Consumes: `--color-ink`, `--color-secondary`, `--color-accent`, `--color-chat-user`, `--color-chat-system`, `--color-inverted` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Replace the entire `<style scoped>` block**

Replace:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: #6b7280;
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: #111827;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: #9ca3af;
  margin: 0;
}

.not-found {
  text-align: center;
  padding: 48px;
  color: #9ca3af;
  font-size: 14px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: #9ca3af;
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  height: 38px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: #1b3ca0;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  padding: 14px;
}

.metric-card--accent .metric-value {
  color: #18a836;
}

.metric-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #20232a;
}

.metric-value {
  margin: 8px 0 2px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  color: #111827;
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: #6f7480;
}

.comparison-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
}

.comparison-head {
  padding: 14px 18px;
  border-bottom: 1px solid #f0f1f3;
}

.comparison-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.table-wrap {
  overflow: auto;
}

.result-table {
  width: 100%;
  min-width: 480px;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 11px 18px;
  text-align: left;
  border-bottom: 1px solid #f0f1f3;
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
  color: #18a836;
  font-weight: 700;
}

.analysis-card,
.chat-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  padding: 18px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.analysis-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #eef1ff;
  color: #2347c5;
}

.analysis-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.analysis-loading {
  margin: 0;
  font-size: 13px;
  color: #6f7480;
}

.analysis-error {
  margin: 0 0 8px;
  font-size: 13px;
  color: #d64545;
}

.analysis-retry-btn {
  border: none;
  background: none;
  color: #2347c5;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-block h3 {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #20232a;
}

.analysis-block p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5160;
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.chat-empty {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
}

.chat-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.6;
}

.chat-bubble--user {
  align-self: flex-end;
  background: #2347c5;
  color: #ffffff;
}

.chat-bubble--model {
  align-self: flex-start;
  background: #f4f5f8;
  color: #1f2532;
}

.chat-bubble--failed {
  opacity: 0.65;
  outline: 1px solid #d64545;
}

.chat-bubble-failed-hint {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: #ffd7d7;
}

.chat-bubble-text {
  margin: 0;
  white-space: pre-wrap;
}

.chat-papers {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.chat-paper-card {
  display: block;
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  text-decoration: none;
  border: 1px solid #e2e4ea;
}

.chat-paper-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: #2347c5;
}

.chat-paper-meta {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: #6f7480;
}

.chat-loading,
.chat-error {
  margin: 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.chat-error {
  color: #d64545;
}

.chat-input-row {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #e2e4ea;
  border-radius: 8px;
  font-size: 13px;
}

.chat-input:disabled {
  background: #f7f7f9;
}

.chat-send-btn {
  height: 38px;
  padding: 0 18px;
  background: #2347c5;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.chat-send-btn:disabled {
  background: #b7c2e6;
  cursor: not-allowed;
}

@media (max-width: 1260px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

With:

```css
<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  color: var(--color-secondary);
  text-decoration: none;
  margin-bottom: 20px;
  transition: color 0.12s;
}

.back-link:hover {
  color: var(--color-ink);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 30px;
  font-weight: 700;
  color: var(--color-ink);
  margin: 0 0 5px;
}

.page-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0;
}

.not-found {
  text-align: center;
  padding: 48px;
  color: var(--color-secondary);
  font-size: 14px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 64px 24px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: var(--color-secondary);
}

.open-workflow-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
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
  transition: background 0.15s;
}

.open-workflow-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  padding: 14px;
}

.metric-card--accent .metric-value {
  color: #16a34a;
}

.metric-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-ink);
}

.metric-value {
  margin: 8px 0 2px;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--color-ink);
}

.metric-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-secondary);
}

.comparison-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  overflow: hidden;
}

.comparison-head {
  padding: 14px 18px;
  border-bottom: 1px solid #f0f1f3;
}

.comparison-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}

.table-wrap {
  overflow: auto;
}

.result-table {
  width: 100%;
  min-width: 480px;
  border-collapse: collapse;
}

.result-table th,
.result-table td {
  padding: 11px 18px;
  text-align: left;
  border-bottom: 1px solid #f0f1f3;
  font-size: 12px;
  white-space: nowrap;
}

.result-table th {
  font-weight: 700;
  color: var(--color-ink);
  background: #fafbff;
}

.result-table tbody tr:last-child td {
  border-bottom: none;
}

.model-name {
  font-weight: 700;
  color: var(--color-ink);
}

.score-best {
  color: #16a34a;
  font-weight: 700;
}

.analysis-card,
.chat-card {
  margin-top: 16px;
  border: 1px solid #e8e8e8;
  border-radius: 14px;
  background: #ffffff;
  padding: 18px;
}

.analysis-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.analysis-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #eef1ff;
  color: var(--color-accent);
}

.analysis-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}

.analysis-loading {
  margin: 0;
  font-size: 13px;
  color: var(--color-secondary);
}

.analysis-error {
  margin: 0 0 8px;
  font-size: 13px;
  color: #ef4444;
}

.analysis-retry-btn {
  border: none;
  background: none;
  color: var(--color-accent);
  font-size: 13px;
  cursor: pointer;
  padding: 0;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-block h3 {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-ink);
}

.analysis-block p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-secondary);
}

.chat-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.chat-empty {
  margin: 0;
  font-size: 13px;
  color: var(--color-secondary);
}

.chat-bubble {
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13.5px;
  line-height: 1.6;
}

.chat-bubble--user {
  align-self: flex-end;
  background: var(--color-chat-user);
  color: var(--color-inverted);
}

.chat-bubble--model {
  align-self: flex-start;
  background: var(--color-chat-system);
  color: var(--color-ink);
}

.chat-bubble--failed {
  opacity: 0.65;
  outline: 1px solid #ef4444;
}

.chat-bubble-failed-hint {
  margin: 4px 0 0;
  font-size: 11.5px;
  color: #ffd7d7;
}

.chat-bubble-text {
  margin: 0;
  white-space: pre-wrap;
}

.chat-papers {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.chat-paper-card {
  display: block;
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  text-decoration: none;
  border: 1px solid #e2e4ea;
}

.chat-paper-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--color-accent);
}

.chat-paper-meta {
  margin: 3px 0 0;
  font-size: 11.5px;
  color: var(--color-secondary);
}

.chat-loading,
.chat-error {
  margin: 0;
  font-size: 12.5px;
  color: var(--color-secondary);
}

.chat-error {
  color: #ef4444;
}

.chat-input-row {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  height: 38px;
  padding: 0 12px;
  border: 1px solid #e2e4ea;
  border-radius: 8px;
  font-size: 13px;
}

.chat-input:disabled {
  background: #f7f7f9;
}

.chat-send-btn {
  height: 38px;
  padding: 0 18px;
  background: var(--color-accent);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.chat-send-btn:disabled {
  background: #b7c2e6;
  cursor: not-allowed;
}

@media (max-width: 1260px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style>
```

Note: `.chat-bubble-failed-hint`'s `color: #ffd7d7` is a light-red hint text specifically designed to be legible against the failed-message bubble's own background (still `chat-user`'s dark navy, since a failed message is still a user message) — left unchanged; it isn't one of the two duplicate error hex values named in Global Constraints (`#b91c1c`/`#d64545`→`#ef4444`), it's a distinct tint chosen for readability on a dark bubble.

- [ ] **Step 2: Verify no leftover old color values**

Run: `grep -n "#111827\|#9ca3af\|#6b7280\|#2347c5\|#1b3ca0\|#18a836\|#d64545\|#20232a\|#2a2f39\|#1f2532\|#4b5160\|#6f7480" frontend/src/views/hub/ResultView.vue`
Expected: no output.

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/hub/ResultView.vue
git commit -m "feat: apply color tokens to ResultView, wire chat bubbles to chat-user/chat-system tokens"
```

---

### Task 9: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: the changes from Tasks 1-8
- Produces: nothing

- [ ] **Step 1: Run a clean full build**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 2: Confirm no leftover old-palette references across all 8 files**

Run: `grep -rn "#111827\|#9ca3af\|#6b7280\|#374151\|#1b3ca0\|#18a836\|#b91c1c\|#d64545\|#20232a\|#2a2f39\|#1f2532\|#4b5160\|#6f7480\|#1d4ed8" frontend/src/views/hub/DashboardView.vue frontend/src/views/hub/ProjectsView.vue frontend/src/views/hub/FrameworkLibraryView.vue frontend/src/views/hub/CreateProjectView.vue frontend/src/views/hub/ExtractFrameworkView.vue frontend/src/views/hub/SettingsView.vue frontend/src/views/hub/ProjectDetailView.vue frontend/src/views/hub/ResultView.vue`
Expected: no output.

Run: `grep -rn "#2347c5" frontend/src/views/hub/DashboardView.vue frontend/src/views/hub/ProjectsView.vue frontend/src/views/hub/FrameworkLibraryView.vue frontend/src/views/hub/CreateProjectView.vue frontend/src/views/hub/ExtractFrameworkView.vue frontend/src/views/hub/SettingsView.vue frontend/src/views/hub/ProjectDetailView.vue frontend/src/views/hub/ResultView.vue`
Expected: exactly 2 matches, both inside `.badge--completed` rules (`ProjectsView.vue` and `ProjectDetailView.vue`) — the intentional exception.

- [ ] **Step 3: Live browser check — CTA accent color**

Run (from `frontend/`): `npm run dev`. Open `/hub/projects`.

In the browser devtools console:
```js
getComputedStyle(document.querySelector('.new-btn')).backgroundColor
// expect: "rgb(232, 163, 61)" (accent)
```

- [ ] **Step 4: Live browser check — text colors**

While still on `/hub/dashboard`:
```js
getComputedStyle(document.querySelector('.page-title')).color
// expect: "rgb(28, 33, 48)" (ink)
getComputedStyle(document.querySelector('.page-sub')).color
// expect: "rgb(51, 65, 85)" (secondary)
```

- [ ] **Step 5: Live browser check — chat bubbles**

Open `/hub/projects/:id/result` for a project that has workflow results (if none exists in this environment, skip this step and note it in your report — the source-level verification in Tasks 8's Step 2 grep already confirms the token wiring is correct). Type a message and send it. Expected: the user's message bubble renders with a dark navy background and light text; the model's reply bubble renders with a light peach background and dark text.

```js
getComputedStyle(document.querySelector('.chat-bubble--user')).backgroundColor
// expect: "rgb(18, 33, 59)" (chat-user)
getComputedStyle(document.querySelector('.chat-bubble--model')).backgroundColor
// expect: "rgb(251, 234, 208)" (chat-system)
```

- [ ] **Step 6: Live browser check — badge--completed exception held**

Navigate to `/hub/projects` and `/hub/projects/:id` for a project with `status: 'completed'`. Expected: the "已完成" badge is still blue (not amber), and the color is identical between the two pages.

```js
getComputedStyle(document.querySelector('.badge--completed')).color
// expect: "rgb(35, 71, 197)" (#2347c5) on both pages
```

Stop the dev server after checking.
