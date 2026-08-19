# TOAP Benchmark Harness

Automated benchmark to test LLM compliance with TOAP syntax and measure token savings.

## Quick Start

```bash
pip install -r requirements.txt
pip install -e ../toap-python
cp .env.example .env   # add your API keys
python runner/benchmark.py --runs 5 --tier 1 --model gemini --condition few_shot_2
```

## Models

| Flag | Model |
|---|---|
| `--model gemini` | Gemini (set GEMINI_MODEL in .env) |
| `--model gpt-4o` | OpenAI GPT-4o |
| `--model claude-3-5-sonnet` | Anthropic Claude 3.5 Sonnet |

## Community Testing

See [COMMUNITY_TEST.md](../COMMUNITY_TEST.md) in repo root.

## Results

See [results/REPORT.md](results/REPORT.md) for author's Gemini results.
