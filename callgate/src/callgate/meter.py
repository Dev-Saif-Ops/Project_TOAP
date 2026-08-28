"""Audit/cost meter for callgate (D-016 compliant).

Provider usage metadata is the only unflagged token source. Any heuristic count
carries estimated=True on the event and is called out in the summary. Use
extract_usage() to pull exact counts from OpenAI / Anthropic / Gemini responses.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# Overridable defaults (Gemini Flash-class ballpark, USD per 1M tokens).
# Not billing-grade; costs computed from estimated tokens are estimates too.
DEFAULT_RATES_USD_PER_1M = {
    "gemini-input": 0.10,
    "gemini-output": 0.40,
    "default-input": 0.10,
    "default-output": 0.40,
}


def estimate_tokens(text: str) -> int:
    """Crude len//4 heuristic. Events built from this MUST set estimated=True."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def extract_usage(payload: Any) -> tuple[int | None, int | None]:
    """Pull exact (prompt_tokens, completion_tokens) from a provider response.

    Supports dicts and SDK objects (via model_dump/to_dict). Shapes:
      OpenAI chat:       usage.prompt_tokens / usage.completion_tokens
      OpenAI responses:  usage.input_tokens / usage.output_tokens
      Anthropic:         usage.input_tokens / usage.output_tokens
      Gemini:            usageMetadata.promptTokenCount / candidatesTokenCount
                         (or snake_case usage_metadata variants)

    Returns (None, None) when no usage block is found.
    """
    data = payload
    if not isinstance(data, dict):
        for attr in ("model_dump", "to_dict", "to_json_dict"):
            fn = getattr(data, attr, None)
            if callable(fn):
                try:
                    data = fn()
                    break
                except TypeError:
                    continue
    if not isinstance(data, dict):
        return (None, None)

    usage = data.get("usage")
    if isinstance(usage, dict):
        prompt = usage.get("prompt_tokens", usage.get("input_tokens"))
        completion = usage.get("completion_tokens", usage.get("output_tokens"))
        if prompt is not None or completion is not None:
            return (prompt, completion)

    meta = data.get("usageMetadata") or data.get("usage_metadata")
    if isinstance(meta, dict):
        prompt = meta.get("promptTokenCount", meta.get("prompt_token_count"))
        completion = meta.get("candidatesTokenCount", meta.get("candidates_token_count"))
        if prompt is not None or completion is not None:
            return (prompt, completion)

    return (None, None)


@dataclass
class RunEvent:
    lane: str  # "gate" | "baseline" | custom
    kind: str  # "llm" | "intercept" | "tool" | "note"
    ok: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    namespace: str | None = None
    error: str | None = None
    estimated: bool = False  # True when any token count is heuristic (D-016)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class RunReport:
    events: list[RunEvent] = field(default_factory=list)
    model: str = "unknown"
    rates_usd_per_1m: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_RATES_USD_PER_1M)
    )

    def add(self, event: RunEvent) -> None:
        self.events.append(event)

    def tokens_for(self, lane: str | None = None) -> dict[str, int]:
        prompt = completion = 0
        for e in self.events:
            if lane is not None and e.lane != lane:
                continue
            prompt += e.prompt_tokens
            completion += e.completion_tokens
        return {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        }

    def success_rate(self, lane: str | None = None, kind: str = "intercept") -> float:
        rows = [e for e in self.events if e.kind == kind and (lane is None or e.lane == lane)]
        if not rows:
            return 0.0
        return sum(1 for e in rows if e.ok) / len(rows)

    def estimated_count(self, lane: str | None = None) -> int:
        return sum(
            1 for e in self.events if e.estimated and (lane is None or e.lane == lane)
        )

    def estimate_cost_usd(self, lane: str | None = None) -> float:
        rates = self.rates_usd_per_1m
        inp = rates.get("gemini-input", rates.get("default-input", 0.0))
        out = rates.get("gemini-output", rates.get("default-output", 0.0))
        totals = self.tokens_for(lane)
        return (totals["prompt_tokens"] / 1_000_000) * inp + (
            totals["completion_tokens"] / 1_000_000
        ) * out

    def summary(self) -> dict[str, Any]:
        lanes = sorted({e.lane for e in self.events}) or ["gate"]
        by_lane = {}
        for lane in lanes:
            toks = self.tokens_for(lane)
            by_lane[lane] = {
                **toks,
                "estimated_cost_usd": round(self.estimate_cost_usd(lane), 8),
                "intercept_success_rate": round(self.success_rate(lane), 4),
                "estimated_events": self.estimated_count(lane),
            }
        out: dict[str, Any] = {
            "model": self.model,
            "event_count": len(self.events),
            "lanes": by_lane,
        }
        est = self.estimated_count()
        if est:
            out["note"] = (
                f"{est} event(s) use heuristic token estimates (estimated=true). "
                "All other counts came from provider usage metadata."
            )
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "rates_usd_per_1m": self.rates_usd_per_1m,
            "summary": self.summary(),
            "events": [asdict(e) for e in self.events],
        }

    def write_json(self, path: "str | Path") -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    def write_csv(self, path: "str | Path") -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "lane",
            "kind",
            "ok",
            "prompt_tokens",
            "completion_tokens",
            "latency_ms",
            "namespace",
            "error",
            "estimated",
        ]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for e in self.events:
                writer.writerow({k: getattr(e, k) for k in fieldnames})
        return path


class Meter:
    """Collects RunEvents during a gated session."""

    def __init__(
        self,
        *,
        model: str = "gate",
        rates_usd_per_1m: dict[str, float] | None = None,
    ):
        self.report = RunReport(
            model=model,
            rates_usd_per_1m=dict(rates_usd_per_1m or DEFAULT_RATES_USD_PER_1M),
        )

    def record(self, event: RunEvent) -> RunEvent:
        self.report.add(event)
        return event

    def record_llm(
        self,
        *,
        lane: str,
        prompt: str = "",
        completion: str = "",
        ok: bool = True,
        latency_ms: float = 0.0,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        response: Any = None,
        error: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> RunEvent:
        """Record an LLM call. Token sources, in order of preference:

        1. Explicit prompt_tokens/completion_tokens (exact, from your own capture)
        2. response= payload, parsed via extract_usage() (exact)
        3. len//4 heuristic over prompt/completion text (flagged estimated=True)
        """
        estimated = False
        if response is not None and (prompt_tokens is None or completion_tokens is None):
            extracted_prompt, extracted_completion = extract_usage(response)
            if prompt_tokens is None:
                prompt_tokens = extracted_prompt
            if completion_tokens is None:
                completion_tokens = extracted_completion
        if prompt_tokens is None:
            prompt_tokens = estimate_tokens(prompt)
            estimated = True
        if completion_tokens is None:
            completion_tokens = estimate_tokens(completion)
            estimated = True
        return self.record(
            RunEvent(
                lane=lane,
                kind="llm",
                ok=ok,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                error=error,
                estimated=estimated,
                meta=meta or {},
            )
        )

    def record_intercept(
        self,
        *,
        lane: str,
        ok: bool,
        namespace: str | None = None,
        latency_ms: float = 0.0,
        error: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> RunEvent:
        return self.record(
            RunEvent(
                lane=lane,
                kind="intercept",
                ok=ok,
                latency_ms=latency_ms,
                namespace=namespace,
                error=error,
                meta=meta or {},
            )
        )

    def timed(self) -> "_Timer":
        return _Timer()

    def export(
        self, json_path: "str | Path", csv_path: "str | Path | None" = None
    ) -> dict[str, Path]:
        out = {"json": self.report.write_json(json_path)}
        if csv_path is not None:
            out["csv"] = self.report.write_csv(csv_path)
        return out


class _Timer:
    def __enter__(self) -> "_Timer":
        self._start = time.perf_counter()
        self.latency_ms = 0.0
        return self

    def __exit__(self, *args: object) -> None:
        self.latency_ms = (time.perf_counter() - self._start) * 1000
