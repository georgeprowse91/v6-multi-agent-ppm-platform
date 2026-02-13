import type { Meta, StoryObj } from '@storybook/react';
import { tokens } from '@ppm/design-tokens';

type Swatch = { name: string; value: string };

const TokenPalette = ({ swatches }: { swatches: Swatch[] }) => (
  <div style={{ display: 'grid', gap: 12, gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
    {swatches.map((swatch) => (
      <div key={swatch.name} style={{ border: '1px solid var(--color-border-default)', borderRadius: 6, padding: 8 }}>
        <div style={{ background: swatch.value, height: 56, borderRadius: 4, marginBottom: 8 }} />
        <strong>{swatch.name}</strong>
        <div style={{ fontSize: 12 }}>{swatch.value}</div>
      </div>
    ))}
  </div>
);

const meta: Meta<typeof TokenPalette> = {
  title: 'Design System/Tokens/Palette',
  component: TokenPalette,
  parameters: {
    docs: {
      description: {
        component:
          'Brand/semantic color tokens. Accessibility: maintain minimum contrast ratio of 4.5:1 for body text and prefer semantic state colors for status communication.',
      },
    },
  },
};

export default meta;
type Story = StoryObj<typeof TokenPalette>;

export const CoreColors: Story = {
  args: {
    swatches: [
      { name: 'brand.orange500', value: tokens.color.brand.orange500 },
      { name: 'brand.orange300', value: tokens.color.brand.orange300 },
      { name: 'text.primary', value: tokens.color.text.primary },
      { name: 'state.success.fg', value: tokens.color.state.success.fg },
      { name: 'state.warning.fg', value: tokens.color.state.warning.fg },
      { name: 'state.error.fg', value: tokens.color.state.error.fg },
    ],
  },
};
