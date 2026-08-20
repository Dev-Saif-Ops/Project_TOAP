"""TOAP — Token-Optimized Agent Protocol."""

from toap.compare import summarize_ab
from toap.encoder import baseline_json, encode_action, encode_json_tool_call, encode_tool_call
from toap.meter import Meter, RunEvent, RunReport, estimate_tokens
from toap.parser import TOAPParser, ParseResult, ParseError
from toap.proxy import TOAPProxy, ToolRegistry, InterceptResult
from toap.schema import ToolSchema, schema_from_signature

__version__ = "0.1.1"

__all__ = [
    "TOAPParser",
    "ParseResult",
    "ParseError",
    "TOAPProxy",
    "ToolRegistry",
    "InterceptResult",
    "Meter",
    "RunEvent",
    "RunReport",
    "estimate_tokens",
    "ToolSchema",
    "schema_from_signature",
    "encode_action",
    "encode_tool_call",
    "encode_json_tool_call",
    "baseline_json",
    "summarize_ab",
    "__version__",
]
