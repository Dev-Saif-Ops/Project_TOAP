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

### Example 2 — Web Search (no thought)

```
ƒ(WEB_SRC)>q:"CVE-2026-1234 critical exploits"|l:10
```

### Example 3 — API Call with Multiple Args

```
§T[infra_health_check]
ƒ(API_SRC)>endpoint:"/v1/status"|method:GET|timeout:30
```

---

## Production Arg Aliases (Parser Normalization)

| Model output | Canonical key |
|---|---|
| `url`, `uri` | `endpoint` |
| `query` | `q` |
| `limit` | `l` |
| `k` | `key` |
| `time`, `timeframe` | `window` |
| `action` | `mode` |
| `op` (FS_SRC only) | `mode` |

---

## Validation Rules

1. Action line is **required**
2. Thought line is **optional**
3. Namespace must be a valid identifier
4. String values must be double-quoted
5. No JSON, no natural language in output
