"""Argument receipts: what was checked is what executes.

Reported on Reddit by u/deelight_0909: "Let a mutable delete_records argument pass
with a narrow filter, then replace the filter with {} before execution. If it trusts
a bare ALLOW boolean, fail-closed can reopen one line later." Reproduced on both
paths before fixing.
"""

import pytest

from toolwall import Gate, Policy, ToolSchema, Verdict, not_empty
from toolwall.receipt import ReceiptError, fingerprint


def build(approval=None):
    ran = []

    def delete_records(filter: dict):
        ran.append(dict(filter))
        return {"ok": True}

    gate = Gate(default="deny", approval=approval)
    gate.register(
        "delete_records",
        delete_records,
        schema=ToolSchema(required=["filter"], types={"filter": dict}),
        policy=Policy(
            constraints={"filter": not_empty},
            require_approval=approval is not None,
        ),
    )
    return gate, ran


def test_caller_cannot_swap_args_after_the_verdict():
    """The caller keeps a reference to the dict it passed in."""
    gate, ran = build()
    payload = {"name": "delete_records", "args": {"filter": {"id": 42}}}

    result = gate.check(payload)
    assert result.allowed

    payload["args"]["filter"].clear()  # widen the delete to everything
    gate.execute(result)

    assert ran == [{"id": 42}], "the tool must receive the arguments that were checked"


def test_approval_handler_cannot_swap_args():
    """The handler is given the GateResult itself, so it can reach the gate's own copy."""
    def approver(result):
        result.call.args["filter"] = {}
        return True

    gate, ran = build(approval=approver)
    out = gate.run({"name": "delete_records", "args": {"filter": {"id": 42}}})

    assert ran == [], "nothing may run once the approved arguments have changed"
    assert out.verdict is Verdict.BLOCK
    assert not out.executed
    assert "changed between check and execute" in " ".join(out.reasons)


def test_direct_mutation_between_check_and_execute_is_refused():
    gate, ran = build()
    result = gate.check({"name": "delete_records", "args": {"filter": {"id": 42}}})
    result.call.args["filter"] = {}

    out = gate.execute(result)
    assert ran == []
    assert out.verdict is Verdict.BLOCK
    assert not out.executed


def test_a_refused_execute_does_not_spend_budget():
    gate, ran = build()
    gate.budget(max_calls=1)

    first = gate.check({"name": "delete_records", "args": {"filter": {"id": 1}}})
    first.call.args["filter"] = {}
    gate.execute(first)  # refused, must not consume the single allowed call

    second = gate.run({"name": "delete_records", "args": {"filter": {"id": 2}}})
    assert second.executed and ran == [{"id": 2}]


def test_unfingerprintable_args_block_by_default():
    gate = Gate(default="deny")
    gate.register("takes_object", lambda thing: "ran", schema=ToolSchema(required=["thing"]))

    out = gate.run({"name": "takes_object", "args": {"thing": object()}})
    assert out.blocked
    assert not out.executed
    assert "cannot bind receipt" in out.reasons[0]


def test_receipt_false_is_an_explicit_opt_out():
    gate = Gate(default="deny")
    gate.register(
        "takes_object",
        lambda thing: "ran",
        schema=ToolSchema(required=["thing"]),
        receipt=False,
    )

    out = gate.run({"name": "takes_object", "args": {"thing": object()}})
    assert out.allowed and out.executed
    assert out.receipt is None


def test_replace_clears_a_previous_opt_out():
    """A re-registration must not inherit the old tool's weaker guarantee."""
    gate = Gate(default="deny")
    gate.register("t", lambda thing: "a", schema=ToolSchema(required=["thing"]), receipt=False)
    gate.register("t", lambda thing: "b", schema=ToolSchema(required=["thing"]), replace=True)

    assert gate.registry.wants_receipt("t")
    assert gate.run({"name": "t", "args": {"thing": object()}}).blocked


def test_key_order_does_not_produce_a_false_block():
    assert fingerprint("t", {"a": 1, "b": 2}) == fingerprint("t", {"b": 2, "a": 1})


@pytest.mark.parametrize(
    "left,right",
    [
        ({"v": 1}, {"v": True}),          # bool is an int in Python
        ({"v": 1}, {"v": 1.0}),           # 1 == 1.0
        ({"v": [1]}, {"v": (1,)}),        # list vs tuple
        ({"v": {}}, {"v": {"id": 1}}),    # the reported case
        ({"v": "1"}, {"v": 1}),
    ],
)
def test_distinguishable_values_get_distinct_fingerprints(left, right):
    assert fingerprint("t", left) != fingerprint("t", right)


def test_tool_name_is_part_of_the_receipt():
    assert fingerprint("delete_records", {"a": 1}) != fingerprint("read_records", {"a": 1})


def test_redacted_args_still_execute():
    """The shield rewrites args during check; the receipt must cover the rewritten form."""
    from toolwall import Shield

    ran = []
    gate = Gate(default="deny", shield=Shield(mode="redact"))
    gate.register(
        "note",
        lambda text: ran.append(text),
        schema=ToolSchema(required=["text"], types={"text": str}),
    )

    out = gate.run({"name": "note", "args": {"text": "key " + "AKIA" + "IOSFODNN7EXAMPLE"}})
    assert out.executed
    assert "AKIA" + "IOSFODNN7EXAMPLE" not in ran[0]


def test_fingerprint_rejects_non_string_dict_keys():
    with pytest.raises(ReceiptError, match="dict keys"):
        fingerprint("t", {"a": {1: "x"}})


def test_an_approved_result_cannot_be_replayed():
    """One verdict authorises one execution, not a stream of them."""
    gate, ran = build()
    result = gate.check({"name": "delete_records", "args": {"filter": {"id": 42}}})

    gate.execute(result)
    again = gate.execute(result)

    assert ran == [{"id": 42}], "the same approved result must not run twice"
    assert again.verdict is Verdict.BLOCK
    assert "already spent" in " ".join(again.reasons)


def test_replay_is_refused_even_when_the_first_attempt_failed():
    """A tool that raised may still have had side effects; a retry gets re-checked."""
    gate = Gate(default="deny")
    calls = []

    def flaky(x: int):
        calls.append(x)
        raise RuntimeError("boom")

    gate.register("flaky", flaky, schema=ToolSchema(required=["x"], types={"x": int}))
    result = gate.check({"name": "flaky", "args": {"x": 1}})

    first = gate.execute(result)
    assert not first.executed and first.error

    second = gate.execute(result)
    assert calls == [1], "a failed attempt is still an attempt"
    assert second.verdict is Verdict.BLOCK


def test_unreceipted_tools_are_documented_as_replayable():
    """receipt=False opts out of tamper-checking, and of replay protection with it."""
    gate = Gate(default="deny")
    ran = []
    gate.register(
        "obj", lambda thing: ran.append(1),
        schema=ToolSchema(required=["thing"]), receipt=False,
    )
    r = gate.check({"name": "obj", "args": {"thing": object()}})
    gate.execute(r)
    gate.execute(r)
    assert len(ran) == 2  # known limitation of the explicit opt-out


# --- common stdlib value types must not be false-blocked ------------------------

def test_common_value_types_are_fingerprintable():
    """datetime, date, time, Decimal, UUID and Enum are ordinary tool arguments.

    Blocking them would be a false block caused by the canonicaliser being
    unfinished, not by anything being unsafe. Found by probing with realistic
    args (a booking date, a Decimal price) rather than the suite's plain types.
    """
    import datetime as dt
    import enum
    import uuid
    from decimal import Decimal

    class Tier(enum.Enum):
        FREE = "f"
        PRO = "p"

    gate = Gate(default="deny")
    seen = []
    gate.register("book", lambda **kw: seen.append(kw), schema=ToolSchema())

    out = gate.run({
        "name": "book",
        "args": {
            "when": dt.datetime(2026, 8, 29, 10, 30),
            "day": dt.date(2026, 8, 29),
            "at": dt.time(10, 30),
            "price": Decimal("10.50"),
            "ref": uuid.UUID("12345678-1234-5678-1234-567812345678"),
            "tier": Tier.PRO,
        },
    })
    assert out.allowed and out.executed


def test_swapping_a_datetime_is_still_caught():
    """The new types are tamper-checked like everything else, not exempted."""
    import datetime as dt

    gate = Gate(default="deny")
    ran = []
    gate.register("book", lambda when: ran.append(when), schema=ToolSchema(required=["when"]))

    result = gate.check({"name": "book", "args": {"when": dt.datetime(2026, 8, 29)}})
    result.call.args["when"] = dt.datetime(1999, 1, 1)

    out = gate.execute(result)
    assert ran == [] and out.blocked


def test_new_types_cannot_collide_with_their_string_forms():
    import datetime as dt
    import enum
    from decimal import Decimal

    class Level(enum.IntEnum):
        HIGH = 2

    assert fingerprint("t", {"v": Decimal("10.50")}) != fingerprint("t", {"v": "10.50"})
    assert fingerprint("t", {"v": dt.datetime(2026, 8, 29)}) != fingerprint(
        "t", {"v": "2026-08-29T00:00:00"}
    )
    # IntEnum subclasses int; the member must not fingerprint as its value
    assert fingerprint("t", {"v": Level.HIGH}) != fingerprint("t", {"v": 2})
    # exponent is preserved: numerically equal Decimals may differ, which can only
    # refuse a swap, never admit one
    assert fingerprint("t", {"v": Decimal("10.50")}) != fingerprint("t", {"v": Decimal("10.5")})
