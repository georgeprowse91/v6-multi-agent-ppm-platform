# Design System

Shared design assets and Storybook-ready component references for `@ppm/ui-kit`.

## What lives here

| Folder | Description |
|--------|-------------|
| [icons/](./icons/) | Icon system and icon map |
| [tokens/](./tokens/) | Re-exported design tokens consumed from `@ppm/design-tokens` |
| [stories/](./stories/) | Storybook stories covering component variants, states, and a11y notes |

## Story requirements

Each component story must include:

1. Primary and secondary variants.
2. State coverage (`disabled`, `loading`, error/success as applicable).
3. Accessibility contract notes in Storybook docs descriptions.
