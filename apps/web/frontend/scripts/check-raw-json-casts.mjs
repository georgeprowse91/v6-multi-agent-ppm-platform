import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = new URL('../', import.meta.url).pathname;
const srcRoot = join(root, 'src');
const allowlistPath = join(root, 'scripts/raw-json-cast-allowlist.txt');

const collect = (dir) => {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      out.push(...collect(full));
      continue;
    }
    if (full.endsWith('.ts') || full.endsWith('.tsx')) {
      out.push(full);
    }
  }
  return out;
};

const files = collect(srcRoot);
const patterns = [
  { regex: /\(\s*await\s+[^\n]*\.json\(\)\s*\)\s+as\s+/g, label: 'await response.json() as Type' },
  { regex: /JSON\.parse\([^\n]*\)\s+as\s+/g, label: 'JSON.parse(...) as Type' },
];

const allowlist = new Set(
  readFileSync(allowlistPath, 'utf8')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
);

const current = [];
for (const file of files) {
  const content = readFileSync(file, 'utf8');
  const rel = relative(root, file);
  for (const { regex, label } of patterns) {
    for (const match of content.matchAll(regex)) {
      const before = content.slice(0, match.index ?? 0);
      const line = before.split('\n').length;
      current.push({ key: `${rel}:${line}`, label });
    }
  }
}

const newViolations = current.filter((v) => !allowlist.has(v.key));
const fixedViolations = [...allowlist].filter((key) => !current.some((v) => v.key === key));

if (newViolations.length || fixedViolations.length) {
  if (newViolations.length) {
    console.error('Found new forbidden raw JSON casts. Parse untrusted payloads with schema validation.');
    for (const violation of newViolations) {
      console.error(` - ${violation.key} -> ${violation.label}`);
    }
  }
  if (fixedViolations.length) {
    console.error('Raw JSON cast allowlist is stale; remove fixed entries:');
    for (const fixed of fixedViolations) {
      console.error(` - ${fixed}`);
    }
  }
  process.exit(1);
}

console.log(`No new raw JSON cast violations found (${current.length} allowlisted legacy violations).`);
