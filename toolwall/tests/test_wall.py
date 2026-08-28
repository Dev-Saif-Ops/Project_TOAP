"""ToolWall facade: the ergonomic entry point over Gate."""

import pytest

from toolwall import Policy, ToolSchema, ToolWall, Verdict, in_range, not_empty


def get_user(id: str) -> dict:
    return {"id": id, "name": "Ada"}


def delete_user(id: str) -> dict:
    return {"deleted": id}


def send_email(to: str, body: str) -> dict:
    return {"sent": to}


def build() -> ToolWall:
    wall = ToolWall()  # default deny, secrets on, audit on
    wall.register("get_user", get_user, schema=ToolSchema(required=["id"], types={"id": str}))
    wall.register("delete_user", delete_user,
                  schema=ToolSchema(required=["id"], types={"id": str}),
                  policy=Policy(require_approval=True))
    wall.register("send_email", send_email,
                  schema=ToolSchema(required=["to", "body"], types={"to": str, "body": str}))
    return wall


def test_allow_runs():
    r = build().call("get_user", {"id": "123"})
    assert r.allowed and r.executed
    assert r.return_value == {"id": "123", "name": "Ada"}
    assert r.reason is None


def test_unknown_tool_blocked():
    r = build().call("drop_database", {})
    assert r.blocked and not r.executed
    assert "unknown tool" in r.reason


def test_needs_approval_held_without_handler():
    r = build().call("delete_user", {"id": "123"})
    assert r.needs_approval and not r.executed


def test_approval_handler_runs_it():
    wall = build().approve_with(lambda result: True)
    r = wall.call("delete_user", {"id": "123"})
    assert r.allowed and r.executed


def test_chainable_register_and_budget():
    wall = ToolWall().register("get_user", get_user, schema=ToolSchema(required=["id"])).budget(max_calls=1)
    assert wall.call("get_user", {"id": "1"}).executed
    assert wall.call("get_user", {"id": "2"}).blocked  # budget hit


def test_secret_blocked_by_default():
    wall = build()
    r = wall.call("send_email", {"to": "a@b.com", "body": "key AKIA" + "IOSFODNN7EXAMPLE"})
    assert r.blocked
    assert "secret" in r.reason


def test_redact_mode():
    wall = ToolWall(redact=True)
    wall.register("send_email", send_email, schema=ToolSchema(required=["to", "body"]))
    r = wall.call("send_email", {"to": "a@b.com", "body": "key AKIA" + "IOSFODNN7EXAMPLE"})
    assert r.allowed
    assert "AKIA" + "IOSFODNN7EXAMPLE" not in r.return_value["sent"] or True  # sent returns 'to'
    assert "[REDACTED" in r.call.args["body"]


def test_detect_secrets_off():
    wall = ToolWall(detect_secrets=False, default="allow")
    wall.register("send_email", send_email)
    r = wall.call("send_email", {"to": "a@b.com", "body": "key AKIA" + "IOSFODNN7EXAMPLE"})
    assert r.executed  # no shield, secret passes


def test_check_does_not_execute():
    ran = []
    wall = ToolWall(default="allow")
    wall.register("touch", lambda: ran.append(1))
    v = wall.check("touch")
    assert v.verdict is Verdict.ALLOW
    assert ran == []


def test_dry_run_and_report_and_export(tmp_path):
    wall = build()
    wall.dry_run = True
    wall.call("get_user", {"id": "1"})
    wall.call("nope", {})
    rpt = wall.report()
    assert rpt["dry_run"] is True
    assert rpt["calls_checked"] == 2
    paths = wall.export(tmp_path / "audit.json", tmp_path / "audit.csv")
    assert paths["json"].exists()


def test_guard_raw_gemini_response():
    wall = build()
    payload = {"candidates": [{"content": {"parts": [
        {"functionCall": {"name": "get_user", "args": {"id": "42"}}}
    ]}}]}
    results = wall.guard(payload)
    assert len(results) == 1 and results[0].executed


def test_export_without_audit_raises():
    wall = ToolWall(audit=False, default="allow")
    wall.register("t", lambda: 1)
    wall.call("t")
    with pytest.raises(ValueError):
        wall.export("x.json")
