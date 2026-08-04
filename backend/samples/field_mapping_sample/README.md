# 欄位對齊測試素材

一組人造的論文 + 資料集，用來測試/展示欄位對齊功能。刻意設計成**每一條配對路徑都會被走到**，
而且不含任何真實病人資料（`samples/gemini_sample/` 裡的壓瘡資料集是真實去識別化資料，
拿來 demo 前請先確認是否合適）。

## 檔案

| 檔案 | 用途 |
|---|---|
| `demo_paper.pdf` | **從 UI 測試請用這個。** 論文 PDF，由 `demo_paper.md` 轉出 |
| `demo_paper.md` | 同一篇論文的原始 markdown，方便閱讀或修改後重新轉檔 |
| `demo_workflow.json` | 已經寫好的 workflow JSON，跳過 Gemini 分析直接測對齊（免費、結果穩定） |
| `demo_dataset.csv` | 使用者資料集，14 欄、60 筆 |
| `demo_answers.json` | 人工答案卷，給驗證腳本算準確率用 |

**為什麼要有 PDF 版**：後端的 `ALLOWED_EXTENSIONS` 其實收 `txt / md / pdf`，
但前端上傳論文的檔案選擇器寫死 `accept=".pdf"`（`ExtractFrameworkView.vue`），
所以從畫面上只選得到 PDF。要改成三種都能選的話，改那一行 `accept` 即可。

`demo_paper.pdf` 已實測可用：Gemini 正確抽出全部 10 個變數、`target_col=readmission_30d`、
三個模型與 SMOTE 都符合論文內容（唯一小差異是 `admission_date` 被判成 `categorical` 而非 `date`，
不影響配對結果）。

## 資料集的欄位是刻意取名的

| 資料表欄位 | 對應論文變數 | 測什麼 |
|---|---|---|
| `age` | `age` | 完全相同 → 直接自動配對 |
| `col_gender` | `gender` | `col_` 前綴剝除 → 自動配對 |
| `BMI` | `bmi` | 大小寫正規化 → 自動配對 |
| `hba1c_pct` | `hba1c` | 模糊比對 + 數值型態加分 → 自動配對 |
| `bp_sys` | `systolic_blood_pressure` | 名稱看不出來，要靠 AI 語意判斷 |
| `los_days` | `length_of_stay` | 醫療縮寫（LOS），要靠 AI |
| `adm_dt` | `admission_date` | 縮寫 + 日期型態樣本值輔助 |
| `dm_dx` | `diabetes_diagnosis` | 雙重縮寫（DM = 糖尿病、Dx = 診斷） |
| `疼痛分數` | `pain_score` | **跨語言**：英文論文變數對中文欄位 |
| `charlson_comorbidity_idx` | `charlson_index` | 欄位名比論文變數多了描述文字 |
| `readmit_30d` | `readmission_30d` | target 變數（一律強制人工確認） |
| `patient_id` | （無） | 誘餌：不該被配到任何論文變數 |
| `ward` | （無） | 誘餌 |
| `attending_physician` | （無） | 誘餌 |

## 從畫面上手動測（推薦，會走到完整流程）

1. 先萃取框架：Hub → 框架庫 → 萃取框架，上傳 `demo_paper.pdf`
2. 建立專案：Hub → 專案 → 建立新專案，選剛才那個框架，資料集上傳 `demo_dataset.csv`
3. 按「執行分析」→ 會自動導向欄位對齊頁
4. 左邊應該看到 4 個綠勾（`age`、`gender`、`bmi`、`hba1c`）、7 個黃色待確認，沒有紅色未對應
5. 右邊聊天框可以試：「readmit_30d 就是再入院那個變數」、「patient_id 不要用」、
   「為什麼你把 dm_dx 配到 diabetes_diagnosis？」
6. 按「確認並執行」→ 進 workflow 頁，Data Table 面板的欄位名應該已經變成論文的變數名

## 用腳本跑（快、可重複、會算準確率）

```bash
cd backend
uv run python scripts/test_field_mapping.py \
  samples/field_mapping_sample/demo_workflow.json \
  samples/field_mapping_sample/demo_dataset.csv \
  samples/field_mapping_sample/demo_answers.json
```

會實際打 5 次 Gemini API（量測 JSON 輸出穩定度），需要 `backend/.env` 裡的 `GEMINI_API_KEY`。

## 2026-08-03 的基準結果

```
AUTO_MATCHED  4    （age、gender、bmi、hba1c —— 純演算法，沒花到 API）
NEEDS_REVIEW  7    （其餘全部靠 AI 語意配出來，含中文的 疼痛分數）
UNMATCHED     0
Gemini 解析成功率  5/5
自動配對正確率     4/4 = 100%
假陽性            0
```

三個誘餌欄位都正確地沒有被配走。

**如果之後跑出來變差了**，先看解析成功率：不是 5/5 就代表 Gemini 回應被截斷
（思考 token 吃掉 `max_output_tokens`），去看 `field_mapping_prompts.py` 的額度常數。
