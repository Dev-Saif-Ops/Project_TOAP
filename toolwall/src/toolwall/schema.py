"""Tool schema validation, run before a tool is allowed to execute."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolSchema:
    """Minimal schema: required keys + optional crude types."""

    required: list[str] = field(default_factory=list)
    types: dict[str, type | tuple[type, ...]] = field(default_factory=dict)
    allow_extra: bool = True
    # Known-but-not-required arg names. Only consulted when allow_extra is False,
    # so that an optional parameter carrying no type annotation (and therefore
    # absent from `types`) is not mistaken for an unexpected argument.
    optional: list[str] = field(default_factory=list)

    def validate(self, args: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for key in self.required:
            if key not in args:
                errors.append(f"Missing required arg: {key}")
        if not self.allow_extra:
            allowed = set(self.required) | set(self.types) | set(self.optional)
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
    """Best-effort schema from a callable signature (stdlib inspect).

    Extra arguments are rejected, because the signature already tells us exactly
    what the callable accepts. Passing one would raise TypeError inside the tool,
    which surfaces as an executed=False result carrying an error rather than as a
    verdict; a clean BLOCK is both more honest and fails closed.

    The exception is a callable that declares **kwargs: it genuinely accepts
    arguments we cannot enumerate, so extras stay allowed there.
    """
    import inspect

    sig = inspect.signature(fn)
    req: list[str] = []
    opt: list[str] = []
    types: dict[str, type | tuple[type, ...]] = {}
    takes_var_kwargs = False
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if param.kind is param.VAR_KEYWORD:
            takes_var_kwargs = True
            continue
        if param.kind is param.VAR_POSITIONAL:
            continue
        if param.default is inspect.Parameter.empty:
            req.append(name)
        else:
            opt.append(name)
        ann = param.annotation
        if ann is not inspect.Parameter.empty and isinstance(ann, type):
            types[name] = ann
    if required is not None:
        # A caller-supplied required list overrides which args are mandatory, but
        # every name from the signature is still a known argument.
        opt = [n for n in req + opt if n not in required]
        req = list(required)
    return ToolSchema(
        required=req, types=types, allow_extra=takes_var_kwargs, optional=opt
    )
