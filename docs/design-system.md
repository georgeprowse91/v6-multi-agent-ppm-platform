# Design System Tokens

## Source of truth
The canonical token file lives at:
- `packages/ui-kit/design-system/tokens/design-system-tokens.json`

Runtime outputs:
- `packages/ui-kit/design-system/tokens/tokens.css` (CSS variables)
- `packages/ui-kit/design-system/tokens/tokens.ts` (typed module)
- `apps/web/frontend/src/styles/tokens.css` (web runtime copy for Vite)

> The web frontend imports `apps/web/frontend/src/styles/tokens.css` via `styles/index.css`.

## How to use tokens
### CSS
Use semantic CSS variables in component styles:
- `var(--color-text-primary)`
- `var(--color-surface-card)`
- `var(--color-border-default)`
- `var(--color-button-primary-bg)` and `var(--color-button-primary-text)` for primary buttons

### TypeScript
Import token values when needed:
```ts
import { tokens } from '../../packages/ui-kit/design-system/tokens/tokens';
```

## Dark mode
Dark mode overrides are in the CSS variables under `[data-theme='dark']`. Theme mode is set by the web `ThemeProvider` using system preference with localStorage override (`ppm-theme-mode`).

## High-contrast mode
High-contrast overrides live under `[data-theme='high-contrast']` and should only adjust semantic tokens (text, surface, border, focus) while keeping component styles intact. The web app stores the setting in `ppm-theme-mode` and exposes it in user settings.

Recommended semantic token overrides:
- `--color-text-primary`: high-contrast foreground
- `--color-text-secondary`: subdued but readable foreground
- `--color-surface-page` / `--color-surface-card`: high-contrast backgrounds
- `--color-border-default`: visible outlines
- `--color-button-primary-bg` / `--color-button-primary-text`: emphasize primary actions
- `--focus-ring-color`: clearly visible focus states

## Token Adoption Checklist
- [ ] Use semantic tokens (text/surface/border/state) instead of raw hex values.
- [ ] Use `--color-button-primary-bg` + `--color-button-primary-text` for primary buttons.
- [ ] Avoid Orange500 as a button background with text.
- [ ] Ensure focus rings use `--focus-ring-color`.
- [ ] For AI surfaces, show a generated badge, timestamps, and a no-sources indicator when sources are absent.
- [ ] For AI apply actions, implement preview → apply and confirm high-risk actions.
- [ ] Update both CSS and TS usage if new tokens are added.

## Guardrails
Run the token lint check in the web frontend before merging UI changes:
```bash
cd apps/web/frontend
pnpm run lint:tokens
```
