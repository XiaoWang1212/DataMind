from services.field_mapping_prompts import (
    CHAT_REFINE_SCHEMA,
    MAX_CHAT_HISTORY,
    SEMANTIC_MATCH_SCHEMA,
    build_chat_refine_prompt,
    build_semantic_match_prompt,
)

COLUMNS = [
    {"name": "pt_age", "sample_values": ["65", "72"]},
    {"name": "braden_total", "sample_values": ["18"]},
]


class TestSchemas:
    def test_semantic_schema_wraps_array_in_object(self):
        # 包成物件而非裸陣列，_safe_parse_json 的大括號 fallback 才抓得到
        assert SEMANTIC_MATCH_SCHEMA["type"] == "object"
        assert SEMANTIC_MATCH_SCHEMA["properties"]["matches"]["type"] == "array"

    def test_chat_schema_restricts_status_values(self):
        status = CHAT_REFINE_SCHEMA["properties"]["actions"]["items"]["properties"]["status"]
        assert status["enum"] == ["AUTO_MATCHED", "NEEDS_REVIEW", "UNMATCHED"]

    def test_chat_schema_requires_reply(self):
        assert "reply" in CHAT_REFINE_SCHEMA["required"]


class TestBuildSemanticMatchPrompt:
    def test_includes_every_column_and_its_samples(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "braden_score", "required_type": "numerical"}],
            COLUMNS,
        )
        assert "pt_age" in prompt
        assert "65, 72" in prompt
        assert "braden_total" in prompt

    def test_includes_pending_variable_and_its_type(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "braden_score", "required_type": "numerical"}],
            COLUMNS,
        )
        assert "braden_score" in prompt
        assert "numerical" in prompt

    def test_handles_column_without_samples(self):
        prompt = build_semantic_match_prompt(
            [{"paper_variable": "x", "required_type": ""}],
            [{"name": "lonely", "sample_values": []}],
        )
        assert "lonely" in prompt
        assert "（無樣本值）" in prompt


class TestBuildChatRefinePrompt:
    def test_includes_current_state_and_user_message(self):
        prompt = build_chat_refine_prompt(
            [{"paper_variable": "braden_score", "matched_user_column": None,
              "status": "UNMATCHED", "required_type": "numerical"}],
            COLUMNS,
            [],
            "braden 分數是 braden_total",
        )
        assert "braden_score" in prompt
        assert "braden 分數是 braden_total" in prompt

    def test_truncates_chat_history(self):
        history = [{"role": "user", "content": f"訊息{i}"} for i in range(20)]
        prompt = build_chat_refine_prompt([], COLUMNS, history, "最後一句")
        assert "訊息19" in prompt
        assert "訊息0" not in prompt
        assert prompt.count("使用者：") <= MAX_CHAT_HISTORY + 1

    def test_empty_history_does_not_break(self):
        prompt = build_chat_refine_prompt([], COLUMNS, [], "你好")
        assert "（尚無對話）" in prompt
