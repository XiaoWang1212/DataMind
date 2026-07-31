# Hub Sidebar Glassmorphism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give `HubSidebar.vue` a translucent glassmorphism look (blurred background, edge highlight, periodic shine-sweep animation) with a decorative amber glow-orb layer behind it in `HubLayout.vue`, without changing any existing collapse/expand state logic or component communication.

**Architecture:** `HubLayout.vue` gains a new decorative, non-interactive sibling element (the orb layer) plus one CSS sibling-selector rule to shrink that layer when the sidebar is collapsed. `HubSidebar.vue`'s own `<style scoped>` block changes its background treatment and adds a `::before` pseudo-element for the shine animation. No template changes in `HubSidebar.vue`, no props/emit/v-model added anywhere.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-accent` (`#e8a33d`)
- Do not add any new props, emits, or v-model bindings between `HubLayout.vue` and `HubSidebar.vue`
- Do not change `HubSidebar.vue`'s `collapsed` ref or its toggle button logic
- The orb layer must have `pointer-events: none` and `aria-hidden="true"` — it is purely decorative and must never intercept clicks or be announced to screen readers
- No unit test framework is configured in `frontend/` — verification is `npm run build` and a live browser check, run from the `frontend/` directory

---

### Task 1: `HubLayout.vue` — decorative glow-orb layer

**Files:**
- Modify: `frontend/src/layouts/HubLayout.vue` (template: add the orb layer; style: add its CSS plus the collapse-sync sibling-selector rule)

**Interfaces:**
- Consumes: `--color-accent` (already defined); `HubSidebar.vue`'s existing `hub-sidebar--collapsed` class (already applied to its root `<aside>` today — this task does not add or change that class, only reads it via a CSS sibling selector)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Add the orb layer to the template**

Replace:

```html
<template>
  <div class="hub-wrap">
    <HubSidebar />

    <main class="hub-main">
      <RouterView />
    </main>
  </div>
</template>
```

With:

```html
<template>
  <div class="hub-wrap">
    <HubSidebar />

    <div aria-hidden="true" class="hub-glass-orbs">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
    </div>

    <main class="hub-main">
      <RouterView />
    </main>
  </div>
</template>
```

(The orb layer must stay directly after `<HubSidebar />` and before `<main>` — this DOM order is required for the Step 2 sibling selector to match.)

- [ ] **Step 2: Add the orb layer's CSS and the collapse-sync rule**

Replace:

```css
<style scoped>
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: var(--color-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: var(--color-ink);
}

.hub-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 32px 36px;
}
</style>
```

With:

```css
<style scoped>
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: var(--color-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: var(--color-ink);
}

.hub-glass-orbs {
  position: fixed;
  top: 0;
  left: 0;
  width: 210px;
  height: 100vh;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
  transition: width 0.2s ease;
}

.hub-sidebar--collapsed ~ .hub-glass-orbs {
  width: 56px;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(38px);
}

.orb-1 {
  width: 160px;
  height: 160px;
  top: -40px;
  left: -30px;
  background: radial-gradient(circle, var(--color-accent) 0%, transparent 70%);
  opacity: 0.55;
}

.orb-2 {
  width: 130px;
  height: 130px;
  top: 260px;
  left: 40px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 60%, white) 0%, transparent 70%);
  opacity: 0.5;
}

.orb-3 {
  width: 110px;
  height: 110px;
  top: 480px;
  left: -20px;
  background: radial-gradient(circle, color-mix(in oklab, var(--color-accent) 85%, black) 0%, transparent 70%);
  opacity: 0.35;
}

.hub-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 32px 36px;
}
</style>
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/layouts/HubLayout.vue
git commit -m "feat: add decorative glow-orb layer behind Hub sidebar"
```

---

### Task 2: `HubSidebar.vue` — glass background, edge highlight, shine animation

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue` (`<style scoped>` block only — no template changes)

**Interfaces:**
- Consumes: nothing new
- Produces: the `.hub-sidebar--collapsed` class this task's z-index changes rely on already exists today (from the pre-existing `:class="['hub-sidebar', { 'hub-sidebar--collapsed': collapsed }]"` binding in the template) — Task 1's Step 2 sibling selector depends on this class continuing to exist unchanged, which this task does not touch

- [ ] **Step 1: Replace `.hub-sidebar`'s background/border with the glass treatment**

Replace:

```css
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: var(--color-surface);
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
}
```

With:

```css
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-top: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.25),
    inset -12px -12px 24px -20px rgba(0, 0, 0, 0.15),
    4px 0 24px rgba(28, 33, 48, 0.1);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  overflow: hidden;
  position: sticky;
  top: 0;
  height: 100vh;
  z-index: 2;
}

.hub-sidebar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 70%;
  height: 220%;
  background: linear-gradient(115deg, transparent 35%, rgba(255, 255, 255, 0.7) 50%, transparent 65%);
  transform: translate(-160%, -20%) rotate(12deg);
  animation: hub-sidebar-shine 4.5s ease-in-out infinite;
  pointer-events: none;
  z-index: 1;
}

@keyframes hub-sidebar-shine {
  0%, 25% {
    transform: translate(-160%, -20%) rotate(12deg);
  }
  65%, 100% {
    transform: translate(160%, -20%) rotate(12deg);
  }
}
```

- [ ] **Step 2: Raise the three child sections above the shine layer**

Replace:

```css
.hub-sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 14px 14px;
  gap: 8px;
}
```

With:

```css
.hub-sidebar-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 14px 14px;
  gap: 8px;
  position: relative;
  z-index: 2;
}
```

Replace:

```css
.hub-nav {
  flex: 1;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
```

With:

```css
.hub-nav {
  flex: 1;
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  position: relative;
  z-index: 2;
}
```

Replace:

```css
.hub-sidebar-footer {
  padding: 12px 14px;
  font-size: 10.5px;
  color: #9ca3af;
  line-height: 1.7;
  border-top: 1px solid #f0f0f0;
}
```

With:

```css
.hub-sidebar-footer {
  padding: 12px 14px;
  font-size: 10.5px;
  color: #9ca3af;
  line-height: 1.7;
  border-top: 1px solid #f0f0f0;
  position: relative;
  z-index: 2;
}
```

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "feat: apply glassmorphism styling to HubSidebar"
```

---

### Task 3: Full verification pass

**Files:**
- No file modifications — this task only verifies the state of Tasks 1–2.

**Interfaces:**
- Consumes: the completed state of Tasks 1–2
- Produces: nothing (terminal task)

- [ ] **Step 1: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 2: Live browser check — glass rendering and shine animation**

Run (from `frontend/`): `npm run dev`. Open any Hub page (e.g. `/hub/dashboard`).

Expected: the sidebar shows a translucent blurred glass background with a visible amber glow bleeding through from behind it; a bright highlight along the top edge; and a diagonal light band that sweeps across the sidebar roughly every 4.5 seconds, looping continuously.

- [ ] **Step 3: Live browser check — collapse/expand behavior**

Click the collapse toggle button.

Expected: the sidebar animates from 210px to 56px exactly as it did before this change (collapse/expand logic itself is untouched). Confirm via `getComputedStyle` in the browser console that `.hub-glass-orbs`'s `width` also transitions from `210px` to `56px` when collapsed — this confirms the Task 1 Step 2 sibling-selector rule (`.hub-sidebar--collapsed ~ .hub-glass-orbs`) is actually matching. If it does NOT match (orb layer width stays 210px regardless of collapsed state), STOP and report this — it means the Vue scoped-CSS assumption documented in the design spec didn't hold in practice, and the fallback (passing `collapsed` state from `HubSidebar.vue` up to `HubLayout.vue` via a prop/emit) needs to be discussed before proceeding.

Expand the sidebar back and confirm no unblurred amber color patches are visible outside the sidebar's glass panel in either state.

- [ ] **Step 4: Live browser check — nav item interactivity**

With the sidebar expanded, click through all four nav items (儀表板/框架庫/專案/設定), including once while the shine animation is visibly sweeping over them.

Expected: every nav item navigates correctly regardless of animation timing; text stays legible throughout the shine sweep.

- [ ] **Step 5: Stop the dev server after checking**

Stop the `npm run dev` process started in Step 2.

- [ ] **Step 6: Commit (only if Step 3's fallback was needed)**

If Step 3 required the props/emit fallback, stage and commit that fix:

```bash
git add frontend/src/layouts/HubLayout.vue frontend/src/components/hub/HubSidebar.vue
git commit -m "fix: sync collapsed state via prop instead of CSS sibling selector"
```

If the CSS sibling selector worked as designed, skip this step — Tasks 1–2 already committed everything.

---

## Plan Self-Review

**Spec coverage:** Spec's 段落 A maps to Task 1 Step 1-2; 段落 B maps to Task 2; 段落 C maps to Task 1's `.hub-sidebar--collapsed ~ .hub-glass-orbs` rule, with its own live-verification step (and documented fallback) in Task 3 Step 3.

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" — every step shows the complete before/after code.

**Type consistency:** N/A — pure template/CSS changes, no functions/types/props introduced (Task 3's conditional fallback step is explicitly a contingency, not a guaranteed step, and is fully specified as "discuss before proceeding" rather than silently implemented).
