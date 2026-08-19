"""TOAP middleware proxy — intercept, validate, dispatch."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from toap.parser import TOAPParser, ParseResult


ToolFn = Callable[..., Any]


@dataclass
class ToolRegistry:
    """Maps TOAP namespaces to Python callables."""

    _tools: dict[str, ToolFn] = field(default_factory=dict)

    def register(self, namespace: str, fn: ToolFn) -> None:
        self._tools[namespace] = fn

    def get(self, namespace: str) -> ToolFn | None:
        return self._tools.get(namespace)

    def namespaces(self) -> list[str]:
        return list(self._tools.keys())


@dataclass
class InterceptResult:
    parsed: ParseResult
    executed: bool = False
    return_value: Any = None
    error: str | None = None


class TOAPProxy:
    """Interceptor/proxy layer between LLM output and tool execution.

    Usage:
        proxy = TOAPProxy()
        proxy.registry.register("DB_SRC", query_database)
        result = proxy.intercept(llm_output)
        if result.parsed.valid:
            print(result.return_value)
    """

    def __init__(self, registry: ToolRegistry | None = None):
        self.parser = TOAPParser()
        self.registry = registry or ToolRegistry()

    def intercept(self, raw: str, *, execute: bool = True) -> InterceptResult:
        parsed = self.parser.parse(raw)
        if not parsed.valid:
            return InterceptResult(parsed=parsed, executed=False, error="Invalid TOAP syntax")

        if not execute:
            return InterceptResult(parsed=parsed, executed=False)

        tool = self.registry.get(parsed.namespace or "")
        if tool is None:
            return InterceptResult(
                parsed=parsed,
                executed=False,
                error=f"Unknown namespace: {parsed.namespace}",
            )

        try:
            value = tool(**parsed.args)
            return InterceptResult(parsed=parsed, executed=True, return_value=value)
        except Exception as exc:
            return InterceptResult(parsed=parsed, executed=False, error=str(exc))

    def decode(self, raw: str) -> str:
        return self.parser.pretty_print(raw)
