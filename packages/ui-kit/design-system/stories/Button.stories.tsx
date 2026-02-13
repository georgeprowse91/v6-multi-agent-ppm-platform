import type { Meta, StoryObj } from '@storybook/react';

type ButtonProps = {
  label: string;
  disabled?: boolean;
  loading?: boolean;
  variant: 'primary' | 'secondary' | 'danger';
};

const getVariantStyles = (variant: ButtonProps['variant']) => {
  if (variant === 'secondary') {
    return {
      background: 'var(--color-surface-card)',
      color: 'var(--color-text-primary)',
      border: '1px solid var(--color-border-default)',
    };
  }
  if (variant === 'danger') {
    return {
      background: 'var(--color-state-error-fg)',
      color: 'var(--color-text-inverse)',
      border: '1px solid var(--color-state-error-fg)',
    };
  }
  return {
    background: 'var(--color-button-primary-bg)',
    color: 'var(--color-button-primary-text)',
    border: '1px solid var(--color-button-primary-border)',
  };
};

const Button = ({ label, variant, disabled = false, loading = false }: ButtonProps) => {
  const variantStyles = getVariantStyles(variant);
  return (
    <button
      disabled={disabled || loading}
      aria-busy={loading}
      style={{
        ...variantStyles,
        borderRadius: 'var(--radius-md)',
        padding: '12px 24px',
        fontWeight: 600,
        opacity: disabled ? 0.6 : 1,
      }}
    >
      {loading ? 'Loading…' : label}
    </button>
  );
};

const meta: Meta<typeof Button> = {
  title: 'UI Kit/Components/Button',
  component: Button,
  parameters: {
    docs: {
      description: {
        component:
          'Button API contract: `variant`, `disabled`, and `loading` states must preserve visible focus ring and accessible name. Use primary buttons sparingly to maintain hierarchy.',
      },
    },
  },
  args: {
    label: 'Save changes',
    variant: 'primary',
    disabled: false,
    loading: false,
  },
  argTypes: {
    variant: {
      control: 'inline-radio',
      options: ['primary', 'secondary', 'danger'],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {};
export const Secondary: Story = { args: { variant: 'secondary' } };
export const Danger: Story = { args: { variant: 'danger' } };
export const Disabled: Story = { args: { disabled: true } };
export const Loading: Story = { args: { loading: true } };
