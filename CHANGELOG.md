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

### Pending (next cycles, per plan.md)
- Policy engine (constraints, approval flags, budget caps)
- Real provider token counts as the only unflagged meter source (D-016)
- Failure-scenario suite + G1 gate report
- Dry-run mode, `callgate-mcp`

## [0.1.0-alpha] - 2026-08-19 (TOAP, archived)

See `toap-v0.1-archive` branch. SDK: DSL parser, proxy middleware, CLI, prompt builder,
LangChain/CrewAI adapters, benchmark harness. Gemini-validated format compliance 100%,
net token savings ~5-6% — later re-measured negative vs fair baselines. Archived.
