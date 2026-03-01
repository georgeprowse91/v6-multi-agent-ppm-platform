"""Fine-tune a BERT classifier for risk detection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_training_data(path: Path) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            data.append(json.loads(line))
    return data


def train_model(
    training_data_path: Path,
    output_dir: Path,
    *,
    model_name: str = "bert-base-uncased",
    num_labels: int = 2,
    epochs: int = 3,
    batch_size: int = 8,
) -> None:
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )

    training_data = load_training_data(training_data_path)
    dataset = Dataset.from_list(training_data)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(batch: dict[str, Any]) -> dict[str, Any]:
        return tokenizer(batch["text"], padding="max_length", truncation=True)

    tokenized = dataset.map(tokenize, batched=True)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)
    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=batch_size,
        num_train_epochs=epochs,
        logging_steps=10,
        save_strategy="epoch",
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
    )
    trainer.train()
    trainer.save_model(str(output_dir))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune a risk classifier.")
    parser.add_argument("--training-data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-name", default="bert-base-uncased")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    train_model(
        args.training_data,
        args.output_dir,
        model_name=args.model_name,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
