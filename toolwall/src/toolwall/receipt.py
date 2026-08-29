"""Argument receipts: bind what was checked to what actually executes.

A verdict is about a specific set of arguments. Between check() and execute()
those arguments can change: the caller still holds a reference to the dict it
passed in, and an approval handler is given the GateResult itself. Either can
turn a call the gate approved into a different call, so an ALLOW on its own is
not a safe thing for an executor to trust.

At check time the gate fingerprints (tool name, args). At execute time it
recomputes the fingerprint and refuses to run on a mismatch. A snapshot alone
would not be enough: it closes the caller's window and leaves the approval one
open, because there the gate's own copy is what gets mutated.

Fingerprinting is deliberately strict. A type we cannot canonicalise means we
cannot promise the executed call is the checked call, and quietly running it
anyway would leave exactly the strangest arguments unprotected.

Strict is not the same as narrow. A type belongs here when it has an exact,
stable text form that round-trips: Decimal and datetime are ordinary things to
pass a booking or payment tool, and blocking them would be a false block caused
by this file being unfinished rather than by anything being unsafe. The bar for
adding one is that two distinct values can never produce the same output.
"""

from __future__ import annotations

import datetime as _dt
import decimal
import enum
import hashlib
import json
import uuid
from typing import Any


class ReceiptError(Exception):
    """Arguments could not be canonicalised, so no receipt can be bound."""


_ATOMIC = (str, int, float, bool)


def _canonical(value: Any, path: str = "args") -> Any:
    """Order-independent, type-tagged form. Raises ReceiptError on anything else."""
    # Enums first: IntEnum subclasses int and StrEnum subclasses str, so the atomic
    # branch below would otherwise swallow them and lose which member was passed.
    if isinstance(value, enum.Enum):
        cls = type(value)
        return ["enum", f"{cls.__module__}.{cls.__qualname__}", value.name]
    # datetime before date: datetime is a subclass of date.
    if isinstance(value, _dt.datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, _dt.date):
        return ["date", value.isoformat()]
    if isinstance(value, _dt.time):
        return ["time", value.isoformat()]
    if isinstance(value, decimal.Decimal):
        # str() keeps the exponent, so Decimal("10.50") and Decimal("10.5") differ.
        # They are numerically equal, so this is conservative: it can only ever
        # refuse a swap, never wave one through.
        return ["decimal", str(value)]
    if isinstance(value, uuid.UUID):
        return ["uuid", str(value)]
    if value is None or isinstance(value, _ATOMIC):
        # Tag numeric types so 1 and 1.0 and True cannot collide.
        if isinstance(value, bool):
            return ["bool", value]
        if isinstance(value, int):
            return ["int", value]
        if isinstance(value, float):
            # repr round-trips floats exactly, including nan and inf.
            return ["float", repr(value)]
        if isinstance(value, str):
            return ["str", value]
        return ["null", None]
    if isinstance(value, bytes):
        return ["bytes", value.hex()]
    if isinstance(value, dict):
        items = []
        for key in value:
            if not isinstance(key, str):
                raise ReceiptError(
                    f"{path}: dict keys must be strings to fingerprint, "
                    f"found {type(key).__name__}"
                )
        for key in sorted(value):
            items.append([key, _canonical(value[key], f"{path}.{key}")])
        return ["dict", items]
    if isinstance(value, (list, tuple)):
        kind = "list" if isinstance(value, list) else "tuple"
        return [kind, [_canonical(v, f"{path}[{i}]") for i, v in enumerate(value)]]
    if isinstance(value, (set, frozenset)):
        # Sets have no order; canonicalise members then sort their serialised form.
        members = sorted(
            json.dumps(_canonical(v, f"{path}{{}}"), separators=(",", ":")) for v in value
        )
        return ["set", members]
    raise ReceiptError(
        f"{path}: cannot fingerprint a {type(value).__name__}. Pass a plain value, "
        f"or register the tool with receipt=False to accept that its arguments are "
        f"not tamper-checked between check and execute."
    )


def fingerprint(name: str, args: dict[str, Any]) -> str:
    """Stable fingerprint of a call. Raises ReceiptError if args cannot be canonicalised."""
    canonical = ["call", name, _canonical(args)]
    blob = json.dumps(canonical, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
