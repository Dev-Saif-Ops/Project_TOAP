# Changelog

## [0.2.0-dev] - 2026-08-28 — Pivot: TOAP → callgate

### Why
TOAP's compression thesis failed an honest re-measurement: vs minified JSON it was
+4.6% tokens (o200k) / +11.1% (cl100k); vs native function-calling arguments +56%.
The ~45% claim traced to an `indent=2` baseline. Our own PRD kill criterion
("net < 25% → sell reliability/security, not cost") was met, so we honored it.
Full postmortem: `toap-v0.1-archive` branch README.

### Added
- `callgate` package: fail-closed firewall for agent tool calls
- `intake.py`: OpenAI (chat + responses), Anthropic, Gemini, and plain-dict tool-call normalization
- `gate.py`: `Gate` with `default="deny"|"allow"`, `check`/`execute` split, `run`/`run_all`, verdict enum
- Audit events for every verdict via surviving `Meter` (JSON/CSV export)
- `callgate report` CLI
- New test suite: intake shapes, all gate verdict paths, schema, meter, CLI

### Removed
- TOAP DSL: parser, encoder, compare, few-shot prompts, LangChain/CrewAI adapters
- `toap-bench` harness (superseded; failure-scenario suite lands next cycle)
- All compression claims

### Carried over
- `schema.py` (+ `schema_from_signature`), `meter.py`, fail-closed proxy control flow, MIT license

### Added (phase0-completion cycle, same day)
- `policy.py`: value constraints (`in_range`, `one_of`, `matches`, `ends_with`, `starts_with`, `max_len`, `not_empty`), cross-arg rules, `require_approval`; raising rules fail closed
- Budget caps on the gate: `max_calls`, `max_calls_per_tool`, `max_usd` (meter-derived)
- Approval flow: `NEEDS_APPROVAL` verdict, optional handler on `run`/`run_all`, fail-closed without one
- `shield.py` (D-019): secret patterns (AWS, Google, GitHub, Stripe, Slack, OpenAI, JWT, PEM, credential assignments) + entropy heuristic; modes redact/block/warn; in-memory placeholder vault; findings and audit events never carry values
- Meter D-016: `extract_usage()` pulls exact token counts from OpenAI/Anthropic/Gemini responses; heuristic counts flagged `estimated=true`; summary reports estimated-event count
- `gate-suite/`: 24 attack cases across 9 classes + 10 clean cases; G1 result: 24/24 blocked, 0 false blocks, p95 0.07 ms (`gate-suite/results/REPORT.md`)
- Test suite grown to 70 tests

### Pending (next cycles, per plan.md)
- Dry-run mode + suggested-policy generator
- `callgate-mcp` guard proxy
- PyPI release

## [0.1.0-alpha] - 2026-08-19 (TOAP, archived)

See `toap-v0.1-archive` branch. SDK: DSL parser, proxy middleware, CLI, prompt builder,
LangChain/CrewAI adapters, benchmark harness. Gemini-validated format compliance 100%,
net token savings ~5-6% — later re-measured negative vs fair baselines. Archived.
