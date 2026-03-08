from __future__ import annotations

import re
from dataclasses import dataclass

# Patterns that are so unambiguously malicious that a single match warrants an
# immediate deny decision — no second hit required.
_HIGH_SEVERITY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ignore (all|any|previous) instructions", re.IGNORECASE), "ignore_previous"),
    (re.compile(r"reveal (the )?system prompt", re.IGNORECASE), "reveal_system_prompt"),
    (re.compile(r"exfiltrate secrets?", re.IGNORECASE), "exfiltrate_secrets"),
    (re.compile(r"bypass safety", re.IGNORECASE), "bypass_safety"),
    (re.compile(r"disable safety", re.IGNORECASE), "disable_safety"),
    (re.compile(r"jailbreak", re.IGNORECASE), "jailbreak"),
    (re.compile(r"DAN mode", re.IGNORECASE), "dan_mode"),
    (
        re.compile(r"act as (an? )?(unrestricted|unfiltered|uncensored)", re.IGNORECASE),
        "unrestricted_persona",
    ),
]

# Patterns that are suspicious in isolation but may have legitimate uses.
# A single hit raises a warning; two or more escalate to deny.
_WARNING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"system prompt", re.IGNORECASE), "system_prompt"),
    (re.compile(r"reveal hidden", re.IGNORECASE), "reveal_hidden"),
    (re.compile(r"print env", re.IGNORECASE), "print_env"),
    (re.compile(r"repeat (the )?(above|previous|initial)", re.IGNORECASE), "repeat_previous"),
]

# Combined view for callers that want the full list.
INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = _HIGH_SEVERITY_PATTERNS + _WARNING_PATTERNS


@dataclass(frozen=True)
class PromptSafetyResult:
    decision: str
    reasons: list[str]
    sanitized_text: str


def _sanitize(text: str, matches: list[re.Match[str]]) -> str:
    if not matches:
        return text
    sanitized = text
    for match in matches:
        segment = match.group(0)
        sanitized = sanitized.replace(segment, "[REMOVED_UNSAFE_SEGMENT]")
    return sanitized


def evaluate_prompt(text: str) -> PromptSafetyResult:
    """Evaluate a prompt for injection attempts.

    Decision logic:
    - Any match against a *high-severity* pattern → ``deny`` immediately.
    - Two or more matches against *warning* patterns → ``deny``.
    - One warning-pattern match → ``allow_with_warning``.
    - No matches → ``allow``.
    """
    high_reasons: list[str] = []
    high_matches: list[re.Match[str]] = []
    warn_reasons: list[str] = []
    warn_matches: list[re.Match[str]] = []

    for pattern, label in _HIGH_SEVERITY_PATTERNS:
        match = pattern.search(text)
        if match:
            high_reasons.append(label)
            high_matches.append(match)

    for pattern, label in _WARNING_PATTERNS:
        match = pattern.search(text)
        if match:
            warn_reasons.append(label)
            warn_matches.append(match)

    all_reasons = high_reasons + warn_reasons
    all_matches = high_matches + warn_matches
    sanitized = _sanitize(text, all_matches)

    if high_reasons:
        decision = "deny"
    elif len(warn_reasons) >= 2:
        decision = "deny"
    elif warn_reasons:
        decision = "allow_with_warning"
    else:
        decision = "allow"

    return PromptSafetyResult(decision=decision, reasons=all_reasons, sanitized_text=sanitized)
