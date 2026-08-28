"""toolwall: fail-closed checkpoint between LLM tool calls and execution.

    gate = Gate(default="deny", meter=meter, shield=Shield(mode="block"))
    gate.register("db_query", db_query,
                  schema=ToolSchema(required=["q"]),
                  policy=Policy(constraints={"limit": in_range(1, 100)}))
    gate.budget(max_calls=20)
    result = gate.run(openai_response)   # check + execute only if allowed

Check order (first failure blocks, fail-closed):
  intake -> known tool -> budget -> schema -> policy -> shield -> approval
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from toolwall.intake import IntakeError, ToolCall, parse_tool_calls
from toolwall.meter import Meter, RunEvent
from toolwall.policy import Policy
from toolwall.schema import ToolSchema, schema_from_signature
from toolwall.shield import Finding, Shield

ToolFn = Callable[..., Any]
DefaultMode = Literal["deny", "allow"]
ApprovalHandler = Callable[["GateResult"], bool]


class Verdict(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    NEEDS_APPROVAL = "needs_approval"


@dataclass
class ToolRegistry:
    """Maps tool names to callables (+ optional schema and policy).

    Registration is the allowlist: unregistered tools always block.
    """

    _tools: dict[str, ToolFn] = field(default_factory=dict)
    _schemas: dict[str, ToolSchema] = field(default_factory=dict)
    _policies: dict[str, Policy] = field(default_factory=dict)

    def register(
        self,
        name: str,
        fn: ToolFn,
        schema: ToolSchema | None = None,
        *,
        policy: Policy | None = None,
        infer_schema: bool = False,
    ) -> None:
        self._tools[name] = fn
        if schema is not None:
            self._schemas[name] = schema
        elif infer_schema:
            self._schemas[name] = schema_from_signature(fn)
        if policy is not None:
            self._policies[name] = policy

    def get(self, name: str) -> ToolFn | None:
        return self._tools.get(name)

    def get_schema(self, name: str) -> ToolSchema | None:
        return self._schemas.get(name)

    def get_policy(self, name: str) -> Policy | None:
        return self._policies.get(name)

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
    findings: list[Finding] = field(default_factory=list)  # shield hits (value-free)
    dry_run: bool = False  # True when the gate simulated execution

    @property
    def allowed(self) -> bool:
        return self.verdict is Verdict.ALLOW

    @property
    def blocked(self) -> bool:
        return self.verdict is Verdict.BLOCK

    @property
    def needs_approval(self) -> bool:
        return self.verdict is Verdict.NEEDS_APPROVAL

    @property
    def reason(self) -> str | None:
        """First human-readable reason for a block/hold, or None when allowed."""
        return self.reasons[0] if self.reasons else None


class Gate:
    """Fail-closed gate.

    default="deny"  -> a registered tool with NO schema is still blocked
    default="allow" -> schema optional; registered tool without schema passes

    approval: optional handler called by run()/run_all() when a policy demands
    approval. Returns True to execute. Without a handler, NEEDS_APPROVAL calls
    are never executed (fail closed).
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        default: DefaultMode = "deny",
        meter: Meter | None = None,
        shield: Shield | None = None,
        approval: ApprovalHandler | None = None,
        dry_run: bool = False,
        lane: str = "gate",
    ):
        if default not in ("deny", "allow"):
            raise ValueError(f"default must be 'deny' or 'allow', got {default!r}")
        self.registry = registry or ToolRegistry()
        self.default = default
        self.meter = meter
        self.shield = shield
        self.approval = approval
        self.dry_run = dry_run
        self.lane = lane
        self.history: list[GateResult] = []  # every checked result, for reports/suggest
        self._lock = threading.Lock()
        self._budget: dict[str, Any] = {}
        self._executed_calls = 0
        self._executed_per_tool: dict[str, int] = {}

    def register(
        self,
        name: str,
        fn: ToolFn,
        schema: ToolSchema | None = None,
        *,
        policy: Policy | None = None,
        infer_schema: bool = False,
    ) -> None:
        self.registry.register(name, fn, schema, policy=policy, infer_schema=infer_schema)

    # -- budget ---------------------------------------------------------------

    def budget(
        self,
        *,
        max_calls: int | None = None,
        max_calls_per_tool: int | None = None,
        max_usd: float | None = None,
    ) -> None:
        if max_usd is not None and self.meter is None:
            raise ValueError("max_usd budget requires a meter (cost is meter-derived)")
        self._budget = {
            "max_calls": max_calls,
            "max_calls_per_tool": max_calls_per_tool,
            "max_usd": max_usd,
        }

    def _budget_violation(self, call: ToolCall) -> str | None:
        """Read budget counters under the lock.

        Note: this reads state; the increment happens in execute(). A Gate is
        intended for one agent run. Under heavy concurrent use on a shared Gate,
        counters stay consistent but a check/execute race can still admit an
        extra call. Use one Gate per agent execution context.
        """
        if not self._budget:
            return None
        with self._lock:
            return self._budget_violation_locked(call)

    def _budget_violation_locked(self, call: ToolCall) -> str | None:
        max_calls = self._budget.get("max_calls")
        if max_calls is not None and self._executed_calls >= max_calls:
            return f"budget exceeded: max_calls={max_calls} already executed"
        per_tool = self._budget.get("max_calls_per_tool")
        if per_tool is not None and self._executed_per_tool.get(call.name, 0) >= per_tool:
            return f"budget exceeded: max_calls_per_tool={per_tool} for {call.name!r}"
        max_usd = self._budget.get("max_usd")
        if max_usd is not None and self.meter is not None:
            spent = self.meter.report.estimate_cost_usd(self.lane)
            if spent >= max_usd:
                return f"budget exceeded: estimated ${spent:.4f} >= max_usd={max_usd}"
        return None

    # -- checking ---------------------------------------------------------------

    def check_all(self, payload: Any) -> list[GateResult]:
        """Check every tool call in a payload without executing anything.

        Budget caution: all calls are checked against the *current* counters, so
        with N parallel calls every one of them sees the same budget state. If
        you then execute them yourself, you can exceed a budget. Use run_all(),
        which checks and executes one call at a time so counters advance.
        """
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

        budget_reason = self._budget_violation(call)
        if budget_reason is not None:
            return self._record(GateResult(Verdict.BLOCK, call, [budget_reason]))

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

        policy = self.registry.get_policy(call.name)
        if policy is not None:
            errors = policy.validate(call.args)
            if errors:
                return self._record(GateResult(Verdict.BLOCK, call, errors))

        findings: list[Finding] = []
        if self.shield is not None:
            if self.shield.mode == "redact":
                call.args, findings = self.shield.redact_args(call.args)
            else:
                findings = self.shield.scan_args(call.args)
                if findings and self.shield.mode == "block":
                    reasons = [
                        f"secret detected ({f.kind}) in arg {f.arg!r}" for f in findings
                    ]
                    return self._record(
                        GateResult(Verdict.BLOCK, call, reasons, findings=findings)
                    )

        if policy is not None and policy.require_approval:
            return self._record(
                GateResult(
                    Verdict.NEEDS_APPROVAL,
                    call,
                    [f"approval required for {call.name!r}"],
                    findings=findings,
                )
            )

        return self._record(GateResult(Verdict.ALLOW, call, findings=findings))

    # -- execution ----------------------------------------------------------------

    def execute(self, result: GateResult) -> GateResult:
        if not result.allowed or result.call is None:
            joined = "; ".join(result.reasons) or "no call"
            raise PermissionError(f"refusing to execute a {result.verdict.value} result: {joined}")
        with self._lock:
            self._executed_calls += 1
            self._executed_per_tool[result.call.name] = (
                self._executed_per_tool.get(result.call.name, 0) + 1
            )
        if self.dry_run:
            result.dry_run = True
            if self.meter is not None:
                self.meter.record(
                    RunEvent(
                        lane=self.lane,
                        kind="tool",
                        ok=True,
                        namespace=result.call.name,
                        meta={"dry_run": True, "would_execute": True},
                    )
                )
            return result
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

    def _resolve_approval(self, result: GateResult) -> GateResult:
        """Called by run/run_all on NEEDS_APPROVAL. Fail closed without a handler."""
        if self.approval is None:
            return result
        try:
            granted = bool(self.approval(result))
        except Exception as exc:
            result.verdict = Verdict.BLOCK
            result.reasons.append(f"approval handler raised {type(exc).__name__}: fails closed")
            return self._record_transition(result, "approval-error")
        if granted:
            result.verdict = Verdict.ALLOW
            result.reasons = []
            return self._record_transition(result, "approval-granted")
        result.verdict = Verdict.BLOCK
        result.reasons.append("approval denied")
        return self._record_transition(result, "approval-denied")

    def run(self, payload: Any) -> GateResult:
        result = self.check(payload)
        if result.verdict is Verdict.NEEDS_APPROVAL:
            result = self._resolve_approval(result)
        if result.allowed:
            return self.execute(result)
        return result

    def run_all(self, payload: Any) -> list[GateResult]:
        # Check and execute each call in sequence, not check-all-then-execute-all.
        # Executing one call increments budget counters, so the next call's check
        # sees the updated state. Otherwise N parallel calls all pass a budget of
        # max_calls=1 (checked at counter 0) and then all execute.
        try:
            calls = parse_tool_calls(payload)
        except IntakeError as exc:
            return [self._record(GateResult(Verdict.BLOCK, reasons=[f"intake: {exc}"]))]
        if not calls:
            return [self._record(GateResult(Verdict.BLOCK, reasons=["intake: no tool calls in payload"]))]
        out: list[GateResult] = []
        for call in calls:
            result = self._check_one(call)
            if result.verdict is Verdict.NEEDS_APPROVAL:
                result = self._resolve_approval(result)
            out.append(self.execute(result) if result.allowed else result)
        return out

    # -- reporting ----------------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Summary of everything this gate has seen. Useful after a dry run."""
        by_verdict: dict[str, int] = {}
        by_tool: dict[str, dict[str, int]] = {}
        blocked_reasons: list[str] = []
        finding_kinds: dict[str, int] = {}
        for r in self.history:
            by_verdict[r.verdict.value] = by_verdict.get(r.verdict.value, 0) + 1
            name = r.call.name if r.call else "(unparsed)"
            tool_row = by_tool.setdefault(name, {"allow": 0, "block": 0, "needs_approval": 0})
            tool_row[r.verdict.value] = tool_row.get(r.verdict.value, 0) + 1
            if r.verdict is Verdict.BLOCK and r.reasons:
                blocked_reasons.append(f"{name}: {r.reasons[0]}")
            for f in r.findings:
                finding_kinds[f.kind] = finding_kinds.get(f.kind, 0) + 1
        return {
            "dry_run": self.dry_run,
            "calls_checked": len(self.history),
            "verdicts": by_verdict,
            "would_execute" if self.dry_run else "executed": self._executed_calls,
            "by_tool": by_tool,
            "blocked_reasons": blocked_reasons,
            "secret_findings_by_kind": finding_kinds,
        }

    # -- internals -------------------------------------------------------------------

    def _record(self, result: GateResult) -> GateResult:
        self.history.append(result)
        if self.meter is not None:
            self.meter.record_intercept(
                lane=self.lane,
                ok=result.verdict is Verdict.ALLOW,
                namespace=result.call.name if result.call else None,
                error="; ".join(result.reasons) or None,
                meta={
                    "verdict": result.verdict.value,
                    "default": self.default,
                    "findings": [f.kind for f in result.findings],
                },
            )
        return result

    def _record_transition(self, result: GateResult, event: str) -> GateResult:
        if self.meter is not None:
            self.meter.record(
                RunEvent(
                    lane=self.lane,
                    kind="note",
                    ok=result.verdict is Verdict.ALLOW,
                    namespace=result.call.name if result.call else None,
                    meta={"approval": event},
                )
            )
        return result
