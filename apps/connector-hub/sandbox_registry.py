from pathlib import Path

SANDBOX_CONFIG_DIR = Path(__file__).resolve().parent / "sandbox" / "examples"


def list_sandbox_configs() -> list[Path]:
    return sorted(SANDBOX_CONFIG_DIR.glob("*.yaml"))
