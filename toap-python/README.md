# TOAP — Token-Optimized Agent Protocol

Middleware for compressed AI agent communication. **v0.1.0-alpha**

> Tested on Gemini. Needs community validation on GPT-4o and Claude — see [COMMUNITY_TEST.md](../COMMUNITY_TEST.md).

## Install

```bash
pip install -e .
pip install -e ".[langchain-gemini]"   # LangChain + Gemini
pip install -e ".[crewai-gemini]"     # CrewAI + Gemini
```

## Quick Example

```python
from toap import TOAPParser, TOAPProxy, ToolRegistry

parser = TOAPParser()
result = parser.parse('ƒ(DB_SRC)>q:"Huawei vulnerabilities"|l:5')
print(result.valid, result.args)

registry = ToolRegistry()
registry.register("DB_SRC", lambda q, l=10: {"rows": l})
proxy = TOAPProxy(registry)
print(proxy.intercept('ƒ(DB_SRC)>q:"test"|l:3').return_value)
```

## CLI

```bash
python -m toap.cli pretty -f output.log
python -m toap.cli validate outputs.txt
```

## Live Examples

```bash
python examples/langchain_agent.py   # LangChain + Gemini
python examples/crewai_agent.py      # CrewAI + Gemini
python examples/quickstart.py        # No API key needed
```

## Benchmark Results (Gemini only)

| Metric | Result |
|---|---|
| Compliance | 100% |
| Accuracy | 93.8% |
| Output savings | ~45% |
| Net savings | ~5-6% |

Full report: [toap-bench/results/REPORT.md](../toap-bench/results/REPORT.md)

## Spec

[docs/SPEC_v0.1.md](docs/SPEC_v0.1.md)

## License

MIT
