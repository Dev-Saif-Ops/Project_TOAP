"""Encode structured tool calls into TOAP v0.1 strings."""

from __future__ import annotations

import json
from typing import Any


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
    text = str(value)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def encode_action(
    namespace: str,
    args: dict[str, Any] | None = None,
    *,
    thought: str | None = None,
) -> str:
    """Build a TOAP block from namespace + args."""
    parts: list[str] = []
    if thought:
        parts.append(f"§T[{thought}]")
    arg_str = "|".join(f"{k}:{_format_value(v)}" for k, v in (args or {}).items())
    parts.append(f"ƒ({namespace})>{arg_str}")
    return "\n".join(parts)


def encode_tool_call(payload: dict[str, Any]) -> str:
    """Encode a JSON-like tool call dict.

    Accepted shapes:
      {"namespace": "DB_SRC", "args": {...}, "thought": "..."}
      {"action": "DB_SRC", "params": {...}}
      {"tool": "DB_SRC", "arguments": {...}}
    """
    namespace = (
        payload.get("namespace")
        or payload.get("action")
        or payload.get("tool")
        or payload.get("name")
    )
    if not namespace or not isinstance(namespace, str):
        raise ValueError("payload must include namespace/action/tool name")

    args = (
        payload.get("args")
        or payload.get("params")
        or payload.get("arguments")
        or payload.get("parameters")
        or {}
    )
    if not isinstance(args, dict):
        raise ValueError("args/params must be a dict")

    thought = payload.get("thought")
    if thought is not None:
        thought = str(thought)
    return encode_action(namespace, args, thought=thought)


def encode_json_tool_call(json_text: str) -> str:
    """Parse JSON text then encode to TOAP."""
    data = json.loads(json_text)
    if not isinstance(data, dict):
        raise ValueError("JSON tool call must be an object")
    return encode_tool_call(data)


def baseline_json(payload: dict[str, Any]) -> str:
    """Compact JSON baseline string for token comparison."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
