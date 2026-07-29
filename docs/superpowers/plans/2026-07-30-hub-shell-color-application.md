# Hub Shell Color Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hub area's persistent shell (`HubLayout.vue`'s wrapper and `HubSidebar.vue`'s navigation) actually render the new color palette, by replacing their hardcoded hex colors with references to the `--color-*` CSS variables already defined in `frontend/src/styles/tailwind.css`.

**Architecture:** No structural changes — keep the existing `<style scoped>` blocks in both files, and swap each hardcoded hex literal for the matching `var(--color-token)`. These CSS custom properties are plain CSS (defined in `tailwind.css`'s `@theme` block from the prior color-refresh work) and are usable anywhere via `var()`, not only inside Tailwind utility classes.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-secondary` (`#334155`), `--color-accent` (`#e8a33d`), `--color-surface` (`#ffffff`), `--color-ink` (`#1c2130`)
- No unit test framework is configured in `frontend/` — verification is `npm run build` (`vue-tsc --build --force` then `vite build`), `npm run lint`, `grep`, and live browser `getComputedStyle` checks, run from the `frontend/` directory
- Out of scope — do not touch: `HelloWorld.vue`, `PaperPage.vue`, `WorkflowBuilder.vue`/`WorkflowCanvas.vue`/node panels, any `hub/*View.vue` content area, dark mode, layout/spacing/collapse-toggle interaction logic
- Within `HubLayout.vue`/`HubSidebar.vue`, do not touch the neutral/muted colors that aren't being remapped: `.hub-brand-sub` (`#9ca3af`), `.hub-toggle-btn` border (`#e5e7eb`), `.hub-sidebar` border-right (`#e8e8e8`), `.hub-sidebar-footer` (`#9ca3af` / `#f0f0f0`) — these are neutral UI chrome, not brand color, and are intentionally excluded per the spec
- `.hub-nav-item--active`'s text color must become `var(--color-ink)`, NOT stay `#ffffff` and NOT become `var(--color-inverted)` — white-on-accent contrast is ~2.25:1 (fails WCAG AA); ink-on-accent is ~7.1:1 (AAA). This is a deliberate accessibility correction, not a preservation of the original white.
- Do not add a test framework or write new automated tests as part of this plan

---

### Task 1: Hub shell color tokens

**Files:**
- Modify: `frontend/src/layouts/HubLayout.vue:16-24`
- Modify: `frontend/src/components/hub/HubSidebar.vue:49-146`

**Interfaces:**
- Consumes: `--color-primary`, `--color-secondary`, `--color-accent`, `--color-surface`, `--color-ink` CSS variables (already defined in `frontend/src/styles/tailwind.css`, from the prior color-refresh plan — no changes to that file in this plan)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `frontend/src/layouts/HubLayout.vue`**

Replace:

```css
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: #111827;
}
```

With:

```css
.hub-wrap {
  display: flex;
  min-height: 100vh;
  background: var(--color-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color-scheme: light;
  color: var(--color-ink);
}
```

- [ ] **Step 2: Edit `frontend/src/components/hub/HubSidebar.vue` — sidebar background**

Replace:

```css
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: #ffffff;
  border-right: 1px solid #e8e8e8;
```

With:

```css
.hub-sidebar {
  width: 210px;
  min-width: 210px;
  background: var(--color-surface);
  border-right: 1px solid #e8e8e8;
```

- [ ] **Step 3: Edit `frontend/src/components/hub/HubSidebar.vue` — brand title**

Replace:

```css
.hub-brand-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #111827;
  white-space: nowrap;
  line-height: 1.3;
}
```

With:

```css
.hub-brand-title {
  font-size: 14.5px;
  font-weight: 700;
  color: var(--color-ink);
  white-space: nowrap;
  line-height: 1.3;
}
```

- [ ] **Step 4: Edit `frontend/src/components/hub/HubSidebar.vue` — toggle button hover**

Replace:

```css
.hub-toggle-btn:hover {
  background: #f5f5f5;
}
```

With:

```css
.hub-toggle-btn:hover {
  background: var(--color-primary);
}
```

- [ ] **Step 5: Edit `frontend/src/components/hub/HubSidebar.vue` — nav item text color**

Replace:

```css
.hub-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 7px;
  text-decoration: none;
  color: #4b5563;
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s;
  white-space: nowrap;
}
```

With:

```css
.hub-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 7px;
  text-decoration: none;
  color: var(--color-secondary);
  font-size: 13.5px;
  font-weight: 500;
  transition: background 0.12s;
  white-space: nowrap;
}
```

- [ ] **Step 6: Edit `frontend/src/components/hub/HubSidebar.vue` — nav item hover and active state**

Replace:

```css
.hub-nav-item:hover {
  background: #f5f5f5;
}

.hub-nav-item--active {
  background: #2347c5;
  color: #ffffff;
}
```

With:

```css
.hub-nav-item:hover {
  background: var(--color-primary);
}

.hub-nav-item--active {
  background: var(--color-accent);
  color: var(--color-ink);
}
```

- [ ] **Step 7: Verify no leftover old values for the changed properties**

Run: `grep -n "#f5f5f5\|#111827\|#2347c5" frontend/src/layouts/HubLayout.vue frontend/src/components/hub/HubSidebar.vue`
Expected: no output. (This does not check `#4b5563` or `#ffffff` — those literal strings could coincidentally appear in an unrelated untouched rule; the exact-block replacements in Steps 1-6 are the source of truth for what changed.)

- [ ] **Step 8: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/layouts/HubLayout.vue frontend/src/components/hub/HubSidebar.vue
git commit -m "feat: apply new color tokens to Hub layout shell and sidebar"
```

---

### Task 2: Full verification pass

**Files:** none (verification only)

**Interfaces:**
- Consumes: the color changes from Task 1
- Produces: nothing

- [ ] **Step 1: Run a clean full build**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors.

- [ ] **Step 2: Run lint**

Run (from `frontend/`): `npm run lint`
Expected: no new errors on `frontend/src/layouts/HubLayout.vue` or `frontend/src/components/hub/HubSidebar.vue` (pre-existing errors on unrelated files are expected and acceptable — this repo has pre-existing lint debt unrelated to this change).

- [ ] **Step 3: Manual visual and computed-style check**

Run (from `frontend/`): `npm run dev`
Open any `/hub/*` route (e.g. `/hub/dashboard`) and check:
- `.hub-wrap` background reads as cream, not the old flat grey
- `.hub-sidebar` remains a white surface, visually distinct from the cream page area
- Sidebar nav item label text (`.hub-nav-item`) is a dark slate tone (secondary), not the old neutral grey
- Click a different nav item so a new one becomes active: the active item's background is amber (`accent`), its label text is dark (not white)

In the browser devtools console, run:
```js
getComputedStyle(document.querySelector('.hub-wrap')).backgroundColor
// expect: "rgb(246, 245, 242)"
getComputedStyle(document.querySelector('.hub-sidebar')).backgroundColor
// expect: "rgb(255, 255, 255)"
getComputedStyle(document.querySelector('.hub-nav-item--active')).backgroundColor
// expect: "rgb(232, 163, 61)"
getComputedStyle(document.querySelector('.hub-nav-item--active')).color
// expect: "rgb(28, 33, 48)"
```
Stop the dev server after checking.

- [ ] **Step 4: Confirm no leftover old shell colors**

Run: `grep -n "#f5f5f5\|#2347c5" frontend/src/layouts/HubLayout.vue frontend/src/components/hub/HubSidebar.vue`
Expected: no output.
