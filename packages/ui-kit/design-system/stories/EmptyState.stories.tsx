import type { Meta, StoryObj } from '@storybook/react';
import { EmptyState } from '../../apps/web/frontend/src/components/ui/EmptyState';

const meta = {
  title: 'UI/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
  },
  args: {
    title: 'No metrics yet',
    description: 'KPI data will appear once your project has active deliverables.',
    icon: 'dashboard',
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Metrics: Story = {
  args: {
    icon: 'dashboard',
    title: 'No metrics yet',
    description: 'KPI data will appear once your project has active deliverables.',
    action: { label: 'Configure data sources', href: '/config' },
  },
};

export const Pipeline: Story = {
  args: {
    icon: 'timeline',
    title: 'Pipeline is empty',
    description: 'Add items to your pipeline to track delivery stages.',
    action: { label: 'Add pipeline item', href: '/intake' },
  },
};

export const Search: Story = {
  args: {
    icon: 'search',
    title: 'No matches',
    description: 'Try adjusting your filter criteria.',
    action: { label: 'Clear filter', onClick: () => undefined },
  },
};

export const Confirmation: Story = {
  args: {
    icon: 'confirm',
    title: 'All caught up',
    description: 'No approvals need your attention right now.',
  },
};

export const ConfigAgents: Story = {
  args: {
    icon: 'agents',
    title: 'No agent configurations',
    description: 'Agent configurations appear here after agents are provisioned for this workspace.',
    action: { label: 'Refresh agents', onClick: () => undefined },
  },
};
