# Share this in your community

Copy-paste template:

---

**TOAP — Token-Optimized Agent Protocol (v0.1 alpha)**

I built a middleware that compresses AI agent communication into a smaller syntax instead of verbose JSON — aimed at cutting LLM token costs in multi-agent pipelines.

**What I tested:**
- Gemini 3.5 Flash Lite
- 100% TOAP format compliance (with 2 few-shot examples)
- ~45% smaller output vs JSON (net savings lower due to prompt overhead — see report)
- Works with LangChain + CrewAI live agents

**What I need from you:**
Please run the benchmark on **GPT-4o** or **Claude 3.5 Sonnet** and share results back.

**Quick test (10 min, ~$5 API cost):**
```
git clone <repo-url>
cd project-toap/toap-bench
pip install -r requirements.txt && pip install -e ../toap-python
cp .env.example .env   # add your OPENAI or ANTHROPIC key
python runner/benchmark.py --runs 5 --tier 1 --model gpt-4o --condition few_shot_2
```

Full instructions: see `COMMUNITY_TEST.md` in the repo.

Repo includes: SDK, benchmark harness, LangChain/CrewAI examples, honest benchmark report.

MIT licensed. Alpha — not production-ready yet.

---
