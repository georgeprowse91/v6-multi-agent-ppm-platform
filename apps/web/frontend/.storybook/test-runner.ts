import { injectAxe, checkA11y } from 'axe-playwright';
import type { TestRunnerConfig } from '@storybook/test-runner';

const config: TestRunnerConfig = {
  async preVisit(page) {
    await injectAxe(page);
  },
  async postVisit(page, context) {
    await checkA11y(page, '#storybook-root', {
      detailedReport: true,
      detailedReportOptions: { html: true },
      axeOptions: {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa'],
        },
      },
    });
    await page.waitForSelector('#storybook-root > *');
    await page.evaluate(() => {
      const root = document.querySelector('#storybook-root');
      if (!root || root.textContent?.trim() === '') {
        throw new Error('Story rendered empty output');
      }
    });
    console.info(`A11y baseline met for ${context.id}: 0 violations`);
  },
};

export default config;
