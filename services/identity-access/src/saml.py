from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from security.secrets import resolve_secret

try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.settings import OneLogin_Saml2_Settings
except ImportError:  # pragma: no cover - optional dependency
    OneLogin_Saml2_Auth = None
    OneLogin_Saml2_Settings = None


class SamlUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class SamlConfig:
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str
    sp_sls_url: str
    strict: bool


def load_saml_config() -> SamlConfig:
    idp_entity_id = resolve_secret(os.getenv("SAML_IDP_ENTITY_ID"))
    idp_sso_url = resolve_secret(os.getenv("SAML_IDP_SSO_URL"))
    idp_x509_cert = resolve_secret(os.getenv("SAML_IDP_X509_CERT"))
    sp_entity_id = resolve_secret(os.getenv("SAML_SP_ENTITY_ID"))
    sp_acs_url = resolve_secret(os.getenv("SAML_SP_ACS_URL"))
    sp_sls_url = resolve_secret(os.getenv("SAML_SP_SLS_URL")) or sp_acs_url
    strict = os.getenv("SAML_STRICT", "true").lower() in {"1", "true", "yes"}
    if not (idp_entity_id and idp_sso_url and idp_x509_cert and sp_entity_id and sp_acs_url):
        raise SamlUnavailableError("SAML configuration missing")
    return SamlConfig(
        idp_entity_id=idp_entity_id,
        idp_sso_url=idp_sso_url,
        idp_x509_cert=idp_x509_cert,
        sp_entity_id=sp_entity_id,
        sp_acs_url=sp_acs_url,
        sp_sls_url=sp_sls_url,
        strict=strict,
    )


def _settings_dict(config: SamlConfig) -> dict[str, Any]:
    return {
        "strict": config.strict,
        "sp": {
            "entityId": config.sp_entity_id,
            "assertionConsumerService": {"url": config.sp_acs_url, "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"},
            "singleLogoutService": {"url": config.sp_sls_url, "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"},
        },
        "idp": {
            "entityId": config.idp_entity_id,
            "singleSignOnService": {"url": config.idp_sso_url, "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"},
            "x509cert": config.idp_x509_cert,
        },
    }


def build_saml_settings(config: SamlConfig) -> OneLogin_Saml2_Settings:
    if not OneLogin_Saml2_Settings:
        raise SamlUnavailableError("python3-saml is not installed")
    return OneLogin_Saml2_Settings(settings=_settings_dict(config), custom_base_path=None)


def build_auth(
    request_data: dict[str, Any], *, old_settings: OneLogin_Saml2_Settings | None = None
) -> OneLogin_Saml2_Auth:
    if not OneLogin_Saml2_Auth:
        raise SamlUnavailableError("python3-saml is not installed")
    return OneLogin_Saml2_Auth(request_data, old_settings=old_settings)


def prepare_fastapi_request(request) -> dict[str, Any]:
    url = request.url
    return {
        "https": "on" if url.scheme == "https" else "off",
        "http_host": url.hostname,
        "server_port": url.port or (443 if url.scheme == "https" else 80),
        "script_name": request.scope.get("root_path", ""),
        "get_data": dict(request.query_params),
        "post_data": {},
    }
