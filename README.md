# TOAP — Token-Optimized Agent Protocol [ARCHIVED]

> **Discontinued 2026-08-28.** This branch is the permanent archive of TOAP v0.1.
> The successor — **callgate**, a fail-closed firewall for agent tool calls — lives on [`main`](https://github.com/Dev-Saif-Ops/Project_TOAP/tree/main).
>
> This README is the honest postmortem: what we built, what the numbers really said, and why we stopped.

---

## What TOAP was

Middleware that compressed the serialized representation of AI agent tool calls into a compact DSL, expanded back through a proxy before tools ran:

```
§T[sec_vuln_huawei_2026]
ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5
```

instead of

```json
{"thought": "...", "action": "query_database", "params": {"query": "...", "limit": 5}}
```

The bet: smaller serialization → fewer tokens → lower cost for multi-agent pipelines.

---

## What we built (all of it worked)

- Strict lexer/parser with arg-alias normalization — 19 unit tests
- Fail-closed interceptor/proxy (`parse → validate schema → dispatch tool`)
- Schema gate: valid-but-wrong args blocked **before** `tool(**args)`
- Meter: per-event token/cost accounting with JSON/CSV export
- JSON↔TOAP encoder, A/B compare, dev CLI
- LangChain + CrewAI live demos (greenfield)
- Synthetic benchmark harness (22 tasks, 4 tiers) + multi-hop Gemini pilot
- 25 tests passing at archive time

---

## What the numbers said

**Our own benchmark (Gemini 3.5 Flash Lite, Tier 1, few-shot-2, 16 calls):**

| Metric | Result |
|---|---|
| TOAP format compliance | 100% |
| Semantic accuracy | 93.8% |
| Output token savings vs JSON baseline | ~45% |
| Net savings incl. prompt overhead | ~5–6% |

**Independent re-audit (2026-08-28, real BPE tokenizers, same 8 Tier-1 tasks):**

| Compared against | TOAP result |
|---|---|
| Pretty-printed JSON (`indent=2`) — *our benchmark's baseline* | −50.8% (the source of the ~45% claim) |
| **Minified JSON — what production actually sends** | **+4.6% MORE tokens** (o200k), +11.1% (cl100k) |
| **Native function-calling arguments** | **+56% MORE tokens** |

---

## Why we dropped it — four reasons

**1. The baseline was a straw man.** `build_json_baseline()` used `json.dumps(payload, indent=2)` plus a `thought` wrapper no tool-calling API bills for. The entire headline number came from that one line.

**2. The tokenizer penalty.** Tokenizers are compression tables, not character counters. The canonical TOAP string and its minified-JSON equivalent are both 71 characters — TOAP costs 26 tokens, JSON costs 18. `{"` is one token because JSON saturates training data; `§T[` is three because `§` and `ƒ` sit outside the frequent-merge tables. The characters chosen to make TOAP distinctive were the exact characters making it expensive.

**3. The ceiling math.** A tool call is ~20–25 tokens. An agent turn is thousands (system prompt, history, tool results, reasoning). Tool-call serialization is ~1–3% of the bill — even a *perfect* compressor saves ~1% of total spend. The denominator was never checked.

**4. Platform timing.** Structured outputs (guaranteed-valid JSON, free), prompt caching, and native tool calling solved the 2023-era pain this project targeted — between the research and the build.

Our PRD §8 had a kill criterion written on day one: *"Net savings < 25% even when compliant → sell reliability/security, not cost."* Measured: ~1.5% on a favourable setup, negative on a fair one. **We honored the criterion.**

---

## What survives (on `main`, as callgate)

The part of TOAP that was never about compression:

| TOAP asset | Lives on as |
|---|---|
| Fail-closed proxy | The gate: check every tool call before it executes |
| Schema gate | Policy layer foundation |
| Meter + JSON/CSV audit | Audit trail (with real provider token counts) |
| Benchmark harness skeleton | Failure-scenario suite |
| Critique-gate dev process | Unchanged — it's what caught this |

Because the real gap was never *"tool calls are too verbose"* — it's *"a schema-valid tool call can still be wrong, dangerous, or unauthorized, and nothing stops it."* `delete_records(filter={})` is perfect JSON.

---

## Lessons (free to steal)

1. Benchmark against what production actually sends, not the prettiest version of the alternative.
2. Tokenizers are compression tables, not rulers. Measure with the real tokenizer, never `len//4`.
3. Compute the ceiling before the solution: % improvement × share of total spend = actual value.
4. Write kill criteria before writing code. Being wrong on paper is cheap.
5. If your measuring instrument can't detect your hypothesis being false, it isn't measuring.

---

## License

MIT — see [`toap-python/LICENSE`](toap-python/LICENSE)

Built by [Mohammad Safwan Athar](https://github.com/Dev-Saif-Ops) · Aug 2026 · Archived with respect for the process that killed it.
