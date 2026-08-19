"""TOAP prompt templates for LLM integration."""

NAMESPACE_DOCS = """\
DB_SRC     — Database queries
WEB_SRC    — Web search
API_SRC    — API calls
FS_SRC     — File system operations
EMAIL_SRC  — Email sending
CACHE_SRC  — Cache lookup
LOG_SRC    — Log queries
CALC_SRC   — Calculations
DEPLOY_SRC — Deployments
REPORT_SRC — Report generation"""


GRAMMAR = """\
A valid TOAP response has:
1. An optional thought line: §T[<domain>]
2. A required action line: ƒ(<namespace>)><key>:<value>|<key>:<value>|...

Rules:
- §T[domain] marks your reasoning domain (optional)
- ƒ(NAMESPACE) marks the tool to invoke
- Arguments are pipe-delimited key:value pairs after >
- String values must be double-quoted
- Integer values are unquoted numbers
- Bare identifiers (like GET, ERROR) are unquoted"""


EXAMPLES_FEW_SHOT_2 = """\
Task: "Query the database for Huawei Cloud vulnerabilities, limit 5"
Response:
§T[sec_vuln_huawei_2026]
ƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5

Task: "Search the web for CVE-2026-1234 exploits, top 10 results"
Response:
ƒ(WEB_SRC)>q:"CVE-2026-1234 exploits"|l:10"""


def build_system_prompt(task_description: str, *, shots: int = 2) -> str:
    """Build a TOAP system prompt with optional few-shot examples."""
    parts = [
        "You are an AI agent operating in a production system.",
        "You MUST respond ONLY in TOAP (Token-Optimized Agent Protocol) format.",
        "No JSON. No natural language. No markdown.",
        "",
        "## TOAP Grammar",
        GRAMMAR,
        "",
        "## Available Namespaces",
        NAMESPACE_DOCS,
    ]

    if shots >= 2:
        parts.extend(["", "## Examples", EXAMPLES_FEW_SHOT_2])

    if shots >= 5:
        parts.extend([
            "",
            'Task: "Call the API health endpoint at /v1/status using GET with 30s timeout"',
            "Response:",
            "§T[infra_health_check]",
            'ƒ(API_SRC)>endpoint:"/v1/status"|method:GET|timeout:30',
            "",
            'Task: "Send email to admin@company.com with subject Security Alert"',
            "Response:",
            'ƒ(EMAIL_SRC)>to:"admin@company.com"|subject:"Security Alert"|body:"Alert triggered"',
            "",
            'Task: "Query logs for ERROR level entries in last 1 hour, limit 50"',
            "Response:",
            "§T[error_investigation]",
            'ƒ(LOG_SRC)>level:ERROR|window:"1h"|l:50',
        ])

    parts.extend([
        "",
        "## Task",
        task_description,
        "",
        "Respond with TOAP syntax ONLY:",
    ])
    return "\n".join(parts)
