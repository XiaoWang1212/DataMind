# DataMind

## 安裝套件

```bash
cd frontend
npm install
```

## 開啟前端 （確認在frontend目錄）

```bash
npm run dev
```

執行後，終端機會顯示本機網址。

## Docker 開發

也可以用 Docker Compose 啟動前後端（含 backend、frontend、n8n）：

```bash
docker compose up -d
```

前端容器的 `node_modules` 是獨立的 volume（`frontend_node_modules`）。容器啟動指令雖然每次都會重跑 `npm install`，但 `docker compose up -d` 對「已經在跑」的容器是 no-op（compose 認為設定沒變就不會動它），所以如果 `frontend/package.json` 有新增/更新依賴（例如這次新增的 `@tiptap/extension-image`），已經在跑的容器不會自動裝到新套件。重建一次即可（對 `docker-compose.yml` 本身有變動時也需要這樣做，才能套用新的啟動指令）：

```bash
docker compose up -d --force-recreate frontend
```
