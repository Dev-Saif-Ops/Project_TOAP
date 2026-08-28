# callgate (package)

Fail-closed firewall for AI agent tool calls. See the [repo README](../README.md) for the full story.

```bash
pip install -e .
python examples/quickstart.py   # no API key needed
pytest                          # run the suite
```

## Modules

| Module | Role |
|---|---|
| `intake.py` | Normalize OpenAI / Anthropic / Gemini / plain-dict tool calls |
| `gate.py` | Fail-closed check → verdict → (optional) execute |
| `schema.py` | Required args + type validation before `tool(**args)` |
| `meter.py` | Audit events, token/cost accounting, JSON/CSV export |
| `cli.py` | `callgate report <audit.json>` |
