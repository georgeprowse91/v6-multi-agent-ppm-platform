"""Prompt injection detection and sanitisation helpers."""

from __future__ import annotations

import re
from typing import Final

INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bignore\b.{0,40}\b(previous|earlier|all)\b.{0,40}\binstruction", re.IGNORECASE),
    re.compile(r"\boverride\b.{0,40}\b(system|developer)\b.{0,40}\binstruction", re.IGNORECASE),
    re.compile(r"\breveal\b.{0,40}\b(secret|key|token|password|credential)", re.IGNORECASE),
    re.compile(r"\b(disclose|print|show|dump)\b.{0,40}\b(system prompt|hidden prompt|chain of thought)\b", re.IGNORECASE),
    re.compile(r"\b(do not follow|don't follow)\b.{0,40}\b(safety|policy|rules)\b", re.IGNORECASE),
    re.compile(r"\bpretend\b.{0,20}\bto\b.{0,40}\b(system|developer|admin)\b", re.IGNORECASE),
    re.compile(r"\b(base64|rot13|hex)\b.{0,40}\bdecode\b.{0,40}\b(secret|prompt|instruction)", re.IGNORECASE),
)

ATTACK_PHRASES: Final[tuple[str, ...]] = (
    "ignore previous instructions",
    "ignore all instructions",
    "reveal secrets",
    "reveal the system prompt",
    "show hidden prompt",
    "disclose chain of thought",
    "do not follow safety rules",
)


def detect_injection(prompt: str) -> bool:
    """Return ``True`` when the prompt appears to contain prompt injection patterns."""

    text = prompt.strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def sanitize_prompt(prompt: str) -> str:
    """Neutralise common prompt-injection phrases while preserving most user intent."""

    sanitized = prompt
    for phrase in ATTACK_PHRASES:
        sanitized = re.sub(re.escape(phrase), "[REMOVED_INJECTION_PHRASE]", sanitized, flags=re.IGNORECASE)

    sanitized = sanitized.replace("```", "`\u200b``")
    sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")
    return sanitized
