// news-image-20261117 entry -- graded runtime (Node 22, standard library only).
//
// The picture is authored at build time by render/render_entry.py (Pillow) and
// committed beside this file as entry.png. This program is what the grader runs:
// it writes /output/entry.png out of the committed image with no network, no
// packages and nothing but Node's own modules, and it writes the same bytes on
// every run.
//
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
//
// It also re-reads what it wrote and refuses to finish quietly if those bytes
// would not pass the gate, so a corrupt build fails here rather than at grading.

import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outputDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const dest = join(outputDir, 'entry.png');

mkdirSync(outputDir, { recursive: true });
copyFileSync(join(here, 'entry.png'), dest);

const bytes = readFileSync(dest);
const PNG_MAGIC = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
if (bytes.length < 24 || PNG_MAGIC.some((want, i) => bytes[i] !== want)) {
  throw new Error(`${dest} is not a PNG`);
}
const width = bytes.readUInt32BE(16);
const height = bytes.readUInt32BE(20);
if (bytes.length > 1048576) throw new Error(`entry is ${bytes.length} bytes, over the 1 MiB cap`);
if (width > 1024 || height > 1024) throw new Error(`entry is ${width}x${height}, over 1024x1024`);

console.log(`entry.png written: ${width}x${height}, ${bytes.length} bytes`);
