"""Secret detection and redaction at the callgate checkpoint (D-019).

Findings and audit events carry the pattern class and location only, NEVER the
secret value. Detection is pattern + entropy based and is never 100%; the
detection tests define exactly what is covered. Structureless generic passwords
are out of detection scope by design.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterator, Literal

Mode = Literal["redact", "block", "warn"]

DEFAULT_PATTERNS: tuple[tuple[str, "re.Pattern[str]"], ...] = (
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("stripe-key", re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{4,}\b")),
    (
        "credential-assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?(?P<val>[^\s'\"]{8,})"
        ),
    ),
)

_ENTROPY_CANDIDATE = re.compile(r"\b[A-Za-z0-9+/=_\-]{24,}\b")


def shannon_entropy(text: str) -> float:
    """Bits per character over the string's own distribution."""
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


@dataclass
class Finding:
    """Where a secret-shaped value was seen. Deliberately value-free."""

    kind: str
    start: int
    end: int
    arg: str | None = None
    placeholder: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "start": self.start,
            "end": self.end,
            "arg": self.arg,
            "placeholder": self.placeholder,
        }


class Shield:
    """Scan/redact secrets in text and in tool-call args.

    Modes (used by Gate when attached):
      block  -> any finding blocks the call (recommended for tool args)
      redact -> values are replaced with placeholders, call proceeds
      warn   -> findings are recorded, call proceeds unchanged

    The placeholder-to-value vault lives only in process memory.
    """

    def __init__(
        self,
        mode: Mode = "redact",
        *,
        patterns: tuple[tuple[str, "re.Pattern[str]"], ...] = DEFAULT_PATTERNS,
        entropy: bool = True,
        entropy_threshold: float = 4.5,
        allowlist: tuple[str, ...] | set[str] = (),
    ) -> None:
        if mode not in ("redact", "block", "warn"):
            raise ValueError(f"mode must be redact|block|warn, got {mode!r}")
        self.mode: Mode = mode
        self.patterns = patterns
        self.entropy = entropy
        self.entropy_threshold = entropy_threshold
        self.allowlist = set(allowlist)
        self._vault: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    # -- scanning ------------------------------------------------------------

    def scan(self, text: str) -> list[Finding]:
        if not isinstance(text, str) or not text:
            return []
        spans: list[tuple[int, int, str]] = []
        for kind, pattern in self.patterns:
            for match in pattern.finditer(text):
                if "val" in (match.groupdict() or {}):
                    start, end = match.span("val")
                else:
                    start, end = match.span()
                if text[start:end] in self.allowlist:
                    continue
                spans.append((start, end, kind))
        if self.entropy:
            for match in _ENTROPY_CANDIDATE.finditer(text):
                value = match.group()
                if value in self.allowlist:
                    continue
                if shannon_entropy(value) >= self.entropy_threshold:
                    spans.append((match.start(), match.end(), "high-entropy-string"))
        spans.sort(key=lambda s: (s[0], -s[1]))
        findings: list[Finding] = []
        last_end = -1
        for start, end, kind in spans:
            if start < last_end:
                continue
            findings.append(Finding(kind=kind, start=start, end=end))
            last_end = end
        return findings

    def scan_args(self, args: dict[str, Any]) -> list[Finding]:
        findings: list[Finding] = []
        for path, text in _walk_strings(args):
            for f in self.scan(text):
                f.arg = path
                findings.append(f)
        return findings

    # -- redaction -----------------------------------------------------------

    def redact_text(self, text: str) -> tuple[str, list[Finding]]:
        findings = self.scan(text)
        out = text
        for f in reversed(findings):
            placeholder = self._placeholder(f.kind)
            self._vault[placeholder] = text[f.start : f.end]
            f.placeholder = placeholder
            out = out[: f.start] + placeholder + out[f.end :]
        return out, findings

    def redact_args(self, args: dict[str, Any]) -> tuple[dict[str, Any], list[Finding]]:
        findings: list[Finding] = []

        def transform(value: Any, path: str) -> Any:
            if isinstance(value, str):
                clean, found = self.redact_text(value)
                for f in found:
                    f.arg = path
                findings.extend(found)
                return clean
            if isinstance(value, dict):
                return {k: transform(v, f"{path}.{k}") for k, v in value.items()}
            if isinstance(value, list):
                return [transform(v, f"{path}[{i}]") for i, v in enumerate(value)]
            return value

        clean_args = {k: transform(v, k) for k, v in args.items()}
        return clean_args, findings

    def restore(self, text: str) -> str:
        for placeholder, value in self._vault.items():
            text = text.replace(placeholder, value)
        return text

    def _placeholder(self, kind: str) -> str:
        self._counts[kind] = self._counts.get(kind, 0) + 1
        return f"[REDACTED:{kind}-{self._counts[kind]}]"


def _walk_strings(value: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path or "value", value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk_strings(v, f"{path}[{i}]")
