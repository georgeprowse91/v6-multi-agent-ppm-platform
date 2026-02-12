import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT_DIR = path.resolve('src');
const MODULE_EXTENSIONS = ['.module.css', '.module.scss', '.module.sass'];
const CLASS_NAME_PATTERN = /\.([_a-zA-Z]+[\w-]*)/g;

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map(async (entry) => {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        return walk(fullPath);
      }
      return [fullPath];
    }),
  );

  return files.flat();
}

function toCamelCase(name) {
  return name.replace(/-([a-zA-Z0-9])/g, (_, char) => char.toUpperCase());
}

function collectClassNames(source) {
  const classNames = new Set();
  for (const match of source.matchAll(CLASS_NAME_PATTERN)) {
    classNames.add(match[1]);
    classNames.add(toCamelCase(match[1]));
  }
  return [...classNames].filter(Boolean).sort();
}

function generateDeclaration(classNames) {
  const lines = classNames.map((className) => `  readonly '${className}': string;`);
  return `declare const classes: {\n${lines.join('\n')}\n};\nexport default classes;\n`;
}

async function main() {
  const allFiles = await walk(ROOT_DIR);
  const moduleFiles = allFiles.filter((file) => MODULE_EXTENSIONS.some((ext) => file.endsWith(ext)));

  await Promise.all(
    moduleFiles.map(async (file) => {
      const source = await fs.readFile(file, 'utf8');
      const classNames = collectClassNames(source);
      const declaration = generateDeclaration(classNames);
      await fs.writeFile(`${file}.d.ts`, declaration, 'utf8');
    }),
  );

  console.log(`Generated CSS module typings for ${moduleFiles.length} files.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
