# TOAP — Token-Optimized Agent Protocol

> **Initial Release (v0.1.0-alpha)** — Built and tested on **Gemini**. Needs community validation on **OpenAI (GPT-4o)** and **Anthropic (Claude 3.5)**.

Middleware that compresses AI agent communication into a deterministic DSL — reducing verbose JSON token costs without migrating off LangChain or CrewAI.

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

---

## What's included

| Component | Path | Description |
|---|---|---|
| **SDK** | `toap-python/` | Parser, proxy middleware, CLI, LangChain/CrewAI adapters |
| **Benchmark** | `toap-bench/` | Automated harness to test model compliance + token savings |
| **Docs** | `prd.md`, `plan.md`, `memory.md` | Product spec and decisions |

---

## Quick Start

```bash
# 1. Install SDK
cd toap-python
pip install -e ".[langchain-gemini,crewai-gemini]"

# 2. Try the quickstart
python examples/quickstart.py

# 3. Run LangChain live agent (needs GEMINI_API_KEY)
python examples/langchain_agent.py

# 4. Run CrewAI live agent (needs GEMINI_API_KEY)
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
