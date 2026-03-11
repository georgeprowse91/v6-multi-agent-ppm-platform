from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from security.config import resolve_config

logger = logging.getLogger("security-dlp")

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "security" / "dlp-policies.yaml"

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
TFN_RE = re.compile(r"\b\d{3}\s?\d{3}\s?\d{3}\b")
CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
API_KEY_RE = re.compile(
    r"\b(?:api[_-]?key|apikey)\b[^A-Za-z0-9]{0,3}([A-Za-z0-9_\-]{16,})",
    re.IGNORECASE,
)
STRIPE_KEY_RE = re.compile(r"\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b")
BEARER_RE = re.compile(r"\bBearer\s+([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE)


@dataclass(frozen=True)
class DLPFinding:
    type: str
    severity: str
    field: str
    excerpt: str | None = None


@dataclass(frozen=True)
class DLPResult:
    decision: str
    findings: list[DLPFinding]
    redacted_payload: Any | None = None

    @property
    def advisories(self) -> list[str]:
        return [summarize_finding(finding) for finding in self.findings]


@dataclass(frozen=True)
class DLPPolicy:
    classifications: dict[str, dict[str, str]]
    finding_enforcement: dict[str, str]


def _load_policy(path: Path | None = None) -> DLPPolicy:
    policy_path = path or DEFAULT_POLICY_PATH
    if not policy_path.exists():
        raise FileNotFoundError(f"DLP policy file not found: {policy_path}")
    data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    data = resolve_config(data)
    return DLPPolicy(
        classifications=data.get("classifications", {}),
        finding_enforcement=data.get("finding_enforcement", {}),
    )


def _mask_email(value: str) -> str:
    if "@" not in value:
        return "[REDACTED:email]"
    user, domain = value.split("@", 1)
    return f"{user[:1]}***@{domain}"


def _mask_last4(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) <= 4:
        return "[REDACTED]"
    return f"***{digits[-4:]}"


def _luhn_valid(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def summarize_finding(finding: DLPFinding) -> str:
    return f"DLP {finding.type} detected in {finding.field}"


def _collect_text_findings(text: str, field: str) -> list[DLPFinding]:
    findings: list[DLPFinding] = []

    for match in EMAIL_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="email",
                severity="low",
                field=field,
                excerpt=_mask_email(match.group(0)),
            )
        )

    for match in PHONE_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="phone",
                severity="low",
                field=field,
                excerpt=_mask_last4(match.group(0)),
            )
        )

    for match in TFN_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="tfn",
                severity="high",
                field=field,
                excerpt=_mask_last4(match.group(0)),
            )
        )

    for match in CREDIT_CARD_RE.finditer(text):
        candidate = match.group(0)
        digits = re.sub(r"\D", "", candidate)
        if _luhn_valid(digits):
            findings.append(
                DLPFinding(
                    type="credit_card",
                    severity="high",
                    field=field,
                    excerpt=_mask_last4(candidate),
                )
            )

    for match in AWS_KEY_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="api_key",
                severity="high",
                field=field,
                excerpt=_mask_last4(match.group(0)),
            )
        )

    for match in API_KEY_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="api_key",
                severity="high",
                field=field,
                excerpt=_mask_last4(match.group(1)),
            )
        )

    for match in STRIPE_KEY_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="api_key",
                severity="high",
                field=field,
                excerpt=_mask_last4(match.group(0)),
            )
        )

    for match in BEARER_RE.finditer(text):
        findings.append(
            DLPFinding(
                type="bearer_token",
                severity="high",
                field=field,
                excerpt=_mask_last4(match.group(1)),
            )
        )

    return findings


def _redact_text(text: str) -> str:
    redacted = EMAIL_RE.sub("[REDACTED:email]", text)
    redacted = TFN_RE.sub("[REDACTED:tfn]", redacted)

    def _redact_cc(match: re.Match[str]) -> str:
        value = match.group(0)
        digits = re.sub(r"\D", "", value)
        if not _luhn_valid(digits):
            return value
        return f"[REDACTED:credit_card:{digits[-4:]}]"

    redacted = CREDIT_CARD_RE.sub(_redact_cc, redacted)
    redacted = PHONE_RE.sub("[REDACTED:phone]", redacted)
    redacted = AWS_KEY_RE.sub("[REDACTED:api_key]", redacted)
    redacted = API_KEY_RE.sub("[REDACTED:api_key]", redacted)
    redacted = STRIPE_KEY_RE.sub("[REDACTED:api_key]", redacted)
    redacted = BEARER_RE.sub("[REDACTED:bearer_token]", redacted)
    return redacted


def redact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: redact_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(redact_payload(item) for item in payload)
    if isinstance(payload, str):
        return _redact_text(payload)
    return payload


def _scan_payload(payload: Any, field_prefix: str) -> list[DLPFinding]:
    findings: list[DLPFinding] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            next_field = f"{field_prefix}.{key}" if field_prefix else str(key)
            findings.extend(_scan_payload(value, next_field))
        return findings
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            findings.extend(_scan_payload(value, f"{field_prefix}[{index}]"))
        return findings
    if isinstance(payload, tuple):
        for index, value in enumerate(payload):
            findings.extend(_scan_payload(value, f"{field_prefix}[{index}]"))
        return findings
    if isinstance(payload, str):
        return _collect_text_findings(payload, field_prefix)
    if payload is None:
        return findings
    return _collect_text_findings(str(payload), field_prefix)


def _severity_rank(level: str | None) -> int:
    if not level:
        return 0
    return SEVERITY_RANK.get(level.lower(), 0)


def _decision_for_findings(
    findings: list[DLPFinding], classification: str, policy: DLPPolicy
) -> str:
    classification_key = classification or "internal"
    thresholds = policy.classifications.get(classification_key) or policy.classifications.get(
        "default", {}
    )
    advisory_at = _severity_rank(thresholds.get("advisory_at_or_above"))
    deny_at = _severity_rank(thresholds.get("deny_at_or_above"))

    decision = "allow"
    for finding in findings:
        enforcement = policy.finding_enforcement.get(finding.type, "block")
        severity_rank = _severity_rank(finding.severity)
        if enforcement == "block":
            return "deny"
        if deny_at and severity_rank >= deny_at:
            return "deny"
        if enforcement == "advisory":
            decision = "allow_with_advisory"
        if advisory_at and severity_rank >= advisory_at:
            decision = "allow_with_advisory"
    return decision


def scan_payload(
    payload: Any,
    *,
    classification: str,
    policy_path: Path | None = None,
) -> DLPResult:
    policy = _load_policy(policy_path)
    findings = _scan_payload(payload, field_prefix="")
    decision = _decision_for_findings(findings, classification, policy)
    redacted_payload = redact_payload(payload)
    logger.info(
        "dlp_scan_completed",
        extra={
            "decision": decision,
            "classification": classification,
            "findings": len(findings),
        },
    )
    return DLPResult(decision=decision, findings=findings, redacted_payload=redacted_payload)


def ensure_dlp_environment() -> None:
    if not DEFAULT_POLICY_PATH.exists():
        raise FileNotFoundError("DLP policy file missing")
    if (
        os.getenv("ENVIRONMENT", "development").lower() == "production"
        and not DEFAULT_POLICY_PATH.exists()
    ):
        raise RuntimeError("DLP policy configuration missing in production")
