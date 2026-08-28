"""Meter D-016: provider counts are exact; heuristics are flagged."""

from callgate import Meter, extract_usage


def test_explicit_counts_not_estimated():
    meter = Meter(model="test")
    event = meter.record_llm(lane="gate", prompt_tokens=100, completion_tokens=20)
    assert not event.estimated


def test_heuristic_counts_flagged():
    meter = Meter(model="test")
    event = meter.record_llm(lane="gate", prompt="hello world", completion="hi")
    assert event.estimated
    assert meter.report.summary()["lanes"]["gate"]["estimated_events"] == 1
    assert "heuristic" in meter.report.summary()["note"]


def test_no_note_when_all_exact():
    meter = Meter(model="test")
    meter.record_llm(lane="gate", prompt_tokens=10, completion_tokens=5)
    assert "note" not in meter.report.summary()


def test_extract_usage_openai_chat():
    payload = {"usage": {"prompt_tokens": 50, "completion_tokens": 10}}
    assert extract_usage(payload) == (50, 10)


def test_extract_usage_anthropic_and_openai_responses():
    payload = {"usage": {"input_tokens": 30, "output_tokens": 7}}
    assert extract_usage(payload) == (30, 7)


def test_extract_usage_gemini():
    payload = {"usageMetadata": {"promptTokenCount": 40, "candidatesTokenCount": 9}}
    assert extract_usage(payload) == (40, 9)
    snake = {"usage_metadata": {"prompt_token_count": 41, "candidates_token_count": 8}}
    assert extract_usage(snake) == (41, 8)


def test_extract_usage_sdk_object():
    class Fake:
        def model_dump(self):
            return {"usage": {"input_tokens": 3, "output_tokens": 2}}

    assert extract_usage(Fake()) == (3, 2)


def test_extract_usage_missing():
    assert extract_usage({"choices": []}) == (None, None)


def test_record_llm_with_response_usage():
    meter = Meter(model="test")
    response = {"usage": {"prompt_tokens": 25, "completion_tokens": 6}}
    event = meter.record_llm(lane="gate", response=response)
    assert (event.prompt_tokens, event.completion_tokens) == (25, 6)
    assert not event.estimated
