"""
RAG 論文生成系統測試腳本

用法（docker-compose 要先啟動，需要 GEMINI_API_KEY）：
    MSYS_NO_PATHCONV=1 docker exec -w /app datamind-backend /app/.venv/bin/python scripts/test_paper_gen.py

測試流程：
  1. 借用資料庫裡第一個既有的 user 建立一個測試用 project
  2. 用虛擬論文文字建立論文庫（不需要上傳真實 PDF）
  3. 用 DataMind 格式的模擬輸出呼叫 generate_paper()
  4. 將結果輸出至 artifacts/test_output/，跑完清理測試用的 project

如果資料庫完全沒有 user，先跑過 backend/scripts/seed_admin.py 建一個。
若要使用真實 Flask server 測試 HTTP 端點，可改用 curl 範例（檔案末尾）。
"""

import json
import os
import sys
from pathlib import Path

# ── 設定 PYTHONPATH，讓 script 可 import 後端模組 ──────────────────────────
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# 載入 .env
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    # dotenv 非必要，手動設定也可
    env_file = BACKEND_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

# ── 模擬的 DataMind 輸出（對應 /api/models/workflow/execute 回傳格式）──────
MOCK_DATAMIND_OUTPUT = {
    "success": True,
    "class_distribution": {
        "counts": {"0": 9820, "1": 2180},
        "imbalance_ratio": 4.5046
    },
    "preprocess_variants": [
        {
            "preprocess_steps": [
                {"type": "fill_na", "strategy": "mean"},
                {"type": "standardize"}
            ],
            "feature_engineering_steps": [
                {"type": "select_relevant_features", "k": 20}
            ]
        }
    ],
    "results": [
        {
            "preprocess_pipeline_index": 0,
            "model_name": "Decision Tree",
            "split_name": "split_0",
            "validation_config": {
                "method": "train_test_split",
                "n_splits": 1,
                "stratified": True,
                "train_size": 0.8,
                "test_size": 0.2,
                "shuffle": True,
                "random_state": 42
            },
            "resampling_method": "none",
            "best_params": {},
            "metrics": [
                {"id": "s0", "metric": "balanced_accuracy", "value": 0.5510, "ci_lower": None, "ci_upper": None},
                {"id": "s1", "metric": "auc",               "value": 0.5510, "ci_lower": None, "ci_upper": None},
                {"id": "s2", "metric": "precision",         "value": 0.0505, "ci_lower": None, "ci_upper": None},
                {"id": "s3", "metric": "recall",            "value": 0.1375, "ci_lower": None, "ci_upper": None},
                {"id": "s4", "metric": "specificity",       "value": 0.9645, "ci_lower": None, "ci_upper": None},
                {"id": "s5", "metric": "f1",                "value": 0.0738, "ci_lower": None, "ci_upper": None},
            ],
        },
        {
            "preprocess_pipeline_index": 0,
            "model_name": "Logistic Regression",
            "split_name": "split_0",
            "validation_config": {
                "method": "train_test_split",
                "n_splits": 1,
                "stratified": True,
                "train_size": 0.8,
                "test_size": 0.2,
                "shuffle": True,
                "random_state": 42
            },
            "resampling_method": "none",
            "best_params": {},
            "metrics": [
                {"id": "s0", "metric": "balanced_accuracy", "value": 0.7388, "ci_lower": None, "ci_upper": None},
                {"id": "s1", "metric": "auc",               "value": 0.8035, "ci_lower": None, "ci_upper": None},
                {"id": "s2", "metric": "precision",         "value": 0.0429, "ci_lower": None, "ci_upper": None},
                {"id": "s3", "metric": "recall",            "value": 0.6875, "ci_lower": None, "ci_upper": None},
                {"id": "s4", "metric": "specificity",       "value": 0.7900, "ci_lower": None, "ci_upper": None},
                {"id": "s5", "metric": "f1",                "value": 0.0808, "ci_lower": None, "ci_upper": None},
            ],
        },
        {
            "preprocess_pipeline_index": 0,
            "model_name": "Random Forest",
            "split_name": "split_0",
            "validation_config": {
                "method": "train_test_split",
                "n_splits": 1,
                "stratified": True,
                "train_size": 0.8,
                "test_size": 0.2,
                "shuffle": True,
                "random_state": 42
            },
            "resampling_method": "none",
            "best_params": {},
            "metrics": [
                {"id": "s0", "metric": "balanced_accuracy", "value": 0.5217, "ci_lower": None, "ci_upper": None},
                {"id": "s1", "metric": "auc",               "value": 0.8186, "ci_lower": None, "ci_upper": None},
                {"id": "s2", "metric": "precision",         "value": 0.0952, "ci_lower": None, "ci_upper": None},
                {"id": "s3", "metric": "recall",            "value": 0.0500, "ci_lower": None, "ci_upper": None},
                {"id": "s4", "metric": "specificity",       "value": 0.9935, "ci_lower": None, "ci_upper": None},
                {"id": "s5", "metric": "f1",                "value": 0.0656, "ci_lower": None, "ci_upper": None},
            ],
        }
    ]
}

# ── 模擬的參考論文文字（實際使用時改為 PDF 上傳）────────────────────────────
MOCK_PAPERS = [
    {
        "title": "Machine Learning for ICU Mortality Prediction: A Systematic Review",
        "author": "Johnson et al.",
        "year": "2023",
        "content": """
        Intensive care unit (ICU) mortality prediction is a critical clinical challenge.
        Traditional scoring systems such as APACHE II and SOFA score have been widely used
        but have limitations in capturing complex non-linear relationships.
        Recent advances in machine learning (ML) have shown promising results in improving
        predictive accuracy. Gradient boosting methods, particularly XGBoost, have demonstrated
        superior performance in structured clinical data with AUC values ranging from 0.85 to 0.93.
        Random Forest models also showed competitive performance with robust feature importance
        estimation. The SOFA score was consistently identified as the most important predictor
        across multiple studies, followed by lactate levels and age.
        Class imbalance remains a significant challenge in ICU datasets, with mortality rates
        typically ranging from 10% to 25%. SMOTE oversampling and other resampling techniques
        have been employed to address this issue. Cross-validation with 10 folds is the standard
        validation approach, providing reliable performance estimates.
        Feature selection using Random Forest importance or LASSO regression typically reduces
        the feature space from hundreds of variables to 20-30 most informative features.
        """
    },
    {
        "title": "SOFA Score and Lactate as Predictors of ICU Outcomes",
        "author": "Chen et al.",
        "year": "2022",
        "content": """
        The Sequential Organ Failure Assessment (SOFA) score integrates measurements from
        six organ systems and has been validated as a strong predictor of ICU mortality.
        Studies consistently show that SOFA score at ICU admission provides better discrimination
        than individual organ failure markers. Lactate clearance, defined as the reduction in
        serum lactate levels over 6-12 hours, is independently associated with improved survival.
        Elevated lactate (>2.0 mmol/L) at admission increases mortality risk by 3-fold.
        Combining SOFA score with lactate levels and age improves mortality prediction
        compared to using SOFA alone (AUC 0.86 vs 0.81, p<0.001).
        The Glasgow Coma Scale (GCS) total score reflects neurological status and is
        particularly important in patients with sepsis-associated encephalopathy.
        Creatinine levels above 1.5 mg/dL indicate renal dysfunction and are associated
        with increased 28-day mortality. Multi-organ dysfunction syndrome (MODS) identified
        by SOFA score ≥11 carries a mortality risk exceeding 50%.
        """
    },
    {
        "title": "Addressing Class Imbalance in Clinical Prediction Models",
        "author": "Wang et al.",
        "year": "2023",
        "content": """
        Class imbalance is ubiquitous in clinical datasets where adverse outcomes such as
        mortality, readmission, or complications are rare events. The imbalance ratio in
        ICU mortality datasets typically ranges from 3:1 to 10:1 (non-events to events).
        Synthetic Minority Over-sampling Technique (SMOTE) generates synthetic minority
        class samples by interpolating between existing minority samples. Studies show
        that SMOTE consistently improves recall (sensitivity) for the minority class
        without substantially reducing specificity. The Matthews Correlation Coefficient
        (MCC) and Area Under the Precision-Recall Curve (AUPRC) are recommended as
        primary evaluation metrics for imbalanced datasets, as AUC-ROC can be misleading.
        Stratified k-fold cross-validation is essential when working with imbalanced data
        to ensure proportional representation of classes in each fold.
        Ensemble methods including Random Forest and Gradient Boosting naturally handle
        class imbalance better than single models due to their ensemble nature.
        """
    }
]


def main():
    print("=" * 60)
    print("RAG 論文生成系統測試")
    print("=" * 60)

    from apps import create_app
    from extensions import db
    from models.project import Project
    from models.user import User
    from services.rag.paper_rag import PaperRAGService

    app = create_app()
    with app.app_context():
        user = User.query.first()
        if user is None:
            raise SystemExit("資料庫沒有任何 user，先跑 backend/scripts/seed_admin.py")

        project = Project(user_id=user.id, name="test_paper_gen")
        db.session.add(project)
        db.session.commit()
        project_id = project.id

        try:
            service = PaperRAGService()

            # ── Step 1：清空並重建測試論文庫 ────────────────────────────────────
            print("\n[Step 1] 清空測試論文庫...")
            service.clear(project_id)

            print("\n[Step 2] 加入模擬參考論文...")
            for paper in MOCK_PAPERS:
                result = service.add_paper(
                    project_id,
                    title=paper["title"],
                    content=paper["content"],
                    metadata={"author": paper["author"], "year": paper["year"]},
                )
                status = "✓" if result.get("success") else "✗"
                print(f"  {status} {paper['title']} → {result.get('chunks_added', 0)} chunks")

            # ── Step 2：確認論文庫狀態 ──────────────────────────────────────────
            status = service.get_status(project_id)
            print(f"\n[論文庫狀態] {status['total_papers']} 篇論文，{status['total_chunks']} 個 chunks")
            print(f"  Embedding 後端：{status['embedding_backend']}")

            # ── Step 3：生成論文（僅生成研究方法和實驗結果，聚焦於 DataMind 探勘結果）──
            print("\n[Step 3] 開始生成論文...")
            print("  研究主題：以機器學習預測 ICU 病患院內死亡率")
            print("  生成章節：研究方法、實驗結果（完整測試請移除 structure 參數）")

            result = service.generate_paper(
                project_id,
                topic="以機器學習預測加護病房病患院內死亡率：比較研究",
                mining_results=MOCK_DATAMIND_OUTPUT,
                structure=["研究方法", "實驗結果"],  # 完整版：移除此行使用預設六章
                language="zh-TW",
            )

            # ── Step 4：輸出結果 ─────────────────────────────────────────────────
            output_dir = BACKEND_DIR / "artifacts" / "test_output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 論文 Markdown
            paper_path = output_dir / "generated_paper.md"
            paper_path.write_text(result["paper_markdown"], encoding="utf-8")
            print(f"\n[Step 4] 論文已儲存：{paper_path}")

            # 引用地圖 JSON
            citation_map_path = output_dir / "citation_map.json"
            citation_map_path.write_text(
                json.dumps(result["citation_map"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  引用地圖：{citation_map_path}")

            # 參考文獻清單（僅含實際被引用的文獻）
            refs_path = output_dir / "references.json"
            refs_path.write_text(
                json.dumps(result["references"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  引用清單：{refs_path}")

            # 引用對照報告（記錄文章內文對應到參考論文的哪一部分）
            citation_report_path = output_dir / "citation_report.md"
            citation_report_path.write_text(result["citation_report"], encoding="utf-8")
            print(f"  引用對照報告：{citation_report_path}")

            # ── 摘要輸出 ─────────────────────────────────────────────────────────
            print("\n" + "=" * 60)
            print("【生成結果摘要】")
            print("=" * 60)
            print(f"  生成章節：{result['sections_generated']}")
            print(f"  全域引用數：{len(result['references'])} 篇")
            print(f"  引用地圖條目數：{len(result['citation_map'])} 段")
            print(f"  Token 用量：{result['usage']}")

            print("\n【引用地圖預覽（前 3 條）】")
            for entry in result["citation_map"][:3]:
                print(f"\n  章節：{entry['section']}（段落 {entry['paragraph_index']}）")
                print(f"  引用 ref_id：{entry['cited_ref_ids']}")
                print(f"  文字片段：{entry['text'][:100]}...")
                for src in entry["sources"]:
                    print(f"    → [{src['ref_id']}] {src['title']} ({src['year']}) "
                          f"相似度 {src['similarity_score']}")

            print("\n【論文前 500 字預覽】")
            print("-" * 40)
            print(result["paper_markdown"][:500])
            print("...")
            print("\n測試完成！")
        finally:
            db.session.delete(Project.query.get(project_id))
            db.session.commit()


if __name__ == "__main__":
    main()
