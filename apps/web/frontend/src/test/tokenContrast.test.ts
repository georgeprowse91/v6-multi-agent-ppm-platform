import { describe, expect, it } from 'vitest';
import { tokens } from '@ppm/design-tokens';

const toLinear = (channel: number) => {
  const srgb = channel / 255;
  return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
};

const luminance = (hex: string) => {
  const cleaned = hex.replace('#', '');
  const r = parseInt(cleaned.slice(0, 2), 16);
  const g = parseInt(cleaned.slice(2, 4), 16);
  const b = parseInt(cleaned.slice(4, 6), 16);
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
};

const contrastRatio = (fg: string, bg: string) => {
  const l1 = luminance(fg);
  const l2 = luminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
};

describe('design token contrast', () => {
  it('keeps secondary text at AA contrast on page background', () => {
    const ratio = contrastRatio(tokens.color.text.secondary, tokens.color.surface.page);
    expect(ratio).toBeGreaterThanOrEqual(tokens.accessibility.minContrastRatio);
  });

  it('keeps warning foreground contrast on warning background', () => {
    const ratio = contrastRatio(tokens.color.state.warning.fg, tokens.color.state.warning.bg);
    expect(ratio).toBeGreaterThanOrEqual(tokens.accessibility.minContrastRatio);
  });

  it('keeps dark mode border visible on dark card surfaces', () => {
    const ratio = contrastRatio(tokens.color.darkMode.border, tokens.color.darkMode.surfaceCard);
    expect(ratio).toBeGreaterThanOrEqual(1.5);
  });

  it('keeps primary button contrast at AA minimum', () => {
    const rule = tokens.accessibility.primaryButtonRule;
    const ratio = contrastRatio(rule.textMustBe, rule.backgroundMustBe);
    expect(ratio).toBeGreaterThanOrEqual(3.5);
  });

  it('keeps focus ring visible on primary button background', () => {
    const ratio = contrastRatio(tokens.accessibility.focus.ring.color, tokens.accessibility.primaryButtonRule.backgroundMustBe);
    expect(ratio).toBeGreaterThanOrEqual(3);
  });
});
