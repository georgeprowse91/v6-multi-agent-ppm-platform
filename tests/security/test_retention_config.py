from pathlib import Path


def test_storage_lifecycle_rules_present() -> None:
    terraform = Path("infra/terraform/main.tf").read_text()
    for prefix in ["public", "internal", "confidential", "restricted"]:
        assert f'prefix_match = ["{prefix}/"]' in terraform
