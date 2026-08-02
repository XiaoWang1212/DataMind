from services.field_mapping_service import merge_semantic_suggestions


def build_result(items: list[dict]) -> dict:
    return {
        "total_required": len(items),
        "matched_count": sum(1 for item in items if item["status"] == "AUTO_MATCHED"),
        "mapping_status": items,
    }


def unmatched(variable: str, candidates: list[str] | None = None) -> dict:
    return {
        "paper_variable": variable,
        "required_type": "numerical",
        "matched_user_column": None,
        "confidence_score": 0.0,
        "status": "UNMATCHED",
        "sample_values": [],
        "candidate_columns": candidates or [],
    }


COLUMNS = [
    {"name": "braden_total", "sample_values": ["18", "14"]},
    {"name": "bp_sys", "sample_values": ["120", "134"]},
]


class TestMergeSemanticSuggestions:
    def test_suggestion_fills_column_as_needs_review(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 0.95, "candidate_columns": []}],
            COLUMNS,
        )
        item = result["mapping_status"][0]
        assert item["matched_user_column"] == "braden_total"
        assert item["status"] == "NEEDS_REVIEW"
        assert item["sample_values"] == ["18", "14"]
        assert item["candidate_columns"] == []

    def test_confidence_is_capped_below_auto_threshold(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 1.0, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["confidence_score"] == 0.79

    def test_never_overwrites_an_auto_matched_item(self):
        locked = {
            "paper_variable": "age", "required_type": "numerical",
            "matched_user_column": "pt_age", "confidence_score": 0.9,
            "status": "AUTO_MATCHED", "sample_values": ["65"], "candidate_columns": [],
        }
        result = build_result([locked])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "age", "matched_user_column": "bp_sys",
              "confidence_score": 0.99, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["matched_user_column"] == "pt_age"
        assert result["mapping_status"][0]["status"] == "AUTO_MATCHED"

    def test_taken_column_becomes_a_candidate_instead(self):
        taken = {
            "paper_variable": "systolic", "required_type": "numerical",
            "matched_user_column": "bp_sys", "confidence_score": 0.85,
            "status": "AUTO_MATCHED", "sample_values": [], "candidate_columns": [],
        }
        result = build_result([taken, unmatched("blood_pressure")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "blood_pressure", "matched_user_column": "bp_sys",
              "confidence_score": 0.9, "candidate_columns": []}],
            COLUMNS,
        )
        item = result["mapping_status"][1]
        assert item["matched_user_column"] is None
        assert item["candidate_columns"] == ["bp_sys"]

    def test_candidate_only_suggestion_merges_without_duplicates(self):
        result = build_result([unmatched("braden_score", ["bp_sys"])])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": None,
              "confidence_score": 0.0, "candidate_columns": ["bp_sys", "braden_total"]}],
            COLUMNS,
        )
        item = result["mapping_status"][0]
        assert item["candidate_columns"] == ["bp_sys", "braden_total"]
        assert item["status"] == "UNMATCHED"

    def test_candidate_list_is_capped_at_five(self):
        result = build_result([unmatched("x", ["a", "b", "c", "d"])])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "x", "matched_user_column": None,
              "confidence_score": 0.0, "candidate_columns": ["e", "f", "g"]}],
            [{"name": name, "sample_values": []} for name in "abcdefg"],
        )
        assert len(result["mapping_status"][0]["candidate_columns"]) == 5

    def test_unknown_variable_is_ignored(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "does_not_exist", "matched_user_column": "bp_sys",
              "confidence_score": 0.9, "candidate_columns": []}],
            COLUMNS,
        )
        assert result["mapping_status"][0]["matched_user_column"] is None

    def test_matched_count_is_recomputed(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(
            result,
            [{"paper_variable": "braden_score", "matched_user_column": "braden_total",
              "confidence_score": 0.95, "candidate_columns": []}],
            COLUMNS,
        )
        # AI 建議一律是待確認，不會讓 matched_count 增加
        assert result["matched_count"] == 0

    def test_empty_suggestions_is_a_noop(self):
        result = build_result([unmatched("braden_score")])
        merge_semantic_suggestions(result, [], COLUMNS)
        assert result["mapping_status"][0]["status"] == "UNMATCHED"
