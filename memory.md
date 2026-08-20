# TOAP — Project Memory

**Version:** 0.1.1-alpha (Pilot Insert Kit track)  
**Status:** Gemini-only live validation. Building insert + measure capability. Not sell-ready.

---

## Current mission (locked)

Replace the failed community ask (“clone + pay $3–5 + self-integrate”) with a **Pilot Insert Kit**:

1. Meter real runs (tokens, estimated $, success/fail)
2. Schema gate before tool execute
3. Plain Python + Gemini insert path + A/B compare
4. Partner playbook: we insert, they watch

**Do not** spend on OpenAI/Claude until keys/budget exist. **Do not** push Phase 2 gateway or sales campaigns as the next step.

---

## Honest metrics (Gemini Tier 1, few-shot-2)

| Metric | Value |
|---|---|
| Compliance | 100% |
| Semantic accuracy | 93.8% (arg aliases) |
| Output token savings | ~45% |
| Net token savings | ~5–6% (prompt overhead) |

Cross-model (GPT/Claude): **not run** (budget).

---

## What exists vs what was missing

| Capability | Status |
|---|---|
| Parser + aliases | Done |
| Thin proxy | Done → extended with meter/schema/fallback |
| Synthetic bench (Gemini) | Done |
| LangChain/CrewAI demos | Done (greenfield only) |
| Meter / $ report | Pilot Kit |
| Schema fail-closed | Pilot Kit |
| Plain insert + A/B | Pilot Kit |
| Partner playbook | Pilot Kit |

---

## Constraints

- Live LLM budget: **Gemini only**
- Partner stack: **unknown** → default insert target = plain Python + Gemini
- Community psychology: strangers will not pay to test our product

---

## Key docs

| File | Role |
|---|---|
| `memory.md` | Where we stand (this file) |
| `decisions.md` | Why each approach / library / scope cut |
| `EXECUTION_FLOW.md` | Entry points, call graph, AI change log |
| `agents.md` | Agent roles + **Critique PASS** + quiz-before-accept |
| `critiques/` | Per-cycle Critique Agent PASS/FAIL reports |
| `PARTNER_INSERT.md` | How to embed + measure with a builder |
| `prd.md` / `plan.md` | Original product plan (historical) |

---

## Active phases (Pilot Insert Kit)

| Phase | Goal | Status |
|---|---|---|
| P1 | Meter + RunReport | Done (Critique PASS; quiz pending) |
| P2 | Schema gate + fallback | Done (`require_schema`) |
| P3 | Encoder + compare + plain Gemini pilot | Done (offline verified) |
| P4 | Replay/fuzz fixtures | Done |
| P5 | Partner playbook | Done (`PARTNER_INSERT.md`) |

---

## Hero differentiator (unchanged)

Interceptor/proxy architecture — not the unicode syntax itself.
