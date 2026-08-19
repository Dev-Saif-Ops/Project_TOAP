#!/usr/bin/env python3
"""LangChain + TOAP live agent example.

Requires:
    pip install -e ".[langchain]"
    pip install langchain-google-genai python-dotenv

Setup:
    Copy GEMINI_API_KEY to .env (see toap-bench/.env.example)

Run:
    python examples/langchain_agent.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load API key from toap-bench/.env if present
_root = Path(__file__).parent.parent.parent
load_dotenv(_root / "toap-bench" / ".env")
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI

from toap import ToolRegistry
from toap.adapters.langchain import build_toap_chain, TOAPOutputParser


# ── Mock tools (replace with real implementations) ──────────────

def query_database(q: str, l: int = 10) -> dict:
    """Simulate DB query — namespace DB_SRC."""
    rows = [f"vuln_{i}: {q}" for i in range(1, min(l, 5) + 1)]
    return {"query": q, "limit": l, "rows": rows, "count": len(rows)}


def web_search(q: str, l: int = 10) -> dict:
    """Simulate web search — namespace WEB_SRC."""
    hits = [f"https://example.com/cve-{i}" for i in range(1, min(l, 3) + 1)]
    return {"query": q, "limit": l, "hits": hits, "count": len(hits)}


def main() -> int:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY in toap-bench/.env or environment")
        return 1

    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    print(f"=== TOAP + LangChain Live Agent ===")
    print(f"Model: {model}\n")

    registry = ToolRegistry()
    registry.register("DB_SRC", query_database)
    registry.register("WEB_SRC", web_search)

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0,
    )

    tasks = [
        "Query the database for Huawei Cloud vulnerabilities, limit 5",
        "Search the web for CVE-2026-1234 critical exploits, return top 10 results",
    ]

    parser = TOAPOutputParser()

    for i, task in enumerate(tasks, 1):
        print(f"--- Task {i}: {task[:60]}...")

        chain, proxy = build_toap_chain(llm, task, registry, shots=2)
        result = chain.invoke({})

        print(f"  Raw TOAP     : {result['raw'][:80].replace(chr(10), ' ')}...")
        print(f"  Valid        : {result['valid']}")
        print(f"  Namespace    : {result['namespace']}")
        print(f"  Args         : {result['args']}")
        print(f"  Executed     : {result['executed']}")
        if result["executed"]:
            print(f"  Tool result  : {result['return_value']}")
        if result["error"]:
            print(f"  Error        : {result['error']}")

        print(f"\n  Dev decode:\n{proxy.decode(result['raw'])}\n")

    print("=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
