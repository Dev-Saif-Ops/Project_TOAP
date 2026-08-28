"""callgate — fail-closed firewall for AI agent tool calls.

Structured outputs guarantee your agent's tool calls are well-formed.
callgate guarantees they're allowed.
"""

from callgate.gate import Gate, GateResult, ToolRegistry, Verdict
from callgate.intake import IntakeError, ToolCall, parse_tool_calls
from callgate.meter import Meter, RunEvent, RunReport
from callgate.schema import ToolSchema, schema_from_signature

__version__ = "0.2.0.dev0"

__all__ = [
    "Gate",
    "GateResult",
    "Verdict",
    "ToolRegistry",
    "ToolCall",
    "IntakeError",
    "parse_tool_calls",
    "Meter",
    "RunEvent",
    "RunReport",
    "ToolSchema",
    "schema_from_signature",
    "__version__",
]
