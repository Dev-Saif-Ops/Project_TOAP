# Community Testing Guide

> Help validate TOAP on OpenAI and Anthropic models. Takes ~10 minutes.

The author tested TOAP on **Gemini 3.5 Flash Lite** only. We need results from **GPT-4o** and **Claude 3.5 Sonnet** before claiming cross-model compatibility.

---

## What you'll run

The benchmark harness sends 8 standard agent tasks to an LLM, checks if the output is valid TOAP, and compares token usage vs JSON baseline.

---

## Prerequisites

- Python 3.10+
- An API key for the model you're testing

---

## Test on OpenAI (GPT-4o)

```bash
# 1. Clone/download this repo and install
cd toap-bench
pip install -r requirements.txt
pip install -e ../toap-python

# 2. Set your key
cp .env.example .env
# Edit .env:
#   OPENAI_API_KEY=sk-your-key-here

# 3. Run benchmark (Tier 1, 5 runs, ~$3-5)
python runner/benchmark.py --runs 5 --tier 1 --model gpt-4o --condition few_shot_2

# 4. Share the terminal output + results file path with the author
```

---

## Test on Anthropic (Claude 3.5 Sonnet)

```bash
# Same setup, but in .env:
#   ANTHROPIC_API_KEY=sk-ant-your-key-here

python runner/benchmark.py --runs 5 --tier 1 --model claude-3-5-sonnet --condition few_shot_2
```

---

## Test on Gemini (reproduce author's results)

```bash
# In .env:
#   GEMINI_API_KEY=your-key
#   GEMINI_MODEL=gemini-3.5-flash-lite

python runner/benchmark.py --runs 5 --tier 1 --model gemini --condition few_shot_2
```

---

## What to report back

Copy the **GO / NO-GO VERDICT** section from terminal output:

```
Compliance rate     : ??%
Semantic accuracy   : ??%
Avg token savings   : ??%
```

Also mention:
- Model name and version
- Any failures or weird outputs
- Whether you used zero-shot or few-shot (use `few_shot_2` as above)

Share results via GitHub issue, Discord, or whatever channel the author shared this in.

---

## Optional: Try the live agents

```bash
cd toap-python

# LangChain + Gemini
pip install -e ".[langchain-gemini]"
python examples/langchain_agent.py

# LangChain needs OPENAI or ANTHROPIC key — edit examples to swap model
# CrewAI
pip install -e ".[crewai-gemini]"
python examples/crewai_agent.py
```

---

## Understanding the metrics

| Metric | What it means | Good target |
|---|---|---|
| **Compliance** | LLM output valid TOAP syntax | >= 90% |
| **Semantic accuracy** | Correct tool + args after parsing | >= 85% |
| **Token savings** | Output tokens vs JSON baseline | >= 35% output-only |

**Note:** Few-shot prompts add ~400 tokens overhead. Net savings (prompt + output) will be much lower than output-only savings. Report both if possible.

---

## Questions?

Open an issue or reach out to the author directly.
