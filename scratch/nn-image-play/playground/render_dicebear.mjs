// Server-side dicebear renderer: style+seed -> PNG (white bg). argv: style seed size out.png
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { readFileSync, writeFileSync } from 'node:fs';
const Q = '/home/eileen/projects/dicebear-quilt';
const req = createRequire(Q + '/package.json');
const { Resvg } = req('@resvg/resvg-js');
const core = await import(pathToFileURL(Q + '/src/js/core/lib/index.js').href);
const [style, seed, sizeArg, out] = process.argv.slice(2);
const size = parseInt(sizeArg || '512', 10);
const def = JSON.parse(readFileSync(`${Q}/node_modules/@dicebear/styles/dist/${style}.min.json`, 'utf8'));
const svg = new core.Avatar(new core.Style(def), { seed, size }).toString();
const png = new Resvg(svg, { fitTo: { mode: 'width', value: size }, background: 'rgba(255,255,255,1)' }).render().asPng();
writeFileSync(out, png);
console.log(JSON.stringify({ ok: true, bytes: png.length, style, seed }));
