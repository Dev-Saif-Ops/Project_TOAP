"""Surviving TOAP assets: meter export, schema validation, CLI report."""

import json

from toolwall import Meter, ToolSchema, schema_from_signature
from toolwall.cli import cmd_report


def test_schema_required_and_types():
    schema = ToolSchema(required=["q"], types={"q": str, "limit": int})
    assert schema.validate({"q": "x", "limit": 5}) == []
    assert any("Missing required" in e for e in schema.validate({"limit": 5}))
    assert any("expected" in e for e in schema.validate({"q": 1}))


def test_schema_disallow_extra():
    schema = ToolSchema(required=["q"], allow_extra=False)
    assert any("Unexpected arg" in e for e in schema.validate({"q": "x", "sneaky": 1}))


def test_schema_from_signature():
    def tool(q: str, limit: int = 10):
        return q, limit

    schema = schema_from_signature(tool)
    assert schema.required == ["q"]
    assert schema.types["limit"] is int
    assert schema.validate({"limit": 5}) != []


def test_meter_export_json_csv(tmp_path):
    meter = Meter(model="test")
    meter.record_intercept(lane="gate", ok=True, namespace="db_query")
    meter.record_intercept(lane="gate", ok=False, namespace="rm_rf", error="unknown tool")
    paths = meter.export(tmp_path / "audit.json", tmp_path / "audit.csv")

    data = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert data["summary"]["event_count"] == 2
    assert data["summary"]["lanes"]["gate"]["intercept_success_rate"] == 0.5
    assert (tmp_path / "audit.csv").read_text(encoding="utf-8").count("\n") >= 3


def test_cli_report(tmp_path, capsys):
    meter = Meter(model="test")
    meter.record_intercept(lane="gate", ok=True, namespace="db_query")
    meter.export(tmp_path / "audit.json")

    class Args:
        file = str(tmp_path / "audit.json")

    assert cmd_report(Args()) == 0
    out = capsys.readouterr().out
    assert "gate" in out and "intercept_success_rate" in out
