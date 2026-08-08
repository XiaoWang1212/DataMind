# PaperPage Background Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `PaperPage.vue`'s decorative glow/dot-grid background effect (removed in the prior color-application batch), recolored with the project's `--color-accent`/`--color-secondary` tokens instead of the old blue palette, layered over the existing flat `primary`/`surface` base.

**Architecture:** Pure CSS value change in `frontend/src/views/PaperPage.vue`'s existing `<style scoped>` block — no template or script changes. Uses `color-mix(in oklab, ...)`, the same technique already used for the Hub sidebar hover fix.

**Tech Stack:** Vue 3, Tailwind CSS v4 (`@theme` CSS-first config), Vite.

## Global Constraints

- Token values already defined in `frontend/src/styles/tailwind.css` (do not redefine, only reference): `--color-primary` (`#f6f5f2`), `--color-surface` (`#ffffff`), `--color-accent` (`#e8a33d`), `--color-secondary` (`#334155`)
- Preserve exact existing geometry: glow positions (`8% 12%`, `91% 89%`), glow sizes (`38%`, `30%`), dot-grid spacing (`18px`) — only the colors change
- No unit test framework is configured in `frontend/` — verification is `npm run build` and a live browser visual check
- Do not touch anything in `PaperPage.vue` besides the two `background` declarations

---

### Task 1: Restore recolored decorative backgrounds

**Files:**
- Modify: `frontend/src/views/PaperPage.vue` (`.paper-page` and `.paper-main` `background` declarations)

**Interfaces:**
- Consumes: `--color-primary`, `--color-surface`, `--color-accent`, `--color-secondary` (already defined in `frontend/src/styles/tailwind.css`)
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Edit `.paper-page` background**

Replace:

```css
    background: var(--color-primary);
```

With:

```css
    background:
      radial-gradient(circle at 8% 12%, color-mix(in oklab, var(--color-accent) 18%, transparent) 0%, transparent 38%),
      radial-gradient(circle at 91% 89%, color-mix(in oklab, var(--color-accent) 16%, transparent) 0%, transparent 30%),
      var(--color-primary);
```

(This line appears once in the `.paper-page` rule — the only `background: var(--color-primary);` declaration in the file.)

- [ ] **Step 2: Edit `.paper-main` background**

Replace:

```css
    background: var(--color-surface);
```

With:

```css
    background:
      radial-gradient(circle, color-mix(in oklab, var(--color-secondary) 8%, transparent) 1px, transparent 1px) 0 0 / 18px 18px,
      var(--color-surface);
```

(This line appears once in the `.paper-main` rule — the only `background: var(--color-surface);` declaration in the file.)

- [ ] **Step 3: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no errors.

- [ ] **Step 4: Live browser check**

Run (from `frontend/`): `npm run dev`. Open `/paper`. Expected: a soft amber glow visible near the top-left and bottom-right of the page, a subtle blue-grey dot-grid texture visible in the card panel area, base colors still cream (`.paper-page`) and white (`.paper-main`). Stop the dev server after checking.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/PaperPage.vue
git commit -m "feat: restore PaperPage decorative background with new color tokens"
```
