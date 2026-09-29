// x10c_fullpipe.mjs — child runner: FULL-PIPELINE dtype emulation via global monkey-patch.
// Replaces globalThis.Float32Array with a quantizing array class BEFORE requiring the
// quilt-jepa cores, so every tensor (world frames, turbulence, Wc/Wp/Wt, latents, surprise
// vector) stores raw fp64 but yields dtype-grain values on every read — equivalent to
// round-to-dtype after every elementary tensor op. Tracked files untouched.
//
// Usage: node x10c_fullpipe.mjs <fp64|fp16|bf16|int8>
// Emits one JSON line: { dtype, seed_u32, z: {rung: value}, sat_bit_exact, ... }
'use strict';
import { createRequire } from 'node:module';
import process from 'node:process';

const dtype = process.argv[2];
if (!['fp64', 'fp16', 'bf16', 'int8'].includes(dtype)) { console.error('usage: x10c <fp64|fp16|bf16|int8>'); process.exit(2); }

// ---- import lib FIRST (its own module-scope requires happen after the patch below only if
// we patch before import) ----
const patch = async () => {
  const lib = await import('./x10_lib_r3l.mjs');
  return lib;
};

// Build the quantizing replacement BEFORE any core module loads.
const { QUANT, rhe, q127 } = await import('./x10_lib_r3l.mjs').catch(() => ({}));
// NOTE: importing the lib loads the cores with the REAL Float32Array — that is fine for the
// lib's pure-JS helpers; the CORE modules must see the patch. So we re-import cores AFTER
// patching via fresh module URLs (cache-busted query) inside buildPipeline() below.

class QArr {
  constructor(arg) {
    if (typeof arg === 'number') this.d = new Float64Array(arg);
    else if (arg instanceof QArr) this.d = arg.d.slice();
    else this.d = Float64Array.from(arg || []);
  }
  get length() { return this.d.length; }
  get buffer() { return this.d.buffer; }
  get byteOffset() { return this.d.byteOffset; }
  get byteLength() { return this.d.byteLength; }
  subarray(a, b) { const q = Object.create(QArr.prototype); q.d = this.d.subarray(a, b); return q; }
  slice(a, b) { const q = Object.create(QArr.prototype); q.d = this.d.slice(a, b); return q; }
  set(src, off = 0) {
    const s = (src instanceof QArr) ? src.d : src;
    for (let i = 0; i < s.length; i++) this.d[off + i] = s[i];
  }
  static from(x, fn) {
    const q = Object.create(QArr.prototype);
    q.d = Float64Array.from(x, fn ? (v, i) => fn(v, i) : undefined);
    return q;
  }
  static of(...xs) { return QArr.from(xs); }
}
const idxHandler = {
  get(t, k, recv) {
    if (typeof k === 'string' && /^\d+$/.test(k)) return QUANT[dtype](t.d[k]);
    if (k === 'subarray' || k === 'slice' || k === 'set') return Reflect.get(t, k).bind(t);
    const v = Reflect.get(t, k, t);
    return typeof v === 'function' ? v.bind(t) : v;
  },
  has(t, k) { return true; },
  set(t, k, v) { if (typeof k === 'string' && /^\d+$/.test(k)) { t.d[k] = v; return true; } t[k] = v; return true; },
};
const wrap = (q) => new Proxy(q, idxHandler);
const QF32 = new Proxy(QArr, {
  construct(t, args) { return wrap(new QArr(...args)); },
  get(t, k) {
    if (k === 'from') return (x, fn) => wrap(QArr.from(x, fn));
    if (k === 'of') return (...xs) => wrap(QArr.of(...xs));
    if (k === 'name') return 'Float32Array';
    if (k === Symbol.hasInstance) return (inst) => inst instanceof QArr;
    return undefined;
  },
});
globalThis.Float32Array = QF32;

// Now import the cores fresh (this process's lib import above only touched helpers, but the
// cores were already instantiated in its module cache with the real Float32Array — so require
// them AGAIN with a cache-busting query from THIS process scope):
const { createRequire: cr } = await import('node:module');
const require2 = cr(import.meta.url);
const { World2, xorshift32, CELLS, LAT } = require2('/home/eileen/projects/quilt-jepa/core/world2.js?patched=1');
const { Jepa3 } = require2('/home/eileen/projects/quilt-jepa/core/jepa3.js?patched=1');
const fs = await import('node:fs');
const crypto = await import('node:crypto');
const shaS = (s) => crypto.createHash('sha256').update(s).digest('hex');
const seedReceipt = JSON.parse(fs.readFileSync('/home/eileen/projects/quilt-jepa/receipts/certified-seed.json', 'utf8'));
const seedU32 = parseInt(shaS(JSON.stringify(seedReceipt.chosen.selected)).slice(0, 8), 16) >>> 0;

const LADDER = [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.2];
const ANOMALY_TICKS = [430, 465, 500];

// injection hook at this dtype (operand-cast, exact sum, store; read-back re-quantizes)
function makeInjPatched(dt) {
  if (dt === 'fp64') return (o, i, a) => { o[i] = Math.min(1, o[i] + a); };
  if (dt === 'fp16') {
    const { f16val } = require2('/home/eileen/projects/quilt-gpu-lab/experiments/x10_lib_r3l.mjs');
    return (o, i, a) => { o[i] = Math.min(1, f16val(f16val(o[i]) + f16val(a))); };
  }
  if (dt === 'int8') {
    const { rhe: r2, q127: q2 } = require2('/home/eileen/projects/quilt-gpu-lab/experiments/x10_lib_r3l.mjs');
    return (o, i, a) => { const q = Math.max(-128, Math.min(127, q2(o[i]) + r2(a * 127))); o[i] = q / 127; };
  }
  if (dt === 'bf16') {
    const { bf16val } = require2('/home/eileen/projects/quilt-gpu-lab/experiments/x10_lib_r3l.mjs');
    return (o, i, a) => { o[i] = Math.min(1, bf16val(bf16val(o[i]) + bf16val(a))); };
  }
  throw new Error('bad dtype');
}

// verbatim pipeline (patched tensors) — mirrors x10_lib evalWindowDump/normalizerStudy
const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
function normalizerStudy(S, AT, wStart) {
  const idx = (t) => t - wStart;
  const isAnom = (t) => AT.includes(t) || AT.includes(t + 1);
  const B124 = []; for (let t = wStart; t <= wStart + 129; t++) if (!isAnom(t)) B124.push(t);
  const sampleTicks = []; for (const t of B124) { if (sampleTicks.length < 30) sampleTicks.push(t); }
  const mu = new Float64Array(CELLS), sd = new Float64Array(CELLS);
  const sortedCols = Array.from({ length: CELLS }, () => []);
  for (const t of B124) for (let c = 0; c < CELLS; c++) sortedCols[c].push(S[idx(t)][c]);
  for (let c = 0; c < CELLS; c++) {
    const v = sortedCols[c];
    mu[c] = mean(v);
    let s2 = 0; for (const x of v) s2 += (x - mu[c]) * (x - mu[c]);
    sd[c] = Math.sqrt(s2 / v.length);
  }
  const Z = S.map((row) => row.map((x, c) => (sd[c] > 0 ? (x - mu[c]) / sd[c] : 0)));
  const statTop = (M) => (t) => {
    const pairs = [];
    for (let c = 0; c < CELLS; c++) pairs.push([M[idx(t)][c], c]);
    pairs.sort((a, b) => b[0] - a[0]);
    return mean(pairs.slice(0, 4).map(([, c]) => M[idx(t)][c]));
  };
  const ratio = (fn) => mean(AT.map(fn)) / mean(sampleTicks.map(fn));
  return { v1_z_ratio: ratio(statTop(Z)) };
}
function evalWindowDumpPatched(seedU32, lr, tau, trainSteps, wStart, AT, amp, inj) {
  const world = new World2(seedU32);
  const jepa = new Jepa3(seedU32);
  jepa.lr = lr; jepa.tau = tau;
  const jInit = new Jepa3(seedU32);
  let obs = world.observe();
  for (let t = 0; t < trainSteps; t++) { world.step(); const o1 = world.observe(); jepa.trainStep(obs, o1); obs = o1; }
  const S = [];
  let obsPrev = obs;
  for (let t = wStart; t <= wStart + 129; t++) {
    world.step();
    const obsNew = world.observe();
    if (AT.includes(t)) {
      const px = (world.bx + 8) % (16 - 2), py = (world.by + 8) % (16 - 2);
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) inj(obsNew, (py + dy) * 16 + px + dx, amp);
    }
    const zCtx = jepa.encode(obsPrev);
    const zPred = jepa.predict(zCtx);
    const zTgt = jepa.encodeTarget(obsNew);
    S.push(Array.from(perCellSurpriseP(zPred, zTgt)));
    obsPrev = obsNew;
  }
  return normalizerStudy(S, AT, wStart);
}
function perCellSurpriseP(zPred, zTgt) {
  const out = new Float32Array(CELLS);
  for (let c = 0; c < CELLS; c++) {
    let s = 0;
    for (let k = 0; k < LAT; k++) { const d = zPred[c * LAT + k] - zTgt[c * LAT + k]; s += d * d; }
    out[c] = s;
  }
  return out;
}

const inj = makeInjPatched(dtype);
const z = {};
for (const amp of LADDER) z[String(amp)] = evalWindowDumpPatched(seedU32, 0.3, 0.99998, 400, 401, ANOMALY_TICKS, amp, inj).v1_z_ratio;
const f64bits = (x) => { const b = new Float64Array(1); b[0] = x; return new BigUint64Array(b.buffer)[0]; };
console.log(JSON.stringify({
  dtype, seed_u32: seedU32, z,
  sat_bit_exact: z['1.2'] === z['0.9'],
  z09_hex: '0x' + f64bits(z['0.9']).toString(16).padStart(16, '0'),
  distinct_z: [...new Set(Object.values(z))].length,
  null_z: z['0'],
}));
