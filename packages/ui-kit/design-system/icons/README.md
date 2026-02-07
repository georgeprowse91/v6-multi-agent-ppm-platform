# Icon system

This directory holds the canonical icon map for the platform. Use the map with the shared `<Icon />` abstraction so every icon is semantic, accessible, and token-aware.

## How to use the Icon component

```tsx
import { Icon } from '@/components/icon/Icon';

<Icon semantic="actions.settings" label="Settings" />
<Icon semantic="status.success" decorative />
```

Guidelines:
- Use `label` for icon-only controls or when there is no adjacent text.
- Use `decorative` when the icon is next to visible text that already conveys meaning.
- Use `size` only when you need to override the mapped size (e.g., empty states):

```tsx
<Icon semantic="communication.message" decorative size="3xl" />
```

## How to add a new semantic icon

1. Add a new semantic entry to `design-system/icons/icon-map.json` under the most appropriate category.
2. Ensure the icon name matches a `lucide-react` export.
3. Update the shared icon registry in `apps/web/frontend/src/components/icon/Icon.tsx` to include the new icon.
4. Use the new semantic string (e.g., `domain.project`) in UI code instead of importing `lucide-react` directly.

## Accessibility rules

- Icons must never be the only indicator of meaning; pair with text or a tooltip.
- For icon-only buttons, always pass a `label` and keep the button’s `aria-label` aligned.
- Decorative icons must set `decorative` so they are hidden from assistive technologies.
- Only loader icons may animate (`ai.thinking`).
