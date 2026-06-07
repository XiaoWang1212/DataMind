import base64
import logging
import os
import json
import re
from dataclasses import dataclass
from typing import Optional

import google.generativeai as genai

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
請根據論文內容輸出一份 workflow JSON 設定檔。只輸出 JSON，不要 markdown，不要任何說明。

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
            logger.warning("workflow JSON parse failed, trying normalization pass")
            workflow_json = self._normalize_to_json(answer)
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


def truncate_content(text: str, max_chars: int = 18000) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[內容過長，已截斷以避免超出模型上下文限制]"
