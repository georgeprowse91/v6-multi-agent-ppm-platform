from pathlib import Path


def test_storage_lifecycle_rules_present() -> None:
    terraform = Path("infra/terraform/main.tf").read_text()
    for prefix in ["public", "internal", "confidential", "restricted"]:
        assert f'prefix_match = ["{prefix}/"]' in terraform


def test_audit_worm_immutability_configured() -> None:
    terraform = Path("infra/terraform/main.tf").read_text()
    assert "immutable_storage_enabled" in terraform
    assert "immutability_policy" in terraform
    assert 'name                  = "audit-events"' in terraform
    assert 'state                         = "Locked"' in terraform
