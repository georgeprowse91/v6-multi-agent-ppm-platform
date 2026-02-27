from __future__ import annotations

import re
from pathlib import Path


def _load_patterns(path: Path) -> list[re.Pattern[str]]:
    content = path.read_text()
    matches = re.findall(r"regex\": \"([^\"]+)\"", content)
    normalized = [pattern.replace("\\\\", "\\") for pattern in matches]
    return [re.compile(pattern) for pattern in normalized]


def _denied(payload: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(pattern.search(payload) for pattern in patterns)


def test_pii_policy_denies_payloads() -> None:
    patterns = _load_patterns(Path("ops/infra/policies/dlp/bundles/pii.rego"))
    assert _denied("Contact me at dev@example.com", patterns)
    assert _denied("SSN 123-45-6789 should be blocked", patterns)


def test_credentials_policy_denies_payloads() -> None:
    patterns = _load_patterns(Path("ops/infra/policies/dlp/bundles/credentials.rego"))
    assert _denied("AWS key AKIA1234567890ABCDEF", patterns)
    assert _denied("Bearer ghp_1234567890abcdef1234567890abcdef1234", patterns)
