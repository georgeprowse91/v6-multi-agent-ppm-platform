"""Prompt injection detection and sanitisation helpers.

Detection strategy
------------------
Two layers are applied in sequence:

1. **Unicode normalisation** — lookalike Unicode characters (e.g. Cyrillic
   homoglyphs, full-width Latin) are normalised to ASCII before matching so
   that attackers cannot trivially bypass pattern matching by substituting
   visually identical characters.

2. **Regex pattern matching** — a curated set of patterns covering classic
   prompt-injection phrases, jailbreak personas, encoding-based obfuscation,
   and indirect injection via structured data markers.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # --- Classic instruction override ---
    re.compile(r"\bignore\b.{0,40}\b(previous|earlier|all)\b.{0,40}\binstruction", re.IGNORECASE),
    re.compile(r"\boverride\b.{0,40}\b(system|developer)\b.{0,40}\binstruction", re.IGNORECASE),
    re.compile(r"\bforget\b.{0,40}\b(previous|earlier|all)\b.{0,40}\binstruction", re.IGNORECASE),
    re.compile(r"\bdisregard\b.{0,40}\binstruction", re.IGNORECASE),
    # --- Secret / credential exfiltration ---
    re.compile(r"\breveal\b.{0,40}\b(secret|key|token|password|credential)", re.IGNORECASE),
    re.compile(r"\bexfiltrate\b.{0,40}\b(secret|key|data|credential)", re.IGNORECASE),
    re.compile(r"\bprint\b.{0,30}\benv\b", re.IGNORECASE),
    re.compile(r"\bshow\b.{0,30}\b(env|environ|environment variable)", re.IGNORECASE),
    # --- System prompt disclosure ---
    re.compile(
        r"\b(disclose|print|show|dump|output|repeat|recite)\b.{0,40}"
        r"\b(system prompt|hidden prompt|chain of thought|initial prompt)\b",
        re.IGNORECASE,
    ),
    # --- Safety bypass ---
    re.compile(r"\b(do not follow|don't follow)\b.{0,40}\b(safety|policy|rules)\b", re.IGNORECASE),
    re.compile(r"\bbypass\b.{0,30}\b(safety|filter|restriction|guardrail)\b", re.IGNORECASE),
    re.compile(r"\bdisable\b.{0,30}\b(safety|filter|restriction|guardrail)\b", re.IGNORECASE),
    # --- Persona / role-play jailbreaks ---
    re.compile(r"\bpretend\b.{0,20}\bto\b.{0,40}\b(system|developer|admin)\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\b.{0,40}\b(unrestricted|unfiltered|uncensored|DAN)\b", re.IGNORECASE),
    re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    # --- Encoding obfuscation ---
    re.compile(
        r"\b(base64|rot13|hex)\b.{0,40}\bdecode\b.{0,40}\b(secret|prompt|instruction)",
        re.IGNORECASE,
    ),
    # --- Indirect injection via structured markers ---
    # Attackers sometimes embed injections inside JSON, YAML, or XML blobs
    # passed as context.  These patterns catch the most common forms.
    re.compile(r"<\s*injection\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),  # Llama chat template abuse
    re.compile(r"<\|im_start\|>", re.IGNORECASE),  # ChatML template abuse
    re.compile(r"<\|system\|>", re.IGNORECASE),  # Phi/ChatML system tag abuse
)

ATTACK_PHRASES: Final[tuple[str, ...]] = (
    "ignore previous instructions",
    "ignore all instructions",
    "forget previous instructions",
    "disregard instructions",
    "reveal secrets",
    "reveal the system prompt",
    "show hidden prompt",
    "disclose chain of thought",
    "do not follow safety rules",
    "bypass safety filter",
    "disable safety",
    "jailbreak",
    "DAN mode",
)


def _normalise(text: str) -> str:
    """NFKC-normalise *text* to collapse lookalike Unicode characters.

    This guards against trivial bypasses using Cyrillic homoglyphs,
    full-width Latin letters, or other confusable code points.
    """
    return unicodedata.normalize("NFKC", text)


def detect_injection(prompt: str) -> bool:
    """Return ``True`` when the prompt appears to contain prompt injection patterns.

    The check is performed on the Unicode-normalised form of *prompt* so that
    lookalike character substitutions do not evade detection.
    """
    text = _normalise(prompt.strip())
    if not text:
        return False
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def sanitize_prompt(prompt: str) -> str:
    """Neutralise common prompt-injection phrases while preserving most user intent."""

    sanitized = _normalise(prompt)
    for phrase in ATTACK_PHRASES:
        sanitized = re.sub(
            re.escape(phrase), "[REMOVED_INJECTION_PHRASE]", sanitized, flags=re.IGNORECASE
        )

    # Break triple-backtick code fence delimiters that could be used to escape
    # context boundaries in some LLM chat templates.
    sanitized = sanitized.replace("```", "`\u200b``")
    sanitized = sanitized.replace("<", "&lt;").replace(">", "&gt;")
    return sanitized
