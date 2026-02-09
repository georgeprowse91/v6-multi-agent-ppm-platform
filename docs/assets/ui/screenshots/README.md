# UI Screenshot Assets

This folder centralizes UI screenshots used in documentation and product artifacts. Store all UI captures here so docs and release notes can link to a single, curated source of truth.

## Naming conventions

Use descriptive, kebab-case filenames with the app surface, feature, and context:

```
<app>-<surface>-<feature>-<context>-<YYYYMMDD>.png
```

Examples:

- `web-workspace-portfolio-overview-default-20250115.png`
- `admin-console-settings-roles-edit-20250115.png`

## Expected resolution

- Preferred: **1920×1080** (16:9) for full-page views.
- Acceptable: **1440×900** for laptop-sized captures.
- Avoid scaling in post-processing; capture at the native resolution of the viewport.

## Capture guidelines

- Capture screenshots from the running UI in `apps/web` or `apps/admin-console`.
- Use seed/demo data that does not contain customer or personal information.
- Ensure UI chrome is consistent (no dev tools panels, no debug banners, no local-only feature flags).
- Capture in light mode unless explicitly documenting a dark theme variant.
- If multiple states are required, include a short suffix (e.g., `-empty`, `-filled`, `-hover`).

## File organization

- Store raw and final assets directly in this folder.
- If you need subfolders, group by app (e.g., `web/`, `admin-console/`).

## Binary diff note

PNG screenshots are binary assets, so some PR viewers (especially on mobile) cannot render a text diff and may display a "binary files not supported" message. If you hit that limitation, create the PR from the main GitHub web UI (desktop) or from the CLI; the assets will still be included in the change set even if the diff view fails to render.

## Recent captures

- `web-login-default-20260208.png`
- `web-intake-new-project-form-default-20260208.png`
- `web-project-workspace-three-panel-default-20260208.png`
