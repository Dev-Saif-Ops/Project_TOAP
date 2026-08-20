"""Tests for Pilot Insert Kit: meter, schema, encoder, compare, proxy gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from toap import (
    Meter,
    TOAPProxy,
    ToolRegistry,
    ToolSchema,
    baseline_json,
    encode_tool_call,
    estimate_tokens,
    summarize_ab,
)


FIXTURES = Path(__file__).parent / "fixtures"


def test_estimate_tokens():
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("a" * 40) == 10


def test_meter_export(tmp_path):
    meter = Meter(model="gemini-test")
    meter.record_llm(lane="baseline", prompt="hello" * 20, completion='{"a":1}')
    meter.record_intercept(lane="toap", ok=True, namespace="DB_SRC", completion_text='ƒ(DB_SRC)>q:"x"')
    jp = tmp_path / "r.json"
    cp = tmp_path / "r.csv"
    meter.export(jp, cp)
    data = json.loads(jp.read_text(encoding="utf-8"))
    assert data["model"] == "gemini-test"
    assert "toap" in data["summary"]["lanes"]
    assert cp.exists()


def test_require_schema_blocks_unschematized_tools():
    registry = ToolRegistry()
    registry.register("DB_SRC", lambda q, l=10: {"q": q, "l": l})
    proxy = TOAPProxy(registry, require_schema=True)
    result = proxy.intercept('ƒ(DB_SRC)>q:"x"|l:1')
    assert not result.executed
    assert "No schema" in (result.error or "")


def test_schema_blocks_missing_required():
    registry = ToolRegistry()
    registry.register(
        "DB_SRC",
        lambda q, l=10: {"q": q, "l": l},
        schema=ToolSchema(required=["q"], types={"l": int}),
    )
    proxy = TOAPProxy(registry)
    bad = proxy.intercept("ƒ(DB_SRC)>l:5")
    assert not bad.executed
    assert bad.schema_errors
    good = proxy.intercept('ƒ(DB_SRC)>q:"ok"|l:5')
    assert good.executed


def test_infer_schema_from_signature():
    def query_database(q: str, l: int = 10) -> dict:
        return {"q": q, "l": l}

    registry = ToolRegistry()
    registry.register("DB_SRC", query_database, infer_schema=True)
    proxy = TOAPProxy(registry)
    assert not proxy.intercept("ƒ(DB_SRC)>l:1").executed
    assert proxy.intercept('ƒ(DB_SRC)>q:"x"').executed


def test_encoder_roundtrip_parse():
    from toap import TOAPParser

    payload = {
        "namespace": "DB_SRC",
        "args": {"q": "Huawei Cloud vulnerabilities", "l": 5},
        "thought": "sec_vuln",
    }
    raw = encode_tool_call(payload)
    parsed = TOAPParser().parse(raw)
    assert parsed.valid
    assert parsed.namespace == "DB_SRC"
    assert parsed.args["q"] == "Huawei Cloud vulnerabilities"
    assert parsed.args["l"] == 5


def test_summarize_ab():
    meter = Meter()
    meter.record_llm(lane="baseline", prompt="p" * 40, completion=baseline_json({"a": 1}) * 5)
    meter.record_llm(lane="toap", prompt="p" * 40, completion='ƒ(DB_SRC)>q:"x"')
    meter.record_intercept(lane="baseline", ok=True)
    meter.record_intercept(lane="toap", ok=True)
    summary = summarize_ab(meter.report)
    assert "net_token_savings_pct" in summary
    assert "honest_note" in summary


def test_replay_fixtures():
    path = FIXTURES / "tool_calls.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    from toap import TOAPParser

    parser = TOAPParser()
    for row in data:
        raw = encode_tool_call(row["payload"])
        parsed = parser.parse(raw)
        assert parsed.valid, row
        for k, v in row["expect_args"].items():
            assert parsed.args[k] == v


def test_fuzz_invalid_strings():
    proxy = TOAPProxy()
    for raw in [
        "",
        "hello",
        "ƒ()>q:1",
        "ƒ(DB_SRC)",
        'ƒ(DB_SRC)>q:"unterminated',
        "§T[only_thought]",
    ]:
        result = proxy.intercept(raw)
        assert not result.executed
