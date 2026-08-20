"""TOAP middleware proxy — intercept, validate, dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from toap.meter import Meter
from toap.parser import TOAPParser, ParseResult
from toap.schema import ToolSchema, schema_from_signature


ToolFn = Callable[..., Any]
FallbackMode = Literal["error", "skip"]


@dataclass
class ToolRegistry:
    """Maps TOAP namespaces to Python callables (+ optional schemas)."""

    _tools: dict[str, ToolFn] = field(default_factory=dict)
    _schemas: dict[str, ToolSchema] = field(default_factory=dict)

    def register(
        self,
        namespace: str,
        fn: ToolFn,
        schema: ToolSchema | None = None,
        *,
        infer_schema: bool = False,
    ) -> None:
        self._tools[namespace] = fn
        if schema is not None:
            self._schemas[namespace] = schema
        elif infer_schema:
            self._schemas[namespace] = schema_from_signature(fn)

    def get(self, namespace: str) -> ToolFn | None:
        return self._tools.get(namespace)

    def get_schema(self, namespace: str) -> ToolSchema | None:
        return self._schemas.get(namespace)

    def namespaces(self) -> list[str]:
        return list(self._tools.keys())


@dataclass
class InterceptResult:
    parsed: ParseResult
    executed: bool = False
    return_value: Any = None
    error: str | None = None
    schema_errors: list[str] = field(default_factory=list)


class TOAPProxy:
    """Interceptor/proxy layer between LLM output and tool execution.

    Usage:
        meter = Meter(model="gemini")
        proxy = TOAPProxy(meter=meter, require_schema=True)
        proxy.registry.register("DB_SRC", query_database, infer_schema=True)
        result = proxy.intercept(llm_output)
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        meter: Meter | None = None,
        fallback: FallbackMode = "error",
        lane: str = "toap",
        require_schema: bool = False,
    ):
        self.parser = TOAPParser()
        self.registry = registry or ToolRegistry()
        self.meter = meter
        self.fallback = fallback
        self.lane = lane
        self.require_schema = require_schema

    def intercept(self, raw: str, *, execute: bool = True) -> InterceptResult:
        timer = self.meter.timed() if self.meter else None
        if timer is not None:
            timer.__enter__()

        parsed = self.parser.parse(raw)
        latency = 0.0

        def _finish(result: InterceptResult) -> InterceptResult:
            nonlocal latency
            if timer is not None:
                timer.__exit__(None, None, None)
                latency = timer.latency_ms
            if self.meter is not None:
                self.meter.record_intercept(
                    lane=self.lane,
                    ok=result.executed if execute else result.parsed.valid,
                    namespace=result.parsed.namespace,
                    latency_ms=latency,
                    error=result.error,
                    completion_text=raw,
                    meta={
                        "schema_errors": list(result.schema_errors),
                        "execute": execute,
                        "fallback": self.fallback,
                        "require_schema": self.require_schema,
                    },
                )
            return result

        if not parsed.valid:
            err = "Invalid TOAP syntax"
            if parsed.errors:
                err = parsed.errors[0].message
            return _finish(
                InterceptResult(
                    parsed=parsed,
                    executed=False,
                    error=err,
                )
            )

        if not execute:
            return _finish(InterceptResult(parsed=parsed, executed=False))

        namespace = parsed.namespace or ""
        tool = self.registry.get(namespace)
        if tool is None:
            return _finish(
                InterceptResult(
                    parsed=parsed,
                    executed=False,
                    error=f"Unknown namespace: {parsed.namespace}",
                )
            )

        schema = self.registry.get_schema(namespace)
        if schema is None and self.require_schema:
            return _finish(
                InterceptResult(
                    parsed=parsed,
                    executed=False,
                    error=f"No schema registered for namespace: {namespace}",
                    schema_errors=[f"No schema registered for namespace: {namespace}"],
                )
            )

        if schema is not None:
            schema_errors = schema.validate(parsed.args)
            if schema_errors:
                return _finish(
                    InterceptResult(
                        parsed=parsed,
                        executed=False,
                        error="; ".join(schema_errors),
                        schema_errors=schema_errors,
                    )
                )

        try:
            value = tool(**parsed.args)
            return _finish(
                InterceptResult(parsed=parsed, executed=True, return_value=value)
            )
        except Exception as exc:
            return _finish(
                InterceptResult(parsed=parsed, executed=False, error=str(exc))
            )

    def decode(self, raw: str) -> str:
        return self.parser.pretty_print(raw)
