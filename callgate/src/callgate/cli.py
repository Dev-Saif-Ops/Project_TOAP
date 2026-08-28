"""callgate CLI — inspect meter/audit exports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def cmd_report(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    print(f"Model:  {data.get('model', 'unknown')}")
    print(f"Events: {summary.get('event_count', len(data.get('events', [])))}")
    for lane, stats in (summary.get("lanes") or {}).items():
        print(f"\n[{lane}]")
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "intercept_success_rate",
        ):
            print(f"  {key}: {stats.get(key)}")
    if summary.get("note"):
        print(f"\nNote: {summary['note']}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="callgate", description="callgate dev tools")
    sub = ap.add_subparsers(dest="command", required=True)

    report = sub.add_parser("report", help="Print summary from a Meter JSON export")
    report.add_argument("file", help="Path to meter/audit JSON")
    report.set_defaults(func=cmd_report)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
