#!/usr/bin/env python3
"""TOAP quickstart example — run after: pip install -e ./toap-python"""

from toap import Meter, TOAPParser, TOAPProxy, ToolRegistry, ToolSchema
from toap.prompts import build_system_prompt


def query_database(q: str, l: int = 10) -> dict:
    return {"status": "ok", "query": q, "limit": l, "rows": min(l, 3)}


def main():
    print("=== TOAP Quickstart ===\n")

    # 1. Parse
    parser = TOAPParser()
    sample = '§T[sec_vuln_huawei_2026]\nƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5'
    result = parser.parse(sample)
    print("[1] Parse:", result.valid, result.args)

    # 2. Pretty print
    print("\n[2] Dev-mode decode:")
    print(parser.pretty_print(sample))

    # 3. Proxy + meter + schema
    meter = Meter(model="offline")
    registry = ToolRegistry()
    registry.register(
        "DB_SRC",
        query_database,
        schema=ToolSchema(required=["q"], types={"q": str, "l": int}),
    )
    proxy = TOAPProxy(registry, meter=meter)
    intercepted = proxy.intercept('ƒ(DB_SRC)>q:"active sessions"|l:3')
    print("\n[3] Proxy result:", intercepted.return_value)
    print("[3b] Meter summary:", meter.report.summary())

    # 4. Prompt for LLM
    prompt = build_system_prompt("Query database for critical CVEs", shots=2)
    print("\n[4] System prompt (first 200 chars):")
    print(prompt[:200], "...")


if __name__ == "__main__":
    main()
