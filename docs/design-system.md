# Design System Tokens

## Source of truth
The canonical token file lives at:
- `design-system/tokens/design-system-tokens.json`

Runtime outputs:
- `design-system/tokens/tokens.css` (CSS variables)
- `design-system/tokens/tokens.ts` (typed module)
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
import { tokens } from '../../design-system/tokens/tokens';
```

## Dark mode
Dark mode overrides are in the CSS variables under `[data-theme='dark']`. Theme mode is set by the web `ThemeProvider` using system preference with localStorage override (`ppm-theme-mode`).

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
