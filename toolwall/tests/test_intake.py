"""Intake: provider response shapes -> ToolCall records."""

import pytest

from toolwall.intake import IntakeError, parse_tool_calls


def test_plain_dict():
    calls = parse_tool_calls({"name": "db_query", "args": {"q": "x", "limit": 5}})
    assert len(calls) == 1
    assert calls[0].name == "db_query"
    assert calls[0].args == {"q": "x", "limit": 5}
    assert calls[0].source == "dict"


def test_plain_dict_alt_keys():
    calls = parse_tool_calls({"action": "db_query", "params": {"q": "x"}})
    assert calls[0].name == "db_query"
    assert calls[0].args == {"q": "x"}


def test_openai_chat_shape():
    payload = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "db_query", "arguments": '{"q": "x", "limit": 5}'},
                        }
                    ]
                }
            }
        ]
    }
    calls = parse_tool_calls(payload)
    assert len(calls) == 1
    assert calls[0].name == "db_query"
    assert calls[0].args == {"q": "x", "limit": 5}
    assert calls[0].id == "call_1"
    assert calls[0].source == "openai-chat"


def test_openai_responses_shape():
    payload = {
        "output": [
            {"type": "reasoning", "content": []},
            {"type": "function_call", "call_id": "fc_1", "name": "send_email", "arguments": '{"to": "a@b.com"}'},
        ]
    }
    calls = parse_tool_calls(payload)
    assert len(calls) == 1
    assert calls[0].name == "send_email"
    assert calls[0].args == {"to": "a@b.com"}
    assert calls[0].source == "openai-responses"


def test_anthropic_shape():
    payload = {
        "content": [
            {"type": "text", "text": "Let me query that."},
            {"type": "tool_use", "id": "toolu_1", "name": "db_query", "input": {"q": "x"}},
        ]
    }
    calls = parse_tool_calls(payload)
    assert len(calls) == 1
    assert calls[0].name == "db_query"
    assert calls[0].args == {"q": "x"}
    assert calls[0].source == "anthropic"


def test_gemini_shape():
    payload = {
        "candidates": [
            {"content": {"parts": [{"functionCall": {"name": "web_search", "args": {"q": "cve"}}}]}}
        ]
    }
    calls = parse_tool_calls(payload)
    assert len(calls) == 1
    assert calls[0].name == "web_search"
    assert calls[0].source == "gemini"


def test_multiple_parallel_calls():
    payload = {
        "content": [
            {"type": "tool_use", "id": "t1", "name": "a", "input": {}},
            {"type": "tool_use", "id": "t2", "name": "b", "input": {"x": 1}},
        ]
    }
    calls = parse_tool_calls(payload)
    assert [c.name for c in calls] == ["a", "b"]


def test_envelope_with_no_tool_calls_returns_empty():
    payload = {"choices": [{"message": {"content": "just text"}}]}
    assert parse_tool_calls(payload) == []


def test_bad_json_arguments_raises():
    payload = {
        "choices": [
            {"message": {"tool_calls": [{"id": "c", "function": {"name": "f", "arguments": "{not json"}}]}}
        ]
    }
    with pytest.raises(IntakeError):
        parse_tool_calls(payload)


def test_unrecognizable_shape_raises():
    with pytest.raises(IntakeError):
        parse_tool_calls({"foo": "bar"})


def test_non_dict_args_raises():
    with pytest.raises(IntakeError):
        parse_tool_calls({"name": "f", "args": [1, 2, 3]})


def test_sdk_object_via_model_dump():
    class FakeSDKResponse:
        def model_dump(self):
            return {"content": [{"type": "tool_use", "id": "t", "name": "f", "input": {"a": 1}}]}

    calls = parse_tool_calls(FakeSDKResponse())
    assert calls[0].name == "f"
    assert calls[0].args == {"a": 1}


# --- regression: a non-string tool name must BLOCK, not crash the gate -------
# Found by property-based fuzzing. Envelope extractors only checked truthiness,
# so a dict/int/list name reached the registry lookup and raised TypeError,
# which escaped the gate instead of becoming a verdict.

@pytest.mark.parametrize("bad_name", [{"a": 1}, ["x"], 42, None, "", "   ", 3.5])
def test_non_string_tool_name_raises_intake_error(bad_name):
    shapes = [
        {"content": [{"type": "tool_use", "id": "1", "name": bad_name, "input": {}}]},
        {"candidates": [{"content": {"parts": [{"functionCall": {"name": bad_name, "args": {}}}]}}]},
        {"choices": [{"message": {"tool_calls": [{"id": "1", "function": {"name": bad_name, "arguments": "{}"}}]}}]},
        {"output": [{"type": "function_call", "call_id": "1", "name": bad_name, "arguments": "{}"}]},
    ]
    for payload in shapes:
        with pytest.raises(IntakeError):
            parse_tool_calls(payload)


def test_gate_turns_a_bad_name_into_a_block_not_an_exception():
    from toolwall import Gate
    gate = Gate(default="allow")
    gate.register("real", lambda: "ran")
    results = gate.check_all(
        {"content": [{"type": "tool_use", "id": "1", "name": {"nope": 1}, "input": {}}]}
    )
    assert len(results) == 1
    assert results[0].blocked
    assert "intake" in results[0].reasons[0]
