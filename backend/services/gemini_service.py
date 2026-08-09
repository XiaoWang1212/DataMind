import base64
import logging
import os
import json
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai
from google import genai as genai_client
from google.genai import types as genai_types

from services.field_mapping_prompts import (
    CHAT_REFINE_SCHEMA,
    FIELD_MAPPING_SYSTEM_INSTRUCTION,
    MAX_CHAT_ACTIONS,
    SEMANTIC_MATCH_SCHEMA,
    build_chat_refine_prompt,
    build_semantic_match_prompt,
)

logger = logging.getLogger(__name__)

_AVAILABLE_MODELS = (
    "Logistic Regression, Logistic Regression CV, Ridge Classifier, Ridge Classifier CV, "
    "Linear Discriminant Analysis, Quadratic Discriminant Analysis, SGD Classifier, "
    "Passive Aggressive, SVM, Linear SVC, Nu-SVC, K-Nearest Neighbors, Radius Neighbors, "
    "Decision Tree, Bagging, Random Forest, Extra Trees, Gradient Boosting, "
    "HistGradient Boosting, AdaBoost, Voting Classifier, Stacking Classifier, "
    "MLP, Gaussian NB, Multinomial NB, Complement NB, Bernoulli NB, "
    "Gaussian Process, Calibrated Classifier, XGBoost, LightGBM, CatBoost, "
    "Balanced Random Forest, Easy Ensemble"
)

_WORKFLOW_EXAMPLE = """{
  "target_col": "pressure_injury",
  "models": [
    {"name": "Logistic Regression", "type": "Classification", "purpose_zh": "建立基線分類模型"},
    {"name": "Random Forest", "type": "Classification", "purpose_zh": "集成方法提升準確率"},
    {"name": "XGBoost", "type": "Classification", "purpose_zh": "梯度提升處理非線性關係"}
  ],
  "preprocessing": [
    {"type": "fill_na", "strategy": "mean"},
    {"type": "standardize"}
  ],
  "featureEngineering": [
    {"type": "select_relevant_features", "k": 10}
  ],
  "validation": {
    "method": "k_fold",
    "n_splits": 10,
    "stratified": true,
    "train_size": 0.8
  },
  "metrics": ["balanced_accuracy", "auc", "auprc", "mcc", "f1", "recall", "specificity"],
  "resampling": {
    "method": "smote",
    "config": {"k_neighbors": 5}
  },
  "tuning": {
    "method": "random",
    "cv": 3,
    "n_iter": 20,
    "scoring": "roc_auc"
  },
  "compute_ci": true,
  "features": [
    {"name": "age", "type": "numerical", "description_zh": "病患年齡"},
    {"name": "gender", "type": "categorical", "description_zh": "性別"},
    {"name": "braden_score", "type": "numerical", "description_zh": "布雷登量表分數"}
  ]
}"""

_WORKFLOW_SYSTEM_PROMPT = f"""你是醫學研究自動化 ML workflow 設計助手。
請根據論文內容輸出一份 workflow JSON 設定檔。輸出格式為純 JSON 物件，不得包含任何 markdown、程式碼區塊、說明文字或其他非 JSON 內容。

【重要】輸出必須包含以下所有 key，一個都不能少：
target_col, models, preprocessing, featureEngineering, validation, metrics, resampling, tuning, compute_ci, features

論文有提到某個設定 → 依論文填入。
論文沒提到 → 使用下方完整範例的預設值，不可省略任何 key。

可用模型名稱（必須完全符合，不可縮寫）：
{_AVAILABLE_MODELS}

可用 preprocessing type：fill_na, knn_impute, iterative_impute, standardize, normalize, one_hot, label_encode, drop_columns, remove_outliers_iqr, remove_outliers_zscore
可用 featureEngineering type：select_relevant_features, pca, discretize_continuous, continuize_discrete, normalize_features, remove_sparse_features
可用 validation method：k_fold, test_on_test, group_k_fold, random_sampling, leave_one_out
可用 metrics：accuracy, balanced_accuracy, precision, recall, specificity, f1, mcc, kappa, auc, auprc
可用 resampling method：none, smote, adasyn, borderline_smote, random_oversample, random_undersample, smoteenn, smotetomek
可用 tuning method：none, grid, random

【完整輸出範例（當論文資訊不足時，以此為預設）】
{_WORKFLOW_EXAMPLE}

填寫原則：
- models：依論文列出的模型，name 必須完全符合可用模型名稱清單
- preprocessing：依論文資料處理方式，若未提及則用 fill_na+standardize
- featureEngineering：依論文特徵選擇方式，若未提及則用 select_relevant_features k=10
- validation：依論文驗證方式，若未提及則用 k_fold n_splits=10
- metrics：依論文評估指標，至少包含 balanced_accuracy 和 auc
- resampling：論文有提類別不平衡處理 → 填對應 method；否則填 none
- tuning：論文有提超參數搜尋 → 填 grid 或 random；否則填 none
- compute_ci：論文有報告信賴區間或 bootstrap → true；否則 false
- features：論文提到的輸入特徵，每個一筆"""


@dataclass
class AnalysisInput:
    title: str
    content: str
    focus: Optional[str] = None
    language: str = "zh-TW"


class GeminiService:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required.")

        genai.configure(api_key=api_key)
        self.requested_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model_name = self.requested_model
        self.model = genai.GenerativeModel(model_name=self.model_name)

    def _build_prompt(self, analysis_input: AnalysisInput) -> str:
        focus_clause = f"\n特別關注：{analysis_input.focus}" if analysis_input.focus else ""
        return (
            f"{_WORKFLOW_SYSTEM_PROMPT}"
            f"{focus_clause}\n"
            f"論文標題：{analysis_input.title}\n"
            "--- 論文內容開始 ---\n"
            f"{analysis_input.content}\n"
            "--- 論文內容結束 ---"
        )

    def _safe_parse_json(self, text: str) -> Optional[dict]:
        raw = text.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        fenced = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
        fenced = re.sub(r"\s*```$", "", fenced)
        try:
            return json.loads(fenced.strip())
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", fenced)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _normalize_to_json(self, raw_text: str) -> Optional[dict]:
        normalize_prompt = (
            "請把下面內容轉為『合法 JSON』，只輸出 JSON 本體，不要 markdown、不要任何說明。\n"
            "規則：\n"
            "1. 若某個陣列欄位無法確認內容，請用空陣列 [] 代替，絕不使用 unknown 或任何猜測值。\n"
            "2. 必須包含以下所有 key（缺少者補預設值）：\n"
            "   target_col（string）, models（array）, preprocessing（array）, "
            "featureEngineering（array）, features（array）,\n"
            "   validation（object）, metrics（array）, resampling（object）, "
            "tuning（object）, compute_ci（boolean）\n"
            "3. preprocessing 的 type 只能是：fill_na, knn_impute, iterative_impute, "
            "standardize, normalize, one_hot, label_encode, drop_columns, "
            "remove_outliers_iqr, remove_outliers_zscore\n"
            "4. featureEngineering 的 type 只能是：select_relevant_features, pca, "
            "discretize_continuous, continuize_discrete, normalize_features, "
            "remove_sparse_features\n"
            "   若原始內容有不合法的 type，請從陣列中移除該筆，不要替換成 unknown。\n\n"
            "--- 原始內容開始 ---\n"
            f"{raw_text}\n"
            "--- 原始內容結束 ---"
        )
        response = self.model.generate_content(
            normalize_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=4096,
            ),
        )
        return self._safe_parse_json(getattr(response, "text", "") or "")

    def _generation_config(self) -> genai.GenerationConfig:
        return genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
        )

    @staticmethod
    def _fill_defaults(workflow_json: Optional[dict]) -> dict:
        """Merge AI output with required execution defaults.

        preprocessing and featureEngineering are intentionally NOT defaulted:
        if the AI didn't find them in the paper, no nodes are created in the
        frontend canvas. Only execution-control fields get defaults so the
        backend always has valid params to run.
        """
        defaults: dict = {
            "target_col": None,
            "models": [],
            "preprocessing": [],       # no node if paper didn't mention it
            "featureEngineering": [],  # no node if paper didn't mention it
            "features": [],
            # Always needed for execution — safe defaults
            "validation": {
                "method": "k_fold",
                "n_splits": 10,
                "stratified": True,
                "train_size": 0.8,
            },
            "metrics": ["balanced_accuracy", "auc", "auprc", "mcc", "f1"],
            "resampling": {"method": "none", "config": {}},
            "tuning": {
                "method": "none",
                "cv": 3,
                "n_iter": 20,
                "scoring": "roc_auc",
            },
            "compute_ci": False,
        }
        if not workflow_json:
            return defaults
        merged = {**defaults, **workflow_json}
        return merged

    def _parse_response(self, response) -> tuple[Optional[dict], Optional[str], Optional[object]]:
        answer = getattr(response, "text", "") or ""
        workflow_json = self._safe_parse_json(answer)
        if workflow_json is None and answer.strip():
            logger.warning(
                "workflow JSON parse failed (first pass), trying normalization.\n"
                "Raw response (first 500 chars): %s",
                answer[:500],
            )
            workflow_json = self._normalize_to_json(answer)
            if workflow_json is not None:
                logger.info("normalization pass succeeded")
            else:
                logger.error("normalization pass also failed — using defaults")
        raw = answer.strip() if workflow_json is None else None
        usage = getattr(response, "usage_metadata", None)
        return workflow_json, raw, usage

    def _usage_dict(self, usage) -> dict:
        if usage is None:
            return {"prompt_tokens": None, "completion_tokens": None, "total_tokens": None}
        return {
            "prompt_tokens": getattr(usage, "prompt_token_count", None),
            "completion_tokens": getattr(usage, "candidates_token_count", None),
            "total_tokens": getattr(usage, "total_token_count", None),
        }

    # ── Text input ──────────────────────────────────────────────────────────

    def analyze(self, analysis_input: AnalysisInput) -> dict:
        """Generate workflow JSON from plain text (paper content as string)."""
        prompt = self._build_prompt(analysis_input)
        response = self.model.generate_content(prompt, generation_config=self._generation_config())
        workflow_json, raw, usage = self._parse_response(response)
        return {
            "provider": "gemini",
            "model": self.model_name,
            "workflow_json": self._fill_defaults(workflow_json),
            "raw": raw,
            "usage": self._usage_dict(usage),
        }

    # ── PDF input (native Gemini understanding) ─────────────────────────────

    def analyze_pdf(
        self,
        pdf_bytes: bytes,
        title: str = "",
        focus: Optional[str] = None,
    ) -> dict:
        """Generate workflow JSON by passing the PDF directly to Gemini.

        Gemini 2.5 can natively understand PDF structure (tables, figures, etc.),
        which gives much better results than text extraction.
        """
        focus_clause = f"\n特別關注：{focus}" if focus else ""
        prompt = (
            f"{_WORKFLOW_SYSTEM_PROMPT}"
            f"{focus_clause}\n"
            f"論文標題：{title or '（見上傳 PDF）'}\n"
            "請根據上傳的 PDF 論文內容生成 workflow JSON。"
        )

        pdf_part = {
            "inline_data": {
                "mime_type": "application/pdf",
                "data": base64.b64encode(pdf_bytes).decode("utf-8"),
            }
        }

        response = self.model.generate_content(
            [prompt, pdf_part],
            generation_config=self._generation_config(),
        )
        workflow_json, raw, usage = self._parse_response(response)
        return {
            "provider": "gemini",
            "model": self.model_name,
            "workflow_json": self._fill_defaults(workflow_json),
            "raw": raw,
            "usage": self._usage_dict(usage),
        }

    # ── Field mapping（欄位對齊）─────────────────────────────────────────────
    #
    # 以下方法與上面的論文分析完全獨立：另建 model 實例、另一組 generation
    # config，不共用 self.model 也不共用 _generation_config()。

    # 聊天路徑不接受 AUTO_MATCHED：SEMANTIC_SCORE_CAP 只擋得住 /init，
    # 這裡若放行，使用者打一句話就能讓某列（含 target）直接變綠而沒人確認過
    _CHAT_STATUSES = {"NEEDS_REVIEW", "UNMATCHED"}

    # Gemini 2.5 系列會消耗「thinking」token，這些 token 一樣算進
    # max_output_tokens，卻不會出現在可見輸出（response.text）裡。實測規模
    # （22 個論文變數 × 55 個資料集欄位）光 thinking 就吃掉 3700+ tokens，
    # 把可見 JSON 從中間截斷、變成無法解析。這兩個上限刻意留了很大餘裕，
    # 之後不要因為「看起來很大」就把它們調小。
    _SEMANTIC_MATCH_MAX_OUTPUT_TOKENS = 16384
    _CHAT_REFINE_MAX_OUTPUT_TOKENS = 8192

    def _field_mapping_model(self) -> genai.GenerativeModel:
        """欄位對齊專用的 model 實例。

        每次呼叫都重新建構：GenerativeModel 只是本地物件，不會發出網路請求，
        這樣就不必動到 __init__（既有論文分析邏輯必須零修改）。
        """
        return genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=FIELD_MAPPING_SYSTEM_INSTRUCTION,
        )

    @staticmethod
    def _field_mapping_config(schema: dict, max_output_tokens: int) -> genai.GenerationConfig:
        """配對是判斷題，temperature 設 0；格式交給 response_schema 強制。"""
        return genai.GenerationConfig(
            temperature=0,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )

    @staticmethod
    def _valid_score(value) -> Optional[float]:
        """信心度必須是 0~1 的數值，否則視為無效。

        bool 是 int 的子類別，得先擋掉，不然 True 會被當成 1.0。
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        score = float(value)
        if score < 0.0 or score > 1.0:
            return None
        return score

    @staticmethod
    def _sanitize_columns(values, allowed: set, limit: int) -> list:
        """只保留白名單內、且不重複的欄位名，最多 limit 個。"""
        result: list = []
        for value in values or []:
            if isinstance(value, str) and value in allowed and value not in result:
                result.append(value)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _log_if_truncated(response, caller: str) -> None:
        """回應被 max_output_tokens 截斷時記一筆，方便排查。

        截斷的 JSON 跟「模型亂回」在下游長得一模一樣，沒這個 log 分不出來。
        全程 getattr 是因為測試的 fake response 只有 .text，診斷邏輯不能反過來弄壞呼叫。
        """
        try:
            candidates = getattr(response, "candidates", None) or []
            first = candidates[0] if candidates else None
            finish_reason = getattr(first, "finish_reason", None)
            is_max_tokens = finish_reason == 2 or str(finish_reason).endswith("MAX_TOKENS")
            if not is_max_tokens:
                return
            usage = getattr(response, "usage_metadata", None)
            logger.error(
                "%s：Gemini 回應因達到 max_output_tokens 上限而截斷"
                "（thinking token 也計入此額度），請調高上限。"
                "usage_metadata: prompt_tokens=%s, candidates_tokens=%s, total_tokens=%s",
                caller,
                getattr(usage, "prompt_token_count", None),
                getattr(usage, "candidates_token_count", None),
                getattr(usage, "total_token_count", None),
            )
        except Exception:
            logger.debug("%s：檢查 finish_reason 時發生例外，略過診斷 log", caller)

    def semantic_match(self, items: list, user_columns: list) -> Optional[list]:
        """對演算法配不出來的項目做語意配對建議。

        回傳 [] 代表「AI 可用但沒有有效建議」，回傳 None 代表「AI 不可用」——
        路由層靠這個區別決定要不要在前端顯示「AI 建議暫時無法使用」。
        """
        if not items:
            return []

        prompt = build_semantic_match_prompt(items, user_columns)
        try:
            response = self._field_mapping_model().generate_content(
                prompt,
                generation_config=self._field_mapping_config(
                    SEMANTIC_MATCH_SCHEMA, self._SEMANTIC_MATCH_MAX_OUTPUT_TOKENS
                ),
            )
        except Exception:
            logger.exception("semantic_match 呼叫 Gemini 失敗")
            return None

        self._log_if_truncated(response, "semantic_match")
        parsed = self._safe_parse_json(getattr(response, "text", "") or "")
        if not isinstance(parsed, dict):
            logger.warning("semantic_match 回應無法解析為 JSON 物件")
            return None

        allowed_columns = {column["name"] for column in user_columns}
        allowed_variables = {item["paper_variable"] for item in items}

        results = []
        for entry in parsed.get("matches") or []:
            if not isinstance(entry, dict):
                continue
            variable = entry.get("paper_variable")
            if variable not in allowed_variables:
                continue
            score = self._valid_score(entry.get("confidence_score"))
            if score is None:
                continue
            column = entry.get("matched_user_column")
            if column not in allowed_columns:
                column = None  # 掰出來的欄位名 → 當作沒配到，其餘欄位照收
            results.append({
                "paper_variable": variable,
                "matched_user_column": column,
                "confidence_score": score,
                "candidate_columns": self._sanitize_columns(
                    entry.get("candidate_columns"), allowed_columns, 3
                ),
            })
        return results

    def chat_refine(
        self,
        current_mapping_state: dict,
        user_message: str,
        chat_history: list,
    ) -> dict:
        """依使用者的自然語言指令，產出這一輪的對映變更 diff。

        current_mapping_state 形狀：
          {"mapping_status": [...], "user_columns": [{"name", "sample_values"}]}

        永遠回傳可用的結果，不拋例外 —— 聊天壞掉時使用者還有下拉選單可用，
        不該讓整頁跟著掛掉。
        """
        mapping_status = current_mapping_state.get("mapping_status") or []
        user_columns = current_mapping_state.get("user_columns") or []

        try:
            prompt = build_chat_refine_prompt(
                mapping_status, user_columns, chat_history, user_message
            )
            response = self._field_mapping_model().generate_content(
                prompt,
                generation_config=self._field_mapping_config(
                    CHAT_REFINE_SCHEMA, self._CHAT_REFINE_MAX_OUTPUT_TOKENS
                ),
            )
        except Exception:
            logger.exception("chat_refine 呼叫 Gemini 失敗")
            return {
                "actions": [],
                "reply": "AI 目前無法回應，請改用下拉選單手動對應。",
            }

        self._log_if_truncated(response, "chat_refine")
        parsed = self._safe_parse_json(getattr(response, "text", "") or "")
        if not isinstance(parsed, dict):
            logger.warning("chat_refine 回應無法解析為 JSON 物件")
            return {
                "actions": [],
                "reply": "AI 的回覆格式無法解析，請換個說法再試一次，或改用下拉選單。",
            }

        raw_actions = parsed.get("actions") or []
        if len(raw_actions) > MAX_CHAT_ACTIONS:
            # 一次要改這麼多筆，多半是模型誤解了指令範圍。整批拒絕比部分套用安全。
            return {
                "actions": [],
                "reply": (
                    f"這個要求會一次更動 {len(raw_actions)} 個欄位，超出單次修改上限，"
                    "已暫停套用。請說得更具體一點，例如指名要改哪一個變數。"
                ),
            }

        allowed_columns = {
            column.get("name") for column in user_columns if isinstance(column, dict)
        }
        allowed_variables = {
            item.get("paper_variable") for item in mapping_status if isinstance(item, dict)
        }

        actions = []
        for entry in raw_actions:
            if not isinstance(entry, dict):
                continue
            variable = entry.get("paper_variable")
            if variable not in allowed_variables:
                continue
            column = entry.get("matched_user_column")
            if column is not None and column not in allowed_columns:
                continue  # 欄位不存在 → 整筆丟棄，不猜使用者想要哪一欄
            status = entry.get("status")
            if status not in self._CHAT_STATUSES:
                continue
            score = self._valid_score(entry.get("confidence_score"))
            if score is None:
                continue
            actions.append({
                "paper_variable": variable,
                "matched_user_column": column,
                "status": status,
                "confidence_score": score,
            })

        reply = parsed.get("reply")
        if not isinstance(reply, str) or not reply.strip():
            reply = "已更新對映，請確認左側表格。"
        return {"actions": actions, "reply": reply}

    def analyze_pdf_stream(self, pdf_bytes: bytes, title: str = ""):
        """Stream Gemini's thinking process while analyzing a PDF, then the final result.

        Yields dicts of one of three shapes:
        - {"type": "thought", "text": str} — one per thinking chunk
        - {"type": "result", "data": {...same shape as analyze_pdf()'s return value...}}
        - {"type": "error", "message": str}
        """
        prompt = (
            f"{_WORKFLOW_SYSTEM_PROMPT}\n"
            f"論文標題：{title or '（見上傳 PDF）'}\n"
            "請根據上傳的 PDF 論文內容生成 workflow JSON。"
        )

        try:
            client = genai_client.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
            pdf_part = genai_types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")

            stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=[prompt, pdf_part],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    thinking_config=genai_types.ThinkingConfig(
                        include_thoughts=True,
                        thinking_budget=-1,
                    ),
                ),
            )

            answer_parts: list[str] = []
            last_chunk = None
            for chunk in stream:
                last_chunk = chunk
                if not chunk.candidates:
                    continue
                content = chunk.candidates[0].content
                if content is None or not content.parts:
                    continue
                for part in content.parts:
                    text = getattr(part, "text", None)
                    if not text:
                        continue
                    if getattr(part, "thought", False):
                        yield {"type": "thought", "text": text}
                    else:
                        answer_parts.append(text)

            answer = "".join(answer_parts)
            workflow_json = self._safe_parse_json(answer)
            raw = None
            if workflow_json is None and answer.strip():
                workflow_json = self._normalize_to_json(answer)
            if workflow_json is None:
                raw = answer.strip()

            usage = getattr(last_chunk, "usage_metadata", None) if last_chunk is not None else None
            yield {
                "type": "result",
                "data": {
                    "provider": "gemini",
                    "model": self.model_name,
                    "workflow_json": self._fill_defaults(workflow_json),
                    "raw": raw,
                    "usage": self._usage_dict(usage),
                },
            }
        except Exception as exc:
            logger.exception("analyze_pdf_stream failed")
            yield {"type": "error", "message": str(exc)}


def truncate_content(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[內容過長，已截斷以避免超出模型上下文限制]"
