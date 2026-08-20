"""Compare baseline vs TOAP meter lanes for pilot A/B reports."""

from __future__ import annotations

from typing import Any

from toap.meter import RunReport


def summarize_ab(report: RunReport, *, baseline_lane: str = "baseline", toap_lane: str = "toap") -> dict[str, Any]:
    base = report.tokens_for(baseline_lane)
    toap = report.tokens_for(toap_lane)
    base_total = base["total_tokens"] or 0
    toap_total = toap["total_tokens"] or 0
    saved = base_total - toap_total
    pct = (saved / base_total * 100.0) if base_total else 0.0

    base_out = base["completion_tokens"]
    toap_out = toap["completion_tokens"]
    out_saved = base_out - toap_out
    out_pct = (out_saved / base_out * 100.0) if base_out else 0.0

    return {
        "baseline": base,
        "toap": toap,
        "net_token_delta": saved,
        "net_token_savings_pct": round(pct, 2),
        "output_token_delta": out_saved,
        "output_token_savings_pct": round(out_pct, 2),
        "baseline_cost_usd": round(report.estimate_cost_usd(baseline_lane), 8),
        "toap_cost_usd": round(report.estimate_cost_usd(toap_lane), 8),
        "baseline_intercept_success_rate": round(report.success_rate(baseline_lane), 4),
        "toap_intercept_success_rate": round(report.success_rate(toap_lane), 4),
        "honest_note": (
            "Net savings include prompt tokens when recorded. "
            "Single-turn few-shot prompts often shrink net savings vs output-only."
        ),
    }
