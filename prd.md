# TOAP — Product Requirements Document

**Version:** 0.1.0-alpha  
**Status:** Initial release — Gemini validated, community testing needed  
**Author:** Mohammad Safwan Athar  
**Last Updated:** 2026-08-19

---

## 1. Problem Statement

Enterprise AI pipelines using multi-agent orchestration (LangChain, CrewAI) communicate via verbose JSON payloads. This causes:

- **Token bloat** — up to 3× unnecessary tokens, costing tens of thousands/month at scale
- **Latency** — longer sequences = slower LLM responses in multi-step chains
- **Structural hallucinations** — LLMs break JSON (missing commas, bad brackets), causing cascading failures
- **Prompt injection** — conversational keys provide attack surface for hijacking agent behavior

**Root cause:** Developers use human-readable conversational formats for programmatic machine-to-machine logic.

---

## 2. Product Vision

TOAP is an interceptor/proxy middleware that compresses agent-to-agent communication into a deterministic DSL — reducing token costs, improving reliability, and hardening security — without requiring teams to rewrite their AI logic or migrate off existing orchestration frameworks.

---

## 3. Target Users (ICP)

| Persona | Role | Pain |
|---|---|---|
| **Platform Engineer** | Manages AI infra at scale | API cost burn, unreliable agent chains |
| **AI Architect** | Designs multi-agent systems | JSON breakage, debugging opaque failures |
| **DevOps Lead** | Owns CI/CD + security | Prompt injection, no visibility into agent traffic |

**Not targeting:** Hobbyists, junior devs, single-prompt chat apps.

---

## 4. Hero Differentiator

**The Interceptor/Proxy Architecture.**

> Seamless middleware. No framework migration. Instant token savings.

The unicode DSL syntax is an implementation detail, not the selling point. MCP and native JSON modes are the competitive context — TOAP differentiates on plug-and-play proxy integration.

---

## 5. Core Features by Phase

### Phase 0 — Benchmark Validation (Current)

| ID | Feature | Priority |
|---|---|---|
| P0-F1 | TOAP grammar spec v0.1 (frozen) | P0 |
| P0-F2 | Strict lexer/parser with unit tests | P0 |
| P0-F3 | Test case registry (25–30 tasks, Tier 1–5) | P0 |
| P0-F4 | Prompt templates (zero-shot, few-shot 2, few-shot 5) | P0 |
| P0-F5 | Model adapters (GPT-4o, Claude 3.5 Sonnet) | P0 |
| P0-F6 | Benchmark runner with automated report | P0 |
| P0-F7 | Go/no-go decision matrix output | P0 |

**Exit criteria:** Gates G1–G4 pass (see Section 8).

### Phase 1 — Core Protocol & Open-Source Seed (Months 1–2)

| ID | Feature | Priority |
|---|---|---|
| P1-F1 | `toap-python` parser library (PyPI publish) | P0 |
| P1-F2 | Dev-mode CLI pretty-printer (`toap-cli --pretty`) | P0 |
| P1-F3 | LangChain adapter (loose-coupled plugin) | P1 |
| P1-F4 | CrewAI adapter (loose-coupled plugin) | P1 |
| P1-F5 | Benchmark documentation with reproducible results | P0 |
| P1-F6 | Formal TOAP language specification (public) | P1 |

**Prerequisite:** Phase 0 gates passed.

### Phase 2 — Enterprise API Gateway (Months 3–5)

| ID | Feature | Priority |
|---|---|---|
| P2-F1 | Hosted proxy gateway (intercept, validate, route) | P0 |
| P2-F2 | Real-time syntax validator (AI firewall) | P0 |
| P2-F3 | Rate limiting + anomaly detection | P1 |
| P2-F4 | Server hardening (SSH, fail2ban, zero-downtime deploy) | P0 |

**Note:** Phase 2 is a separate infrastructure product — own eng budget and SLA targets.

### Phase 3 — Observability Hub (Months 6+)

| ID | Feature | Priority |
|---|---|---|
| P3-F1 | Dashboard — agent chain visualization | P0 |
| P3-F2 | Real-time token savings telemetry | P0 |
| P3-F3 | Latency + error interception metrics | P1 |
| P3-F4 | Usage-based billing integration | P1 |

---

## 6. TOAP Syntax Specification v0.1

### Grammar Overview

```
toap_output   ::= thought_line? action_line
thought_line  ::= "§T[" domain "]"
action_line   ::= "ƒ(" namespace ")>" arg_list
domain        ::= identifier
namespace     ::= identifier
arg_list      ::= arg ("|" arg)*
arg           ::= key ":" value
key           ::= identifier
value         ::= string | number | identifier
identifier    ::= [a-zA-Z_][a-zA-Z0-9_]*
string        ::= '"' [^"]* '"'
number        ::= [0-9]+
```

### Example

```
§T[sec_vuln_huawei_2026]
ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5
```

| Token | Meaning |
|---|---|
| `§T[domain]` | Thought/state — anchors LLM attention to operational domain |
| `ƒ(namespace)` | Executable tool/action target |
| `>key:value\|key:value` | Pipe-delimited positional arguments |

### Parser Requirements

- Strict validation — reject any non-conforming output locally
- Zero-downtime health check before execution attempt
- Translate parsed output to exact Python kwargs for tool invocation
- No fuzzy matching in v1 — exact match only

---

## 7. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Parser latency | < 5ms per string (local) |
| Parser test coverage | 100% on synthetic strings |
| Framework coupling | Adapter pattern — core has zero LangChain/CrewAI imports |
| Dev-mode CLI | Human-readable decode of any TOAP stream in terminal |
| Benchmark reproducibility | Fixed seeds, versioned grammar hash in every result |
| API cost for full benchmark | ≤ $100 |

---

## 8. Success Metrics & Go/No-Go Gates

### Phase 0 Gates

| Gate | Metric | Pass | Fail Action |
|---|---|---|---|
| **G1 — Compliance** | Few-shot parse success rate (Tier 1) | ≥ 90% | Require 5-shot or redesign syntax |
| **G2 — Accuracy** | Semantic correctness when parseable | ≥ 85% | Fix grammar or abandon DSL |
| **G3 — Savings** | Net token reduction vs JSON baseline | ≥ 35% | Pivot hero to reliability/security |
| **G4 — Reliability** | End-to-end task success with ≤ 1 retry | ≥ 85% | TOAP adds more cost than it saves |

### Kill Criteria

- Few-shot compliance < 80% → pivot to JSON minification proxy, not custom DSL
- Net savings < 25% even when compliant → sell reliability/security, not cost

### Compression Claim Language

> "Up to ~45% output token reduction observed on Gemini 3.5 Flash Lite with few-shot prompting. Net savings including prompt overhead: ~5-6%. Pending validation on GPT-4o and Claude."

Do NOT claim guaranteed savings without model-specific benchmark data.

---

## 9. Monetization

| Stream | Model | When |
|---|---|---|
| Open-source parser | Free (Trojan horse) | Phase 1 |
| Observability SaaS | Per 1K requests or enterprise seats | Phase 3 |
| B2B consulting | Fixed-price integration contracts | Parallel from Phase 1 |

---

## 10. Out of Scope (v1)

- Fine-tuning models on TOAP syntax
- Support for models beyond GPT-4o and Claude 3.5
- Multi-language parser (Python only for v1)
- Real-time streaming proxy
- Mobile or native app clients

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Model won't emit valid TOAP | Product doesn't work | Phase 0 benchmark — fail fast |
| Few-shot prompt overhead eats savings | Weak cost wedge | Measure net tokens per success, not output only |
| LangChain/CrewAI breaking changes | Maintenance burden | Loose-coupled adapter pattern |
| MCP / JSON mode as "good enough" | No differentiation | Lead with proxy ease + observability, not syntax |
| Compressed logs unreadable | Dev rejection | Dev-mode CLI in Phase 1, not Phase 3 |
| Phase 2 infra scope creep | Delayed revenue | Budget Phase 2 as separate product line |

---

## 12. Open Questions

- [ ] Will Claude 3.5 outperform GPT-4o on TOAP compliance?
- [ ] Is 2-example few-shot enough, or do we need 5?
- [ ] Should v1 include a JSON-minification fallback mode if DSL fails gates?
- [ ] What's the minimum viable adapter surface for LangChain vs CrewAI?
