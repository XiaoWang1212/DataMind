# 使用者登入制與資料庫架構設計

## 背景

DataMind 目前完全沒有資料庫、沒有使用者、沒有登入機制。盤點現況後發現資料分散在好幾個地方：

- **Project（專案）**：只存在瀏覽器 `localStorage`（`frontend/src/store/projectStore.ts`），後端完全沒有對應的資料表
- **Framework（分析框架庫）**：同樣只存在 `localStorage`（`frontend/src/store/frameworkStore.ts`）
- **Workflow 執行狀態**（節點/連線圖、分析結果、AI 對話紀錄）：`localStorage`（`frontend/src/composables/workflow/useWorkflowStorage.ts`）
- **上傳的資料集檔案（CSV）**：瀏覽器 `IndexedDB`（二進位檔案本身）
- **論文內容 + 文獻清單**：後端 JSON 檔案（`backend/services/report/report_store.py`，用 `project_id` 當檔名）
- **arXiv 文獻探勘知識庫（含語意搜尋向量）**：後端 JSON + numpy 檔案（`backend/services/rag/vector_store.py`），且是**全 App 共用一份**，不分 project、不分使用者
- **語言偏好設定**：`localStorage`，屬於裝置/系統設定，不在這次遷移範圍內

目的：導入「使用者登入制」，讓每個使用者只看得到自己的資料。過程中發現一個既有的設計問題：文獻探勘知識庫是全域共用的，同一個使用者不同 project 之間都可能互相污染引用內容（A project 探勘的文獻可能被 B project 生成論文時意外引用進去）。解法是把知識庫的歸屬單位從「全域」改成「project」——這樣使用者分離會自動達成（project 本來就歸屬某個使用者），同時也修正了這個既有問題。

使用者也希望這次不只加使用者機制，而是把上述所有目前存在本地/瀏覽器的資料都正式遷移進資料庫（裝置設定、純測試資料除外）。

## 目標

1. 設計一套 PostgreSQL 資料庫 schema，涵蓋：使用者、專案、框架庫、工作流程狀態、資料集檔案 metadata、論文內容與文獻、arXiv 文獻探勘知識庫（含向量）
2. 設計 email + 密碼登入機制（schema 預留 OAuth 擴充空間，但這次只實作 email + 密碼）
3. 文獻探勘知識庫從「全域共用」改為「跟著 project 走」
4. 確立檔案（資料集、之後可能的其他上傳檔案）的儲存原則：檔案留在磁碟，資料庫只存路徑與 metadata

## 非目標

- 不做前端登入/註冊頁面 UI
- 不修改現有 API 路由加上 `@login_required` 權限檢查（機制設計好，實際套用到每個路由留到下一個子題）
- 不寫實際的資料搬遷腳本（把現有 localStorage/JSON 檔案裡「已經存在」的資料匯入新資料庫）
- 不接 Google OAuth 或其他第三方登入
- 不做 email 驗證信、忘記密碼流程
- 不做 JWT——這次確定用 Flask 內建的簽章 cookie session 機制

## 設計

### 段落 A：技術選型

| 項目 | 選擇 | 理由 |
|---|---|---|
| 資料庫 | PostgreSQL | 符合中長期擴容、多人併發需求 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | Python/Flask 生態系標準組合 |
| Migration 工具 | Alembic | 搭配 SQLAlchemy 的標準 schema 版本控制工具 |
| 登入狀態 | Flask-Login + Flask 內建 session | Session 資訊直接加密簽章放進 cookie，不需要額外的 session 資料表；純網頁應用（無 App、無第三方 API 串接需求），不需要 JWT 的跨平台彈性 |
| 密碼雜湊 | bcrypt | |
| 向量儲存 | pgvector（PostgreSQL 擴充套件） | 讓 embedding 向量也能存在同一套資料庫裡，不用另外維護 numpy 檔案 |
| 檔案儲存 | 磁碟資料夾（沿用現有 `backend/uploads/` 模式） | 資料庫只存路徑/metadata，不存檔案二進位內容；之後要換雲端物件儲存（如 S3）只需要改儲存層程式碼，資料庫 schema 與其他程式碼都不用動 |

### 段落 B：`users`

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| email | 字串, unique, not null | 登入帳號 |
| password_hash | 字串, 可為空 | bcrypt 雜湊；可為空是為了以後好接 OAuth（純 OAuth 帳號沒有密碼） |
| display_name | 字串 | |
| is_admin | 布林, 預設 false | 管理員帳號用 |
| created_at | 時間戳記 | |

### 段落 C：`projects`（從 localStorage 正式搬進資料庫）

對照現在 `frontend/src/store/projectStore.ts` 的 `Project` interface：

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| user_id | 整數, FK → users.id, not null | |
| name | 字串, not null | |
| description | 文字 | |
| framework_id | 整數, FK → frameworks.id, 可為空 | 對照 `frameworkId`；`frameworks` 這次也正式建表，所以直接關聯，不再額外存 `framework_name`（要顯示時用 join 取得） |
| dataset_name | 字串, 可為空 | |
| status | enum('draft','running','completed') | |
| progress | 整數, 預設 0 | |
| accuracy | 字串, 可為空 | |
| key_finding | 文字, 可為空 | |
| variables | 整數, 預設 0 | |
| created_at | 時間戳記 | |
| updated_at | 時間戳記 | |

### 段落 D：既有檔案型資料的歸屬原則

- 論文內容（`reports`，見段落 H）跟文獻知識庫（`rag_papers`/`rag_chunks`，見段落 I）都改成正式的資料庫表格（而非停留在檔案），並透過 `project_id` 建立歸屬
- 文獻探勘知識庫從「全域一份」改成「每個 project 各自獨立」——一個 project 探勘/選用的文獻，只有那個 project 生成論文時看得到、用得到

### 段落 E：`frameworks`（從 localStorage 正式搬進資料庫）

對照 `frontend/src/store/frameworkStore.ts` 的 `Framework` interface：

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| user_id | 整數, FK → users.id, not null | |
| title | 字串 | |
| subtitle | 字串 | |
| tag | 字串 | |
| variables | 整數 | |
| paper_title | 字串 | |
| description | 文字 | |
| independent_vars | 字串陣列 | Postgres 原生陣列型別，對照 `independentVars: string[]` |
| dependent_vars | 字串陣列 | |
| hypotheses | 字串陣列 | |
| workflow_json | JSONB | 對照 `workflowJson?: Record<string, unknown>`，結構多變，直接存 JSON |
| created_at | 時間戳記 | |

### 段落 F：`datasets`（上傳檔案的 metadata；檔案本身留在磁碟）

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| project_id | 整數, FK → projects.id, not null | |
| original_filename | 字串 | 使用者上傳時的檔名 |
| storage_path | 字串 | 實際存在磁碟哪裡 |
| size_bytes | 整數 | |
| uploaded_at | 時間戳記 | |

### 段落 G：`workflow_states`（從 localStorage 正式搬進資料庫）

對照 `useWorkflowStorage.ts` 現在存的內容——節點/連線圖跟執行狀態本來就是混在一起的一包 JSON，不特別拆開每個欄位：

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| project_id | 整數, FK → projects.id, unique, not null | 一個 project 對應一份工作流程狀態 |
| state | JSONB | 整包存 `{ nodes, edges, nodeStatuses, workflowResult, ... }`，維持現有彈性結構 |
| updated_at | 時間戳記 | |

### 段落 H：`reports` + `citations`（論文內容，原本是 JSON 檔）

**reports**

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| project_id | 整數, FK → projects.id, unique, not null | 一個 project 對應一份論文 |
| title | 字串 | |
| content | JSONB | Tiptap 編輯器的文件結構 |
| citation_style | enum('apa','ieee','mla'), 預設 'apa' | |
| updated_at | 時間戳記 | |

**citations**（原本是 report JSON 裡的一個陣列，這次拆成獨立資料表）

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| report_id | 整數, FK → reports.id, not null | |
| title | 字串 | |
| authors | 字串 | |
| journal | 字串, 可為空 | |
| year | 整數 | |
| snippet | 文字, 可為空 | |
| arxiv_id | 字串, 可為空 | |
| sort_order | 整數 | 保留原本文中第一次出現的順序（IEEE 編號依據） |

### 段落 I：`rag_papers` + `rag_chunks`（文獻探勘知識庫，含向量）

**rag_papers**（跟著 project 走，不是全域）

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| project_id | 整數, FK → projects.id, not null | |
| title | 字串 | |
| author | 字串, 可為空 | |
| year | 整數, 可為空 | |
| arxiv_id | 字串, 可為空 | |
| created_at | 時間戳記 | |

**rag_chunks**（論文切段後的內容+向量，語意搜尋用）

| 欄位 | 型別 | 說明 |
|---|---|---|
| id | 整數 PK | |
| paper_id | 整數, FK → rag_papers.id, not null | |
| content | 文字 | |
| embedding | vector(384) | pgvector 型別；384 維對照現行 `BAAI/bge-small-zh-v1.5` embedding 模型的實際輸出維度（`backend/docs/rag-paper-generation.md`） |
| chunk_index | 整數 | 在論文裡的順序 |

### 段落 J：登入機制細節

- 密碼用 bcrypt 雜湊後存進 `users.password_hash`，資料庫裡不會出現明文密碼
- 用 Flask-Login 管理登入狀態：登入成功呼叫 `login_user()`，自動處理簽章 cookie；之後受保護的 API 路由用 `@login_required` 裝飾器（實際套用到每個既有路由屬於下一個子題）
- 新增 `backend/scripts/seed_admin.py`：本地啟動時執行，如果資料庫裡還沒有任何使用者就自動建立一個管理員帳號，email/密碼透過環境變數設定，不寫死在程式碼裡

## 資料庫整體關聯圖

```
users
  ├─< projects
  │     ├─< datasets
  │     ├─1 workflow_states
  │     ├─1 reports ─< citations
  │     └─< rag_papers ─< rag_chunks
  └─< frameworks
```
（`─<` 表示一對多，`─1` 表示一對一）

## 下一步（不在這次範圍內）

1. **既有資料遷移**：目前所有 localStorage/JSON/numpy 資料都還在原地，這次設計完成後資料庫是空的。需要另外規劃：一次性遷移腳本（把使用者現有的 project/framework/workflow 資料匯入新表），以及前端從讀寫 localStorage 改成呼叫新的後端 API
2. **API 路由權限檢查**：把 `@login_required` 實際套用到 `backend/routes/` 底下每一支需要登入才能用的路由，並確認每個查詢都有加上 `WHERE user_id = ...` 或透過 project 歸屬過濾
3. **前端登入/註冊頁面**：目前沒有任何登入 UI，需要另外設計
4. **忘記密碼、email 驗證**：這次的密碼機制是最基本版本，沒有信箱驗證或密碼重設流程
