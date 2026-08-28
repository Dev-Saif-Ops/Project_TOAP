#!/usr/bin/env python3
"""callgate quickstart — no API key needed.

An agent's tool call (any provider shape) hits the gate before it can execute.
Well-formed is not the same as allowed.
"""

from callgate import Gate, Meter, ToolSchema


# --- your existing tools -----------------------------------------------------

def db_query(q: str, limit: int = 10) -> dict:
    return {"status": "ok", "q": q, "rows": min(limit, 3)}


def delete_records(filter: dict) -> dict:
    return {"status": "deleted", "filter": filter}


# --- wire the gate -----------------------------------------------------------

meter = Meter(model="offline-demo")
gate = Gate(default="deny", meter=meter)

gate.register("db_query", db_query, schema=ToolSchema(required=["q"], types={"q": str, "limit": int}))
gate.register("delete_records", delete_records, schema=ToolSchema(required=["filter"], types={"filter": dict}))


# --- 1. a normal call passes (OpenAI response shape) --------------------------

openai_style = {
    "choices": [
        {
            "message": {
                "tool_calls": [
                    {"id": "call_1", "function": {"name": "db_query", "arguments": '{"q": "open tickets", "limit": 5}'}}
                ]
            }
        }
    ]
}
result = gate.run(openai_style)
print(f"[1] db_query        -> {result.verdict.value:6}  executed={result.executed}  {result.return_value}")


# --- 2. a hallucinated tool is blocked ----------------------------------------

result = gate.run({"name": "drop_all_tables", "args": {}})
print(f"[2] drop_all_tables -> {result.verdict.value:6}  reason: {result.reasons[0]}")


# --- 3. schema-valid shape, missing required arg: blocked ---------------------

result = gate.run({"name": "delete_records", "args": {}})
print(f"[3] delete (no filter) -> {result.verdict.value:6}  reason: {result.reasons[0]}")


# --- audit trail ---------------------------------------------------------------

paths = meter.export("audit.json", "audit.csv")
print(f"\nAudit written: {paths['json']} / {paths['csv']}")
print("Inspect with:  callgate report audit.json")
