# Google 登入與忘記密碼設計

## 背景

[2026-08-01-user-auth-database-design.md](2026-08-01-user-auth-database-design.md) 建立了 email + 密碼的登入機制，並在「下一步」明確列出「Google OAuth 或其他第三方登入」「忘記密碼、email 驗證」為之後才做的範圍。目前 `backend/routes/auth.py` 只有 `/register`、`/login`、`/logout`、`/me`，前端 `LoginView.vue`／`RegisterView.vue` 只支援帳號密碼。

這次要補上這兩塊：Google 登入，以及忘記密碼（重設密碼）流程。

## 目標

1. 使用者可以用 Google 帳號登入/註冊，不用另外設密碼
2. 已用密碼註冊的使用者，用同一個 email 的 Google 帳號登入時自動綁定成同一個帳號
3. 使用者忘記密碼時，可以透過 email 拿到重設連結，設定新密碼
4. 寄信邏輯做成可插拔介面，這次先實作「印到後端 log」，之後接真的寄信服務時只需替換實作

## 非目標

- 不做 email 驗證信（註冊時確認信箱真實性）
- 不接真的 SMTP/SendGrid 等寄信服務（這次先用可插拔介面 + log 輸出頂替）
- 不支援 Google 以外的第三方登入（Facebook、GitHub 等）
- 不做「記住我」「多裝置登出」等進階 session 管理功能
- 不申請實際的 Google OAuth Client ID（環境變數留空位，由使用者自行申請並填入）

## 設計

### 段落 A：資料模型變更

在既有 `users` 表（`backend/models/user.py`）新增三個欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| google_id | 字串, unique, 可為空 | Google 回傳的使用者唯一識別碼（ID token 的 `sub`） |
| reset_token_hash | 字串, 可為空 | 忘記密碼重設 token 的雜湊值（不存明文） |
| reset_token_expires_at | 時間戳記, 可為空 | 重設 token 的過期時間 |

不另外開 `password_resets` 表：同一時間只需要一組有效的重設 token，重新申請就覆蓋舊的（等同讓舊連結自動失效），加在 `users` 上最簡單、符合現有規模。

`password_hash` 本來就是可為空的欄位，純 Google 帳號（`password_hash = NULL`）不需要額外改動即可支援。

需要一支新的 Alembic migration 加上這三個欄位。

### 段落 B：Google 登入流程

**串接方式**：前端 Google 按鈕 + ID Token 驗證（不用後端導向式 OAuth，不需設定 redirect URI，跟現有 session-cookie 架構最搭）。

**前端**
- `LoginView.vue`、`RegisterView.vue` 都加上「使用 Google 登入」按鈕
- 載入 Google Identity Services 腳本（`https://accounts.google.com/gsi/client`），用新環境變數 `VITE_GOOGLE_CLIENT_ID` 初始化（加進 `frontend/.env.example`，值先留空由使用者自行申請填入）
- 使用者選好 Google 帳號後，取得 `id_token`，POST 給後端 `/auth/google`
- 成功後比照現有 `login()`/`register()`，導向 `/hub/dashboard`

**後端**
- 新增套件 `google-auth`（加進 `backend/requirements.txt`），驗證 `id_token` 的簽章與 `aud`（須等於 `GOOGLE_CLIENT_ID`）
- 新增環境變數 `GOOGLE_CLIENT_ID`（加進 `backend/.env.example`，值先留空）
- 新增 `POST /auth/google`：
  1. 驗證 `id_token`，取出 `email`、`sub`（Google 使用者 ID）、`name`
  2. 依 email 查 `users`：
     - 查無此人 → 建立新使用者（`password_hash=None`、`google_id=sub`、`display_name=name`）
     - 查到但 `google_id` 是空的 → 補上 `google_id = sub`（自動綁定既有密碼帳號）
     - 查到且 `google_id` 已存在 → 直接視為登入
  3. `login_user()` 建立 session，回傳格式與 `/login`、`/register` 一致：`{"success": true, "result": {"id":, "email":}}`
  4. token 驗證失敗（簽章錯誤、過期、`aud` 不符）→ 回傳 401 `{"success": false, "error": "Google 登入驗證失敗"}`

### 段落 C：忘記密碼流程

**新增路由（前端，需加進 `router/index.ts` 的 `PUBLIC_PATHS`）**
- `/forgot-password` → `ForgotPasswordView.vue`：輸入 email 送出
- `/reset-password` → `ResetPasswordView.vue`：帶 `?token=xxx` query，輸入新密碼送出

**新增後端 API**
- `POST /auth/forgot-password`：
  - body：`{ email }`
  - 若使用者存在且有 `password_hash`（代表是密碼帳號，非純 Google 帳號）：產生 `secrets.token_urlsafe(32)`，雜湊後存入 `reset_token_hash`，`reset_token_expires_at` 設為現在 + 1 小時，透過 email 介面寄出含 token 的重設連結（沿用既有的 `CORS_ORIGIN` 環境變數當作前端網址組出 `{CORS_ORIGIN}/reset-password?token=...`，不另外新增環境變數）
  - 不論 email 是否存在、是否為 Google 帳號，一律回傳同一句成功訊息 `{"success": true, "result": {"message": "若此 email 已註冊，重設密碼信已寄出"}}`，避免被用來探測哪些 email 已註冊
- `POST /auth/reset-password`：
  - body：`{ token, password }`
  - 雜湊比對 `reset_token_hash`，並檢查 `reset_token_expires_at` 未過期
  - 通過：更新 `password_hash`（bcrypt），清空 `reset_token_hash`／`reset_token_expires_at`，回傳成功
  - 不通過（找不到對應 token 或已過期）：回傳 400 `{"success": false, "error": "重設連結已失效，請重新申請"}`

**前端頁面行為**
- `LoginView.vue` 密碼欄位下方加一行「忘記密碼？」連結至 `/forgot-password`
- `ForgotPasswordView.vue` 送出後不論後端回傳什麼都顯示同一句提示文字，同樣是為了不洩漏 email 是否已註冊
- `ResetPasswordView.vue` 送出成功後導向 `/login` 並提示可以用新密碼登入；token 無效/過期時顯示錯誤並提供「重新申請」連結回 `/forgot-password`

### 段落 D：可插拔寄信介面

新增 `backend/services/email_sender.py`：

```python
def send_reset_password_email(to: str, reset_link: str) -> None:
    """目前實作：印到 log。之後接真的寄信服務時替換這支函式即可，呼叫端不需修改。"""
    logger.info("[password-reset] to=%s link=%s", to, reset_link)
```

`/auth/forgot-password` 只呼叫這個函式，不直接處理寄信細節，未來要接 SMTP/SendGrid 只需要改這支檔案的實作。

## 驗證方式

- 後端：新增測試腳本（比照 `backend/scripts/test_*.py` 風格），涵蓋：
  - 新 email 用 Google 登入 → 建立新帳號
  - 既有密碼帳號用同 email 的 Google 登入 → 自動綁定，`google_id` 補上
  - 忘記密碼 → log 印出重設連結 → 用連結重設密碼 → 新密碼可登入
  - 重設 token 過期或使用後再次使用 → 回傳失效錯誤
- 前端：`npm run build` 確認無編譯錯誤；瀏覽器手動測試登入頁 Google 按鈕、忘記密碼 → 從後端 log 取得連結 → 重設密碼 → 新密碼登入的完整流程
