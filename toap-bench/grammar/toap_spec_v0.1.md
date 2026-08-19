# TOAP Grammar Specification v0.1

**Status:** FROZEN — do not modify during benchmark runs  
**Hash target:** Used in benchmark result rows for reproducibility

---

## Overview

TOAP (Token-Optimized Agent Protocol) is a deterministic DSL for agent-to-agent communication. Every valid TOAP output consists of an optional thought line followed by a required action line.

---

## Syntax

### Thought Line (optional)

```
§T[<domain>]
```

| Component | Rule |
|---|---|
| `§T` | Literal unicode anchor — marks thought/state |
| `<domain>` | Identifier: `[a-zA-Z_][a-zA-Z0-9_]*` |

**Example:** `§T[sec_vuln_huawei_2026]`

### Action Line (required)

```
ƒ(<namespace>)><arg_list>
```

| Component | Rule |
|---|---|
| `ƒ` | Literal unicode marker — marks executable action |
| `<namespace>` | Identifier: tool/function namespace |
| `>` | Separator between namespace and arguments |
| `<arg_list>` | Pipe-delimited key:value pairs |

**Example:** `ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5`

### Argument List

```
<arg> ("|" <arg>)*
```

Each argument:
```
<key>:<value>
```

| Component | Rule |
|---|---|
| `<key>` | Identifier: `[a-zA-Z_][a-zA-Z0-9_]*` |
| `<value>` | Quoted string `"..."`, integer, or bare identifier |

---

## Full Examples

### Example 1 — Database Query

```
§T[sec_vuln_huawei_2026]
ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5
```

Parsed:
```json
{
  "thought": "sec_vuln_huawei_2026",
  "action": {
    "namespace": "DB_SRC",
    "args": {"q": "Huawei Cloud vulnerabilities", "l": 5}
  }
}
```

### Example 2 — Web Search (no thought)

```
ƒ(WEB_SRC)>q:"CVE-2026-1234 critical exploits"|l:10
```

### Example 3 — API Call with Multiple Args

```
§T[infra_health_check]
ƒ(API_SRC)>endpoint:"/v1/status"|method:GET|timeout:30
```

### Example 4 — File Operation

```
§T[report_generation]
ƒ(FS_SRC)>path:"/tmp/report.pdf"|mode:write|content:"summary data"
```

---

## Validation Rules

1. Action line is **required** — output without `ƒ(...)` is invalid
2. Thought line is **optional** — but if present must match `§T[identifier]`
3. Namespace must be a valid identifier
4. All argument keys must be valid identifiers
5. String values must be double-quoted
6. Integer values are unquoted digits
7. No extra whitespace inside tokens (leading/trailing whitespace on lines is trimmed)
8. No JSON, no natural language, no markdown — pure TOAP syntax only

---

## Invalid Examples

| Output | Reason |
|---|---|
| `{"action": "query"}` | JSON, not TOAP |
| `§T[]` | Empty domain |
| `ƒ()>q:"test"` | Empty namespace |
| `§T[domain]` (no action) | Missing required action line |
| `ƒ(DB_SRC)>q:unquoted string` | Unquoted string value with spaces |
