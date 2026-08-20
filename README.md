# TOAP — Token-Optimized Agent Protocol

> **v0.1.1-alpha** — Gemini-validated. **Pilot Insert Kit** in progress (meter + schema + plain insert).  
> Not production-ready. Cross-model (GPT/Claude) not run (no budget). Community self-pay benches are optional, not the primary validation path.

Middleware that compresses the *serialized representation* of AI agent tool calls into a compact DSL, then expands via a proxy before tools run.

---

## What is this?

When AI agents talk to each other, they use bloated JSON. TOAP replaces that with a compressed syntax:

```
§T[sec_vuln_huawei_2026]
ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5
```

Instead of:
```json
{"thought": "...", "action": "query_database", "params": {"query": "...", "limit": 5}}
```

**Honest status:** LangChain/CrewAI demos exist (greenfield). Drop-in into an *existing* production agent is still early; use the plain Gemini pilot example to measure locally.

---

## What's included

| Component | Path | Description |
|---|---|---|
| **SDK** | `toap-python/` | Parser, proxy, meter, schema gate, encoder, CLI, adapters |
| **Pilot path** | `toap-python/examples/pilot_plain_gemini.py` | Offline/live multi-hop A/B + CSV/JSON meter export |
| **Community test** | `COMMUNITY_TEST.md` | Optional self-serve harness steps |
| **Benchmark** | `toap-bench/` | Synthetic Gemini Tier-1 harness + reports |

---

## Quick Start

```bash
# 1. Install SDK
cd toap-python
pip install -e .

# 2. Offline pilot (no API cost) — meter A/B CSV
python examples/pilot_plain_gemini.py

# 3. Quickstart (parse + proxy + meter)
python examples/quickstart.py

# 4. Optional live Gemini / framework demos (needs GEMINI_API_KEY)
pip install -e ".[langchain-gemini,crewai-gemini]"
python examples/langchain_agent.py
python examples/crewai_agent.py
```

---

## Gemini Test Results (by author)

Tested on **Gemini 3.5 Flash Lite** with few-shot prompting (2 examples):

| Metric | Result |
|---|---|
| TOAP format compliance | **100%** (16/16 runs, Tier 1) |
| Tool execution accuracy | **93.8%** (with arg alias normalization) |
| Output token savings vs JSON | **~45%** (output only) |
| Net token savings (incl. prompt) | **~5-6%** (few-shot prompt is ~400 tokens) |

Full details: [`toap-bench/results/REPORT.md`](toap-bench/results/REPORT.md)

---

## Community Request

I've only tested this on **Gemini**. I need your help testing on:

- **OpenAI GPT-4o**
- **Anthropic Claude 3.5 Sonnet**

See **[COMMUNITY_TEST.md](COMMUNITY_TEST.md)** for step-by-step instructions. Takes ~10 minutes and ~$5 in API credits.

Please share your results — compliance %, accuracy %, and token savings.

---

## Architecture

```
Your Framework (LangChain / CrewAI)
        |
TOAP Proxy (parse + validate + alias normalize)
        |
LLM API (Gemini / GPT-4o / Claude)
```

---

## Status

| Phase | Status |
|---|---|
| Phase 0 — Benchmark | Gemini validated, Claude/GPT pending community |
| Phase 1 — SDK | Alpha release (this repo) |
| Phase 2 — API Gateway | Not started |
| Phase 3 — Observability SaaS | Not started |

---

## License

MIT — see [`toap-python/LICENSE`](toap-python/LICENSE)

---

Built by [Mohammad Safwan Athar](https://github.com/Dev-Saif-Ops) | Initial release August 2026
