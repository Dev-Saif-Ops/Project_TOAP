"""Budget caps and approval flow, all fail-closed."""

import pytest

from callgate import Gate, Meter, Policy, ToolSchema, Verdict, not_empty


def make_gate(**kwargs):
    gate = Gate(default="deny", **kwargs)
    gate.register(
        "ping",
        lambda n=0: n,
        schema=ToolSchema(types={"n": int}),
    )
    gate.register(
        "delete_records",
        lambda filter: {"deleted": 1},
        schema=ToolSchema(required=["filter"], types={"filter": dict}),
        policy=Policy(constraints={"filter": not_empty}, require_approval=True),
    )
    return gate


def test_max_calls_blocks_after_limit():
    gate = make_gate()
    gate.budget(max_calls=3)
    results = [gate.run({"name": "ping", "args": {"n": i}}) for i in range(5)]
    assert [r.executed for r in results] == [True, True, True, False, False]
    assert results[3].verdict is Verdict.BLOCK
    assert "budget exceeded" in results[3].reasons[0]


def test_max_calls_per_tool():
    gate = make_gate()
    gate.budget(max_calls_per_tool=2)
    results = [gate.run({"name": "ping", "args": {"n": i}}) for i in range(3)]
    assert [r.executed for r in results] == [True, True, False]


def test_max_usd_requires_meter():
    gate = make_gate()
    with pytest.raises(ValueError):
        gate.budget(max_usd=0.5)


def test_max_usd_blocks_when_spent():
    meter = Meter(model="test")
    gate = make_gate(meter=meter)
    gate.budget(max_usd=0.000001)
    meter.record_llm(lane="gate", prompt_tokens=1_000_000, completion_tokens=0)
    result = gate.run({"name": "ping", "args": {}})
    assert result.verdict is Verdict.BLOCK
    assert "max_usd" in result.reasons[0]


DELETE = {"name": "delete_records", "args": {"filter": {"id": 42}}}


def test_no_handler_fails_closed():
    gate = make_gate()
    result = gate.run(DELETE)
    assert result.verdict is Verdict.NEEDS_APPROVAL
    assert not result.executed


def test_execute_refuses_needs_approval():
    gate = make_gate()
    result = gate.check(DELETE)
    assert result.verdict is Verdict.NEEDS_APPROVAL
    with pytest.raises(PermissionError):
        gate.execute(result)


def test_approval_granted_executes():
    gate = make_gate(approval=lambda r: True)
    result = gate.run(DELETE)
    assert result.verdict is Verdict.ALLOW
    assert result.executed
    assert result.return_value == {"deleted": 1}


def test_approval_denied_blocks():
    gate = make_gate(approval=lambda r: False)
    result = gate.run(DELETE)
    assert result.verdict is Verdict.BLOCK
    assert not result.executed
    assert "approval denied" in result.reasons[-1]


def test_approval_handler_exception_fails_closed():
    def bad_handler(result):
        raise RuntimeError("ui crashed")

    gate = make_gate(approval=bad_handler)
    result = gate.run(DELETE)
    assert result.verdict is Verdict.BLOCK
    assert not result.executed


def test_policy_violation_beats_approval():
    gate = make_gate(approval=lambda r: True)
    result = gate.run({"name": "delete_records", "args": {"filter": {}}})
    assert result.verdict is Verdict.BLOCK
    assert not result.executed
