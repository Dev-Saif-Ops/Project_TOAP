"""TOAP CLI — dev-mode pretty printer and validator."""

from __future__ import annotations

import argparse
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

    # Support multi-line TOAP blocks separated by blank lines
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

    args = ap.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
