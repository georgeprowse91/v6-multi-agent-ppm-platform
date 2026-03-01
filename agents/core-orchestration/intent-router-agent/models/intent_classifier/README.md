# Intent Classifier Model Artifacts

This directory stores fine-tuned transformer artifacts for the Intent Router classifier.

## Expected files
- `config.json`
- `tokenizer.json` / tokenizer vocab files
- `model.safetensors` or `pytorch_model.bin`

By default, the router falls back to `distilbert-base-uncased` when local artifacts are not present.
