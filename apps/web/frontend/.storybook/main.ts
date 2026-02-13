import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: [
    '../../../design-system/**/*.stories.@(ts|tsx|mdx)',
    '../../../packages/ui-kit/design-system/**/*.stories.@(ts|tsx|mdx)',
  ],
  addons: ['@storybook/addon-essentials', '@storybook/addon-interactions', '@storybook/addon-a11y'],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  async viteFinal(config) {
    config.server = config.server || {};
    config.server.fs = config.server.fs || {};
    config.server.fs.allow = [
      ...(config.server.fs.allow || []),
      '../../../design-system',
      '../../../packages/ui-kit/design-system',
    ];
    return config;
  },
};

export default config;
