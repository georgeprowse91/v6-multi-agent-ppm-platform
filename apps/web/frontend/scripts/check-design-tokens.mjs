import fs from 'fs';
import path from 'path';

const root = path.resolve(process.cwd());
const targets = [
  path.join(root, 'src'),
  path.join(root, '../../packages/canvas-engine/src'),
];

const bannedBackgroundPatterns = [
  /background(-color)?:[^;]*(#FD5108)/i,
  /background(-color)?:[^;]*var\(--color-brand-orange-500\)/i,
  /background(-color)?:[^;]*var\(--color-primary-500\)/i,
  /background(-color)?:[^;]*var\(--color-primary-600\)/i,
];

const violations = [];

const visit = (dir) => {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'node_modules' || entry.name.startsWith('.')) {
        continue;
      }
      visit(fullPath);
      continue;
    }
    if (!/\.(css|tsx|ts)$/.test(entry.name)) {
      continue;
    }
    const content = fs.readFileSync(fullPath, 'utf8');
    const lines = content.split(/\r?\n/);
    lines.forEach((line, index) => {
      bannedBackgroundPatterns.forEach((pattern) => {
        if (pattern.test(line)) {
          violations.push({
            file: fullPath,
            line: index + 1,
            text: line.trim(),
          });
        }
      });
    });
  }
};

targets.forEach(visit);

if (violations.length > 0) {
  console.error('Design token check failed. Orange500 cannot be used as a button background.');
  violations.forEach((violation) => {
    console.error(`${violation.file}:${violation.line} ${violation.text}`);
  });
  process.exit(1);
}

console.log('Design token check passed.');
