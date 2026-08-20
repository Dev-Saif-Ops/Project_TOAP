"""TOAP meter — token/cost estimates and run reports for pilot insert paths."""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# Overridable defaults (Gemini Flash-class ballpark, USD per 1M tokens).
# Not billing-grade — see decisions.md D-006.
DEFAULT_RATES_USD_PER_1M = {
    "gemini-input": 0.10,
    "gemini-output": 0.40,
    "default-input": 0.10,
    "default-output": 0.40,
}


def estimate_tokens(text: str) -> int:
    """Stdlib heuristic when provider token counts are unavailable."""
    if not text:
        return 0
    return max(1, len(text) // 4)


@dataclass
class RunEvent:
    lane: str  # "toap" | "baseline" | "other"
    kind: str  # "llm" | "intercept" | "tool" | "note"
    ok: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    namespace: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class RunReport:
    events: list[RunEvent] = field(default_factory=list)
    model: str = "unknown"
    rates_usd_per_1m: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_RATES_USD_PER_1M))

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

    def estimate_cost_usd(self, lane: str | None = None) -> float:
        rates = self.rates_usd_per_1m
        inp = rates.get("gemini-input", rates.get("default-input", 0.0))
        out = rates.get("gemini-output", rates.get("default-output", 0.0))
        totals = self.tokens_for(lane)
        return (totals["prompt_tokens"] / 1_000_000) * inp + (
            totals["completion_tokens"] / 1_000_000
        ) * out

    def summary(self) -> dict[str, Any]:
        lanes = sorted({e.lane for e in self.events}) or ["toap"]
        by_lane = {}
        for lane in lanes:
            toks = self.tokens_for(lane)
            by_lane[lane] = {
                **toks,
                "estimated_cost_usd": round(self.estimate_cost_usd(lane), 8),
                "intercept_success_rate": round(self.success_rate(lane), 4),
            }
        return {
            "model": self.model,
            "event_count": len(self.events),
            "lanes": by_lane,
            "note": "Token counts may be heuristic (len//4) unless provider counts were supplied.",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "rates_usd_per_1m": self.rates_usd_per_1m,
            "summary": self.summary(),
            "events": [asdict(e) for e in self.events],
        }

    def write_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    def write_csv(self, path: str | Path) -> Path:
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
        ]
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for e in self.events:
                writer.writerow({k: getattr(e, k) for k in fieldnames})
        return path


class Meter:
    """Collects RunEvents during a pilot session."""

    def __init__(
        self,
        *,
        model: str = "gemini",
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
        prompt: str,
        completion: str,
        ok: bool = True,
        latency_ms: float = 0.0,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        error: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> RunEvent:
        return self.record(
            RunEvent(
                lane=lane,
                kind="llm",
                ok=ok,
                prompt_tokens=prompt_tokens if prompt_tokens is not None else estimate_tokens(prompt),
                completion_tokens=(
                    completion_tokens
                    if completion_tokens is not None
                    else estimate_tokens(completion)
                ),
                latency_ms=latency_ms,
                error=error,
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
        completion_text: str = "",
        meta: dict[str, Any] | None = None,
    ) -> RunEvent:
        return self.record(
            RunEvent(
                lane=lane,
                kind="intercept",
                ok=ok,
                completion_tokens=estimate_tokens(completion_text) if completion_text else 0,
                latency_ms=latency_ms,
                namespace=namespace,
                error=error,
                meta=meta or {},
            )
        )

    def timed(self) -> "_Timer":
        return _Timer()

    def export(self, json_path: str | Path, csv_path: str | Path | None = None) -> dict[str, Path]:
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
