# TOAP — Execution Flow

How control travels through the codebase. Update the **AI change log** every cycle.

---

## Repository entry points

| Entry | Path | Role |
|---|---|---|
| SDK import | `toap-python/src/toap/__init__.py` | Public exports |
| CLI | `toap-cli` → `toap.cli:main` | `pretty`, `validate`, `report` |
| Offline demo | `toap-python/examples/quickstart.py` | Parse + proxy (no LLM) |
| Live LC demo | `examples/langchain_agent.py` | Gemini + LangChain chain |
| Live Crew demo | `examples/crewai_agent.py` | Gemini + CrewAI |
| Plain pilot | `examples/pilot_plain_gemini.py` | A/B insert kit (Gemini) |
| Bench | `toap-bench/runner/benchmark.py` | Synthetic Tier-1+ harness |

---

## Core runtime call graph (SDK)

```
LLM text (or fixture string)
        │
        ▼
TOAPProxy.intercept(raw)
        │
        ├─► TOAPParser.parse(raw)
        │         └─► normalize_args / aliases
        │
        ├─► (optional) schema.validate(namespace, args)
        │         └─► fail → InterceptResult(error=...)  [no execute]
        │
        ├─► ToolRegistry.get(namespace)
        │         └─► tool(**args)
        │
        └─► Meter.record(RunEvent)   [if meter attached]
                  └─► export JSON/CSV
```

### Encoder / compare (pilot A/B)

```
task / expected tool call dict
        │
        ├─► encode_tool_call(...) → TOAP string → proxy path → Meter
        │
        └─► json.dumps(baseline) → token estimate → Meter (baseline lane)
                 │
                 └─► compare.summarize(baseline_report, toap_report)
```

---

## Module responsibilities

| Module | Function |
|---|---|
| `parser.py` | Lex/parse TOAP; aliases; pretty_print |
| `proxy.py` | Intercept → validate → dispatch tools |
| `meter.py` | RunEvent log; token/cost estimate; export |
| `schema.py` | ToolSchema; validate args before execute |
| `encoder.py` | Structured call → TOAP string |
| `compare.py` | Baseline vs TOAP report summary |
| `prompts.py` | System prompt + few-shot builder |
| `adapters/*` | Framework glue (not core) |
| `cli.py` | Dev tools |

---

## Bench path (separate from SDK product path)

```
benchmark.py main
  → load test_cases.yaml + prompts
  → model adapter.complete(...)
  → TOAPParser.parse
  → score compliance / semantic / tokens vs JSON baseline
  → write results/*.json|csv + print gates
```

Bench proves **lab** metrics. Meter proves **path** metrics inside an app.

---

## What AI changed this cycle

**Cycle ID:** `pilot-kit-2026-08-20`  
**Critique:** PASS — see `critiques/pilot-kit-2026-08-20.md`  
**Human quiz:** PASS (re-quiz 2026-08-20; owner demonstrated entry-point + gate understanding)  
**Status:** ACCEPTED

### Accept criteria
1. Critique VERDICT PASS (done)
2. Human quiz PASS (done)

**Acceptance:** `ACCEPTED`
