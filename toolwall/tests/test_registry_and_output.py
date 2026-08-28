"""Duplicate registration guard and tool-output scanning."""

import pytest

from toolwall import Gate, Policy, Shield, ToolSchema, ToolWall, Verdict, in_range

AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"


# --- duplicate registration -------------------------------------------------

def test_duplicate_registration_raises():
    gate = Gate(default="allow")
    gate.register("t", lambda: "first")
    with pytest.raises(ValueError, match="already registered"):
        gate.register("t", lambda: "second")


def test_replace_true_overrides():
    gate = Gate(default="allow")
    gate.register("t", lambda: "first")
    gate.register("t", lambda: "second", replace=True)
    assert gate.run({"name": "t"}).return_value == "second"


def test_replace_drops_stale_policy():
    """A replaced tool must not inherit the previous tool's constraints."""
    gate = Gate(default="allow")
    gate.register("t", lambda limit=1: limit,
                  schema=ToolSchema(types={"limit": int}),
                  policy=Policy(constraints={"limit": in_range(1, 10)}))
    assert gate.run({"name": "t", "args": {"limit": 999}}).blocked

    gate.register("t", lambda limit=1: limit, replace=True)   # no policy this time
    assert gate.run({"name": "t", "args": {"limit": 999}}).executed


def test_toolwall_facade_also_guards_duplicates():
    wall = ToolWall(default="allow")
    wall.register("t", lambda: 1)
    with pytest.raises(ValueError):
        wall.register("t", lambda: 2)


# --- tool output scanning ---------------------------------------------------

def leaky_tool():
    """A tool that reads a secret out of storage and hands it back."""
    return {"note": "here is the key " + AWS_KEY}


def build(mode):
    gate = Gate(default="allow", shield=Shield(mode=mode))
    gate.register("read_note", leaky_tool)
    return gate


def test_output_secret_blocked():
    result = build("block").run({"name": "read_note"})
    assert result.executed                       # the tool ran
    assert result.return_value is None           # but its output was withheld
    assert "tool output withheld" in result.error
    assert any(f.kind == "aws-access-key" for f in result.findings)


def test_output_secret_redacted():
    result = build("redact").run({"name": "read_note"})
    assert AWS_KEY not in str(result.return_value)
    assert "[REDACTED" in result.return_value["note"]


def test_output_warn_mode_passes_through_but_records():
    result = build("warn").run({"name": "read_note"})
    assert AWS_KEY in result.return_value["note"]
    assert any(f.kind == "aws-access-key" for f in result.findings)


def test_output_findings_are_tagged_as_return():
    result = build("warn").run({"name": "read_note"})
    assert any(f.arg and f.arg.startswith("return") for f in result.findings)


def test_clean_output_untouched():
    gate = Gate(default="allow", shield=Shield(mode="block"))
    gate.register("ok", lambda: {"rows": 3, "note": "nothing sensitive here"})
    result = gate.run({"name": "ok"})
    assert result.return_value == {"rows": 3, "note": "nothing sensitive here"}
    assert result.findings == []


def test_output_scanning_can_be_disabled():
    gate = Gate(default="allow", shield=Shield(mode="block", scan_output=False))
    gate.register("read_note", leaky_tool)
    result = gate.run({"name": "read_note"})
    assert AWS_KEY in result.return_value["note"]


def test_output_scan_does_not_leak_into_audit(tmp_path):
    from toolwall import Meter
    meter = Meter(model="test")
    gate = Gate(default="allow", shield=Shield(mode="block"), meter=meter)
    gate.register("read_note", leaky_tool)
    gate.run({"name": "read_note"})
    paths = meter.export(tmp_path / "a.json", tmp_path / "a.csv")
    for p in paths.values():
        assert AWS_KEY not in p.read_text(encoding="utf-8")
