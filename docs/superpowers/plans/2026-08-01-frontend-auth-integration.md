# 前端登入串接 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓前端擁有登入狀態、強制登入才能使用整個 App，並提供登入/註冊/登出 UI，串接既有的後端 `/api/auth/*` API。

**Architecture:** 新增一個 Pinia `authStore` 統一管理登入狀態（呼叫既有後端 API），`main.ts` 啟動時先確認 session 是否有效，`router.beforeEach` 全域守衛依登入狀態導向 `/login` 或攔截，新增 `LoginView.vue`/`RegisterView.vue` 兩個頁面，並在 `HubSidebar.vue` 加上使用者資訊與登出按鈕。

**Tech Stack:** Vue 3.5（Composition API, `<script setup lang="ts">`）、Pinia 3、Vue Router 5、原生 `fetch`（無 axios）。

## Global Constraints

- 對應設計文件：`docs/superpowers/specs/2026-08-01-frontend-auth-integration-design.md`
- 後端 `/api/auth/*` 已完整實作，**這次計畫不修改任何後端程式碼**。四支 API 的實際回傳格式：
  - `POST /api/auth/register` body `{email, password, displayName}` → 成功 `{"success": true, "result": {"id": number, "email": string}}`；失敗 `{"success": false, "error": string}`（400/409）
  - `POST /api/auth/login` body `{email, password}` → 成功 `{"success": true, "result": {"id": number, "email": string}}`；失敗 `{"success": false, "error": string}`（401）
  - `POST /api/auth/logout`（需已登入）→ `{"success": true}`
  - `GET /api/auth/me`（需已登入）→ 成功 `{"success": true, "result": {"id": number, "email": string, "displayName": string|null, "isAdmin": boolean}}`；未登入 401 `{"success": false, "error": string}`
  - 注意：`register`/`login` 的回傳**不含** `displayName`/`isAdmin`，只有 `/me` 有完整欄位——所以 store 的 `login`/`register` 動作完成後必須再打一次 `/me` 補齊完整使用者資料
- Vite dev server 已設定 `/api` proxy 轉發到後端（`frontend/vite.config.mts` `server.proxy["/api"]`），瀏覽器端視為 same-origin；所有 auth 相關 fetch 都要帶 `credentials: 'include'`，讓 Flask-Login 的 session cookie 能正確送出/接收
- 開發用管理員帳號（`backend/.env`）：`ADMIN_EMAIL=admin@datamind.local`、`ADMIN_PASSWORD=changeme-locally`
- 前端**沒有**自動化測試框架（`frontend/package.json` 沒有 vitest/jest/cypress），驗證手段是 `npm run type-check`（`vue-tsc --build --force`）、`npm run lint`（eslint），以及手動瀏覽器操作——所有指令都在 `frontend/` 目錄下直接執行（host 上已有 `frontend/node_modules`，不需要透過 docker exec）
- 視覺風格**不用** Vuetify 表單元件（`v-text-field`/`v-alert`/`v-form` 等），沿用專案既有慣例：純 HTML `input`/`button`/`textarea` + scoped CSS，套用既有 CSS 變數 `--color-accent`/`--color-ink`/`--color-secondary`/`--color-surface`/`--color-primary`（定義於 `frontend/src/styles/tailwind.css`）。只有圖示用 Vuetify 的 `<v-icon>`。可參考 `frontend/src/views/hub/CreateProjectView.vue` 的 `.form-field`/`.form-label`/`.form-input` 寫法
- 新頁面放在 `frontend/src/views/`（跟 `WorkflowPage.vue`、`PaperPage.vue` 同層級），不是 `views/hub/` 底下
- Pinia store 用既有的 composition-style 寫法：`defineStore('name', () => { ... return {...} })`（參考 `frontend/src/store/projectStore.ts`）
- 路由守衛規則：非 `/login`、`/register` 的路由，未登入一律導去 `/login`；已登入的人訪問 `/login`/`/register` 導去 `/hub/dashboard`
- 這次不搬移任何既有 localStorage 資料，不修改 Projects/Frameworks/Workflow/Report/RAG 相關程式碼

---

### Task 1: `frontend/src/api/auth.ts` — 後端 API 包裝

**Files:**
- Create: `frontend/src/api/auth.ts`

**Interfaces:**
- Consumes: 後端既有 `/api/auth/register`、`/login`、`/logout`、`/me`（見 Global Constraints，不需修改）
- Produces：
  - `export interface AuthUser { id: number; email: string; displayName: string | null; isAdmin: boolean }`
  - `export async function register(email: string, password: string, displayName: string): Promise<void>`
  - `export async function login(email: string, password: string): Promise<void>`
  - `export async function logout(): Promise<void>`
  - `export async function fetchCurrentUser(): Promise<AuthUser | null>`（未登入時回傳 `null`，不拋出例外）

- [ ] **Step 1: 建立檔案**

```ts
export interface AuthUser {
  id: number
  email: string
  displayName: string | null
  isAdmin: boolean
}

async function parseAuthResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

function toAuthUser (raw: Record<string, unknown>): AuthUser {
  return {
    id: raw.id as number,
    email: raw.email as string,
    displayName: (raw.displayName as string | null | undefined) ?? null,
    isAdmin: Boolean(raw.isAdmin),
  }
}

export async function register (email: string, password: string, displayName: string): Promise<void> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password, displayName }),
  })
  await parseAuthResponse(response)
}

export async function login (email: string, password: string): Promise<void> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  })
  await parseAuthResponse(response)
}

export async function logout (): Promise<void> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
  await parseAuthResponse(response)
}

export async function fetchCurrentUser (): Promise<AuthUser | null> {
  const response = await fetch('/api/auth/me', { credentials: 'include' })
  if (response.status === 401) return null
  const result = await parseAuthResponse(response)
  return toAuthUser(result.result as Record<string, unknown>)
}
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤（exit code 0），輸出不含 `src/api/auth.ts` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤，輸出不含 `src/api/auth.ts` 相關錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/auth.ts
git commit -m "feat: add frontend auth API wrapper"
```

---

### Task 2: `frontend/src/store/authStore.ts` — 登入狀態管理

**Files:**
- Create: `frontend/src/store/authStore.ts`

**Interfaces:**
- Consumes: Task 1 的 `AuthUser`、`register`、`login`、`logout`、`fetchCurrentUser`（`frontend/src/api/auth.ts`）
- Produces:
  - `export const useAuthStore = defineStore('auth', () => {...})`，回傳：
    - `user: Ref<AuthUser | null>`
    - `isReady: Ref<boolean>`
    - `isAuthenticated: ComputedRef<boolean>`
    - `checkSession(): Promise<void>`
    - `login(email: string, password: string): Promise<void>`（失敗會 throw，呼叫端要自己 catch）
    - `register(email: string, password: string, displayName: string): Promise<void>`（失敗會 throw）
    - `logout(): Promise<void>`

- [ ] **Step 1: 建立檔案**

```ts
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  fetchCurrentUser,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  type AuthUser,
} from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const isReady = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  async function checkSession (): Promise<void> {
    try {
      user.value = await fetchCurrentUser()
    } finally {
      isReady.value = true
    }
  }

  async function login (email: string, password: string): Promise<void> {
    await apiLogin(email, password)
    await checkSession()
  }

  async function register (email: string, password: string, displayName: string): Promise<void> {
    await apiRegister(email, password, displayName)
    await checkSession()
  }

  async function logout (): Promise<void> {
    await apiLogout()
    user.value = null
  }

  return { user, isReady, isAuthenticated, checkSession, login, register, logout }
})
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/store/authStore.ts` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/store/authStore.ts
git commit -m "feat: add auth Pinia store"
```

---

### Task 3: `frontend/src/views/LoginView.vue` — 登入頁

**Files:**
- Create: `frontend/src/views/LoginView.vue`

**Interfaces:**
- Consumes: Task 2 的 `useAuthStore()`（`login` action、`user`/`isAuthenticated`）
- Produces: 路由元件，之後 Task 5 會在 `router/index.ts` 把 `/login` 指向這個檔案

- [ ] **Step 1: 建立檔案**

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">登入</h1>
      <p class="auth-sub">登入以繼續使用 DataMind</p>

      <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="login-email">Email</label>
          <input
            id="login-email"
            v-model="email"
            type="email"
            class="form-input"
            placeholder="you@example.com"
            required
          >
        </div>
        <div class="form-field">
          <label class="form-label" for="login-password">密碼</label>
          <input
            id="login-password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="輸入密碼"
            required
          >
        </div>
        <button type="submit" class="auth-submit-btn" :disabled="isSubmitting">
          {{ isSubmitting ? '登入中...' : '登入' }}
        </button>
      </form>

      <button type="button" class="auth-dev-btn" @click="fillAdminCredentials">
        使用管理員帳號（開發用）
      </button>

      <p class="auth-switch">
        還沒有帳號？<RouterLink to="/register">註冊</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const DEV_ADMIN_EMAIL = 'admin@datamind.local'
  const DEV_ADMIN_PASSWORD = 'changeme-locally'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  function fillAdminCredentials (): void {
    email.value = DEV_ADMIN_EMAIL
    password.value = DEV_ADMIN_PASSWORD
  }

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.login(email.value, password.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 32px;
  color: var(--color-ink);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0 0 20px;
}

.auth-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
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

.auth-submit-btn {
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
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.auth-submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.auth-dev-btn {
  width: 100%;
  height: 36px;
  margin-top: 12px;
  background: #ffffff;
  color: var(--color-secondary);
  border: 1px dashed #d1d5db;
  border-radius: 7px;
  font-size: 12.5px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.auth-dev-btn:hover {
  color: var(--color-ink);
  border-color: var(--color-accent);
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-secondary);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/views/LoginView.vue` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/LoginView.vue
git commit -m "feat: add login page"
```

---

### Task 4: `frontend/src/views/RegisterView.vue` — 註冊頁

**Files:**
- Create: `frontend/src/views/RegisterView.vue`

**Interfaces:**
- Consumes: Task 2 的 `useAuthStore()`（`register` action）
- Produces: 路由元件，之後 Task 5 會在 `router/index.ts` 把 `/register` 指向這個檔案

- [ ] **Step 1: 建立檔案**

```vue
<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">註冊</h1>
      <p class="auth-sub">建立一個新的 DataMind 帳號</p>

      <div v-if="errorMessage" class="auth-error">{{ errorMessage }}</div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label class="form-label" for="register-email">Email</label>
          <input
            id="register-email"
            v-model="email"
            type="email"
            class="form-input"
            placeholder="you@example.com"
            required
          >
        </div>
        <div class="form-field">
          <label class="form-label" for="register-display-name">顯示名稱（選填）</label>
          <input
            id="register-display-name"
            v-model="displayName"
            type="text"
            class="form-input"
            placeholder="你的名字"
          >
        </div>
        <div class="form-field">
          <label class="form-label" for="register-password">密碼</label>
          <input
            id="register-password"
            v-model="password"
            type="password"
            class="form-input"
            placeholder="設定密碼"
            required
          >
        </div>
        <button type="submit" class="auth-submit-btn" :disabled="isSubmitting">
          {{ isSubmitting ? '註冊中...' : '註冊' }}
        </button>
      </form>

      <p class="auth-switch">
        已經有帳號？<RouterLink to="/login">登入</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import { RouterLink, useRouter } from 'vue-router'
  import { useAuthStore } from '@/store/authStore'

  const router = useRouter()
  const authStore = useAuthStore()

  const email = ref('')
  const displayName = ref('')
  const password = ref('')
  const errorMessage = ref('')
  const isSubmitting = ref(false)

  async function handleSubmit (): Promise<void> {
    errorMessage.value = ''
    isSubmitting.value = true
    try {
      await authStore.register(email.value, password.value, displayName.value)
      router.push('/hub/dashboard')
    } catch (error) {
      errorMessage.value = error instanceof Error ? error.message : '無法連線到伺服器，請稍後再試'
    } finally {
      isSubmitting.value = false
    }
  }
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary);
}

.auth-card {
  width: 100%;
  max-width: 380px;
  background: #ffffff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 32px;
  color: var(--color-ink);
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 5px;
}

.auth-sub {
  font-size: 13.5px;
  color: var(--color-secondary);
  margin: 0 0 20px;
}

.auth-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 6px;
  padding: 9px 12px;
  font-size: 13px;
  margin-bottom: 16px;
}

.form-field {
  margin-bottom: 16px;
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

.auth-submit-btn {
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
  margin-top: 4px;
}

.auth-submit-btn:hover:not(:disabled) {
  background: color-mix(in oklab, var(--color-accent) 85%, black);
}

.auth-submit-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.auth-switch {
  text-align: center;
  font-size: 13px;
  color: var(--color-secondary);
  margin: 18px 0 0;
}

.auth-switch a {
  color: var(--color-accent);
  font-weight: 500;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/views/RegisterView.vue` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/RegisterView.vue
git commit -m "feat: add register page"
```

---

### Task 5: 路由 — 新增 `/login`、`/register` + 全域登入守衛

**Files:**
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: Task 2 的 `useAuthStore()`（`isAuthenticated`、`isReady`、`checkSession`），Task 3/4 的 `LoginView.vue`/`RegisterView.vue`
- Produces: 全站生效的 `router.beforeEach` 守衛，後續任務不需要再碰路由設定

- [ ] **Step 1: 修改檔案**

把整個檔案內容換成：

```ts
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/store/authStore";

const PUBLIC_PATHS = ["/login", "/register"];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      redirect: "/hub/dashboard",
    },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("@/views/RegisterView.vue"),
    },
    {
      path: "/tutorial",
      name: "tutorial",
      component: () => import("@/views/TutorialPage.vue"),
    },
    {
      path: "/workflow",
      name: "workflow",
      component: () => import("@/views/WorkflowPage.vue"),
    },
    {
      path: "/results",
      name: "results",
      component: () => import("@/views/ResultsPage.vue"),
    },
    {
      path: "/paper",
      name: "paper",
      component: () => import("@/views/PaperPage.vue"),
    },
    {
      path: "/paper/sources",
      name: "paper-sources",
      component: () => import("@/views/PaperSourcesView.vue"),
    },
    {
      path: "/hub",
      component: () => import("@/layouts/HubLayout.vue"),
      redirect: "/hub/dashboard",
      children: [
        {
          path: "dashboard",
          name: "hub-dashboard",
          component: () => import("@/views/hub/DashboardView.vue"),
        },
        {
          path: "library",
          name: "hub-library",
          component: () => import("@/views/hub/FrameworkLibraryView.vue"),
        },
        {
          path: "library/extract",
          name: "hub-extract",
          component: () => import("@/views/hub/ExtractFrameworkView.vue"),
        },
        {
          path: "projects",
          name: "hub-projects",
          component: () => import("@/views/hub/ProjectsView.vue"),
        },
        {
          path: "projects/new",
          name: "hub-projects-new",
          component: () => import("@/views/hub/CreateProjectView.vue"),
        },
        {
          path: "projects/:id",
          name: "hub-project-detail",
          component: () => import("@/views/hub/ProjectDetailView.vue"),
        },
        {
          path: "projects/:id/result",
          name: "hub-project-result",
          component: () => import("@/views/hub/ResultView.vue"),
        },
        {
          path: "settings",
          name: "hub-settings",
          component: () => import("@/views/hub/SettingsView.vue"),
        },
      ],
    },  
  ],
});

router.beforeEach(async to => {
  const authStore = useAuthStore();

  if (!authStore.isReady) {
    await authStore.checkSession();
  }

  const isPublicPath = PUBLIC_PATHS.includes(to.path);

  if (!isPublicPath && !authStore.isAuthenticated) {
    return "/login";
  }

  if (isPublicPath && authStore.isAuthenticated) {
    return "/hub/dashboard";
  }
});

export default router;
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/router/index.ts` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/router/index.ts
git commit -m "feat: add login/register routes and global auth guard"
```

---

### Task 6: `frontend/src/main.ts` — App 啟動時先確認 session

**Files:**
- Modify: `frontend/src/main.ts`

**Interfaces:**
- Consumes: Task 2 的 `useAuthStore()`（`checkSession`）
- Produces: 無（純啟動流程調整），後續任務不依賴這個檔案

- [ ] **Step 1: 修改檔案**

把整個檔案內容換成：

```ts
/**
 * main.ts
 *
 * Bootstraps Vuetify and other plugins then mounts the App`
 */

// Composables
import { createApp } from 'vue'

// Plugins
import { registerPlugins } from '@/plugins'

// Components
import App from './App.vue'

// Store
import { useAuthStore } from '@/store/authStore'

// Styles
import 'unfonts.css'
import './styles/tailwind.css'
import './styles/main.scss'

const app = createApp(App)

registerPlugins(app)

const authStore = useAuthStore()

authStore.checkSession().finally(() => {
  app.mount('#app')
})
```

- [ ] **Step 2: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/main.ts` 相關錯誤

- [ ] **Step 3: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 4: Commit**

```bash
git add frontend/src/main.ts
git commit -m "feat: check auth session before mounting app"
```

---

### Task 7: `frontend/src/components/hub/HubSidebar.vue` — 顯示使用者 + 登出

**Files:**
- Modify: `frontend/src/components/hub/HubSidebar.vue`

**Interfaces:**
- Consumes: Task 2 的 `useAuthStore()`（`user`、`logout`）
- Produces: 無（UI 端點），這是這個子專案的最後一個程式碼變更任務

- [ ] **Step 1: 修改 `<template>`**

在既有的 `</nav>` 和 `<div v-if="!collapsed" class="hub-sidebar-footer">` 之間，插入使用者資訊區塊：

```html
    </nav>

    <div v-if="!collapsed && authStore.user" class="hub-sidebar-user">
      <div class="hub-user-name">{{ authStore.user.displayName || authStore.user.email }}</div>
      <button class="hub-logout-btn" title="登出" @click="handleLogout">
        <v-icon icon="mdi-logout" size="16" />
      </button>
    </div>

    <div v-if="!collapsed" class="hub-sidebar-footer">
```

- [ ] **Step 2: 修改 `<script setup>`**

把：

```ts
import { ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'

const route = useRoute()
const collapsed = ref(false)
```

換成：

```ts
import { ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/store/authStore'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

async function handleLogout (): Promise<void> {
  await authStore.logout()
  router.push('/login')
}
```

- [ ] **Step 3: 在 `<style scoped>` 加入新樣式**

在 `.hub-sidebar-footer` 規則區塊**之前**插入：

```css
.hub-sidebar-user {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid #f0f0f0;
  position: relative;
  z-index: 2;
}

.hub-user-name {
  font-size: 12.5px;
  color: var(--color-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hub-logout-btn {
  width: 26px;
  height: 26px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-secondary);
  transition: background 0.15s, color 0.15s;
}

.hub-logout-btn:hover {
  background: color-mix(in oklab, var(--color-accent) 12%, var(--color-surface));
  color: var(--color-ink);
}
```

- [ ] **Step 4: 型別檢查**

Run: `cd frontend && npm run type-check`
Expected: 無錯誤，輸出不含 `src/components/hub/HubSidebar.vue` 相關錯誤

- [ ] **Step 5: Lint**

Run: `cd frontend && npm run lint`
Expected: 無錯誤

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/hub/HubSidebar.vue
git commit -m "feat: show current user and logout button in hub sidebar"
```

---

### Task 8: 整批驗證

**Files:** 無新增/修改檔案，純驗證

**Interfaces:**
- Consumes: Task 1-7 全部產出

驗證分兩部分：(A) 用 curl 驗證 API 層與 session cookie 行為（可完全自動化，不需要瀏覽器）；(B) 用瀏覽器驗證路由守衛與 UI（Vue Router 的導向邏輯是純前端行為，curl 打不到，需要實際渲染頁面才能確認）。

- [ ] **Step 1: 確認容器正在跑**

Run: `docker ps --format "{{.Names}}"`
Expected: 輸出包含 `datamind-frontend`、`datamind-backend`、`datamind-postgres`（三個都已在跑，這個計畫不需要額外啟動任何服務）

- [ ] **Step 2（A）: curl 驗證 — 未登入打 `/api/auth/me` 應該 401**

Run（在乾淨的 cookie jar 下）：
```bash
curl -s -o /dev/null -w "%{http_code}\n" -c /tmp/auth-verify-cookies.txt http://localhost:5173/api/auth/me
```
Expected: `401`

- [ ] **Step 3（A）: curl 驗證 — 註冊一個臨時測試帳號並確認自動登入**

Run：
```bash
curl -s -b /tmp/auth-verify-cookies.txt -c /tmp/auth-verify-cookies.txt \
  -X POST http://localhost:5173/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"auth-verify-temp@example.com","password":"testpass123","displayName":"Auth Verify"}'
```
Expected: 回傳 JSON 含 `"success":true`

Run：
```bash
curl -s -b /tmp/auth-verify-cookies.txt -c /tmp/auth-verify-cookies.txt http://localhost:5173/api/auth/me
```
Expected: 回傳 JSON 含 `"success":true` 且 `"email":"auth-verify-temp@example.com"`、`"displayName":"Auth Verify"`

- [ ] **Step 4（A）: curl 驗證 — 登出後 session 失效**

Run：
```bash
curl -s -b /tmp/auth-verify-cookies.txt -c /tmp/auth-verify-cookies.txt -X POST http://localhost:5173/api/auth/logout
curl -s -o /dev/null -w "%{http_code}\n" -b /tmp/auth-verify-cookies.txt http://localhost:5173/api/auth/me
```
Expected: 第二個指令回傳 `401`

- [ ] **Step 5（A）: 清理測試帳號**

Run：
```bash
docker exec datamind-postgres psql -U datamind -d datamind -c "DELETE FROM users WHERE email = 'auth-verify-temp@example.com';"
rm -f /tmp/auth-verify-cookies.txt
```
Expected: `DELETE 1`

- [ ] **Step 6（B）: 瀏覽器驗證 — 未登入被擋**

用瀏覽器工具開啟無痕視窗（或先清除 `localhost:5173` 的 cookie），導航到 `http://localhost:5173/hub/dashboard`
Expected: 網址被導向 `http://localhost:5173/login`，畫面顯示登入頁

- [ ] **Step 7（B）: 瀏覽器驗證 — 管理員帳號一鍵登入**

在登入頁按「使用管理員帳號（開發用）」按鈕，確認 email/password 欄位被填入 `admin@datamind.local` / `changeme-locally`，按「登入」
Expected: 導向 `http://localhost:5173/hub/dashboard`，側邊欄底部顯示使用者資訊（管理員帳號沒有設定 displayName，應顯示 email：`admin@datamind.local`）

- [ ] **Step 8（B）: 瀏覽器驗證 — 重新整理仍保持登入**

在 Hub 頁面重新整理瀏覽器
Expected: 仍停留在 Hub 頁面，沒有被導回登入頁

- [ ] **Step 9（B）: 瀏覽器驗證 — 登出**

點側邊欄的登出按鈕
Expected: 導向 `http://localhost:5173/login`；再次嘗試訪問 `http://localhost:5173/hub/dashboard` 應再次被導回登入頁

- [ ] **Step 10（B）: 瀏覽器驗證 — 已登入時訪問 `/login`/`/register` 會被導開**

重新登入後，直接在網址列輸入 `http://localhost:5173/login`
Expected: 立刻被導向 `http://localhost:5173/hub/dashboard`（不會顯示登入頁）

無需 commit（這個任務不產生程式碼變更）。
