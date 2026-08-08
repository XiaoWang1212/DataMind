# Typography Unification and Paper Page Background Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align `PaperPage.vue`, `PaperSourcesView.vue`, and `ResultsPage.vue`'s font-family to the system font stack already used by `HubLayout.vue` (which covers most of the app), and adjust `PaperPage.vue`'s two background layers (the dot-grid texture's base color and the outer decorative glow) to beige per the approved design.

**Architecture:** Pure CSS value edits inside each file's existing `<style scoped>` block — no template or script changes anywhere.

**Tech Stack:** Vue 3, Vuetify 4, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-secondary` (`#334155`)
- The target font stack (copied verbatim from `HubLayout.vue`'s `.hub-wrap` rule): `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Do not modify `HubLayout.vue` itself — it is the reference, not a target
- Do not modify `.paper-sheet` (the white "paper" card in `PaperPage.vue`) — it keeps its white background regardless of the surrounding changes
- Do not touch `PaperSourcesView.vue`'s or `ResultsPage.vue`'s background (glow/gradient) — only their `font-family` changes in this plan; their backgrounds are explicitly out of scope
- No unit test framework is configured in `frontend/` — verification is `npm run build` and a live browser check, run from the `frontend/` directory

---

### Task 1: Font-family alignment across the three standalone pages

**Files:**
- Modify: `frontend/src/views/PaperPage.vue` (`.paper-page` rule)
- Modify: `frontend/src/views/PaperSourcesView.vue` (`.sources-page` rule)
- Modify: `frontend/src/views/ResultsPage.vue` (`.results-page` rule)

**Interfaces:**
- Consumes: nothing new
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `PaperPage.vue`'s font-family**

Replace:

```css
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
```

With:

```css
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

(This line appears once, inside the `.paper-page` rule.)

- [ ] **Step 2: Edit `PaperSourcesView.vue`'s font-family**

Replace:

```css
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
```

With:

```css
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

(This line appears once, inside the `.sources-page` rule.)

- [ ] **Step 3: Edit `ResultsPage.vue`'s font-family**

Replace:

```css
    font-family: 'Noto Sans TC', 'Segoe UI', sans-serif;
```

With:

```css
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

(This line appears once, inside the `.results-page` rule.)

- [ ] **Step 4: Verify no leftover old font-family values**

Run: `grep -rn "Noto Sans TC" frontend/src/views/PaperPage.vue frontend/src/views/PaperSourcesView.vue frontend/src/views/ResultsPage.vue`
Expected: no output.

- [ ] **Step 5: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/PaperPage.vue frontend/src/views/PaperSourcesView.vue frontend/src/views/ResultsPage.vue
git commit -m "feat: align font-family across standalone pages with HubLayout"
```

---

### Task 2: `PaperPage.vue` background — beige dot-grid, remove outer glow

**Files:**
- Modify: `frontend/src/views/PaperPage.vue` (`.paper-page` and `.paper-main` `background` declarations)

**Interfaces:**
- Consumes: `--color-primary` (already defined)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Remove the outer glow from `.paper-page`**

Replace:

```css
    background:
      radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
      var(--color-primary);
```

With:

```css
    background: var(--color-primary);
```

(This is the only `background` declaration inside the `.paper-page` rule.)

- [ ] **Step 2: Change the dot-grid base color in `.paper-main`**

Replace:

```css
    background:
      radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
      var(--color-surface);
```

With:

```css
    background:
      radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
      var(--color-primary);
```

(This is the only `background` declaration inside the `.paper-main` rule. Only the second layer — the base color — changes; the dot-pattern radial-gradient layer stays identical.)

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Live browser check**

Run (from `frontend/`): `npm run dev`. Open `/paper`.

Expected: the page background is flat beige (no accent-colored glow in the corners); the dot-grid textured area behind the paper card is beige with visible dots (not white); the white paper card (`.paper-sheet`) in the center is unchanged. Stop the dev server after checking.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: change PaperPage background to beige, remove accent glow"
```

---

## Plan Self-Review

**Spec coverage:** Spec's 段落 A maps to Task 1; 段落 B and 段落 C both map to Task 2 (same file, same `<style scoped>` block, reviewed together as one deliverable).

**Placeholder scan:** No "TBD"/"add appropriate"/"similar to Task N" — every step shows the complete before/after CSS.

**Type consistency:** N/A — pure CSS value edits, no functions/types/props introduced or consumed across tasks.
