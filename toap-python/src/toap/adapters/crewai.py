"""CrewAI adapter — loose-coupled, optional dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from toap.parser import TOAPParser, ParseResult
from toap.proxy import TOAPProxy, ToolRegistry, InterceptResult
from toap.prompts import build_system_prompt


def toap_task_prompt(task_description: str, *, shots: int = 2) -> str:
    return build_system_prompt(task_description, shots=shots)


@dataclass
class TOAPCrewResult:
    raw: str
    parsed: ParseResult
    executed: bool
    return_value: Any = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "valid": self.parsed.valid,
            "thought": self.parsed.thought,
            "namespace": self.parsed.namespace,
            "args": self.parsed.args,
            "executed": self.executed,
            "return_value": self.return_value,
            "error": self.error,
        }


class TOAPCrewCallback:
    """Intercept agent output, parse TOAP, optionally dispatch to tools."""

    def __init__(self, registry: ToolRegistry | None = None, *, execute: bool = True):
        self.proxy = TOAPProxy(registry)
        self.execute = execute
        self.history: list[dict[str, Any]] = []

    def handle(self, raw_output: str) -> ParseResult:
        result = self.proxy.intercept(raw_output, execute=self.execute)
        entry = {
            "raw": raw_output,
            "valid": result.parsed.valid,
            "namespace": result.parsed.namespace,
            "args": result.parsed.args,
            "executed": result.executed,
            "error": result.error,
            "return_value": result.return_value,
        }
        self.history.append(entry)
        return result.parsed

    def intercept_full(self, raw_output: str) -> InterceptResult:
        return self.proxy.intercept(raw_output, execute=self.execute)

    def pretty_last(self) -> str:
        if not self.history:
            return "(no output yet)"
        return self.proxy.decode(self.history[-1]["raw"])

    @classmethod
    def wrap_tools(cls, registry: ToolRegistry) -> "TOAPCrewCallback":
        return cls(registry=registry, execute=True)


def build_toap_crew(task: str, llm, *, shots: int = 2):
    """Build a single-agent CrewAI crew that emits TOAP output.

    Returns (crew, callback, agent, crew_task).
    """
    try:
        from crewai import Agent, Crew, Task
    except ImportError as exc:
        raise ImportError("pip install toap[crewai]") from exc

    callback = TOAPCrewCallback(execute=False)

    agent = Agent(
        role="TOAP Protocol Agent",
        goal="Execute operational tasks by emitting valid TOAP syntax only",
        backstory=(
            "You are a machine-to-machine infrastructure agent. "
            "You never respond in JSON, markdown, or conversational English. "
            "Your only output format is TOAP."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    crew_task = Task(
        description=toap_task_prompt(task, shots=shots),
        expected_output=(
            "Valid TOAP output: optional §T[domain] line followed by "
            "required ƒ(NAMESPACE)>key:value|... action line"
        ),
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[crew_task], verbose=False)
    return crew, callback, agent, crew_task


def run_toap_crew(
    crew,
    callback: TOAPCrewCallback,
    registry: ToolRegistry,
    *,
    execute: bool = True,
) -> TOAPCrewResult:
    """Run crew.kickoff(), parse TOAP output, optionally execute tool."""
    output = crew.kickoff()
    raw = output.raw if hasattr(output, "raw") else str(output)

    proxy = TOAPProxy(registry)
    intercept = proxy.intercept(raw, execute=execute)

    callback.history.append({
        "raw": raw,
        "valid": intercept.parsed.valid,
        "namespace": intercept.parsed.namespace,
        "args": intercept.parsed.args,
        "executed": intercept.executed,
        "error": intercept.error,
        "return_value": intercept.return_value,
    })

    return TOAPCrewResult(
        raw=raw,
        parsed=intercept.parsed,
        executed=intercept.executed,
        return_value=intercept.return_value,
        error=intercept.error,
    )
