# Scripts

Automation scripts for local development, CI, and operational workflows. Prefer running them
via Makefile targets so CI and local behavior stay aligned.

## Markdown link checks

Validate internal markdown links and anchors:

```bash
python scripts/check-links.py
```

Expected output when everything is valid:

```text
# (no output, exit code 0)
```

If a link is broken, the script prints the file, destination, and reason.

## Forbidden phrase scan

Scan the repo for forbidden filler phrases:

```bash
python scripts/check-placeholders.py
```

Expected output when everything is clean:

```text
Forbidden phrase scan passed with no matches.
```

## Workflow validation

Validate GitHub workflow files for common issues:

```bash
python scripts/validate-github-workflows.py
```

Expected output:

```text
Validated <N> GitHub workflow file(s) successfully.
```
