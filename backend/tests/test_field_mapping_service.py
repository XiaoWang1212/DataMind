import pytest

from services.field_mapping_service import exact_match, fuzzy_match, normalize_field
from services.field_mapping_service import boost_by_sample_values, infer_value_type


class TestNormalizeField:
    def test_lowercases_and_strips_whitespace(self):
        assert normalize_field(" Pt_Age ") == "ptage"

    def test_removes_tbl_prefix(self):
        assert normalize_field("tbl_user_name") == "username"

    def test_removes_col_prefix_and_dashes(self):
        assert normalize_field("col_BP-High") == "bphigh"

    def test_keeps_prefix_like_text_without_separator(self):
        # "tblname" 沒有分隔符號，tbl 是名字的一部分而非前綴，不可剝掉
        assert normalize_field("tblname") == "tblname"

    def test_empty_input(self):
        assert normalize_field("") == ""


class TestExactMatch:
    def test_finds_match_ignoring_formatting(self):
        assert exact_match("patient_age", ["PatientAge", "gender"]) == "PatientAge"

    def test_returns_none_when_no_match(self):
        assert exact_match("braden_score", ["age", "gender"]) is None

    def test_returns_original_column_name_not_normalized(self):
        assert exact_match("age", ["  Age  "]) == "  Age  "


class TestFuzzyMatch:
    def test_sorts_by_score_descending(self):
        scored = fuzzy_match("age", ["gender", "pt_age"])
        assert scored[0][0] == "pt_age"
        assert round(scored[0][1], 2) == 0.75

    def test_returns_every_column(self):
        scored = fuzzy_match("age", ["gender", "pt_age", "bp_sys"])
        assert len(scored) == 3

    def test_identical_name_scores_one(self):
        scored = fuzzy_match("age", ["age"])
        assert scored[0][1] == 1.0


class TestInferValueType:
    def test_detects_iso_date(self):
        assert infer_value_type(["2024-01-03", "2024-02-11", "2024-3-5"]) == "date"

    def test_detects_slash_date(self):
        assert infer_value_type(["2024/01/03", "2024/02/11"]) == "date"

    def test_detects_compact_date(self):
        assert infer_value_type(["20240103", "20240211"]) == "date"

    def test_detects_numeric(self):
        assert infer_value_type(["65", "72", "48.5"]) == "numeric"

    def test_detects_text(self):
        assert infer_value_type(["男", "女", "男"]) == "text"

    def test_ignores_empty_values(self):
        assert infer_value_type(["65", "", "  ", "72"]) == "numeric"

    def test_returns_none_when_no_usable_values(self):
        assert infer_value_type([]) is None
        assert infer_value_type(["", "  "]) is None

    def test_minority_mismatch_still_counts_as_numeric(self):
        # 4 筆數字 + 1 筆文字 = 80% >= 60%
        assert infer_value_type(["1", "2", "3", "4", "n/a"]) == "numeric"

    def test_below_threshold_falls_back_to_text(self):
        # 只有 40% 是數字，達不到 60% 門檻
        assert infer_value_type(["1", "2", "甲", "乙", "丙"]) == "text"


class TestBoostBySampleValues:
    def test_matching_type_adds_bonus(self):
        assert boost_by_sample_values(0.75, "numerical", ["65", "72"]) == pytest.approx(0.85)

    def test_mismatched_type_applies_penalty(self):
        assert boost_by_sample_values(0.75, "numerical", ["男", "女"]) == pytest.approx(0.55)

    def test_date_type_matches(self):
        assert boost_by_sample_values(0.6, "date", ["2024-01-03", "2024-02-11"]) == pytest.approx(0.7)

    def test_categorical_matches_text(self):
        assert boost_by_sample_values(0.6, "categorical", ["男", "女"]) == pytest.approx(0.7)

    def test_no_samples_leaves_score_unchanged(self):
        assert boost_by_sample_values(0.75, "numerical", []) == 0.75

    def test_unknown_required_type_leaves_score_unchanged(self):
        assert boost_by_sample_values(0.75, "mystery", ["65"]) == 0.75
        assert boost_by_sample_values(0.75, "", ["65"]) == 0.75

    def test_type_comparison_is_case_insensitive(self):
        assert boost_by_sample_values(0.75, "Numerical", ["65"]) == pytest.approx(0.85)

    def test_clamps_to_upper_bound(self):
        assert boost_by_sample_values(0.95, "numerical", ["65"]) == 1.0

    def test_clamps_to_lower_bound(self):
        assert boost_by_sample_values(0.1, "numerical", ["男"]) == 0.0
