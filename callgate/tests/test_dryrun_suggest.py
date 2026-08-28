"""Dry-run mode, gate.report(), and suggested-policy generation."""

from callgate import Gate, Meter, Policy, ToolSchema, Verdict, in_range, not_empty, suggest_policies


def build(**kwargs):
    gate = Gate(default="deny", **kwargs)
    gate.register(
        "db_query",
        lambda q, limit=10: {"rows": min(limit, 3)},
        schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
        policy=Policy(constraints={"limit": in_range(1, 100)}),
    )
    gate.register(
        "delete_records",
        lambda filter: {"deleted": 1},
        schema=ToolSchema(required=["filter"], types={"filter": dict}),
        policy=Policy(constraints={"filter": not_empty}),
    )
    return gate


def test_dry_run_does_not_execute():
    executed = []
    gate = Gate(default="allow", dry_run=True)
    gate.register("touch", lambda: executed.append(1))
    result = gate.run({"name": "touch"})
    assert result.verdict is Verdict.ALLOW
    assert result.dry_run
    assert not result.executed          # simulated
    assert executed == []               # real tool never ran


def test_dry_run_still_blocks_bad_calls():
    gate = build(dry_run=True)
    result = gate.run({"name": "db_query", "args": {"q": "x", "limit": 10_000_000}})
    assert result.verdict is Verdict.BLOCK
    assert not result.dry_run           # never reached execute
    assert not result.executed


def test_report_counts_verdicts():
    gate = build()
    gate.run({"name": "db_query", "args": {"q": "ok", "limit": 5}})       # allow
    gate.run({"name": "db_query", "args": {"q": "x", "limit": 999}})      # block (policy)
    gate.run({"name": "nope", "args": {}})                               # block (unknown)
    report = gate.report()
    assert report["calls_checked"] == 3
    assert report["verdicts"]["allow"] == 1
    assert report["verdicts"]["block"] == 2
    assert report["executed"] == 1
    assert any("nope" in r for r in report["blocked_reasons"])


def test_dry_run_report_uses_would_execute():
    gate = build(dry_run=True)
    gate.run({"name": "db_query", "args": {"q": "ok", "limit": 5}})
    report = gate.report()
    assert report["dry_run"] is True
    assert report["would_execute"] == 1


def test_suggest_policies_from_history():
    gate = Gate(default="allow", dry_run=True)
    gate.register("db_query", lambda **k: None)
    gate.register("web_search", lambda **k: None)
    for limit in (5, 10, 20):
        gate.run({"name": "db_query", "args": {"q": "hi", "limit": limit}})
    gate.run({"name": "web_search", "args": {"q": "cve", "mode": "fast"}})

    draft = suggest_policies(gate)
    assert 'gate.register(' in draft
    assert '"db_query"' in draft and '"web_search"' in draft
    assert "in_range(5, 20)" in draft          # observed numeric range
    assert "'q'" in draft and "required=[" in draft  # q present in every db_query call
    assert "'mode'" not in draft.split('"web_search"')[0]  # mode only in web_search block
    assert "REVIEW EVERY LINE" in draft


def test_suggest_empty():
    gate = Gate()
    assert "No tool calls observed" in suggest_policies(gate)
