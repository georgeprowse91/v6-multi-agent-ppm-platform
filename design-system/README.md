# Design System

This folder is the source-of-truth for shared visual language and cross-product UI contracts.

## Token package and versioning

Design tokens are published as the npm package `@ppm/design-tokens` from `packages/design-tokens/`.

- Package version follows semver.
- `major`: breaking token renames/removals.
- `minor`: additive token groups and non-breaking values.
- `patch`: typo/docs fixes or metadata-only updates.

Consumers:

- `packages/ui-kit` imports tokens from `@ppm/design-tokens`.
- `apps/web/frontend` imports CSS variables via `@ppm/design-tokens/tokens.css`.

## Token naming conventions

Use path-like names with predictable scopes:

- `color.<domain>.<role>` (example: `color.text.primary`, `color.state.error.fg`)
- `spacingPx.<scale>` (`xs`, `sm`, `md`, `lg`, `xl`, `2xl`)
- `typography.fontSizePx.<role>` (`h1`, `body`, `micro`)
- `componentDefaults.<component>.<property>` for stable component defaults

Rules:

1. Prefer semantic names (`text.primary`) over raw hue names.
2. Keep units in the namespace (`Px`, `Ms`) when values are numeric.
3. Avoid reusing deprecated aliases for new features.

## Theming strategy

Theme selection is done through the `data-theme` attribute with supported themes:

- `light` (default)
- `dark`
- `high-contrast`

Theme overrides should only change semantic CSS custom properties (for example `--color-surface-page`), not consumer component code.

## Component API contracts

Component API contracts define guaranteed props and states shared across products.

### Button (baseline)

- Required: `variant` (`primary|secondary|danger`), `disabled`, `loading`.
- Accessibility: focus ring required, accessible label required, loading sets `aria-busy=true`.
- Visual hierarchy: only one primary action per view section.

### Input (baseline)

- Required states: `default`, `disabled`, `error`.
- Accessibility: label association and error text announced through `aria-describedby`.

### Card (baseline)

- Required slots: header/content/footer with tokenized spacing.
- Accessibility: cards containing interactive controls must preserve tab order.

## Storybook coverage

Storybook is configured in `apps/web/frontend/.storybook` and includes stories from:

- `design-system/**/*.stories.*`
- `packages/ui-kit/design-system/**/*.stories.*`

Stories must include variants/states and accessibility notes in docs descriptions.
