from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent / "examples"


def list_prompts() -> list[Path]:
    return sorted(PROMPT_DIR.glob("*.prompt.yaml"))
