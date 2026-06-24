// Guards against pt/en translation drift: every key in one locale must exist
// in the other. The i18n files are plain object literals (with comments and
// string concatenation), so once the TS-only bits are stripped they evaluate
// as JS. Run with: npm run check:i18n
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));

function load(file) {
  const src = readFileSync(resolve(here, "../src/i18n", file), "utf8")
    .replace(/export\s+default\s+/, "")
    .replace(/as\s+const\s*;?\s*$/, "");
  // eslint-disable-next-line no-new-func
  return Function(`"use strict"; return (${src});`)();
}

function keys(obj, prefix = "") {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

const pt = new Set(keys(load("pt.ts")));
const en = new Set(keys(load("en.ts")));
const onlyPt = [...pt].filter((k) => !en.has(k));
const onlyEn = [...en].filter((k) => !pt.has(k));

if (onlyPt.length || onlyEn.length) {
  if (onlyPt.length) console.error("✗ Faltam em en.ts:\n  - " + onlyPt.join("\n  - "));
  if (onlyEn.length) console.error("✗ Faltam em pt.ts:\n  - " + onlyEn.join("\n  - "));
  process.exit(1);
}
console.log(`✓ i18n OK — ${pt.size} chaves alinhadas entre pt e en.`);
