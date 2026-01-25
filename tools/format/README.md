# Formatting

Formatting is driven by Black and Ruff, using settings in `pyproject.toml`.
The wrapper script in this folder ensures consistent repo-wide formatting.

## Usage

```bash
python -m tools.format.run
```

To format only specific paths:

```bash
python -m tools.format.run --paths agents apps packages
```

The default paths are stored in `tools/format/format_config.yaml`.
