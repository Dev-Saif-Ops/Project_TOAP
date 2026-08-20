# TOAP — Decisions Log

Every non-trivial choice: **what**, **why**, **why not alternatives**, **libraries**.

---

## D-001 — Pivot from community self-test to Pilot Insert Kit

**Date:** 2026-08-20  
**Decision:** Stop relying on strangers to clone + spend $3–5 + self-integrate. Build insert + measure kit instead.  
**Why:** Community liked the idea but did not run benches (senior feedback + observed behavior). Human psychology blocks unpaid work that costs money.  
**Why not:** More X/Reddit posts. Awareness already exists; conversion path was the failure.  
**Impact:** Primary engineering track = meter, schema, plain Gemini pilot, playbook.

---

## D-002 — Live LLM = Gemini only for now

**Decision:** No OpenAI/Claude spend in this track.  
**Why:** No budget for paid multi-model benches. Gemini already validates format compliance.  
**Why not:** Waiting forever for free GPT/Claude keys before shipping insert kit. Progress > perfect cross-model proof.  
**Claim language:** “Gemini-validated alpha.” Do not claim cross-model readiness.

---

## D-003 — Default insert target = plain Python + Gemini

**Decision:** Canonical pilot path is framework-free (plain functions + Gemini chat), not LangChain-first.  
**Why:** Partner stacks are unknown (Abdullah was an example only). Lowest common denominator is text-out → parse → tools.  
**Why not:** Bet everything on LangChain or CrewAI adapters first. Those remain optional thin wrappers.  
**Library:** Existing `google-genai` / dotenv only in optional example path; **core SDK stays stdlib-only**.

---

## D-004 — Core SDK has zero required dependencies

**Decision:** `toap` package `dependencies = []`. Meter, schema, encoder, compare use stdlib only.  
**Why:** Drop-in friction must be minimal for pilots. No surprise installs in partner envs.  
**Why not:** `tiktoken`, `pydantic`, `jsonschema` as hard deps. Optional later if partners need exact OpenAI token parity.  
**Token estimate:** `max(1, len(text) // 4)` heuristic when provider counts unavailable. Documented as estimate, not billing-grade.

---

## D-005 — Meter lives in the SDK, not only in toap-bench

**Decision:** `toap.meter.Meter` records proxy/LLM events and exports JSON/CSV.  
**Why:** Seniors asked for measurement apparatus *in their code path*. Bench harness is synthetic lab, not partner proof.  
**Why not:** Only extending `toap-bench/runner`. That never sits in a day-to-day agent.

---

## D-006 — Gemini price table as overridable constants

**Decision:** Estimate USD with a small built-in rate table (Flash-class defaults), overridable per Meter.  
**Why:** Partners need a visible $ number. Exact Google SKUs change; overrides avoid hardcoding forever.  
**Why not:** Live price API. Overkill and network-dependent for pilots.

---

## D-007 — Schema gate before tool(**args)

**Decision:** Optional/required field schemas on registry; fail closed before execute.  
**Why:** “Valid-but-wrong” tool calls are the dangerous failure mode (community critique). Syntax-valid TOAP ≠ safe invocation.  
**Why not:** Trust Python exceptions only. Wrong values can still succeed silently.

---

## D-008 — Fallback mode on parse/schema failure

**Decision:** Proxy supports `fallback="error"` (default) and hooks for pilot passthrough logging.  
**Why:** Inserting into a live app must not silently no-op or crash the whole agent without a clear policy.  
**Why not:** Always raise. Pilots need predictable InterceptResult for meters.

---

## D-009 — JSON ↔ TOAP encoder in core

**Decision:** Add encode helpers for baseline A/B and replay fixtures.  
**Why:** Compare path needs a deterministic JSON baseline representation without calling an LLM.  
**Why not:** LLM-only generation of TOAP for every unit test (costs quota, flaky).

---

## D-010 — Out of scope until CP3 (plain Gemini A/B works)

- Phase 2 API gateway  
- PyPI marketing push  
- ZIP/binary compression experiments  
- TOON deep integration  
- Paid GPT/Claude Tier-1 (queue when keys exist)

**Why:** Those do not remove the insert/measure blocker.

---

## D-011 — Quiz-before-accept process

**Decision:** Major AI cycles require human quiz pass before acceptance (`agents.md`).  
**Why:** Owner must understand entry points and call graph, not rubber-stamp diffs.  
**Why not:** Blind “LGTM” on large agent patches.

---

## D-012 — Critique Agent is a hard gate before quiz/accept

**Decision:** No major cycle is `ACCEPTED` until Critique Agent writes `critiques/<cycle-id>.md` with **VERDICT: PASS**, then human quiz PASS.  
**Why:** Self-review from the implementing agent is biased; overselling and schema holes already bit us in community feedback.  
**Why not:** Quiz-only gate. Quiz checks understanding; Critique checks honesty, safety, tests, scope.  
**Process:** Integration submits → Critique C1–C10 → FAIL forces REWORK → only then Architect quiz → ACCEPTED.
