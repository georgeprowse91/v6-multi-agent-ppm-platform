// @vitest-environment jsdom
import axe from 'axe-core';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const staticDir = path.resolve(__dirname, '../../../static');
const pages = ['index.html'];

const runAxe = async (html: string) => {
  document.open();
  document.write(html);
  document.close();
  return axe.run(document, {
    rules: {
      'color-contrast': { enabled: true },
    },
  });
};

describe('static pages accessibility', () => {
  it.each(pages)('has no axe violations on %s', async (page) => {
    const html = readFileSync(path.join(staticDir, page), 'utf-8');
    const results = await runAxe(html);
    expect(results.violations).toEqual([]);
  });
});
