"""
Utility classes for the Approval Workflow Agent.

Contains storage adapters, role lookup, delegation management,
notification template rendering, and subscription management.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from string import Template
from typing import Any

import yaml
from data_sync_status import StatusStore

from agents.runtime.src.state_store import TenantStateStore


class ApprovalStore:
    def __init__(self, path: Path) -> None:
        self.store = StatusStore(path)

    def _key(self, tenant_id: str, approval_id: str) -> str:
        return f"{tenant_id}:{approval_id}"

    def create(self, tenant_id: str, approval_id: str, details: dict[str, Any]) -> None:
        key = self._key(tenant_id, approval_id)
        self.store.create(key, tenant_id, "pending")
        self.store.update(key, "pending", details)

    def update(
        self, tenant_id: str, approval_id: str, status: str, details: dict[str, Any]
    ) -> None:
        key = self._key(tenant_id, approval_id)
        self.store.update(key, status, details)

    def get(self, tenant_id: str, approval_id: str) -> dict[str, Any] | None:
        key = self._key(tenant_id, approval_id)
        record = self.store.get(key)
        if not record:
            return None
        return {
            "approval_id": approval_id,
            "status": record.status,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
            "tenant_id": tenant_id,
            "details": record.details,
        }


class RoleLookupClient:
    def __init__(self, config: dict[str, Any] | None) -> None:
        self.config = config or {}
        self.role_directory = self.config.get("role_directory", {})

    async def get_users_for_roles(self, tenant_id: str, roles: list[str]) -> dict[str, list[str]]:
        resolved: dict[str, list[str]] = {}
        for role in roles:
            users = self.role_directory.get(role, [])
            resolved[role] = list(users)
        return resolved


class DelegationClient:
    def __init__(self, config: dict[str, Any] | None) -> None:
        self.config = config or {}
        self.default_duration_days = int(self.config.get("default_duration_days", 14))
        self.rules = self._normalize_rules(self.config.get("rules", {}))

    def _normalize_rules(self, rules: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        normalized: dict[str, list[dict[str, Any]]] = {}
        for user_id, entries in rules.items():
            prepared: list[dict[str, Any]] = []
            candidates = entries if isinstance(entries, list) else [entries]
            for candidate in candidates:
                if isinstance(candidate, str):
                    start = datetime.now(timezone.utc)
                    end = start + timedelta(days=self.default_duration_days)
                    prepared.append(
                        {
                            "delegate": candidate,
                            "start": start,
                            "end": end,
                        }
                    )
                    continue
                if not isinstance(candidate, dict):
                    continue
                delegate = str(candidate.get("delegate") or "").strip()
                if not delegate:
                    continue
                start = self._parse_datetime(candidate.get("start")) or datetime.min.replace(
                    tzinfo=timezone.utc
                )
                end = self._parse_datetime(candidate.get("end"))
                if end is None:
                    end = start + timedelta(days=self.default_duration_days)
                prepared.append(
                    {
                        "delegate": delegate,
                        "start": start,
                        "end": end,
                    }
                )
            if prepared:
                normalized[user_id] = prepared
        return normalized

    def _parse_datetime(self, raw: Any) -> datetime | None:
        if not raw:
            return None
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
        if isinstance(raw, str):
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def get_delegate(self, user_id: str, date: datetime) -> str | None:
        candidate_date = date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        for rule in self.rules.get(user_id, []):
            if rule["start"] <= candidate_date <= rule["end"]:
                return rule["delegate"]
        return None

    def get_active_rule(self, user_id: str, date: datetime) -> dict[str, Any] | None:
        candidate_date = date if date.tzinfo else date.replace(tzinfo=timezone.utc)
        for rule in self.rules.get(user_id, []):
            if rule["start"] <= candidate_date <= rule["end"]:
                return rule
        return None


class NotificationTemplateEngine:
    def __init__(
        self,
        templates: dict[str, dict[str, str]] | None = None,
        default_locale: str = "en",
        template_root: Path | None = None,
    ) -> None:
        self.default_locale = default_locale
        self.template_root = template_root
        self.templates = templates or self._load_templates_from_filesystem()

    def _load_templates_from_filesystem(self) -> dict[str, dict[str, str]]:
        if not self.template_root or not self.template_root.exists():
            return {}

        templates: dict[str, dict[str, str]] = {}
        for locale_dir in self.template_root.iterdir():
            if not locale_dir.is_dir():
                continue
            template_file = locale_dir / "approval_notification.md"
            if not template_file.exists():
                continue
            parsed = self._parse_markdown_template(template_file)
            if parsed:
                templates[locale_dir.name] = parsed
        return templates

    def _parse_markdown_template(self, template_file: Path) -> dict[str, str]:
        content = template_file.read_text(encoding="utf-8").strip()
        if not content.startswith("---"):
            return {}
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        loaded = yaml.safe_load(parts[1])
        if not isinstance(loaded, dict):
            return {}
        return {str(key): str(value) for key, value in loaded.items()}

    def _resolve_locale_templates(self, locale: str) -> dict[str, str]:
        return self.templates.get(locale) or self.templates.get(self.default_locale, {})

    def render(self, template_key: str, locale: str, context: dict[str, Any]) -> str:
        raw_template = self._resolve_locale_templates(locale).get(template_key) or ""
        return Template(raw_template).safe_substitute(context)

    def render_accessible(
        self,
        *,
        template_key: str,
        locale: str,
        context: dict[str, Any],
        accessible_format: str,
    ) -> tuple[str, str | None]:
        rendered = self.render(template_key, locale, context)
        if accessible_format == "html_with_alt_text":
            return rendered, self._to_accessible_html(rendered)
        return rendered, None

    def _to_accessible_html(self, rendered: str) -> str:
        escaped = rendered.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        paragraph = escaped.replace("\n", "<br>")
        return (
            '<html><body style="background-color:#ffffff;color:#111111;font-size:18px;'
            'line-height:1.6;font-family:Arial,sans-serif;">'
            f"<p>{paragraph}</p>"
            "</body></html>"
        )


class NotificationSubscriptionStore:
    def __init__(self, path: Path | None = None) -> None:
        if path is not None:
            self.store: TenantStateStore | None = TenantStateStore(path)
        else:
            # No explicit path configured: use ephemeral in-memory storage so
            # tests (and processes without a configured path) start with a clean
            # state and don't pollute shared files.
            self.store = None
        self._memory: dict[str, dict[str, dict[str, Any]]] = {}

    def get_preferences(self, tenant_id: str, recipient_id: str) -> dict[str, Any] | None:
        if self.store is not None:
            return self.store.get(tenant_id, recipient_id)
        return self._memory.get(tenant_id, {}).get(recipient_id)

    def upsert_preferences(
        self, tenant_id: str, recipient_id: str, preferences: dict[str, Any]
    ) -> None:
        normalized = dict(preferences)
        normalized.setdefault("locale", "en")
        accessible = normalized.get("accessible_format", "text_only")
        if accessible not in {"text_only", "html_with_alt_text"}:
            accessible = "text_only"
        normalized["accessible_format"] = accessible
        notify_delegate_directly = normalized.get("notify_delegate_directly", True)
        normalized["notify_delegate_directly"] = bool(notify_delegate_directly)
        if self.store is not None:
            self.store.upsert(tenant_id, recipient_id, normalized)
        else:
            self._memory.setdefault(tenant_id, {})[recipient_id] = normalized

    def delete_preferences(self, tenant_id: str, recipient_id: str) -> None:
        if self.store is not None:
            self.store.delete(tenant_id, recipient_id)
        else:
            self._memory.get(tenant_id, {}).pop(recipient_id, None)


def default_notification_templates() -> dict[str, dict[str, str]]:
    """Return built-in notification templates for supported locales."""
    return {
        "en": {
            "approval_request_subject": "Approval required: ${description}",
            "approval_request_body": (
                "Hello ${approver},\n\n"
                "An approval decision is required for request ${request_id}.\n"
                "Description: ${description}\n"
                "Urgency: ${urgency}\n"
                "Deadline: ${deadline}\n\n"
                "${delegation_note}\n\n"
                "Please review and submit your decision."
            ),
            "approval_escalation_subject": "Escalation notice: ${description}",
            "approval_escalation_body": (
                "Hello ${approver},\n\n"
                "Approval request ${request_id} is being escalated.\n"
                "Due to ${risk_score} risk and ${criticality_level} criticality, escalation "
                "will occur after ${escalation_timeout_hours} hours.\n"
                "Deadline: ${deadline}."
            ),
            "approval_escalation_chat": (
                "Escalation for request ${request_id}: ${risk_score} risk / "
                "${criticality_level} criticality. Escalates after "
                "${escalation_timeout_hours} hours."
            ),
            "approval_escalation_push": (
                "Escalation: ${request_id} (${risk_score} risk, ${criticality_level} criticality)"
            ),
            "approval_request_chat": (
                "Approval required for request ${request_id}: ${description} "
                "(deadline ${deadline})."
            ),
            "approval_request_push": "Approval required: ${description} (deadline ${deadline})",
            "approval_digest_subject": "You have ${count} pending approvals",
            "approval_digest_body": (
                "Here is your approval digest:\n" "${items}\n" "Generated at ${generated_at}."
            ),
            "approval_decision_subject": "Approval ${decision} for ${request_id}",
            "approval_decision_body": (
                "Approval ${decision} for request ${request_id} by ${approver}.\n"
                "Comments: ${comments}"
            ),
        },
        "es": {
            "approval_request_subject": "Aprobación requerida: ${description}",
            "approval_request_body": (
                "Hola ${approver},\n\n"
                "Se requiere una decisión de aprobación para la solicitud ${request_id}.\n"
                "Descripción: ${description}\n"
                "Urgencia: ${urgency}\n"
                "Fecha límite: ${deadline}\n\n"
                "${delegation_note}\n\n"
                "Revisa y envía tu decisión."
            ),
            "approval_escalation_subject": "Aviso de escalamiento: ${description}",
            "approval_escalation_body": (
                "Hola ${approver},\n\n"
                "La solicitud ${request_id} se está escalando.\n"
                "Debido al riesgo ${risk_score} y criticidad ${criticality_level}, "
                "el escalamiento ocurre después de ${escalation_timeout_hours} horas.\n"
                "Fecha límite: ${deadline}."
            ),
            "approval_escalation_chat": (
                "Escalamiento para la solicitud ${request_id}: riesgo ${risk_score} / "
                "criticidad ${criticality_level}. Escala después de "
                "${escalation_timeout_hours} horas."
            ),
            "approval_escalation_push": (
                "Escalamiento: ${request_id} (${risk_score} riesgo, ${criticality_level} criticidad)"
            ),
            "approval_request_chat": (
                "Aprobación requerida para la solicitud ${request_id}: ${description} "
                "(fecha límite ${deadline})."
            ),
            "approval_request_push": "Aprobación requerida: ${description} (fecha límite ${deadline})",
            "approval_digest_subject": "Tienes ${count} aprobaciones pendientes",
            "approval_digest_body": (
                "Resumen de aprobaciones:\n" "${items}\n" "Generado a las ${generated_at}."
            ),
            "approval_decision_subject": "Aprobación ${decision} para ${request_id}",
            "approval_decision_body": (
                "Aprobación ${decision} para la solicitud ${request_id} por ${approver}.\n"
                "Comentarios: ${comments}"
            ),
        },
    }


def load_approval_policies(
    config: dict[str, Any] | None,
    logger: logging.Logger,
) -> dict[str, Any]:
    """Load approval policies and routing rules from configuration."""
    default_policies = {
        "budget_thresholds": [10000, 50000, 100000],
        "escalation_timeout_hours": 48,
        "risk_thresholds": {"high": 12, "medium": 24, "low": 48},
        "criticality_levels": {"critical": 6, "high": 12, "normal": 24, "low": 48},
        "reminder_before_deadline_hours": 24,
        "default_chain_type": "sequential",
        "digest_interval_minutes": 60,
        "response_time_threshold_hours": 48,
    }
    config_path = Path(
        config.get("approval_policies_path", "ops/config/agents/approval_policies.yaml")
        if config
        else "ops/config/agents/approval_policies.yaml"
    )
    fallback_path = Path("ops/config/approval_policies.json")
    if not config_path.exists():
        if not fallback_path.exists():
            logger.warning("Approval policies file not found at %s; using defaults.", config_path)
            return default_policies
        config_path = fallback_path
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            if config_path.suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(handle)
            else:
                data = json.load(handle)
        if not isinstance(data, dict):
            logger.warning(
                "Approval policies file %s did not contain an object; using defaults.",
                config_path,
            )
            return default_policies
        return {**default_policies, **data}
    except (json.JSONDecodeError, yaml.YAMLError, OSError) as exc:
        logger.warning(
            "Failed to load approval policies from %s: %s; using defaults.",
            config_path,
            exc,
        )
        return default_policies
