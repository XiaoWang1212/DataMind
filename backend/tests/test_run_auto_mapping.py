from services.field_mapping_service import normalize_user_columns, run_auto_mapping


def find(result: dict, variable: str) -> dict:
    """從 mapping_status 取出指定變數那一筆。"""
    for item in result["mapping_status"]:
        if item["paper_variable"] == variable:
            return item
    raise AssertionError(f"{variable} 不在 mapping_status 裡")


class TestNormalizeUserColumns:
    def test_accepts_plain_strings(self):
        assert normalize_user_columns(["age"]) == [{"name": "age", "sample_values": []}]

    def test_accepts_objects(self):
        assert normalize_user_columns([{"name": "age", "sample_values": ["65"]}]) == [
            {"name": "age", "sample_values": ["65"]},
        ]

    def test_coerces_sample_values_to_strings(self):
        result = normalize_user_columns([{"name": "age", "sample_values": [65, None]}])
        assert result[0]["sample_values"] == ["65", "None"]

    def test_drops_nameless_columns(self):
        assert normalize_user_columns([{"name": "  "}, "age"]) == [
            {"name": "age", "sample_values": []},
        ]


class TestRunAutoMapping:
    def test_exact_match_is_auto_matched_with_full_confidence(self):
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "Age", "sample_values": ["65", "72"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "AUTO_MATCHED"
        assert item["matched_user_column"] == "Age"
        assert item["confidence_score"] == 1.0
        assert item["sample_values"] == ["65", "72"]
        assert item["candidate_columns"] == []

    def test_fuzzy_plus_type_bonus_reaches_auto_matched(self):
        # "age" vs "pt_age" = 0.75，型態相符 +0.1 → 0.85 >= 0.8
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "pt_age", "sample_values": ["65", "72"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "AUTO_MATCHED"
        assert item["matched_user_column"] == "pt_age"

    def test_type_mismatch_downgrades_to_needs_review(self):
        # 同樣是 0.75，但樣本值是文字、論文要數字 → 0.55，落在待確認區間
        result = run_auto_mapping(
            [{"name": "age", "type": "numerical"}],
            normalize_user_columns([{"name": "pt_age", "sample_values": ["甲", "乙"]}]),
        )
        item = find(result, "age")
        assert item["status"] == "NEEDS_REVIEW"
        assert item["matched_user_column"] == "pt_age"

    def test_unrelated_name_is_unmatched_with_candidates(self):
        result = run_auto_mapping(
            [{"name": "braden_score", "type": "numerical"}],
            normalize_user_columns(["gender", "hospital_id"]),
        )
        item = find(result, "braden_score")
        assert item["status"] == "UNMATCHED"
        assert item["matched_user_column"] is None
        assert item["confidence_score"] == 0.0
        assert item["sample_values"] == []
        assert len(item["candidate_columns"]) <= 3
        assert set(item["candidate_columns"]) <= {"gender", "hospital_id"}

    def test_target_never_reaches_auto_matched(self):
        result = run_auto_mapping(
            [{"name": "outcome", "type": "categorical", "is_target": True}],
            normalize_user_columns(["outcome"]),
        )
        item = find(result, "outcome")
        assert item["status"] == "NEEDS_REVIEW"
        assert item["confidence_score"] == 1.0  # 分數照實回報，只有狀態被降級
        assert item["matched_user_column"] == "outcome"

    def test_one_column_cannot_serve_two_variables(self):
        result = run_auto_mapping(
            [{"name": "age", "type": ""}, {"name": "ageyears", "type": ""}],
            normalize_user_columns(["age"]),
        )
        assert find(result, "age")["matched_user_column"] == "age"
        loser = find(result, "ageyears")
        assert loser["matched_user_column"] is None
        assert loser["status"] == "UNMATCHED"
        assert loser["candidate_columns"] == ["age"]

    def test_target_wins_the_column_even_with_lower_score(self):
        # target "ageyears"(0.545) 比 "age"(1.0) 分數低，但 target 優先分配
        result = run_auto_mapping(
            [
                {"name": "age", "type": ""},
                {"name": "ageyears", "type": "", "is_target": True},
            ],
            normalize_user_columns(["age"]),
        )
        assert find(result, "ageyears")["matched_user_column"] == "age"
        assert find(result, "age")["matched_user_column"] is None

    def test_target_is_always_present_even_with_zero_confidence(self):
        result = run_auto_mapping(
            [{"name": "zzzz_nothing_alike", "type": "", "is_target": True}],
            normalize_user_columns(["age", "gender"]),
        )
        item = find(result, "zzzz_nothing_alike")
        assert item["status"] == "UNMATCHED"

    def test_counts(self):
        result = run_auto_mapping(
            [
                {"name": "age", "type": "numerical"},
                {"name": "note", "type": "", "required": False},
                {"name": "outcome", "type": "categorical", "is_target": True},
            ],
            normalize_user_columns([
                {"name": "age", "sample_values": ["65"]},
                {"name": "outcome", "sample_values": ["1", "0"]},
            ]),
        )
        assert result["total_required"] == 2   # note 不算，target 一律算
        assert result["matched_count"] == 1    # 只有 age；target 被降為待確認

    def test_output_keeps_input_order(self):
        result = run_auto_mapping(
            [{"name": "zzz", "type": ""}, {"name": "aaa", "type": ""}],
            normalize_user_columns(["aaa", "zzz"]),
        )
        assert [item["paper_variable"] for item in result["mapping_status"]] == ["zzz", "aaa"]

    def test_variables_without_name_are_dropped(self):
        result = run_auto_mapping(
            [{"name": "  ", "type": ""}, {"name": "age", "type": ""}],
            normalize_user_columns(["age"]),
        )
        assert len(result["mapping_status"]) == 1

    def test_empty_user_columns_marks_everything_unmatched(self):
        result = run_auto_mapping([{"name": "age", "type": "numerical"}], [])
        item = find(result, "age")
        assert item["status"] == "UNMATCHED"
        assert item["candidate_columns"] == []
