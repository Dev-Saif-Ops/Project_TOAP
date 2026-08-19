# Changelog

## [0.1.0-alpha] - 2026-08-19

### Added
- `toap-python` SDK: parser, proxy middleware, CLI, prompt builder
- LangChain adapter with `build_toap_chain()` and live Gemini example
- CrewAI adapter with `build_toap_crew()` and live Gemini example
- `toap-bench` automated benchmark harness
- Dev-mode CLI (`toap-cli pretty`, `toap-cli validate`)
- Arg alias normalization (url->endpoint, query->q, etc.)

### Validated (Gemini 3.5 Flash Lite only)
- 100% TOAP format compliance (Tier 1, few-shot-2)
- 93.8% semantic accuracy with alias layer
- ~45% output token reduction vs JSON baseline
- LangChain + CrewAI live agent examples working

### Known Limitations
- Only tested on Gemini — GPT-4o and Claude need community validation
- Net token savings ~5-6% when including few-shot prompt overhead
- Tier 2-4 benchmark tasks not yet run
- No PyPI publish yet — install via `pip install -e ./toap-python`

### Community Request
- Please test on OpenAI GPT-4o and Anthropic Claude 3.5 — see COMMUNITY_TEST.md
