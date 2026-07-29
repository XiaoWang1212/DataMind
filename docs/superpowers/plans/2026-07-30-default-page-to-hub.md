# Default Page to Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the standalone landing page (`HomePage.vue` / `HelloWorld.vue`) and make the root path `/` redirect to the Hub dashboard at `/hub/dashboard`, matching the existing `/hub` → `/hub/dashboard` redirect pattern.

**Architecture:** No new code — delete two now-dead files and change one route entry in the existing Vue Router config from a component route to a `redirect`.

**Tech Stack:** Vue 3, Vue Router, Vite.

## Global Constraints

- `frontend/src/components/HelloWorld.vue` is confirmed (via repo-wide grep) to be referenced only by `frontend/src/views/HomePage.vue` — no other file imports it
- The route `name: "home"` and literal path `"/"` are confirmed (via repo-wide grep) to have no other references anywhere in `frontend/src` — safe to remove/repurpose
- Do not touch `/hub`'s own route definition, its children, or any other route (`/tutorial`, `/workflow`, `/results`, `/paper`, `/paper/sources`)
- No unit test framework is configured in `frontend/` — verification is `npm run build` (`vue-tsc --build --force` then `vite build`) run from the `frontend/` directory, plus a live browser check
- Do not add a test framework or write new automated tests as part of this plan

---

### Task 1: Remove HomePage/HelloWorld and redirect `/` to the Hub dashboard

**Files:**
- Delete: `frontend/src/views/HomePage.vue`
- Delete: `frontend/src/components/HelloWorld.vue`
- Modify: `frontend/src/router/index.ts:6-10`

**Interfaces:**
- Consumes: none
- Produces: nothing consumed by later tasks

- [ ] **Step 1: Delete the two dead files**

```bash
git rm frontend/src/views/HomePage.vue frontend/src/components/HelloWorld.vue
```

- [ ] **Step 2: Edit `frontend/src/router/index.ts`**

Replace:

```ts
    {
      path: "/",
      name: "home",
      component: () => import("@/views/HomePage.vue"),
    },
```

With:

```ts
    {
      path: "/",
      redirect: "/hub/dashboard",
    },
```

- [ ] **Step 3: Verify no leftover references to the deleted files**

Run: `grep -rn "HomePage\|HelloWorld" frontend/src`
Expected: no output.

- [ ] **Step 4: Verify the build succeeds**

Run (from `frontend/`): `npm run build`
Expected: exits 0, no TypeScript or Vite errors (in particular, no "failed to resolve import" errors referencing the deleted files).

- [ ] **Step 5: Manual browser check**

Run (from `frontend/`): `npm run dev`
Open the app at its root URL (e.g. `http://localhost:PORT/`). Expected: the browser's address bar updates to end in `/hub/dashboard`, and the Hub dashboard renders (stat tiles, "最近活動" list, sidebar). Also visit `/tutorial`, `/workflow`, `/results`, `/paper`, and `/hub` directly to confirm they still load without errors. Stop the dev server after checking.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: remove standalone HomePage, redirect / to Hub dashboard"
```

Note: Step 1's `git rm` already stages the deletions; this commit's `git add` only needs the router file, but running `git status` before committing to confirm both deletions and the router change are staged together is worth doing if unsure.
