# 資料庫架構說明與操作指南

這份文件是白話版的參考手冊，說明「使用者登入制」資料庫要怎麼運作、每張表在做什麼、以後動手實作時大概要怎麼啟動環境。設計決策的理由（為什麼選 PostgreSQL、為什麼 session 不用 JWT、為什麼文獻庫要跟著 project 走）記在正式的設計文件裡：`docs/superpowers/specs/2026-08-01-user-auth-database-design.md`，這份文件不重複講那些，只講「這套架構長什麼樣子、要怎麼把它跑起來」。

> 目前這份資料庫設計**還沒有真的實作**——現在專案裡完全沒有 PostgreSQL、沒有 SQLAlchemy model、沒有 migration 檔案。這份文件是「之後要動手做的時候會長什麼樣子」的參考，不是現在就能照著跑的操作手冊。

---

## 一、架構總覽（白話版）

把整套系統想像成一棵樹，根是「使用者」：

```
一個使用者（users）
 │
 ├─ 有很多「專案」（projects）── 這是核心，其他東西幾乎都掛在專案底下
 │    │
 │    ├─ 一份「上傳的資料集清單」（datasets）── 你丟進去分析的 CSV 檔案記錄
 │    ├─ 一份「工作流程狀態」（workflow_states）── 資料前處理/建模那個流程圖畫到哪、跑出什麼結果
 │    ├─ 一份「論文」（reports）
 │    │    └─ 裡面的「參考文獻清單」（citations）
 │    └─ 一批「探勘來的文獻」（rag_papers）
 │         └─ 每篇文獻切成很多「文字段落＋向量」（rag_chunks）── AI 寫論文時用來檢索引用
 │
 └─ 有很多「分析框架」（frameworks）── 跟專案分開的模板庫，可以在多個專案裡重複使用
```

**核心原則：所有東西最終都能追溯回一個使用者。** 「誰能看到這筆資料」這個問題，答案永遠是「往上找它屬於哪個 project（或直接屬於哪個使用者），再看那個 project/使用者是誰的」。

---

## 二、資料表逐一說明

### `users`——帳號本身

存「誰可以登入系統」。密碼不是明碼存，是用 bcrypt 雜湊過的亂碼，就算資料庫外洩，也還原不出原始密碼。`is_admin` 是給管理員帳號用的旗標。

### `projects`——一個分析專案

你在「儀表板」建立的每一個專案，例如「市場情緒研究」。這是整套系統裡最重要的一張表，因為底下幾乎所有東西（資料集、工作流程、論文、文獻）都是掛在某一個 project 底下的。

### `frameworks`——分析框架庫

跟 project 不一樣，這是「模板」的概念——例如「CNN 圖像分類」這種預先定義好的分析架構，可以在建立新專案時選用。一個使用者可以有自己的一批框架，不同專案可以共用同一個框架。

### `datasets`——上傳檔案的登記簿

**這張表不存檔案本身**，只記錄「這個檔案叫什麼名字、實際放在磁碟哪個路徑、多大、什麼時候上傳的」。真正的 CSV 內容放在後端磁碟的資料夾裡（跟現在 `backend/uploads/` 同一套邏輯）。

### `workflow_states`——工作流程進度存檔

對應現在「工作流程」頁面畫的節點連線圖，以及跑到哪一步、算出什麼結果。這份資料結構本身變化很大（不同分析階段長相不同），所以整包用一個 JSON 欄位存，不特別拆成一堆固定欄位。

### `reports` / `citations`——論文本體與參考文獻

`reports` 存論文的標題、內文（富文本編輯器的資料格式）、要用哪種引用格式（APA/IEEE/MLA）。`citations` 是論文結尾那份參考文獻清單，每一筆是一篇被引用的文獻。

### `rag_papers` / `rag_chunks`——AI 寫論文時查閱的文獻庫

`rag_papers` 記錄「這個專案探勘/收錄了哪些文獻」（標題、作者、年份）。`rag_chunks` 是把每篇文獻切成一小段一小段的文字，每一段都算出一組「向量」（一串數字，代表這段文字的語意），AI 寫論文時就是拿你要寫的主題去跟這些向量做相似度比對，找出最相關的段落來引用。

---

## 三、資料表關聯圖（技術版）

```
users
  ├─< projects
  │     ├─< datasets
  │     ├─1 workflow_states
  │     ├─1 reports ─< citations
  │     └─< rag_papers ─< rag_chunks
  └─< frameworks
```

`─<` 是一對多（一個 project 可以有多個 dataset），`─1` 是一對一（一個 project 對應一份論文）。完整欄位定義（型別、是否可為空、外鍵指到哪）在設計文件的段落 B～I：`docs/superpowers/specs/2026-08-01-user-auth-database-design.md`。

---

## 四、本機環境怎麼啟動（未來實作時的參考）

### 1. 在 docker-compose 加一個 PostgreSQL 服務

現在的 `docker-compose.yml` 只有 `backend`、`frontend`、`n8n`，之後要加一個帶 pgvector 擴充套件的 Postgres：

```yaml
  postgres:
    image: pgvector/pgvector:pg16
    container_name: datamind-postgres
    environment:
      POSTGRES_USER: datamind
      POSTGRES_PASSWORD: <從 .env 讀，不要寫死>
      POSTGRES_DB: datamind
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
```

並在 `volumes:` 區塊加上 `postgres_data:`。

### 2. 安裝 Python 套件

在 `backend/requirements.txt` 加上：

```
flask-sqlalchemy
flask-login
alembic
psycopg2-binary
bcrypt
pgvector
```

### 3. 設定連線字串

`backend/.env` 加一行：

```
DATABASE_URL=postgresql://datamind:<密碼>@localhost:5432/datamind
```

（在 docker-compose 內部服務之間互連時，`localhost` 要改成服務名稱 `postgres`。）

### 4. 啟用 pgvector 擴充套件

資料庫建好、第一次連線後，需要手動執行一次（之後可以寫進第一份 migration 檔案裡）：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. 初始化並執行 migration

```bash
cd backend
alembic init migrations          # 第一次才需要
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 6. 建立管理員測試帳號

```bash
python scripts/seed_admin.py
```

（腳本內容：如果 `users` 表是空的，就依照環境變數 `ADMIN_EMAIL`/`ADMIN_PASSWORD` 建立一個 `is_admin=true` 的帳號。）

### 7. 想直接看資料庫內容

```bash
docker exec -it datamind-postgres psql -U datamind -d datamind
```

進去之後可以下 `\dt` 看有哪些表、`SELECT * FROM users;` 之類的指令直接查資料。也可以用 GUI 工具（例如 DBeaver、TablePlus）連線，連線資訊就是上面 `.env` 裡設定的帳密跟 port。
