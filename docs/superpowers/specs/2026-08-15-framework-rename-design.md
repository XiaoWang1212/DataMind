# 編輯框架名稱 Design Spec

## 背景

框架庫（`FrameworkLibraryView.vue`，路徑 `frontend/src/views/hub/FrameworkLibraryView.vue`）目前只能在建立框架時（`ExtractFrameworkView.vue`，從上傳的論文自動帶出標題）決定框架名稱（`title` 欄位），之後沒有任何管道可以修改。

後端 `backend/routes/framework.py` 目前只有 `GET /api/frameworks`（列表）和 `POST /api/frameworks`（建立），沒有任何單筆查詢或更新的 endpoint。

## 範圍

- 只在框架庫頁面的**詳情面板**（`.detail-panel` / `.panel-title`，`FrameworkLibraryView.vue:64-69`）加上編輯框架名稱的功能，左側卡片列表（`.fw-title`，`FrameworkLibraryView.vue:39`）維持唯讀，但因與詳情面板共用同一份 store 資料，儲存成功後列表會自動同步顯示新名稱。
- 不涉及框架的其他欄位（`subtitle`、`tag`、`description` 等）、不涉及 `ProjectDetailView.vue` 顯示的框架名稱。
- 後端 PATCH endpoint 採「選擇性欄位更新」設計（比照 `backend/routes/project.py` 的 `update_project`），目前只會用到 `title`，但這個設計本身可以直接延伸支援未來新增其他可編輯欄位。

## 設計

### 1. 後端：`backend/routes/framework.py`

新增：

```python
@framework_bp.route("/<int:framework_id>", methods=["GET"])
@login_required
def get_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404
    return jsonify({"success": True, "result": _serialize_framework(framework)})


@framework_bp.route("/<int:framework_id>", methods=["PATCH"])
@login_required
def update_framework(framework_id):
    framework = Framework.query.get(framework_id)
    if not framework or framework.user_id != current_user.id:
        return jsonify({"success": False, "error": "找不到框架"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "需要 JSON body"}), 400

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return jsonify({"success": False, "error": "title 不可為空"}), 400
        framework.title = title

    db.session.commit()
    return jsonify({"success": True, "result": _serialize_framework(framework)})
```

- Ownership 檢查、錯誤回應格式（`{"success": False, "error": ...}`）與現有的 `list_frameworks`/`create_framework` 以及 `project.py` 的對應寫法一致。
- `title` 存入前 `.strip()`，避免存入純空白字串。
- `GET /<id>` 一併補上，理由是 REST 資源的完整性（有 PATCH 沒有 GET 不合理），即使目前前端不會直接呼叫它。

### 2. 前端 API：`frontend/src/api/framework.ts`

新增：

```ts
export interface UpdateFrameworkPatch {
  title?: string
}

export async function updateFramework (id: number, patch: UpdateFrameworkPatch): Promise<FrameworkDTO> {
  const response = await fetch(`/api/frameworks/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(patch),
  })
  const result = await parseFrameworkResponse(response)
  return result.result as FrameworkDTO
}
```

寫法比照 `frontend/src/api/project.ts` 的 `updateProject`。`parseFrameworkResponse` 既有邏輯（`framework.ts:29-35`）已經會把後端 `error` 欄位轉成 `Error(message)` 丟出，呼叫端可以直接拿 `error.message` 顯示。

### 3. 前端 Store：`frontend/src/store/frameworkStore.ts`

新增 `renameFramework`，採樂觀更新 + 失敗回滾，比照 `projectStore.ts` 的 `saveColumnMapping`（`projectStore.ts:150-173`）：

```ts
async function renameFramework (id: number, title: string): Promise<void> {
  const target = frameworks.value.find(f => f.id === id)
  const previousTitle = target?.title
  if (target) {
    target.title = title
  }
  try {
    await updateFramework(id, { title })
  } catch (error) {
    if (target && previousTitle !== undefined) {
      target.title = previousTitle
    }
    console.error('更新框架名稱失敗', error)
    throw error
  }
}
```

並加入 `return` 物件。呼叫端（UI 元件）負責 catch 這個 throw 並顯示錯誤提示，store 本身不處理 UI 層的錯誤訊息。

### 4. UI：`frontend/src/views/hub/FrameworkLibraryView.vue` 詳情面板

`.panel-title`（`FrameworkLibraryView.vue:68`）行為調整：

- 平常顯示為唯讀文字 + 旁邊一個編輯圖示（鉛筆 icon），比照現有圖示風格。
- 點擊圖示 → 該區塊切換成 `<input>`，`autofocus` 並 `select()` 全選現有文字，圖示暫時隱藏。
- **儲存路徑**（Enter 鍵或 input `blur`）：
  1. 若 trim 後新值與原值相同 → 直接退出編輯狀態，不呼叫 API。
  2. 若 trim 後為空字串 → 擋下（不呼叫 API），在 input 旁顯示錯誤文字「名稱不可為空」，**保留編輯狀態**（input 仍存在、仍是 focus），讓使用者可以直接修正重打。
  3. 否則呼叫 `frameworkStore.renameFramework(id, trimmedTitle)`：
     - 成功 → 退出編輯狀態，顯示更新後的唯讀文字（左側卡片列表因共用 store 資料同步更新）。
     - 失敗（catch 到 store 拋出的 error）→ 顯示錯誤文字「儲存失敗,請重試」（沿用同一個錯誤提示區塊），**保留編輯狀態**，input 內容維持使用者剛才輸入的值，方便直接重試而不必重打。
- **取消路徑**（Esc 鍵）：不呼叫 API，input 內容還原成進入編輯前的原始標題，退出編輯狀態。
- 編輯狀態、暫存的原始標題、錯誤訊息用該元件內的區域 `ref` 管理，選取別的框架卡片（`selectedFramework` 改變）時重置編輯狀態。

## 錯誤處理

- 空名稱：前端在呼叫 API 前就擋下（第一道防線），後端 PATCH 對空字串 `title` 回 400（第二道防線，防止前端檢查被繞過或未來有其他呼叫方）。兩種情況使用者看到的都是中文提示文字，不會看到 HTTP 狀態碼本身。
- 非本人或不存在的框架 id：後端回 404，前端這個情境理論上不會觸發（使用者只能對自己看得到、選得到的框架操作），不特別處理成使用者可見的提示，走一般的「儲存失敗,請重試」路徑即可。
- 網路 / 未預期錯誤：store 端 catch 後回滾本地標題並 rethrow，UI 端 catch 後顯示「儲存失敗,請重試」，不回滾 input 內容（維持使用者輸入方便重試）。

## 測試

- **後端**：
  - `PATCH /api/frameworks/<id>` 成功更新 `title`
  - `title` 為空字串或純空白 → 回 400
  - 更新別人擁有的框架 → 回 404
  - 更新不存在的 id → 回 404
- **前端**：
  - `renameFramework` 成功時本地 `frameworks` 陣列與回傳結果一致
  - `renameFramework` API 失敗時，本地標題回滾成呼叫前的值，且 error 會往外拋
- **手動驗證**（前端無 vitest，需人工瀏覽器測試）：
  - 點編輯圖示 → 輸入框出現、自動選取全部文字
  - Enter 儲存成功 → 詳情面板與左側卡片列表標題同步更新
  - 失焦（blur）儲存成功 → 行為與 Enter 一致
  - Esc 取消 → 還原成原本標題,不送出 API 請求
  - 清空後儲存 → 顯示「名稱不可為空」,輸入框保留在編輯狀態
  - 模擬 API 失敗（例如中斷網路）→ 顯示「儲存失敗,請重試」,輸入框保留使用者輸入的內容
