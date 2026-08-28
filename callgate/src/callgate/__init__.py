"""callgate: fail-closed firewall for AI agent tool calls.

Structured outputs guarantee your agent's tool calls are well-formed.
callgate guarantees they're allowed.
"""

from callgate.gate import Gate, GateResult, ToolRegistry, Verdict
from callgate.intake import IntakeError, ToolCall, parse_tool_calls
from callgate.meter import Meter, RunEvent, RunReport, extract_usage
from callgate.policy import (
    Policy,
    ends_with,
    in_range,
    matches,
    max_len,
    not_empty,
    one_of,
    starts_with,
)
from callgate.schema import ToolSchema, schema_from_signature
from callgate.shield import Finding, Shield
from callgate.suggest import suggest_policies
from callgate.mcp_guard import GuardedCall, MCPGuard, to_mcp_error

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
    "extract_usage",
    "Policy",
    "in_range",
    "one_of",
    "matches",
    "max_len",
    "ends_with",
    "starts_with",
    "not_empty",
    "ToolSchema",
    "schema_from_signature",
    "Shield",
    "Finding",
    "suggest_policies",
    "MCPGuard",
    "GuardedCall",
    "to_mcp_error",
    "__version__",
]
