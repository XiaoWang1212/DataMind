# 前端登入串接 設計文件

## 背景與範圍

後端資料庫與登入 API（`/api/auth/register`、`/login`、`/logout`、`/me`，session cookie based，見 `backend/routes/auth.py`）已經實作完成，但前端目前完全沒有登入相關的 UI、狀態管理或路由保護——沒有 auth store、沒有登入/註冊頁面、沒有 route guard，`frontend/src/api/` 底下的 fetch 呼叫也都沒有帶 `credentials: 'include'`。

這是「把現有功能資料流程移進資料庫」大工程的第一個子專案，目標是把登入這條路先打通，後續子專案（專案/框架庫遷移、工作流程狀態持久化、報告/引用、RAG 文獻庫）才能在此基礎上依 `user_id`/`project_id` 做資料隔離。

**這次的範圍只到「登入串接」本身**：新增登入/註冊頁面、auth store、強制登入的路由守衛、登出功能、一個開發用的一鍵填入管理員帳號按鈕。**不**觸碰 Projects/Frameworks/Workflow/Report/RAG 既有功能的程式碼，這些功能目前仍是 localStorage/檔案存儲，維持現狀，等各自的子專案再處理。也**不**包含既有 localStorage 資料的搬移（這次沒有資料要搬）。

## 架構總覽

```
main.ts
  └─ authStore.checkSession()  ──▶  GET /api/auth/me
        │ (等待完成後才掛載 router/app)
        ▼
  router.beforeEach (全域守衛)
        │
        ├─ 未登入 + 非 /login /register  ──▶ redirect /login
        └─ 已登入 + 訪問 /login /register ──▶ redirect Hub 首頁

LoginView.vue / RegisterView.vue
        │ 呼叫
        ▼
frontend/src/api/auth.ts (fetch, credentials: 'include')
        │
        ▼
backend /api/auth/* (既有，不需修改)

HubSidebar.vue
        └─ 顯示目前使用者 + 登出按鈕 → authStore.logout() → redirect /login
```

## 元件設計

### 1. `frontend/src/api/auth.ts`（新增）

包裝四支既有後端 API，每個 fetch 都帶 `credentials: 'include'`（讓瀏覽器送出/接收 session cookie）：

| 函式 | 對應 API | 用途 |
|---|---|---|
| `register(email, password, displayName)` | `POST /api/auth/register` | 註冊並自動登入 |
| `login(email, password)` | `POST /api/auth/login` | 登入 |
| `logout()` | `POST /api/auth/logout` | 登出 |
| `fetchCurrentUser()` | `GET /api/auth/me` | 查詢目前 session 對應的使用者，401 時回傳 `null`（不當例外拋出，因為「沒登入」是正常狀態） |

回傳格式沿用後端既有的 `{ success, result }` / `{ success: false, error }` 結構。

### 2. `frontend/src/store/authStore.ts`（新增，Pinia）

```
state:
  user: { id, email, displayName, isAdmin } | null
  isReady: boolean   // checkSession() 是否已完成過一次

getters:
  isAuthenticated: computed(() => user !== null)

actions:
  checkSession()   // 呼叫 fetchCurrentUser()，成功則設定 user，401 則 user = null；無論如何最後設 isReady = true
  login(email, password)     // 呼叫 api/auth.ts login()，成功設定 user，失敗回傳/拋出錯誤訊息給呼叫端顯示
  register(email, password, displayName)  // 同上，呼叫 register()
  logout()          // 呼叫 api/auth.ts logout()，清空 user
```

`isReady` 用來讓路由守衛知道「第一次 session 檢查是否已完成」，避免頁面刷新瞬間因為 user 還是初始值 `null` 就被誤判成未登入而閃一下登入頁。

### 3. `main.ts` 啟動流程（修改）

在 `app.mount('#app')` 之前，先 `await authStore.checkSession()`。這是一次性的啟動阻塞（打一支 `/api/auth/me`，正常情況下很快），確保路由守衛第一次執行時 `isReady` 已經是 `true`。

### 4. 路由守衛（修改 `frontend/src/router/`）

`router.beforeEach((to) => {...})`：

- 若 `to.path` 不是 `/login` 也不是 `/register`，且 `!authStore.isAuthenticated` → 導向 `/login`
- 若 `to.path` 是 `/login` 或 `/register`，且 `authStore.isAuthenticated` → 導向 Hub 首頁（`/`，目前已 redirect 到 Hub dashboard）
- 其餘情況放行

不做「記住原本想去的頁面、登入後導回去」這種額外邏輯（YAGNI），登入成功一律導向 Hub 首頁。

### 5. `LoginView.vue`（新增）

- 路徑：`/login`
- Vuetify 表單：email、password 兩個 `v-text-field`，一個「登入」`v-btn`
- 視覺風格沿用既有 Hub 深色玻璃質感與 accent 色票（`HubLayout.vue`/`HubSidebar.vue` 已建立的樣式），不另外設計新視覺語言
- 登入失敗（帳密錯誤）用 `v-alert type="error"` 顯示後端回傳的 `error` 訊息
- 底部連結「還沒有帳號？註冊」導去 `/register`
- **開發用按鈕**：「使用管理員帳號」，按下後把 email/password 欄位分別填成 `admin@datamind.local` / `changeme-locally`（對應 `backend/.env` 的 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 預設值，寫死在前端常數，不額外呼叫 API）。這顆按鈕與其填值函式是暫時性的，之後要移除時只需刪除這一小段，不影響登入主流程

### 6. `RegisterView.vue`（新增）

- 路徑：`/register`
- Vuetify 表單：email、password、displayName（可選）三個欄位，一個「註冊」`v-btn`
- 視覺風格同 LoginView
- 註冊失敗（email 重複、密碼過長等後端已驗證的情況）同樣用 `v-alert` 顯示錯誤訊息
- 成功後 authStore 已經是登入狀態（後端 `register` 會自動 `login_user`），直接導向 Hub 首頁
- 底部連結「已經有帳號？登入」導去 `/login`

### 7. `HubSidebar.vue`（修改）

在既有側邊欄底部新增一小區塊：顯示 `authStore.user.displayName || authStore.user.email`，旁邊一個登出圖示按鈕，點擊呼叫 `authStore.logout()` 後導向 `/login`。

## 錯誤處理

- 帳密錯誤 / email 重複 / 密碼過長：後端已回傳明確的 400/401/409 + `error` 訊息（繁體中文），前端原樣顯示在 `v-alert`
- `checkSession()` 打 `/api/auth/me` 失敗（例如後端沒開）：視同未登入（`user = null`），不彈錯誤視窗，直接讓路由守衛導去登入頁——避免後端暫時不可用時整個 App 卡在空白載入畫面
- 網路層級錯誤（fetch reject）：login/register 顯示通用「無法連線到伺服器，請稍後再試」訊息

## 驗證方式（手動）

1. 未登入直接訪問 Hub 網址 → 應被導去 `/login`
2. `/login` 頁按「使用管理員帳號」→ 欄位自動填好 → 按登入 → 導向 Hub 首頁，側邊欄顯示管理員名稱
3. 重新整理頁面 → 應保持登入狀態（不會被導回登入頁）
4. 側邊欄按登出 → 導向 `/login`，再訪問 Hub 網址應再次被擋
5. `/register` 頁註冊一個新帳號 → 自動登入 → 導向 Hub 首頁
6. 用剛註冊的 email 再註冊一次 → 應顯示「此 email 已被註冊」錯誤
7. 登入頁輸入錯誤密碼 → 應顯示「帳號或密碼錯誤」，不會登入成功

無自動化測試框架（沿用專案既有慣例），以上步驟全部手動在瀏覽器操作驗證。
