"""Budget caps and approval flow, all fail-closed."""

import pytest

from toolwall import Gate, Meter, Policy, ToolSchema, Verdict, not_empty


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


# --- regression: budget must hold across parallel calls in one payload -------
# Reported by a reviewer: check_all() evaluated every call before any executed,
# so N parallel calls all saw counter=0 and all passed a max_calls=1 budget.

def parallel_payload(*names):
    return {"content": [{"type": "tool_use", "id": str(i), "name": n, "input": {}}
                        for i, n in enumerate(names)]}


def test_budget_holds_across_parallel_calls_in_one_payload():
    executed = []
    gate = Gate(default="allow")
    for n in ("a", "b", "c"):
        gate.register(n, lambda n=n: executed.append(n))
    gate.budget(max_calls=1)

    results = gate.run_all(parallel_payload("a", "b", "c"))

    assert executed == ["a"], f"budget bypassed: {executed}"
    assert [r.verdict for r in results] == [Verdict.ALLOW, Verdict.BLOCK, Verdict.BLOCK]
    assert "budget exceeded" in results[1].reasons[0]


def test_per_tool_budget_holds_across_parallel_calls():
    executed = []
    gate = Gate(default="allow")
    gate.register("a", lambda: executed.append("a"))
    gate.budget(max_calls_per_tool=2)

    gate.run_all(parallel_payload("a", "a", "a", "a"))

    assert executed == ["a", "a"], f"per-tool budget bypassed: {executed}"


# --- budget config validation (a crash is not a verdict) -----------------------

def test_budget_rejects_wrong_types_at_config_time():
    """A bad budget type must fail at budget(), not as a TypeError out of check().

    Regression: max_calls_per_tool={"tool": 5} was accepted here and later raised
    TypeError from inside check(), so the exception escaped the gate instead of
    producing a verdict.
    """
    gate = Gate(default="deny")
    gate.register("t", lambda: "ok", schema=ToolSchema())

    for bad in ({"t": 5}, "5", 1.5, [5]):
        with pytest.raises(TypeError, match="max_calls_per_tool"):
            gate.budget(max_calls_per_tool=bad)

    with pytest.raises(TypeError, match="max_calls"):
        gate.budget(max_calls={"t": 5})

    # bools are ints in Python; a bool here is a mistake, not a limit
    with pytest.raises(TypeError):
        gate.budget(max_calls=True)

    with pytest.raises(ValueError, match="negative"):
        gate.budget(max_calls=-1)

    # the gate still works after every rejected config
    assert gate.run({"name": "t", "args": {}}).allowed


def test_budget_accepts_valid_values():
    gate = Gate(default="deny")
    gate.register("t", lambda: "ok", schema=ToolSchema())
    gate.budget(max_calls=3, max_calls_per_tool=2)
    assert gate.run({"name": "t", "args": {}}).allowed
    assert gate.run({"name": "t", "args": {}}).allowed
    assert gate.run({"name": "t", "args": {}}).blocked  # per-tool cap of 2
