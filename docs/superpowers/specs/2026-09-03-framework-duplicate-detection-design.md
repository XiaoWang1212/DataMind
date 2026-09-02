# 框架重複偵測 Design Spec

## 背景

使用者在「從論文提取框架」（`frontend/src/views/hub/ExtractFrameworkView.vue`）上傳 PDF，Gemini 回傳 workflow JSON，按「儲存框架」寫進框架庫。整條路徑沒有任何重複檢查——同一篇論文提取兩次會得到兩筆幾乎相同的框架，而且每次提取都要花一次 Gemini 的 token。框架庫因此會累積難以分辨的重複項目。

### 為什麼不用方法論比對

第一版設計是拿 workflow JSON 的四類清單（模型、前處理、特徵工程、評估指標）正規化後組成「指紋」，完全相同即視為重複。實作後拿資料庫 19 筆真實框架驗證，**兩個方向都不準**：

**漏判**——同一篇論文提取多次，指紋常常不同：

| 論文 | 提取次數 | 不同指紋數 |
|---|---|---|
| demo_paper | 2 | 1 |
| CIN_published | 3 | **3** |
| IJMI_published | 6 | **3** |
| Dexamethasone… | 4 | **2** |

差異集中在「論文沒明講、模型自行推斷」的項目：`one_hot` 有無反覆翻面、`specificity` 時有時無、特徵工程從 `select_relevant_features` 變成 `discretize_continuous`。`gemini_service.py` 已設 `temperature=0`，但服務端批次推論的浮點誤差會讓機率接近的候選翻盤，這支呼叫又開了動態 thinking budget；更根本的是 prompt 的填寫原則沒有界定要不要納入論文隱含但未明說的步驟。

**誤判**——不同論文指紋反而相同：

| 指紋相同的一組 | 實際 |
|---|---|
| id 2、12（demo_paper）+ id 3（hard_paper） | 兩篇不同論文 |
| id 13、16（Dexamethasone…）+ id 18、19（A Randomized Trial…） | 兩篇不同論文 |

原因是 prompt 有預設值（「preprocessing 未提及則用 fill_na+standardize」「featureEngineering 未提及則用 select_relevant_features」「metrics 至少含 balanced_accuracy 和 auc」）。臨床試驗類論文很少描述 ML 前處理細節，不同論文一起塌到同一組預設值上。

結論：**四類方法論不足以識別論文身分**，臨床論文的 ML 方法論本來就大同小異。這不是門檻鬆緊的問題，換成相似度也救不了誤判。因此改用 PDF 檔案本身作為判定依據。

## 範圍

- 前端：選檔後在瀏覽器算 PDF 的 SHA-256，**提取前**就比對，命中即提示，省下一次 Gemini 呼叫
- 後端：`frameworks` 新增 `pdf_hash` 欄位（含 migration），比對 endpoint 依 hash → 檔名兩層查
- 儲存框架時把 hash 一起寫入
- **不**做方法論指紋比對（見〈為什麼不用方法論比對〉）
- **不**在 `POST /api/frameworks` 阻擋重複——只提示，建立行為不變
- **不**提供跳到既有框架的連結（見〈為什麼只提示、不給連結〉）

## 判定規則

兩層，依序查，命中即回：

| 層 | 依據 | `matchType` | 性質 |
|---|---|---|---|
| 1 | PDF 內容的 SHA-256 | `"hash"` | 零誤判：同一份檔案必定相同，不同檔案必定不同 |
| 2 | 檔名（`title` 或 `paper_title`） | `"title"` | 補 hash 抓不到的情況 |

### 第一層：檔案 hash

對 PDF 的完整位元組算 SHA-256，輸出小寫十六進位字串（64 字元）。在**瀏覽器**用 Web Crypto 計算：

```ts
const buffer = await file.arrayBuffer()
const digest = await crypto.subtle.digest('SHA-256', buffer)
```

在前端算的理由：不必先把 PDF 上傳到後端就能判定，重複的情況下連檔案傳輸都省掉。

### 第二層：檔名

hash 沒命中才查。取去掉副檔名的檔名，正規化（trim → 小寫 → 移除空白／底線／連字號）後，比對框架的 `title` 與 `paper_title`。兩個都比是因為 `title` 可能被使用者在框架庫改名，`paper_title` 不會被改名功能動到。

這一層存在的理由有兩個：**舊框架沒有 hash**（無法回填，原始 PDF 沒有留存），以及**同一篇論文的不同檔案**（重新下載、換排版）hash 會不同。誤判風險低——檔名完全相同的兩份 PDF 基本上就是同一篇論文。

## 為什麼 hash 存成欄位

跟方法論指紋不同，hash **無法從既有資料算出來**——`workflow_json` 裡沒有原始 PDF。所以必須在儲存框架時一併寫進資料庫，需要新欄位與 migration。

欄位可為 null：本次改動之前建立的框架都沒有 hash，且無法回填。比對時 `pdf_hash IS NULL` 的框架直接跳過第一層，仍可被第二層的檔名比對命中。

不加唯一索引——重複只提示不阻擋，資料庫層強制唯一會與這個決定衝突。加一般索引供查詢用。

## 為什麼只提示、不給連結

提取結果只存在元件 state，一旦導航到框架庫就消失，而那份結果是花 token 換來的。因此不提供跳轉連結，只顯示提示文字（含框架標題），使用者留在提取頁自行判斷。這也讓框架庫不需要任何改動。

## 元件改動

### 1. `backend/migrations/versions/<rev>_add_pdf_hash_to_frameworks.py`（新增）

```python
down_revision = '4b1d1134b860'   # 目前的 head

def upgrade():
    op.add_column('frameworks', sa.Column('pdf_hash', sa.String(length=64), nullable=True))
    op.create_index('ix_frameworks_pdf_hash', 'frameworks', ['pdf_hash'])

def downgrade():
    op.drop_index('ix_frameworks_pdf_hash', table_name='frameworks')
    op.drop_column('frameworks', 'pdf_hash')
```

### 2. `backend/models/framework.py`

```python
pdf_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
```

### 3. `backend/services/framework_dedupe.py`（新增）

```python
def normalize_title(value) -> str    # trim → 小寫 → 移除空白/底線/連字號
def normalize_hash(value) -> str     # trim → 小寫；非 64 字元十六進位則回傳空字串
```

`normalize_hash` 的長度與字元檢查是為了讓格式不對的輸入落成空字串，由呼叫端當作「沒有 hash」處理，而不是拿垃圾值去比對。

### 4. `backend/routes/framework.py`

**`POST /api/frameworks/check-duplicate`**（`@login_required`）

- Request：`{ "pdfHash": "<64 hex>", "title": "IJMI_published" }`，兩個欄位都可省略
- 先用 `pdfHash` 查（跳過 `pdf_hash` 為 null 的框架），沒命中再用 `title` 查
- Response：`{ "success": true, "result": { "id": 7, "title": "…", "matchType": "hash" } }`；沒命中時 `result` 為 `null`
- 兩個欄位都空或都正規化成空字串 → 直接回 `result: null`
- 掃描依 `created_at desc`，回傳第一個命中的

路由不會與 `/<int:framework_id>` 衝突，因為後者有 `int` 轉換器限制。

**`POST /api/frameworks`**：多讀一個 `pdfHash`，經 `normalize_hash()` 後存進 `pdf_hash`（空字串存 null）。

`_serialize_framework()` **不**回傳 `pdf_hash`——前端沒有任何地方需要它，回傳只是徒增傳輸量。

### 5. `frontend/src/utils/pdfHash.ts`（新增）

```ts
export async function computePdfHash (file: File): Promise<string | null>
```

用 Web Crypto 算 SHA-256 並轉成小寫十六進位。`crypto.subtle` 在非安全情境（用區網 IP 以 http 存取）不存在，此時回傳 `null`，呼叫端退回只用檔名比對。

### 6. `frontend/src/api/framework.ts`

```ts
export type DuplicateMatchType = 'hash' | 'title'
export interface DuplicateFramework {
  id: number
  title: string
  matchType: DuplicateMatchType
}
export async function checkFrameworkDuplicate (
  params: { pdfHash?: string | null, title?: string },
): Promise<DuplicateFramework | null>
```

`CreateFrameworkPayload` 增加 `pdfHash?: string | null`。沿用既有的 `parseFrameworkResponse()` 錯誤處理。

### 7. `frontend/src/views/hub/ExtractFrameworkView.vue`

**選檔時**（`onFileChange`）：算 hash 存進 `pdfHash`，連同檔名呼叫 `checkFrameworkDuplicate()`，命中就把結果存進 `duplicateFramework`。放在選檔而非按下「開始提取」時，是因為此時已具備判定所需的全部資訊，愈早提示愈能避免使用者白等一次提取。

命中時上傳面板顯示提示列，文字依 `matchType` 分兩種：

- `hash` → 「這份檔案已經提取過，框架庫中的《X》」
- `title` → 「框架庫已有同名的《X》」

提示列右側是「仍要提取」按鈕；按下去清掉提示並直接進提取流程。沒有命中時顯示原本的「開始提取」按鈕。

**這次比對的失敗不可影響主流程**——查詢掛掉或 `crypto.subtle` 不可用就當作沒有重複，錯誤記 console，不寫進 `extractError`。

**儲存時**：`saveFramework()` 把 `pdfHash` 一併送出。

`duplicateFramework` 與 `pdfHash` 在換檔案與儲存完成後重置。

樣式沿用本次已完成的 `.notice`：次級底 `--color-surface-alt`、hairline `--color-border`、文字 `--color-ink-soft`、`--radius-sm`、圖示 `mdi-information-outline`。**不用 warning 的琥珀**——DESIGN_SYSTEM §7.5 規定狀態色語意固定且不可做非狀態的裝飾，而「已經有這個框架了」是資訊而非警示。

### 8. 移除

- `backend/services/framework_signature.py` 整個刪除
- `ExtractFrameworkView.vue` 提取完成後的第二次比對移除
- `checkDuplicateByWorkflow()` 移除

## 錯誤處理

| 情況 | 行為 |
|---|---|
| `crypto.subtle` 不可用（非安全情境） | `computePdfHash()` 回傳 null，只用檔名比對 |
| hash 計算擲出例外（檔案讀取失敗） | 同上，錯誤記 console |
| `check-duplicate` 請求失敗 | 不顯示提示，照常可提取，錯誤記 console |
| 舊框架 `pdf_hash` 為 null | 第一層跳過該筆，仍可能被第二層檔名命中 |
| 送進來的 `pdfHash` 格式不對 | `normalize_hash()` 回空字串，視為沒有 hash |
| 使用者未登入 | endpoint 有 `@login_required` 回 401，前端當作查詢失敗 |

## 測試

專案沒有自動化測試框架，這次也不引入。驗證方式：

- `normalize_hash()`：大小寫收斂、長度或字元不對回空字串
- `normalize_title()`：`IJMI published` 與 `IJMI_published` 收斂為同一個 token；`None` 回空字串
- 前端 `vue-tsc` 型別檢查與 eslint
- migration：`alembic upgrade head` 後確認欄位與索引存在，`downgrade` 可回滾
- 手動：同一份 PDF 存過後再選同一個檔案，選檔當下就出現 hash 提示且完全不呼叫 Gemini；把該檔案改名後再選，應改為出現檔名提示；換一份不同的 PDF 不應出現提示；按「仍要提取」能正常走完提取與儲存，且新框架的 `pdf_hash` 有寫入

## 已知限制

- 本次改動之前建立的框架沒有 hash，且無法回填（原始 PDF 未留存），只能靠檔名比對到
- 同一篇論文的不同檔案（重新下載、不同排版）hash 不同，只能靠檔名兜；兩者檔名也不同時就抓不到
- 提取結果本身的不穩定性沒有處理——收緊 prompt 的納入標準是獨立的題目，不在本 spec 範圍
