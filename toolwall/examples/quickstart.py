#!/usr/bin/env python3
"""toolwall quickstart. No API key needed.

An agent's tool call (any provider shape) hits the gate before it can execute.
Well-formed is not the same as allowed.
"""

from toolwall import Gate, Meter, Policy, Shield, ToolSchema, in_range, not_empty


# --- your existing tools -------------------------------------------------------

def db_query(q: str, limit: int = 10) -> dict:
    return {"status": "ok", "q": q, "rows": min(limit, 3)}


def delete_records(filter: dict) -> dict:
    return {"status": "deleted", "filter": filter}


def send_email(to: str, body: str) -> dict:
    return {"status": "sent", "to": to}


# --- wire the gate --------------------------------------------------------------

meter = Meter(model="offline-demo")
gate = Gate(default="deny", meter=meter, shield=Shield(mode="block"))

gate.register(
    "db_query",
    db_query,
    schema=ToolSchema(required=["q"], types={"q": str, "limit": int}),
    policy=Policy(constraints={"limit": in_range(1, 100)}),
)
gate.register(
    "delete_records",
    delete_records,
    schema=ToolSchema(required=["filter"], types={"filter": dict}),
    policy=Policy(constraints={"filter": not_empty}, require_approval=True),
)
gate.register(
    "send_email",
    send_email,
    schema=ToolSchema(required=["to", "body"], types={"to": str, "body": str}),
)
gate.budget(max_calls=20)


def show(label: str, result) -> None:
    reason = result.reasons[0] if result.reasons else ""
    print(f"[{label}] -> {result.verdict.value:15} executed={result.executed}  {reason}")


# 1. normal call passes (OpenAI response shape)
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
show("normal call     ", gate.run(openai_style))

# 2. hallucinated tool: blocked
show("unknown tool    ", gate.run({"name": "drop_all_tables", "args": {}}))

# 3. schema-valid but out-of-range value: policy blocks
show("limit=10000000  ", gate.run({"name": "db_query", "args": {"q": "all", "limit": 10_000_000}}))

# 4. empty filter delete: policy blocks the classic table-wipe
show("delete filter={}", gate.run({"name": "delete_records", "args": {"filter": {}}}))

# 5. valid delete without an approval handler: held, never executed
show("delete, no appr ", gate.run({"name": "delete_records", "args": {"filter": {"id": 42}}}))

# 6. secret exfil attempt: shield blocks before the email leaves
show("secret in email ", gate.run({
    "name": "send_email",
    "args": {"to": "dev@ourco.com", "body": "creds: " + "AKIA" + "IOSFODNN7EXAMPLE"},
}))

# --- audit trail -------------------------------------------------------------------

paths = meter.export("audit.json", "audit.csv")
print(f"\nAudit written: {paths['json']} / {paths['csv']}  (secret values never logged)")
print("Inspect with:  toolwall report audit.json")
