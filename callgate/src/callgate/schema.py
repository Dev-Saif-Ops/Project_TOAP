"""Tool schema validation before TOAP tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """Minimal schema: required keys + optional crude types."""

    required: list[str] = field(default_factory=list)
    types: dict[str, type | tuple[type, ...]] = field(default_factory=dict)
    allow_extra: bool = True

    def validate(self, args: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for key in self.required:
            if key not in args:
                errors.append(f"Missing required arg: {key}")
        if not self.allow_extra:
            allowed = set(self.required) | set(self.types)
            for key in args:
                if key not in allowed:
                    errors.append(f"Unexpected arg: {key}")
        for key, expected in self.types.items():
            if key not in args:
                continue
            if not isinstance(args[key], expected):
                errors.append(
                    f"Arg {key!r} expected {expected}, got {type(args[key]).__name__}"
                )
        return errors


def schema_from_signature(fn: Any, *, required: list[str] | None = None) -> ToolSchema:
    """Best-effort schema from a callable signature (stdlib inspect)."""
    import inspect

    sig = inspect.signature(fn)
    req: list[str] = []
    types: dict[str, type | tuple[type, ...]] = {}
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if param.default is inspect.Parameter.empty:
            req.append(name)
        ann = param.annotation
        if ann is not inspect.Parameter.empty and isinstance(ann, type):
            types[name] = ann
    if required is not None:
        req = list(required)
    return ToolSchema(required=req, types=types, allow_extra=True)
