# Changelog

## [Unreleased]

Both items below came out of writing the onboarding docs: the path a first-time
user actually walks turned out to hit two places where the gate raised instead of
deciding.

### Fixed
- **A wrong budget type crashed the gate instead of failing at configuration.**
  `gate.budget(max_calls_per_tool={"tool": 5})` was accepted silently and then
  raised `TypeError` from inside `check()` on the next call, so the exception
  escaped the gate rather than producing a verdict. `budget()` now validates its
  arguments where the mistake is made, with an error that says budgets apply to
  every tool. Negative values are rejected too. (Per-tool limits are a single cap
  across all tools; a dict is not supported and now says so.)
- **An inferred schema let a hallucinated argument through.**
  `schema_from_signature()` set `allow_extra=True`, so an argument the model
  invented passed the schema and then raised `TypeError` inside the tool. That
  landed as `verdict=allow, executed=False, error=...`, which is not a statement
  about whether the call was permitted. Inferred schemas now reject unexpected
  arguments, because the signature already says exactly what the callable accepts.
  A callable declaring `**kwargs` still allows extras, since it genuinely takes
  arguments we cannot enumerate. This is a behaviour change for
  `schema_from_signature()` and `register(..., infer_schema=True)`; a
  hand-written `ToolSchema` is unaffected and still defaults to `allow_extra=True`.

### Added
- `ToolSchema.optional`: known-but-not-required argument names. Only consulted
  when `allow_extra=False`, so an optional parameter with no type annotation (and
  therefore absent from `types`) is not mistaken for an unexpected argument.
- Tests grown to 130.

## [0.3.2] - 2026-08-29

### Fixed
- **A non-string tool name crashed the gate instead of blocking (security).** Every
  provider envelope extractor validated the tool name by truthiness only, so a name
  that was a dict, list, or number reached the registry lookup and raised
  `TypeError` *out of* the gate. A crash is not a verdict: the exception escapes and
  the caller's error handling decides what happens, which is not fail-closed. Tool
  names are now validated at intake; a bad name is an `IntakeError`, which the gate
  already turns into a BLOCK. Found by the new fuzz suite on its first run.

### Added
- **Property-based fuzzing of the core invariant** (`tests/test_invariant_fuzz.py`):
  2000 generated payloads per shield mode asserting that a non-ALLOW verdict never
  results in the tool running. Generators cover nested structures, empty values,
  huge ints, NaN/inf, unicode and homoglyphs, unserializable objects, wrong types,
  all four provider shapes, and lookalike tool names. Fixed seed, stdlib only, no
  new test dependency. Also asserts budgets hold under arbitrary payload streams
  with approvals always granted, that dry-run executes nothing, and that NaN/inf
  cannot read as "in range".
- Tests grown to 125.

## [0.3.1] - 2026-08-28

### Fixed
- **Budget bypass with parallel tool calls (security).** `run_all()` checked every
  call in a payload before executing any of them, so N parallel calls all saw the
  same budget counters and all passed. A `max_calls=1` budget could execute 3 calls.
  `run_all()` now checks and executes one call at a time, so counters advance
  between calls. Regression tests added for both `max_calls` and
  `max_calls_per_tool`. Reported by a reviewer; confirmed and fixed same day.
- Budget counter reads and writes are now guarded by a lock. A `Gate` is still
  intended for one agent execution context; `check_all()` documents that checking
  many calls without executing them does not advance budget state.
- **Silent tool replacement.** Registering a name twice overwrote the first tool
  (and could leave a stale policy attached). Re-registration now raises unless
  `replace=True`, and a replace drops the previous schema/policy so a new tool
  can never inherit constraints written for the old one.

### Added
- **Tool output scanning.** The shield only ever saw tool *arguments*, so a tool
  that read a secret out of a database or file handed it straight back to the
  model. Return values now get the same treatment: `block` withholds the value,
  `redact` substitutes placeholders, `warn` records findings. Disable with
  `Shield(scan_output=False)`. Output findings are tagged `return.*` and, like all
  findings, never carry the value.
- Attack suite grew a tenth class, `output-exfil`: **25/25 blocked, 0 false blocks**.
- Tests grown to 110.

## [0.3.0] - 2026-08-28

### Added
- `ToolWall`: an ergonomic facade over `Gate`, now the primary entry point.
  `ToolWall()` wires a Gate with a Shield and Meter already attached; use
  `.register(...)`, `.call(name, args)`, `.guard(response)`, `.dry_run`,
  `.report()`, `.export()`. `Gate` remains the low-level primitive.
- `GateResult.blocked`, `.needs_approval`, and `.reason` convenience properties.
- 12 new tests (97 total).

### Changed
- Problem-led positioning across both READMEs ("The security gateway for AI
  agent tool calls"), attack-example blocks, expanded PyPI keywords for
  discovery (ai-agent-security, mcp-firewall, prompt-injection, ...).

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
