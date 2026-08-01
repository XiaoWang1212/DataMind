# 資料庫架構說明與操作指南

設計決策與理由（為什麼選 PostgreSQL、為什麼 session 不用 JWT、為什麼文獻庫要跟著 project 走等）記在設計文件：`docs/superpowers/specs/2026-08-01-user-auth-database-design.md`。這份文件是技術參考：架構、schema、環境啟動方式。

> 這份資料庫設計已經實作完成——PostgreSQL、SQLAlchemy model（`backend/models/`）、Alembic migration（`backend/migrations/`）、登入 API（`backend/routes/auth.py`）都已存在。以下的「本機環境啟動方式」段落沿用建置時的操作記錄，供之後重新建置或除錯時參考。

---

## 一、架構總覽

```
users
  ├─< projects
  │     ├─< datasets
  │     ├─1 workflow_states
  │     ├─1 reports ─< citations
  │     └─< rag_papers ─< rag_chunks
  └─< frameworks
```

`─<`：一對多。`─1`：一對一。所有資料表最終都能透過外鍵追溯回 `users`，作為存取控制的依據（`projects.user_id` / `frameworks.user_id` 直接關聯；其餘表格透過 `project_id` 間接關聯）。

---

## 二、資料表 Schema

### `users`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| email | 字串 | unique, not null |
| password_hash | 字串 | 可為空（OAuth 帳號無密碼） |
| display_name | 字串 | |
| is_admin | 布林 | 預設 false |
| created_at | 時間戳記 | |

### `projects`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| user_id | 整數 | FK → users.id, not null |
| name | 字串 | not null |
| description | 文字 | |
| framework_id | 整數 | FK → frameworks.id, 可為空 |
| dataset_name | 字串 | 可為空 |
| status | enum('draft','running','completed') | |
| progress | 整數 | 預設 0 |
| accuracy | 字串 | 可為空 |
| key_finding | 文字 | 可為空 |
| variables | 整數 | 預設 0 |
| created_at | 時間戳記 | |
| updated_at | 時間戳記 | |

### `frameworks`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| user_id | 整數 | FK → users.id, not null |
| title | 字串 | |
| subtitle | 字串 | |
| tag | 字串 | |
| variables | 整數 | |
| paper_title | 字串 | |
| description | 文字 | |
| independent_vars | 字串陣列 | |
| dependent_vars | 字串陣列 | |
| hypotheses | 字串陣列 | |
| workflow_json | JSONB | |
| created_at | 時間戳記 | |

### `datasets`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| project_id | 整數 | FK → projects.id, not null |
| original_filename | 字串 | |
| storage_path | 字串 | 磁碟路徑；檔案本體不存資料庫 |
| size_bytes | 整數 | |
| uploaded_at | 時間戳記 | |

### `workflow_states`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| project_id | 整數 | FK → projects.id, unique, not null |
| state | JSONB | `{ nodes, edges, nodeStatuses, workflowResult, ... }` |
| updated_at | 時間戳記 | |

### `reports`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| project_id | 整數 | FK → projects.id, unique, not null |
| title | 字串 | |
| content | JSONB | Tiptap 文件結構 |
| citation_style | enum('apa','ieee','mla') | 預設 'apa' |
| updated_at | 時間戳記 | |

### `citations`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| report_id | 整數 | FK → reports.id, not null |
| title | 字串 | |
| authors | 字串 | |
| journal | 字串 | 可為空 |
| year | 整數 | |
| snippet | 文字 | 可為空 |
| arxiv_id | 字串 | 可為空 |
| sort_order | 整數 | 對應文中首次出現順序（IEEE 編號依據） |

### `rag_papers`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| project_id | 整數 | FK → projects.id, not null |
| title | 字串 | |
| author | 字串 | 可為空 |
| year | 整數 | 可為空 |
| arxiv_id | 字串 | 可為空 |
| created_at | 時間戳記 | |

### `rag_chunks`

| 欄位 | 型別 | 約束 |
|---|---|---|
| id | 整數 | PK |
| paper_id | 整數 | FK → rag_papers.id, not null |
| content | 文字 | |
| embedding | vector(384) | pgvector；384 維對應現行 `BAAI/bge-small-zh-v1.5` embedding 模型（`backend/docs/rag-paper-generation.md`） |
| chunk_index | 整數 | 段落順序 |

---

## 三、本機環境啟動方式（實作時參考）

### 1. docker-compose 新增 PostgreSQL 服務

現有 `docker-compose.yml` 只有 `backend`、`frontend`、`n8n`，需新增帶 pgvector 擴充套件的 Postgres：

```yaml
  postgres:
    image: pgvector/pgvector:pg16
    container_name: datamind-postgres
    environment:
      POSTGRES_USER: datamind
      POSTGRES_PASSWORD: datamind
      POSTGRES_DB: datamind
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
```

並在 `volumes:` 區塊加上 `postgres_data:`。密碼採明碼本地開發預設值，跟這個檔案裡既有的 `N8N_SECURE_COOKIE=false` 等明碼設定一致，不特別從 `.env` 讀。

### 2. Python 套件

用 `uv add`（不是手動編輯 `pyproject.toml` 或 `pip install`）：

```bash
cd backend
uv add flask-sqlalchemy flask-login alembic psycopg2-binary bcrypt pgvector
```

### 3. 連線字串

`backend/.env`：

```
DATABASE_URL=postgresql://datamind:datamind@postgres:5432/datamind
```

這裡用服務名稱 `postgres` 而不是 `localhost`——因為 `backend` 也是跑在 docker-compose 的容器裡（不是本機直接跑），容器之間要用 docker-compose 內部網路的服務名稱互連，`localhost` 在容器裡指的是容器自己，連不到 Postgres。

### 4. 啟用 pgvector 擴充套件

資料庫建立後執行一次（可寫進第一份 migration）：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. 初始化與執行 migration

```bash
cd backend
alembic init migrations          # 僅第一次
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 6. 建立管理員測試帳號

```bash
python scripts/seed_admin.py
```

腳本邏輯：`users` 表為空時，依環境變數 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 建立一個 `is_admin=true` 的帳號。

### 7. 直接檢視資料庫內容

```bash
docker exec -it datamind-postgres psql -U datamind -d datamind
```

`\dt` 列出所有表；`SELECT * FROM users;` 等指令直接查詢。亦可用 DBeaver、TablePlus 等 GUI 工具，連線資訊同 `.env` 設定。
