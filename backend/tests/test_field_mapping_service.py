from services.field_mapping_service import exact_match, fuzzy_match, normalize_field


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
