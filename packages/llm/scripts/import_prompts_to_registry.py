from __future__ import annotations

import argparse
from pathlib import Path

from packages.llm.src.llm.prompts import PromptRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Import markdown prompts into prompt registry")
    parser.add_argument("--prompts-dir", default="prompts")
    parser.add_argument("--registry-path", default="data/prompts/registry.json")
    args = parser.parse_args()

    registry = PromptRegistry(registry_path=Path(args.registry_path))
    prompts_dir = Path(args.prompts_dir)

    for prompt_file in sorted(prompts_dir.glob("**/*.md")):
        name = f"{prompt_file.parent.name}/{prompt_file.stem}"
        content = prompt_file.read_text()
        registry.register_prompt(
            name=name,
            content=content,
            owner="migration",
            created_by="migration-script",
            status="migrated",
            environment_tags=["dev"],
            version_label="initial-import-v1",
        )
        print(f"imported {name}")


if __name__ == "__main__":
    main()
