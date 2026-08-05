from __future__ import annotations

import re
from typing import Pattern, Tuple

_REDACTIONS: Tuple[Tuple[Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+"),
        r"\1<redacted>",
    ),
    (
        re.compile(r"(?i)((?:token|access_token|refresh_token|api_key|apikey)\s*[=:]\s*)[^\s,;]+"),
        r"\1<redacted>",
    ),
    (
        re.compile(r"(?i)(https?://[^\s/:]+:)[^@\s]+(@)"),
        r"\1<redacted>\2",
    ),
    (
        re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
        "<redacted-github-token>",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "<redacted-jwt>",
    ),
)


def redact(text: str) -> str:
    result = text
    for pattern, replacement in _REDACTIONS:
        result = pattern.sub(replacement, result)
    return result
