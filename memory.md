# TOAP — Token-Optimized Agent Protocol

**Version:** 0.1.0-alpha  
**Status:** Initial release — Gemini validated, community testing needed

---

## Project Status

| Field | Value |
|---|---|
| **Release** | v0.1.0-alpha (August 2026) |
| **Validated on** | Gemini 3.5 Flash Lite only |
| **Needs testing** | GPT-4o, Claude 3.5 Sonnet |
| **Phase** | Phase 1 alpha — open-source seed |

## Core Bet (Partially Validated)

Models can emit valid TOAP syntax with few-shot prompting. **Confirmed on Gemini.** Pending on OpenAI/Claude.

## Honest Metrics (Gemini, Tier 1, few-shot-2)

| Metric | Value |
|---|---|
| Compliance | 100% |
| Semantic accuracy | 93.8% (with arg aliases) |
| Output token savings | ~45% |
| Net token savings | ~5-6% (prompt overhead dominates) |

## Hero Differentiator

Interceptor/proxy architecture — drop in middleware, keep your framework.

## Go/No-Go Gates

| Gate | Gemini Result | Cross-model |
|---|---|---|
| G1 Compliance | PASS (100%) | Pending GPT/Claude |
| G2 Accuracy | PASS (93.8%) | Pending GPT/Claude |
| G3 Output savings | PASS (~45%) | Pending |
| G3 Net savings | FAIL (~5.6%) | Pending |

## Current Focus

Community validation on OpenAI and Anthropic. See COMMUNITY_TEST.md.

## Key Files

- `README.md` — project overview
- `COMMUNITY_TEST.md` — how to test on your model
- `toap-bench/results/REPORT.md` — honest benchmark report
- `toap-python/` — SDK package
- `CHANGELOG.md` — release notes
