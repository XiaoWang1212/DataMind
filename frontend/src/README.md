# `src` 目錄說明

## 目錄結構（目前）

```text
src/
├─ app/            # App 啟動流程、初始化邏輯
├─ api/            # API client 與 endpoint 定義
├─ assets/         # 靜態資源（圖片、字體、icon）
├─ components/     # 可重用 UI 元件（跨頁/跨功能）
├─ composables/    # 可重用邏輯（Vue composables）
├─ constants/      # 全域常數、設定值、枚舉映射
├─ features/       # 依功能模組切分
├─ layouts/        # 頁面框架布局（例：DefaultLayout）
├─ plugins/        # 插件初始化（例如 Vuetify、i18n）
├─ router/         # 路由表、路由守衛
├─ services/       # 業務服務層（非純 API）
├─ store/          # Pinia/Vuex 狀態管理
├─ styles/         # 全域樣式、主題、Tailwind/Vuetify 設定
├─ types/          # 全域 TypeScript 型別
├─ utils/          # 無狀態工具函式
├─ views/          # 路由頁面元件
├─ App.vue         # 根元件
└─ main.ts         # 進入點
```

## 各資料夾放什麼

### `app/`

- 應用啟動相關：`bootstrap`、全域錯誤處理、啟動前初始化。
- 建議把 `main.ts` 的初始化細節拆到這裡，讓進入點保持精簡。

### `router/`

- 路由設定、分模組路由、`beforeEach` 權限守衛。
- 典型檔案：`index.ts`、`guards.ts`、`modules/*.ts`。

### `store/`

- Pinia stores。
- 只放狀態、getter、action。

### `views/`

- 路由對應的頁面元件（Page-level components）。
- 命名建議：`XxxPage.vue`。

### `features/` （當前不用）

- 依功能切分，例如：`features/auth`、`features/dashboard`（重復使用）。
- 每個功能內可再有自己的 `components`、`api`、`store`、`types`。

### `components/`

- 全專案共用元件：按鈕、表格、表單欄位、彈窗。
- 避免放「只在單一頁面使用」的元件；那類應放在該 feature 或 view 內。

### `composables/`

- Vue composables（`useXxx`）可重用邏輯。
- 例：`usePagination.ts`、`useDebounce.ts`、`useAuth.ts`。

### `api/`

- 純 API 存取層：HTTP client、路徑常數、request/response 型別。
- 建議不含 UI 狀態；只專注資料存取。

### `services/`

- 跨 API 與 UI 之間的業務邏輯層。
- 例：流程組裝、資料整併、快取策略、重試策略。

### `layouts/`

- 應用布局元件。
- 例：`DefaultLayout.vue`、`AuthLayout.vue`。

### `constants/`

- 不會變動的常數：路由名稱、storage key、角色代碼、regex。

### `types/`

- 共用 TypeScript 型別與介面。
- 例：`api.ts`、`user.ts`、`common.ts`。

### `utils/`

- 純工具函式。
- 例：日期格式化、字串處理、數值轉換。

### `plugins/`

- 第三方插件註冊與配置。
- 目前可放：Vuetify、i18n、dayjs plugin setup。

### `styles/`

- 全域樣式與主題（SCSS、Tailwind layer、設計 token）。
- 原則：元件內只放局部樣式，全域設計放這裡。

### `assets/`

- 靜態資源檔案。

## 推薦實務
