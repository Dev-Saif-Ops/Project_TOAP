# Partner Insert Playbook

> Goal: embed TOAP + Meter into an existing agent path **without** asking the partner to spend $3–5 on our synthetic bench.

Live LLM for our dry-runs: **Gemini only** (no OpenAI/Claude budget in current pilots).

---

## What you need from a builder

| Ask | Don't ask |
|---|---|
| 30–60 minutes + screen share | “Clone and pay for GPT bench” |
| Where the model text comes out | Full rewrite of their stack |
| List of tools (name + args) | Blind trust in savings claims |
| Permission to write a meter CSV | Production deploy on day one |

---

## Insert pattern (plain Python)

```python
from toap import Meter, TOAPProxy, ToolRegistry, ToolSchema, summarize_ab
from toap.prompts import build_system_prompt

meter = Meter(model="gemini")
registry = ToolRegistry()
registry.register(
    "DB_SRC",
    their_query_fn,
    schema=ToolSchema(required=["q"], types={"q": str, "l": int}),
)
proxy = TOAPProxy(registry, meter=meter, lane="toap", require_schema=True)

system = build_system_prompt("...", shots=2)
# ... call their LLM with system + user ...
raw = llm_text_output
result = proxy.intercept(raw)
meter.export("toap_report.json", "toap_report.csv")
```

Hook point: **any place that already has model text before tools run.**

---

## Offline dry-run (no API)

```bash
cd toap-python
pip install -e .
python examples/pilot_plain_gemini.py --hops 8
```

## Live Gemini multi-hop A/B

```bash
# GEMINI_API_KEY in toap-bench/.env
python examples/pilot_plain_gemini.py --live --hops 8
toap-cli report ../toap-bench/results/pilot/pilot_live_h8.json
```

Multi-hop counts the few-shot system prompt **once** per lane, then each tool hop — closer to a real agent loop than single-shot demos.
---

## Success for a pilot session

1. Tools registered with schemas  
2. At least one real (or fixture) TOAP intercept succeeds  
3. CSV/JSON meter file left with the builder  
4. Honest read of **net** vs **output** savings (`summarize_ab`)

---

## Out of scope for first insert

- Replacing their entire framework overnight  
- Claiming OpenAI/Claude parity without runs  
- Phase 2 gateway
