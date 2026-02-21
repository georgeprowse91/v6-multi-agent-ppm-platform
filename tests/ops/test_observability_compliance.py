from __future__ import annotations

from ops.tools.observability_compliance_checks import check_service_observability_compliance


def test_all_services_mount_observability_middleware() -> None:
    assert check_service_observability_compliance() == []
