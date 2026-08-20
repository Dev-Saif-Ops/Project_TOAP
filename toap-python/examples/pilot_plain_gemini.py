#!/usr/bin/env python3
"""Plain Gemini / offline pilot: baseline JSON vs TOAP with Meter A/B.

Default offline (no API). Live Gemini with --live.
Multi-hop amortizes the few-shot system prompt (closer to real agent loops):

  python examples/pilot_plain_gemini.py
  python examples/pilot_plain_gemini.py --hops 8
  python examples/pilot_plain_gemini.py --live --hops 8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from toap import (
    Meter,
    TOAPProxy,
    ToolRegistry,
    ToolSchema,
    baseline_json,
    encode_tool_call,
    summarize_ab,
)
from toap.prompts import build_system_prompt


def query_database(q: str, l: int = 10) -> dict:
    return {"status": "ok", "query": q, "limit": l, "rows": min(int(l), 3)}


def web_search(q: str, l: int = 10) -> dict:
    return {"status": "ok", "query": q, "hits": min(int(l), 5)}


TASK_POOL = [
    {
        "user": "Query database for Huawei Cloud vulnerabilities, limit 5",
        "payload": {
            "namespace": "DB_SRC",
            "args": {"q": "Huawei Cloud vulnerabilities", "l": 5},
            "thought": "sec_vuln_huawei",
        },
    },
    {
        "user": "List active sessions limit 3",
        "payload": {
            "namespace": "DB_SRC",
            "args": {"q": "active sessions", "l": 3},
            "thought": "ops_sessions",
        },
    },
    {
        "user": "Search the web for CVE-2026-1234 exploits, top 10",
        "payload": {
            "namespace": "WEB_SRC",
            "args": {"q": "CVE-2026-1234 exploits", "l": 10},
            "thought": "cve_search",
        },
    },
    {
        "user": "Query database for open firewall tickets, limit 8",
        "payload": {
            "namespace": "DB_SRC",
            "args": {"q": "open firewall tickets", "l": 8},
            "thought": "fw_tickets",
        },
    },
    {
        "user": "Search web for Gemini flash rate limits, top 5",
        "payload": {
            "namespace": "WEB_SRC",
            "args": {"q": "Gemini flash rate limits", "l": 5},
            "thought": "rate_limits",
        },
    },
    {
        "user": "Query database for failed logins last hour, limit 20",
        "payload": {
            "namespace": "DB_SRC",
            "args": {"q": "failed logins last hour", "l": 20},
            "thought": "auth_fail",
        },
    },
    {
        "user": "Search web for LangChain tool calling best practices, top 7",
        "payload": {
            "namespace": "WEB_SRC",
            "args": {"q": "LangChain tool calling best practices", "l": 7},
            "thought": "lc_tools",
        },
    },
    {
        "user": "Query database for critical CVEs in cloud accounts, limit 12",
        "payload": {
            "namespace": "DB_SRC",
            "args": {"q": "critical CVEs cloud accounts", "l": 12},
            "thought": "crit_cve",
        },
    },
]


def _load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / "toap-bench" / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _tasks(hops: int) -> list[dict]:
    if hops < 1:
        raise SystemExit("--hops must be >= 1")
    out: list[dict] = []
    while len(out) < hops:
        out.extend(TASK_POOL)
    return out[:hops]


def _baseline_for(task: dict) -> str:
    return baseline_json(
        {"action": task["payload"]["namespace"], "params": task["payload"]["args"]}
    )


def run_offline(meter: Meter, proxy: TOAPProxy, hops: int) -> None:
    """System prompt counted once per lane; each hop adds user+completion only."""
    system = build_system_prompt("You help with DB and web lookups", shots=2)
    tasks = _tasks(hops)

    meter.record_llm(lane="baseline", prompt=system, completion="", meta={"phase": "system_once"})
    meter.record_llm(lane="toap", prompt=system, completion="", meta={"phase": "system_once"})

    for i, task in enumerate(tasks, 1):
        baseline = _baseline_for(task)
        toap_raw = encode_tool_call(task["payload"])

        meter.record_llm(
            lane="baseline",
            prompt=task["user"],
            completion=baseline,
            meta={"hop": i, "mode": "offline"},
        )
        meter.record_intercept(
            lane="baseline",
            ok=True,
            namespace=task["payload"]["namespace"],
            completion_text=baseline,
            meta={"hop": i},
        )

        meter.record_llm(
            lane="toap",
            prompt=task["user"],
            completion=toap_raw,
            meta={"hop": i, "mode": "offline"},
        )
        result = proxy.intercept(toap_raw)
        assert result.executed, result.error


def run_live(meter: Meter, proxy: TOAPProxy, hops: int) -> None:
    try:
        from google import genai
    except ImportError as exc:
        raise SystemExit("Install google-genai for --live") from exc

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY for --live")

    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client(api_key=api_key)
    system = build_system_prompt("You help with DB and web lookups", shots=2)
    tasks = _tasks(hops)

    # Amortize system prompt once per lane
    meter.record_llm(lane="baseline", prompt=system, completion="", meta={"phase": "system_once"})
    meter.record_llm(lane="toap", prompt=system, completion="", meta={"phase": "system_once", "model": model})

    for i, task in enumerate(tasks, 1):
        baseline = _baseline_for(task)
        meter.record_llm(
            lane="baseline",
            prompt=task["user"],
            completion=baseline,
            meta={"hop": i, "mode": "synthetic_json_baseline"},
        )
        meter.record_intercept(
            lane="baseline",
            ok=True,
            namespace=task["payload"]["namespace"],
            completion_text=baseline,
            meta={"hop": i},
        )

        # Live: system sent each call (API reality) but we only *bill* user turn in meter
        # for hop completions; system already counted once above for amortized view.
        prompt = system + "\n\nUser: " + task["user"]
        resp = client.models.generate_content(model=model, contents=prompt)
        text = getattr(resp, "text", None) or str(resp)
        meter.record_llm(
            lane="toap",
            prompt=task["user"],
            completion=text,
            meta={"hop": i, "model": model, "full_prompt_sent": True},
        )
        result = proxy.intercept(text)
        if not result.executed:
            print(f"[hop {i}] TOAP intercept failed:", result.error)
            print("Raw:", text[:400])


def build_proxy(meter: Meter) -> TOAPProxy:
    registry = ToolRegistry()
    registry.register(
        "DB_SRC",
        query_database,
        schema=ToolSchema(required=["q"], types={"q": str, "l": int}),
    )
    registry.register(
        "WEB_SRC",
        web_search,
        schema=ToolSchema(required=["q"], types={"q": str, "l": int}),
    )
    return TOAPProxy(registry, meter=meter, lane="toap", require_schema=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="TOAP plain Gemini/offline A/B pilot")
    ap.add_argument("--live", action="store_true", help="Call Gemini (needs API key)")
    ap.add_argument("--hops", type=int, default=8, help="Tool-call hops (default 8)")
    ap.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[2] / "toap-bench" / "results" / "pilot"),
        help="Directory for meter JSON/CSV",
    )
    args = ap.parse_args()
    _load_env()

    meter = Meter(model="gemini" if args.live else "offline-fixture")
    proxy = build_proxy(meter)

    if args.live:
        run_live(meter, proxy, args.hops)
    else:
        run_offline(meter, proxy, args.hops)

    out = Path(args.out_dir)
    tag = "live" if args.live else "offline"
    paths = meter.export(
        out / f"pilot_{tag}_h{args.hops}.json",
        out / f"pilot_{tag}_h{args.hops}.csv",
    )
    ab = summarize_ab(meter.report)
    print(f"=== Pilot A/B summary ({tag}, hops={args.hops}) ===")
    print(json.dumps(ab, indent=2))
    print("Wrote:", paths["json"])
    print("Wrote:", paths["csv"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
