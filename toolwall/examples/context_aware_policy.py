#!/usr/bin/env python3
"""Context-aware policy today: same arguments, different verdict per environment.

The question: can a policy use runtime context, so a db write is fine in staging
and blocked in production with the exact same arguments?

toolwall has no first-class `context` parameter yet. But policy rules are plain
callables, so a cross-arg rule can read the environment itself and decide. This
shows the same call allowed in staging and blocked in production.

    python examples/context_aware_policy.py

Caveat (and why a first-class version is on the roadmap): the environment here is
*ambient*. It is read from os.environ inside the rule, not passed into check()
and not written to the audit trail. So the log records the verdict, but not the
context the verdict was made under. The planned design passes an explicit
`context=` into check()/call(), hands it to the rules, and records it, so
"allowed in staging, blocked in production" is reproducible and visible.
"""

import os

from toolwall import Gate, Meter, Policy, ToolSchema


# --- your tool ----------------------------------------------------------------

def db_write(table: str, row: dict) -> dict:
    return {"status": "written", "table": table}


# --- a policy that reads runtime context (the environment) --------------------
# The cross-rule receives the args dict. There is no context parameter, so it
# reaches for the environment itself. Same args, different verdict per env.

TABLES_LOCKED_IN_PROD = {"users", "payments", "audit_log"}


def block_locked_writes_in_prod(args: dict) -> str | None:
    env = os.getenv("TOOLWALL_ENV", "staging")
    table = args.get("table")
    if env == "production" and table in TABLES_LOCKED_IN_PROD:
        return f"policy: writes to {table!r} are blocked in production (env={env!r})"
    return None


# --- wire the gate ------------------------------------------------------------

meter = Meter(model="offline-demo")
gate = Gate(default="deny", meter=meter)
gate.register(
    "db_write",
    db_write,
    schema=ToolSchema(required=["table", "row"], types={"table": str, "row": dict}),
    policy=Policy(cross=block_locked_writes_in_prod),
)


def show(env: str, result) -> None:
    reason = result.reasons[0] if result.reasons else "executed"
    print(f"[env={env:11}] {result.verdict.value:12} executed={result.executed}  {reason}")


# --- the exact same call, two environments ------------------------------------

call = {"name": "db_write", "args": {"table": "users", "row": {"id": 1, "name": "Ada"}}}

print("Same call:", call["args"], "\n")

os.environ["TOOLWALL_ENV"] = "staging"
show("staging", gate.run(call))

os.environ["TOOLWALL_ENV"] = "production"
show("production", gate.run(call))

# The audit trail records both verdicts, but not the environment each was decided
# under: that ambient context is exactly what a first-class `context=` would make
# explicit and record. (See the module docstring.)
print("\nNote: the verdict is logged, but 'which env' is not. A first-class")
print("context= parameter would make that explicit and auditable.")
