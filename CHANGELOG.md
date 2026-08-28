# Changelog

## [0.2.2] - 2026-08-28

Docs release: brings the PyPI page in sync with the repo.

### Changed
- Both READMEs gained a step-by-step "How to use" flow and an "Examples" section
  listing all four example scripts, including the live Gemini agent
  (`examples/live_gemini_agent.py`). Repo renamed to `toolwall`; all links updated.
  No code changes; 85 tests unchanged.

## [0.2.1] - 2026-08-28

Docs-only release to give the PyPI project page a proper landing description.

### Changed
- Rich PyPI-facing README (`toolwall/README.md`): badges, problem statement,
  quickstart, feature list, dry-run + MCP examples, honest-status section, links.
  No code changes; 85 tests unchanged. (PyPI descriptions are per-release, so a
  version bump is required to refresh the page.)

## [0.2.0-dev] - 2026-08-28 — Pivot: TOAP → toolwall

### Why
TOAP's compression thesis failed an honest re-measurement: vs minified JSON it was
+4.6% tokens (o200k) / +11.1% (cl100k); vs native function-calling arguments +56%.
The ~45% claim traced to an `indent=2` baseline. Our own PRD kill criterion
("net < 25% → sell reliability/security, not cost") was met, so we honored it.
Full postmortem: `toap-v0.1-archive` branch README.

### Added
- `toolwall` package: fail-closed firewall for agent tool calls
- `intake.py`: OpenAI (chat + responses), Anthropic, Gemini, and plain-dict tool-call normalization
- `gate.py`: `Gate` with `default="deny"|"allow"`, `check`/`execute` split, `run`/`run_all`, verdict enum
- Audit events for every verdict via surviving `Meter` (JSON/CSV export)
- `toolwall report` CLI
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

### Added (phase1-dryrun cycle, same day)
- Dry-run mode: `Gate(dry_run=True)` simulates ALLOW calls (budget still enforced), never executes; `GateResult.dry_run` flag
- `gate.report()`: verdict counts, per-tool table, blocked reasons, secret findings by kind
- `suggest.py`: `suggest_policies(gate)` turns observed calls into a reviewable draft of `register()` calls (schema required/types, `in_range` from observed numerics, `one_of` from small string sets)
- `examples/dangerous_agent_demo.py`: same six off-the-rails tool calls replayed ungated (table wiped, secret emailed, unauthorized deploy) vs gated (1 allowed, 5 blocked, world untouched)
- Test suite grown to 76 tests

### Added (phase1-dryrun cycle, same day)
- Dry-run mode: `Gate(dry_run=True)` simulates execution for ALLOW verdicts; blocks still block; `GateResult.dry_run` marks simulated steps
- `Gate.history` + `Gate.report()`: verdict counts, per-tool breakdown, blocked reasons, secret-finding kinds (value-free)
- `suggest.py` `suggest_policies()`: turns observed calls into a reviewable draft of `register()` + `ToolSchema` + `Policy` (ranges/enums from observed values; every line flagged for human review)
- `examples/dangerous_agent_demo.py`: an off-the-rails agent replayed with vs without the gate (defensive demonstration; no real side effects)
- Tests grown to 76

### Added (phase1-mcp cycle, same day)
- `mcp_guard.py`: `MCPGuard` puts a Gate in front of any MCP server; only ALLOW calls forward, blocks/held return an MCP-style tool error (`to_mcp_error`). Decision core is framework-free and fully unit-tested without an MCP install
- Shield redaction is applied to forwarded args (server never sees the secret)
- `mcp` optional extra (`pip install toolwall[mcp]`); core stays stdlib-only
- `examples/mcp_guard_demo.py`
- D-020: neutral vocabulary in defensive fixtures (avoids content-classifier false flags); suite classes renamed, coverage unchanged
- Tests grown to 85

### Added (phase1-release cycle, same day)
- Verified the package builds (`python -m build`), passes `twine check`, and installs
  clean into a fresh venv with zero required deps (only `mcp`/`dev` extras)
- `toolwall/RELEASING.md`: manual, owner-run publish steps (Test PyPI first)
- `mcp>=1.0.0` optional extra confirmed in built metadata

### Pending (next cycles, per plan.md)
- MCP stdio transport wiring (lands with first real pilot)
- PyPI publish (manual step, owner runs with their own token)
- Approval CLI UX

## [0.1.0-alpha] - 2026-08-19 (TOAP, archived)

See `toap-v0.1-archive` branch. SDK: DSL parser, proxy middleware, CLI, prompt builder,
LangChain/CrewAI adapters, benchmark harness. Gemini-validated format compliance 100%,
net token savings ~5-6% — later re-measured negative vs fair baselines. Archived.
