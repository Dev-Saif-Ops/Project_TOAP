"""TOAP CLI — dev-mode pretty printer, validator, and meter report viewer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from toap.parser import TOAPParser


def cmd_pretty(args: argparse.Namespace) -> int:
    parser = TOAPParser()
    if args.text:
        raw = args.text
    elif args.file:
        raw = Path(args.file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    print(parser.pretty_print(raw))
    return 0 if parser.parse(raw).valid else 1


def cmd_validate(args: argparse.Namespace) -> int:
    parser = TOAPParser()
    path = Path(args.file)
    content = path.read_text(encoding="utf-8")
    checked = 0
    failed = 0

    blocks = [b.strip() for b in content.split("\n\n") if b.strip() and not b.strip().startswith("#")]

    for i, block in enumerate(blocks, 1):
        if block.startswith("#"):
            continue
        result = parser.parse(block)
        checked += 1
        status = "OK" if result.valid else "FAIL"
        preview = block.replace("\n", " ")[:60]
        print(f"  [{status}] block {i}: {preview}...")
        if not result.valid:
            failed += 1
            for err in result.errors:
                print(f"         {err.message}")

    print(f"\n{checked - failed}/{checked} valid")
    return 1 if failed else 0


def cmd_report(args: argparse.Namespace) -> int:
    path = Path(args.file)
    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary") or {}
    print(f"Model: {data.get('model', 'unknown')}")
    print(f"Events: {summary.get('event_count', len(data.get('events', [])))}")
    lanes = summary.get("lanes") or {}
    for lane, stats in lanes.items():
        print(f"\n[{lane}]")
        print(f"  prompt_tokens:      {stats.get('prompt_tokens')}")
        print(f"  completion_tokens:  {stats.get('completion_tokens')}")
        print(f"  total_tokens:       {stats.get('total_tokens')}")
        print(f"  estimated_cost_usd: {stats.get('estimated_cost_usd')}")
        print(f"  intercept_ok_rate:  {stats.get('intercept_success_rate')}")
    if summary.get("note"):
        print(f"\nNote: {summary['note']}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(prog="toap-cli", description="TOAP dev tools")
    sub = ap.add_subparsers(dest="command", required=True)

    pretty = sub.add_parser("pretty", help="Decode TOAP to human-readable output")
    pretty.add_argument("text", nargs="?", help="TOAP string to decode")
    pretty.add_argument("-f", "--file", help="Read TOAP from file (or stdin)")
    pretty.set_defaults(func=cmd_pretty)

    validate = sub.add_parser("validate", help="Validate TOAP lines in a file")
    validate.add_argument("file", help="File with one TOAP output per line")
    validate.set_defaults(func=cmd_validate)

    report = sub.add_parser("report", help="Print summary from a Meter JSON export")
    report.add_argument("file", help="Path to meter report JSON")
    report.set_defaults(func=cmd_report)

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
