"""Normalize LLM provider tool-call outputs into ToolCall records.

Accepted shapes (dicts, or SDK objects exposing model_dump()/to_dict()):

- Plain call:        {"name"|"tool"|"action": str, "args"|"params"|"arguments"|"input": {...}}
- OpenAI chat:       choices[*].message.tool_calls[*].function{name, arguments(JSON str)}
- OpenAI responses:  output[*] where type == "function_call" {name, arguments(JSON str)}
- Anthropic:         content[*] where type == "tool_use" {name, input}
- Gemini:            candidates[*].content.parts[*].functionCall|function_call {name, args}

No provider SDK is imported here — callgate core stays stdlib-only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


class IntakeError(ValueError):
    """Payload could not be interpreted as tool call(s)."""


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    source: str = "dict"


_NAME_KEYS = ("name", "tool", "tool_name", "action", "namespace")
_ARG_KEYS = ("args", "params", "arguments", "parameters", "input", "inputs")


def _as_data(obj: Any) -> Any:
    if isinstance(obj, (dict, list)):
        return obj
    for attr in ("model_dump", "to_dict", "to_json_dict"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                data = fn()
            except TypeError:
                continue
            if isinstance(data, (dict, list)):
                return data
    raise IntakeError(f"unsupported payload type: {type(obj).__name__}")


def _parse_args(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value or "{}")
        except json.JSONDecodeError as exc:
            raise IntakeError(f"tool arguments are not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise IntakeError(f"tool args must be an object, got {type(value).__name__}")
    return value


def _from_openai_chat(data: dict) -> list[ToolCall] | None:
    choices = data.get("choices")
    if not isinstance(choices, list):
        return None
    calls: list[ToolCall] = []
    for choice in choices:
        message = (choice or {}).get("message") or {}
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            name = fn.get("name")
            if not name:
                raise IntakeError("OpenAI tool_call missing function.name")
            calls.append(
                ToolCall(name=name, args=_parse_args(fn.get("arguments")), id=tc.get("id"), source="openai-chat")
            )
    return calls


def _from_openai_responses(data: dict) -> list[ToolCall] | None:
    output = data.get("output")
    if not isinstance(output, list):
        return None
    calls: list[ToolCall] = []
    for item in output:
        if isinstance(item, dict) and item.get("type") == "function_call":
            name = item.get("name")
            if not name:
                raise IntakeError("OpenAI responses function_call missing name")
            calls.append(
                ToolCall(
                    name=name,
                    args=_parse_args(item.get("arguments")),
                    id=item.get("call_id") or item.get("id"),
                    source="openai-responses",
                )
            )
    return calls


def _from_anthropic(data: dict) -> list[ToolCall] | None:
    content = data.get("content")
    if not isinstance(content, list):
        return None
    calls: list[ToolCall] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            name = block.get("name")
            if not name:
                raise IntakeError("Anthropic tool_use block missing name")
            calls.append(
                ToolCall(name=name, args=_parse_args(block.get("input")), id=block.get("id"), source="anthropic")
            )
    return calls


def _from_gemini(data: dict) -> list[ToolCall] | None:
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return None
    calls: list[ToolCall] = []
    for cand in candidates:
        parts = ((cand or {}).get("content") or {}).get("parts") or []
        for part in parts:
            if not isinstance(part, dict):
                continue
            fc = part.get("functionCall") or part.get("function_call")
            if fc:
                name = fc.get("name")
                if not name:
                    raise IntakeError("Gemini functionCall missing name")
                calls.append(ToolCall(name=name, args=_parse_args(fc.get("args")), source="gemini"))
    return calls


def _from_plain(data: dict) -> ToolCall | None:
    name = next((data[k] for k in _NAME_KEYS if isinstance(data.get(k), str)), None)
    if name is None:
        return None
    raw_args = next((data[k] for k in _ARG_KEYS if k in data), None)
    return ToolCall(name=name, args=_parse_args(raw_args), id=data.get("id"), source="dict")


_ENVELOPE_EXTRACTORS = (_from_openai_chat, _from_openai_responses, _from_anthropic, _from_gemini)


def parse_tool_calls(payload: Any) -> list[ToolCall]:
    """Extract every tool call from a provider response or plain dict.

    Returns [] when a recognized envelope contains no tool calls
    (e.g. the model answered with plain text). Raises IntakeError when
    the payload shape is not recognizable at all.
    """
    data = _as_data(payload)

    if isinstance(data, list):
        calls: list[ToolCall] = []
        for item in data:
            calls.extend(parse_tool_calls(item))
        return calls

    for extract in _ENVELOPE_EXTRACTORS:
        calls = extract(data)
        if calls is not None:
            return calls

    plain = _from_plain(data)
    if plain is not None:
        return [plain]

    raise IntakeError(
        "no recognizable tool-call shape (expected OpenAI/Anthropic/Gemini response or "
        f"a dict with one of {_NAME_KEYS})"
    )
