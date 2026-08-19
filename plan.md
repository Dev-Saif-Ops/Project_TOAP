# TOAP — Implementation Plan

**Version:** 0.1.0-alpha  
**Last Updated:** 2026-08-19  
**Current Phase:** Phase 1 — Initial Alpha Release

---

## Phase Overview

```
Phase 0 (Now)     →  Benchmark harness → Go/No-Go
Phase 1 (Mo 1-2)  →  Open-source parser + CLI + SDK adapters
Phase 2 (Mo 3-5)  →  Hosted API Gateway
Phase 3 (Mo 6+)   →  Observability Hub (SaaS)
```

---

## Phase 0 — Benchmark Validation (Current Sprint)

**Goal:** Prove or kill the core bet before investing in product code.  
**Duration:** ~5 days  
**Budget:** $50–100 API cost

### Day 1 — Grammar + Parser

- [x] Create project docs (memory.md, prd.md, plan.md, agents.md)
- [x] Freeze TOAP grammar spec v0.1 → `toap-bench/grammar/toap_spec_v0.1.md`
- [x] Implement strict lexer/parser → `toap-bench/parser/lexer.py`
- [x] Unit tests for parser (100% coverage on synthetic strings) → `toap-bench/tests/test_lexer.py` — **19/19 passing**

**Done when:** Parser correctly validates/rejects all spec examples + 20 edge cases.

### Day 2 — Test Cases + Prompts

- [x] Write 25–30 test cases → `toap-bench/tasks/test_cases.yaml` — **22 cases across Tier 1-4**
- [x] Write 3 prompt templates → `toap-bench/prompts/`

**Done when:** Every test case has frozen ground truth + JSON baseline equivalent.

### Day 3 — Model Adapters

- [x] OpenAI adapter (GPT-4o) → `toap-bench/adapters/openai_adapter.py`
- [x] Anthropic adapter (Claude 3.5 Sonnet) → `toap-bench/adapters/anthropic_adapter.py`
- [x] Shared interface → `toap-bench/adapters/base.py`
- [x] Token counter utility → built into adapters

**Done when:** Both adapters return model output + token counts for a single test call.

### Day 4 — Benchmark Runner

- [x] Main orchestrator → `toap-bench/runner/benchmark.py`
- [x] Semantic validator (compare parsed kwargs to ground truth)
- [x] Results store (JSON/CSV per run)
- [x] Report generator (terminal summary + go/no-go verdict)
- [x] CLI entry point with flags: `--runs`, `--tier`, `--model`, `--condition`, `--dry-run`

**Done when:** `python runner/benchmark.py --runs 5 --tier 1` completes end-to-end.

### Day 5 — Run + Decide

- [ ] Run full benchmark (50 runs × 3 conditions × 2 models × Tier 1-4)
- [ ] Review results against G1–G4 gates
- [ ] Document findings in `toap-bench/results/REPORT.md`
- [ ] Update memory.md with go/no-go decision
- [ ] If GO → begin Phase 1 planning
- [ ] If NO-GO → document pivot options

---

## Phase 1 — Core Protocol & Open-Source (After Gate Pass)

**Prerequisite:** Phase 0 gates G1–G4 passed.

### Week 1–2

- [x] Extract parser from toap-bench into standalone `toap-python` package
- [ ] Publish to PyPI
- [x] Build `toap-cli` with `--pretty` dev-mode stream decoder
- [x] Write formal public language specification → `toap-python/docs/SPEC_v0.1.md`

### Week 3–4

- [x] LangChain adapter (plugin, not core dep) → `toap.adapters.langchain`
- [x] CrewAI adapter (plugin, not core dep) → `toap.adapters.crewai`
- [x] LangChain live integration example → `examples/langchain_agent.py`
- [ ] Integration tests against real agent workflows
- [ ] Publish benchmark results as reproducible documentation

### Week 5–6

- [ ] GitHub repo public release
- [x] README with quickstart (< 5 min integration)
- [ ] Begin design partner outreach

---

## Phase 2 — Enterprise API Gateway (Months 3–5)

**Prerequisite:** Phase 1 adoption signal (≥ 3 design partners integrated).

Separate infrastructure product — own timeline and budget.

- [ ] Proxy gateway service (FastAPI or similar)
- [ ] Request interception + TOAP validation pipeline
- [ ] AI firewall (reject non-conforming syntax before execution)
- [ ] Rate limiting + anomaly detection
- [ ] Server hardening (SSH, fail2ban, zero-downtime deploy)
- [ ] Docker + CI/CD pipeline
- [ ] SLA targets: 99.9% uptime, < 50ms proxy overhead

---

## Phase 3 — Observability Hub (Months 6+)

**Prerequisite:** Phase 2 gateway deployed with ≥ 1 paying customer.

- [ ] Frontend dashboard (agent chain visualization)
- [ ] Real-time token savings telemetry
- [ ] Latency + error interception metrics
- [ ] Usage-based billing (Stripe or similar)
- [ ] Enterprise seat licensing

---

## Project Structure (Target)

```
project-toap/
├── memory.md
├── plan.md
├── prd.md
├── agents.md
├── toap_executive_pitch.pdf
├── toap_architecture_strategy.pdf
│
└── toap-bench/                    ← Phase 0 (building now)
    ├── grammar/
    │   └── toap_spec_v0.1.md
    ├── parser/
    │   ├── __init__.py
    │   └── lexer.py
    ├── tasks/
    │   └── test_cases.yaml
    ├── prompts/
    │   ├── zero_shot.txt
    │   ├── few_shot_2.txt
    │   └── few_shot_5.txt
    ├── adapters/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── openai_adapter.py
    │   ├── anthropic_adapter.py
    │   └── token_counter.py
    ├── runner/
    │   ├── __init__.py
    │   └── benchmark.py
    ├── tests/
    │   └── test_lexer.py
    ├── results/
    │   └── .gitkeep
    ├── requirements.txt
    └── README.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `openai` | GPT-4o API |
| `anthropic` | Claude 3.5 API |
| `pyyaml` | Test case loading |
| `pytest` | Parser unit tests |
| `tiktoken` | OpenAI token counting |
| `python-dotenv` | API key management |

---

## Decision Log

| Date | Decision | Outcome |
|---|---|---|
| 2026-08-19 | Start with Phase 0 benchmark, not SDK | Pending |
| 2026-08-19 | Python-only for v1 | Pending |
| 2026-08-19 | GPT-4o + Claude 3.5 as initial models | Pending |
