# TOAP Benchmark Report

**Version:** 0.1.0-alpha  
**Date:** 2026-08-19  
**Author:** Mohammad Safwan Athar  
**Status:** Gemini-only validation — community testing needed for GPT-4o and Claude

---

## Summary

TOAP was benchmarked on **Gemini 3.5 Flash Lite** using the `toap-bench` harness. This report documents honest results including limitations.

---

## Test Configuration

| Parameter | Value |
|---|---|
| Model | gemini-3.5-flash-lite |
| Condition | few_shot_2 (grammar + 2 examples) |
| Tasks | 8 Tier-1 single tool calls |
| Runs per task | 2 |
| Total API calls | 16 |
| Temperature | 0 |

---

## Results (Best Run: benchmark_20260819_210741)

| Metric | Result | Gate Target | Pass? |
|---|---|---|---|
| TOAP compliance | **100%** (16/16) | >= 90% | YES |
| Semantic accuracy | **93.8%** (15/16) | >= 85% | YES |
| Output token savings | **44.9%** avg | >= 35% | YES (output only) |
| Net token savings | **~5.6%** avg | >= 35% | NO |

---

## Token Analysis (Honest)

| Component | Avg Tokens |
|---|---|
| Few-shot prompt overhead | ~401 |
| TOAP output | ~32 |
| JSON baseline output | ~58 |
| **Total TOAP (prompt + output)** | **~433** |
| **Total JSON equivalent** | **~459** |

**Key insight:** TOAP output is ~45% smaller than JSON, but the few-shot prompt dominates total cost. Net savings are ~5-6%, not 45%.

To improve net savings:
- Shorter prompts (fine-tuned models)
- Caching few-shot examples
- Using TOAP only for inter-agent messages (not initial prompt)

---

## Zero-Shot vs Few-Shot (Gemini)

| Condition | Compliance | Semantic Accuracy |
|---|---|---|
| Zero-shot | 93.7% | 12.5% |
| Few-shot (2 examples) | 100% | 93.8% |

**Conclusion:** Few-shot prompting is required. Zero-shot produces valid format but wrong argument names.

---

## What Passed

- Gemini reliably emits valid TOAP with 2 examples
- Proxy architecture works end-to-end (LangChain + CrewAI live agents)
- Arg alias normalization handles model naming drift (query->q, url->endpoint, etc.)

## What Has NOT Been Tested

- [ ] OpenAI GPT-4o
- [ ] Anthropic Claude 3.5 Sonnet
- [ ] Tier 2-4 tasks (multi-step, adversarial)
- [ ] 50-run statistical significance
- [ ] Zero-shot production viability

---

## Community Action Needed

Please run the benchmark on your model and report back. See [COMMUNITY_TEST.md](../../COMMUNITY_TEST.md) in repo root.

```bash
# OpenAI
python runner/benchmark.py --runs 5 --tier 1 --model gpt-4o --condition few_shot_2

# Anthropic
python runner/benchmark.py --runs 5 --tier 1 --model claude-3-5-sonnet --condition few_shot_2
```

---

## Raw Data

Latest successful run: `benchmark_20260819_210741.json` (local only, not in repo)

---

## Disclaimer

This is an alpha research prototype built in ~1 day. Numbers above are from a single model with limited runs. Do not use for production cost projections without independent validation.
