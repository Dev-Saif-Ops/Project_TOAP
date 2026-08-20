# TOAP — Agent Roles & Development Workflow

> Agent personas + **Critique gate** + **quiz-before-accept**.  
> **No major cycle is ACCEPTED until Critique Agent = PASS and human quiz = PASS.**

---

## Hard gates (non-negotiable)

```
Implementation cycle
        │
        ▼
Critique Agent  ──FAIL──► REWORK (do not quiz, do not accept)
        │
       PASS
        │
        ▼
Architect quizzes human ──FAIL──► REWORK / re-teach
        │
       PASS
        │
        ▼
EXECUTION_FLOW.md → Acceptance: ACCEPTED
```

| Gate | Owner | Block on fail |
|---|---|---|
| **Critique PASS** | Critique Agent | Yes — always |
| **Human quiz PASS** | Architect + human | Yes — major cycles |
| Unit tests green | Integration / Parser | Yes — before critique can PASS |

Minor typo/docs-only: Critique may be `N/A (docs-only)` with Architect sign-off.  
Anything touching `proxy`, `parser`, `meter`, `schema`, `encoder`, `compare`, adapters, CLI, or public API: **full Critique required**.

---

## Agent Roster

### 1. Architect Agent

**Role:** Product architect + engineering lead  
**Scope:** Gates, scope cuts, `memory.md`, `decisions.md`, pilot vs sell  
**Rules:**
- Gemini-only live until budget exists
- No Phase 2 gateway until insert kit + ≥1 dry-run
- Challenge savings claims with net vs output honesty
- Hero = proxy, not syntax
- **Must not mark ACCEPTED without Critique PASS**

**Outputs:** verdicts, scope locks, human quiz

---

### 2. Parser Agent

**Role:** Grammar + lexer/parser  
**Scope:** `toap-python/src/toap/parser.py`, grammar docs, lexer tests  
**Rules:** Grammar frozen during benches; strict validation; aliases in `decisions.md`

---

### 3. Benchmark Agent

**Role:** Harness + reporting  
**Scope:** `toap-bench/`  
**Rules:** Tier 1 first; no cherry-picking; do not depend on stranger $3–5 spends

---

### 4. Integration Agent

**Role:** Insert kit + adapters  
**Scope:** `proxy`, `meter`, `schema`, `encoder`, `compare`, adapters, `PARTNER_INSERT.md`  
**Rules:**
- Core framework-free; default pilot = plain Python + Gemini
- Always wire Meter into live paths
- Submit work to Critique before asking for accept

---

### 5. DevOps Agent

**Role:** Gateway / deploy — **BLOCKED** until Architect unblocks after pilot proof

---

### 6. Dev-Experience Agent

**Role:** CLI, examples, docs  
**Rules:** CLI decodes every TOAP string; examples show meter output

---

### 7. Critique Agent (HARD GATE)

**Role:** Adversarial reviewer — assumes the change is oversold until proven otherwise  
**Scope:** Entire cycle: code, docs, claims, tests, security, scope creep  
**Invoked when:** Any major implementation cycle is proposed as “done”

**Must check (all applicable):**

| Check ID | Question | Fail if |
|---|---|---|
| C1 Honesty | Do README/memory/partner docs overclaim savings or “drop-in”? | Inflated claims |
| C2 Scope | Did we build gateway/PyPI/sales fluff instead of insert kit? | Scope creep |
| C3 Safety | Can valid-but-wrong args still execute when schema registered? | Schema bypass |
| C4 Meter | Is measurement real (exportable) or theater? | No JSON/CSV path |
| C5 Deps | Did core gain heavy required dependencies without decision? | Undocumented deps |
| C6 Tests | Do new paths have failing-risk coverage (schema, fuzz, replay)? | Untested critical path |
| C7 Flow docs | Is `EXECUTION_FLOW.md` / `decisions.md` updated this cycle? | Missing trail |
| C8 Budget | Does anything require OpenAI/Claude spend as mandatory? | Breaks Gemini-only lock |
| C9 Fallback | Parse/schema failure policy clear (no silent wrong tool)? | Silent failure |
| C10 Reversibility | Can we state what was *not* done? | Kitchen-sink PR |

**Verdict format (required in `critiques/`):**

```
[Agent: Critique] Cycle <id>
C1..C10: PASS|FAIL|N/A — <one line each>
VERDICT: PASS | FAIL
BLOCKERS: <list or none>
REWORK: <exact fixes required if FAIL>
```

**Rules:**
- Critique Agent **cannot** grade its own implementation (Integration must not self-PASS)
- FAIL means Architect must not run accept quiz until REWORK done and Critique re-run
- PASS is provisional until unit tests are green in the same cycle
- Write report to `critiques/<cycle-id>.md`

**Outputs:** `critiques/<cycle-id>.md` with PASS/FAIL

---

## Active workflow: Pilot Insert Kit

```
Architect  → locks Gemini-only + insert kit scope (decisions.md)
     │
     ▼
Integration → P1 Meter → P2 Schema → P3 Encoder/Compare/Pilot
     │                      → P4 Replay → P5 Playbook
     ▼
Dev-Experience → wire examples + CLI
     │
     ▼
Critique Agent → PASS / FAIL (+ critiques/*.md)
     │
    PASS only
     ▼
Architect → quiz human → PASS / FAIL
     │
    both PASS
     ▼
Acceptance: ACCEPTED in EXECUTION_FLOW.md
```

---

## Communication protocol

```
[Agent: <name>] <action>
```

Examples:
```
[Agent: Integration] Pilot kit modules landed. Submitting to Critique.
[Agent: Critique] Cycle pilot-kit-2026-08-20 VERDICT: FAIL. Blocker: C3 schema not wired.
[Agent: Critique] Cycle pilot-kit-2026-08-20 VERDICT: PASS. Tests green. Quiz may proceed.
[Agent: Architect] Quiz ready — accept only if human passes.
```
