"""callgate — fail-closed checkpoint between LLM tool calls and execution.

    gate = Gate(default="deny", meter=meter)
    gate.register("db_query", db_query, schema=ToolSchema(required=["q"]))
    result = gate.run(openai_response)   # check + execute only if allowed
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from callgate.intake import IntakeError, ToolCall, parse_tool_calls
from callgate.meter import Meter, RunEvent
from callgate.schema import ToolSchema, schema_from_signature

ToolFn = Callable[..., Any]
DefaultMode = Literal["deny", "allow"]


class Verdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    # Reserved for the approval-hook cycle (plan.md Phase 1). Never emitted yet.
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class ToolRegistry:
    """Maps tool names to Python callables (+ optional schemas)."""

    _tools: dict[str, ToolFn] = field(default_factory=dict)
    _schemas: dict[str, ToolSchema] = field(default_factory=dict)

    def register(
        self,
        name: str,
        fn: ToolFn,
        schema: ToolSchema | None = None,
        *,
        infer_schema: bool = False,
    ) -> None:
        self._tools[name] = fn
        if schema is not None:
            self._schemas[name] = schema
        elif infer_schema:
            self._schemas[name] = schema_from_signature(fn)

    def get(self, name: str) -> ToolFn | None:
        return self._tools.get(name)

    def get_schema(self, name: str) -> ToolSchema | None:
        return self._schemas.get(name)

    def names(self) -> list[str]:
        return list(self._tools.keys())


@dataclass
class GateResult:
    verdict: Verdict
    call: ToolCall | None = None
    reasons: list[str] = field(default_factory=list)
    executed: bool = False
    return_value: Any = None
    error: str | None = None

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW


class Gate:
    """Fail-closed gate.

    default="deny"  -> a registered tool with NO schema is still blocked
    default="allow" -> schema optional; registered tool without schema passes

    Unknown tools, intake failures, and schema violations always BLOCK.
    check() never executes anything; execute() runs ALLOW results only.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        default: DefaultMode = "deny",
        meter: Meter | None = None,
        lane: str = "gate",
    ):
        if default not in ("deny", "allow"):
            raise ValueError(f"default must be 'deny' or 'allow', got {default!r}")
        self.registry = registry or ToolRegistry()
        self.default = default
        self.meter = meter
        self.lane = lane

    def register(
        self,
        name: str,
        fn: ToolFn,
        schema: ToolSchema | None = None,
        *,
        infer_schema: bool = False,
    ) -> None:
        self.registry.register(name, fn, schema, infer_schema=infer_schema)

    # -- checking ---------------------------------------------------------

    def check_all(self, payload: Any) -> list[GateResult]:
        try:
            calls = parse_tool_calls(payload)
        except IntakeError as exc:
            return [self._record(GateResult(Verdict.BLOCK, reasons=[f"intake: {exc}"]))]
        if not calls:
            return [self._record(GateResult(Verdict.BLOCK, reasons=["intake: no tool calls in payload"]))]
        return [self._check_one(call) for call in calls]

    def check(self, payload: Any) -> GateResult:
        results = self.check_all(payload)
        if len(results) != 1:
            raise ValueError(f"expected exactly 1 tool call, got {len(results)}; use check_all()")
        return results[0]

    def _check_one(self, call: ToolCall) -> GateResult:
        if self.registry.get(call.name) is None:
            return self._record(GateResult(Verdict.BLOCK, call, [f"unknown tool: {call.name!r}"]))

        schema = self.registry.get_schema(call.name)
        if schema is None:
            if self.default == "deny":
                return self._record(
                    GateResult(
                        Verdict.BLOCK,
                        call,
                        [f"no schema registered for {call.name!r} and gate default is deny"],
                    )
                )
        else:
            errors = schema.validate(call.args)
            if errors:
                return self._record(GateResult(Verdict.BLOCK, call, errors))

        return self._record(GateResult(Verdict.ALLOW, call))

    # -- execution --------------------------------------------------------

    def execute(self, result: GateResult) -> GateResult:
        if not result.allowed or result.call is None:
            joined = "; ".join(result.reasons) or "no call"
            raise PermissionError(f"refusing to execute a {result.verdict.value} result: {joined}")
        tool = self.registry.get(result.call.name)
        if tool is None:  # registry mutated between check and execute
            result.error = f"unknown tool at execute time: {result.call.name!r}"
        else:
            try:
                result.return_value = tool(**result.call.args)
                result.executed = True
            except Exception as exc:
                result.error = f"{type(exc).__name__}: {exc}"
        if self.meter is not None:
            self.meter.record(
                RunEvent(
                    lane=self.lane,
                    kind="tool",
                    ok=result.executed,
                    namespace=result.call.name,
                    error=result.error,
                )
            )
        return result

    def run(self, payload: Any) -> GateResult:
        result = self.check(payload)
        if result.allowed:
            return self.execute(result)
        return result

    def run_all(self, payload: Any) -> list[GateResult]:
        return [self.execute(r) if r.allowed else r for r in self.check_all(payload)]

    # -- internals ----------------------------------------------------------

    def _record(self, result: GateResult) -> GateResult:
        if self.meter is not None:
            self.meter.record_intercept(
                lane=self.lane,
                ok=result.verdict is Verdict.ALLOW,
                namespace=result.call.name if result.call else None,
                error="; ".join(result.reasons) or None,
                meta={"verdict": result.verdict.value, "default": self.default},
            )
        return result
