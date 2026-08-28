"""Policy layer: value constraints, cross rules, fail-closed on rule errors."""

from callgate import Gate, Policy, ToolSchema, Verdict, in_range, matches, max_len, not_empty, one_of
from callgate.policy import ends_with, starts_with


def test_constraint_pass_and_fail():
    policy = Policy(constraints={"limit": in_range(1, 100)})
    assert policy.validate({"limit": 50}) == []
    assert policy.validate({"limit": 10_000_000}) != []
    assert policy.validate({"limit": 0}) != []


def test_absent_arg_is_schemas_job():
    policy = Policy(constraints={"limit": in_range(1, 100)})
    assert policy.validate({}) == []


def test_raising_rule_fails_closed():
    policy = Policy(constraints={"limit": in_range(1, 100)})
    errors = policy.validate({"limit": "not-a-number"})
    assert errors and "fails closed" in errors[0]


def test_cross_rule():
    policy = Policy(cross=lambda args: "path traversal" if ".." in args.get("path", "") else None)
    assert policy.validate({"path": "/app/ok.txt"}) == []
    assert policy.validate({"path": "/app/../etc/passwd"}) == ["path traversal"]


def test_cross_rule_raising_fails_closed():
    policy = Policy(cross=lambda args: 1 / 0)
    errors = policy.validate({"x": 1})
    assert errors and "fails closed" in errors[0]


def test_rule_helpers():
    assert one_of("staging", "prod")("staging")
    assert not one_of("staging")("prod")
    assert matches(r"[a-z]+@ourco\.com")("dev@ourco.com")
    assert not matches(r"[a-z]+@ourco\.com")("dev@evil.com")
    assert max_len(5)("abc")
    assert not max_len(2)("abc")
    assert ends_with("@ourco.com")("a@ourco.com")
    assert not ends_with("@ourco.com")("a@ourco.com.evil.net")
    assert starts_with("/app/")("/app/x")
    assert not starts_with("/app/")("/etc/passwd")
    assert not_empty({"id": 1})
    assert not not_empty({})


def test_gate_blocks_on_policy_violation():
    gate = Gate(default="deny")
    gate.register(
        "db_query",
        lambda q, limit=10: {"rows": 1},
        schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
        policy=Policy(constraints={"limit": in_range(1, 100)}),
    )
    blocked = gate.run({"name": "db_query", "args": {"q": "x", "limit": 10_000_000}})
    assert blocked.verdict is Verdict.BLOCK
    assert not blocked.executed
    allowed = gate.run({"name": "db_query", "args": {"q": "x", "limit": 5}})
    assert allowed.executed


def test_empty_filter_delete_blocked():
    gate = Gate(default="deny")
    gate.register(
        "delete_records",
        lambda filter: {"deleted": 1},
        schema=ToolSchema(required=["filter"], types={"filter": dict}),
        policy=Policy(constraints={"filter": not_empty}),
    )
    result = gate.run({"name": "delete_records", "args": {"filter": {}}})
    assert result.verdict is Verdict.BLOCK
    assert not result.executed
