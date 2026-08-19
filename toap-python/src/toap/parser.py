"""TOAP v0.1 strict lexer/parser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseError:
    message: str
    line: int | None = None
    raw: str = ""


@dataclass
class ParseResult:
    valid: bool
    thought: str | None = None
    namespace: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    errors: list[ParseError] = field(default_factory=list)
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "thought": self.thought,
            "namespace": self.namespace,
            "args": self.args,
            "errors": [{"message": e.message, "line": e.line} for e in self.errors],
        }


IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"
THOUGHT_RE = re.compile(rf"^§T\[({IDENT})\]$")
ACTION_RE = re.compile(rf"^ƒ\(({IDENT})\)>(.+)$")
ARG_PAIR_RE = re.compile(
    rf"^({IDENT}):("
    rf'"(?:[^"\\\\]|\\\\.)*"'
    rf"|{IDENT}"
    rf"|\d+"
    rf")$"
)

ARG_ALIASES: dict[str, str] = {
    "url": "endpoint",
    "uri": "endpoint",
    "query": "q",
    "limit": "l",
    "k": "key",
    "time": "window",
    "timeframe": "window",
    "action": "mode",
    "operation": "op",
}


def normalize_arg_key(key: str) -> str:
    return ARG_ALIASES.get(key, key)


def normalize_arg_value(key: str, value: Any) -> Any:
    if isinstance(value, str) and key in ("mode", "op"):
        return value.lower().strip('"')
    return value


def normalize_window_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    v = value.lower().replace("_", " ").strip()
    if v in ("1h", "1 hour", "last 1 hour", "last hour"):
        return "1h"
    return value


def normalize_args(args: dict[str, Any], namespace: str | None = None) -> dict[str, Any]:
    raw = dict(args)
    normalized: dict[str, Any] = {}

    if namespace == "FS_SRC" and "op" in raw and "mode" not in raw:
        op_val = raw.pop("op")
        if isinstance(op_val, str) and op_val.lower() in ("read", "write", "get"):
            raw["mode"] = op_val

    for key, value in raw.items():
        canon = normalize_arg_key(key)
        value = normalize_arg_value(canon, value)
        if canon == "window":
            value = normalize_window_value(value)
        if canon not in normalized:
            normalized[canon] = value
    return normalized


class TOAPParser:
    """Strict TOAP v0.1 parser with production arg alias normalization."""

    def parse(self, raw: str) -> ParseResult:
        result = ParseResult(valid=False, raw=raw)
        lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]

        if not lines:
            result.errors.append(ParseError("Empty output", raw=raw))
            return result

        thought: str | None = None
        action_lines: list[str] = []

        for i, line in enumerate(lines):
            thought_match = THOUGHT_RE.match(line)
            if thought_match:
                if thought is not None:
                    result.errors.append(
                        ParseError("Multiple thought lines", line=i + 1, raw=line)
                    )
                thought = thought_match.group(1)
                continue

            action_match = ACTION_RE.match(line)
            if action_match:
                action_lines.append(line)
                continue

            result.errors.append(
                ParseError(f"Unrecognized line: {line!r}", line=i + 1, raw=line)
            )

        if not action_lines:
            result.errors.append(ParseError("Missing required action line", raw=raw))
            return result

        if len(action_lines) > 1:
            result.errors.append(
                ParseError(f"Multiple action lines ({len(action_lines)}), expected 1", raw=raw)
            )
            return result

        action_match = ACTION_RE.match(action_lines[0])
        assert action_match is not None
        namespace = action_match.group(1)
        arg_str = action_match.group(2)

        args: dict[str, Any] = {}
        if arg_str:
            for pair in arg_str.split("|"):
                pair = pair.strip()
                if not pair:
                    result.errors.append(ParseError("Empty argument in pipe list", raw=arg_str))
                    continue

                arg_match = ARG_PAIR_RE.match(pair)
                if not arg_match:
                    result.errors.append(ParseError(f"Invalid argument: {pair!r}", raw=pair))
                    continue

                key = arg_match.group(1)
                value_raw = arg_match.group(2)

                if value_raw.startswith('"') and value_raw.endswith('"'):
                    value: Any = value_raw[1:-1]
                elif value_raw.isdigit():
                    value = int(value_raw)
                else:
                    value = value_raw

                if key in args:
                    result.errors.append(ParseError(f"Duplicate argument key: {key}", raw=pair))
                args[key] = value

        if result.errors:
            return result

        result.valid = True
        result.thought = thought
        result.namespace = namespace
        result.args = normalize_args(args, namespace=namespace)
        return result

    def pretty_print(self, raw: str) -> str:
        result = self.parse(raw)
        if not result.valid:
            lines = ["[TOAP PARSE FAILED]"]
            for err in result.errors:
                loc = f" (line {err.line})" if err.line else ""
                lines.append(f"  x {err.message}{loc}")
            lines.append(f"\nRaw:\n{raw}")
            return "\n".join(lines)

        lines = ["[TOAP DECODED]"]
        if result.thought:
            lines.append(f"  Thought domain : {result.thought}")
        lines.append(f"  Tool namespace : {result.namespace}")
        lines.append("  Arguments:")
        for k, v in result.args.items():
            lines.append(f"    {k} = {v!r}")
        return "\n".join(lines)
