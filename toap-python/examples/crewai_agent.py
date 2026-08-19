#!/usr/bin/env python3
"""CrewAI + TOAP live agent example.

Requires:
    pip install -e ".[crewai]"
    pip install "crewai[google-genai]"

Setup:
    GEMINI_API_KEY in toap-bench/.env

Run:
    python examples/crewai_agent.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).parent.parent.parent
load_dotenv(_root / "toap-bench" / ".env")
load_dotenv()
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")

from crewai import LLM

from toap import ToolRegistry, TOAPParser
from toap.adapters.crewai import build_toap_crew, run_toap_crew


def query_database(q: str, l: int = 10) -> dict:
    rows = [f"vuln_{i}: {q}" for i in range(1, min(l, 5) + 1)]
    return {"query": q, "limit": l, "rows": rows, "count": len(rows)}


def web_search(q: str, l: int = 10) -> dict:
    hits = [f"https://example.com/cve-{i}" for i in range(1, min(l, 3) + 1)]
    return {"query": q, "limit": l, "hits": hits, "count": len(hits)}


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY in toap-bench/.env")
        return 1

    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    gemini_model = f"gemini/{model}" if not model.startswith("gemini/") else model

    print("=== TOAP + CrewAI Live Agent ===")
    print(f"Model: {gemini_model}\n")

    registry = ToolRegistry()
    registry.register("DB_SRC", query_database)
    registry.register("WEB_SRC", web_search)

    llm = LLM(model=gemini_model, api_key=api_key, temperature=0)

    tasks = [
        "Query the database for Huawei Cloud vulnerabilities, limit 5",
        "Search the web for CVE-2026-1234 critical exploits, return top 10 results",
    ]

    parser = TOAPParser()

    for i, task in enumerate(tasks, 1):
        print(f"--- Task {i}: {task[:60]}...")

        crew, callback, agent, crew_task = build_toap_crew(task, llm, shots=2)
        result = run_toap_crew(crew, callback, registry, execute=True)

        print(f"  Raw TOAP     : {result.raw[:80].replace(chr(10), ' ')}...")
        print(f"  Valid        : {result.parsed.valid}")
        print(f"  Namespace    : {result.parsed.namespace}")
        print(f"  Args         : {result.parsed.args}")
        print(f"  Executed     : {result.executed}")
        if result.executed:
            print(f"  Tool result  : {result.return_value}")
        if result.error:
            print(f"  Error        : {result.error}")

        print(f"\n  Dev decode:\n{parser.pretty_print(result.raw)}\n")

    print("=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
