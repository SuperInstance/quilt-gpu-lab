// x10_lib_r3l.mjs — shared library for the R3L saturation probe (x10/x10c).
// The pipeline blocks below are carried VERBATIM from quilt-jepa run5.mjs (commit c5712f1)
// with exactly two audited deltas:
//   (1) evalWindowDump takes an optional `inject(o, i, amp)` hook; the default is the
//       as-run expression `o[i] = Math.min(1, o[i] + amp)` — bit-identical when omitted.
//   (2) normalizerStudy computes only v0_raw / v1_z / v3_mad (rank/statistic blocks that
//       run5 also computes are dropped — pure removal, no arithmetic reordering).
// PART 0 of x10 gates the copy: every ladder value must reproduce receipts/run5.json
// bit-exactly or the probe refuses.
'use strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

export const QJ = '/home/eileen/projects/quilt-jepa';
const requireQJ = createRequire(import.meta.url);
export const { GRID, xorshift32 } = requireQJ(QJ + '/core/world2.js');
export const { World2 } = requireQJ(QJ + '/core/world2.js');
export const { CELLS, LAT } = requireQJ(QJ + '/core/jepa.js');
export const { Jepa3 } = requireQJ(QJ + '/core/jepa3.js');

export const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');
export const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
export const LADDER = [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.2];
export const ANOMALY_TICKS = [430, 465, 500];
export const LR3 = 0.3, TAU4 = 0.99998, TRAIN_STEPS = 400, WSTART = 401;

// ---------- bit helpers / dtype cast primitives ----------
export const f64bits = (x) => { const b = new Float64Array(1); b[0] = x; return new BigUint64Array(b.buffer)[0]; };
export const hex64 = (x) => '0x' + f64bits(x).toString(16).padStart(16, '0');
export const f32bits = (x) => { const b = new Float32Array(1); b[0] = x; return new Uint32Array(b.buffer)[0]; };
export const bitsf32 = (u) => { const b = new Uint32Array(1); b[0] = u >>> 0; return new Float32Array(b.buffer)[0]; };
export const f32 = (x) => Math.fround(x);

// fp16: fp32 bits -> fp16 bits, round-to-nearest-even (single rounding via the +half+lsb carry trick)
export function f16bitsFromF32(u) {
  const sign16 = (u >>> 16) & 0x8000;
  const exp = (u >>> 23) & 0xff;
  const man = u & 0x7fffff;
  if (exp === 0xff) return sign16 | 0x7c00 | (man ? (0x0200 | ((man >>> 13) & 0x03ff)) : 0);
  if (exp === 0) return sign16; // fp32 subnormal -> fp16 zero (never hit on our data)
  const r = ((u & 0x7fffffff) + 0x00000fff + ((u >>> 13) & 1)) >>> 0; // RNE mantissa, carry into exponent
  const e32 = (r >>> 23) & 0xff;
  if (e32 >= 0xff) return sign16 | 0x7c00;
  const e16 = e32 - 112; // 127-15
  if (e16 >= 31) return sign16 | 0x7c00;
  if (e16 <= 0) {
    if (e16 < -10) return sign16;
    const m = (r & 0x7fffff) | 0x800000;
    const k = 13 - e16; // drop k bits, RNE
    let q = m >>> k;
    const rem = m & ((1 << k) - 1), half = 1 << (k - 1);
    if (rem > half || (rem === half && (q & 1))) q++;
    return sign16 | q;
  }
  return sign16 | (e16 << 10) | ((r >>> 13) & 0x3ff);
}
export function f16val(x) { return bitsf32bits16(f16bitsFromF32(f32bits(x))); }
export function bitsf32bits16(h) {
  const sign = h & 0x8000, e = (h >>> 10) & 0x1f, m = h & 0x03ff;
  let v;
  if (e === 0) v = m * 2 ** -24;
  else if (e === 31) v = m ? NaN : Infinity;
  else v = (1 + m / 1024) * 2 ** (e - 15);
  return sign ? -v : v;
}
export function f16bitsVal(h) { return bitsf32bits16(h); }
// bf16: fp32 bits -> RNE round of low 16 mantissa bits, back to f32 bits/value
export function bf16val(x) {
  const u = f32bits(x);
  const r = (u + 0x7fff + ((u >>> 16) & 1)) & 0xffff0000;
  return bitsf32(r);
}
// int8 symmetric full-range: q = roundHalfEven(x*127) clipped to [-128,127]; dequant q/127
export function rhe(v) { const f = Math.floor(v), d = v - f; if (d > 0.5) return f + 1; if (d < 0.5) return f; return (f % 2 === 0) ? f : f + 1; }
export const q127 = (x) => Math.max(-128, Math.min(127, rhe(x * 127)));
export const q127val = (x) => q127(x) / 127;

export const QUANT = {
  fp64: (x) => x,
  fp32: (x) => f32(x),
  fp16: (x) => f16val(x),
  bf16: (x) => bf16val(x),
  int8: (x) => q127val(x),
};

export function loadSeedU32() {
  const seedReceipt = JSON.parse(fs.readFileSync(QJ + '/receipts/certified-seed.json', 'utf8'));
  const selJson = JSON.stringify(seedReceipt.chosen.selected);
  return parseInt(sha(selJson).slice(0, 8), 16) >>> 0;
}

// ---------- verbatim blocks from run5.mjs ----------
export function perCellSurprise(zPred, zTgt) {
  const out = new Float32Array(CELLS);
  for (let c = 0; c < CELLS; c++) {
    let s = 0;
    for (let k = 0; k < LAT; k++) { const d = zPred[c * LAT + k] - zTgt[c * LAT + k]; s += d * d; }
    out[c] = s;
  }
  return out;
}
export function varRatio(T, T0) {
  const nT = T.length, D = T[0].length;
  const v = (rows) => { let s = 0; for (let d = 0; d < D; d++) { let m = 0, m2 = 0; for (let t = 0; t < nT; t++) { m += rows[t][d]; m2 += rows[t][d] * rows[t][d]; } m /= nT; s += m2 / nT - m * m; } return s; };
  return v(T) / Math.max(1e-30, v(T0));
}
export function normalizerStudy(S, AT, wStart) {
  const idx = (t) => t - wStart;
  const isAnom = (t) => AT.includes(t) || AT.includes(t + 1);
  const B124 = []; for (let t = wStart; t <= wStart + 129; t++) if (!isAnom(t)) B124.push(t);
  const sampleTicks = []; for (const t of B124) { if (sampleTicks.length < 30) sampleTicks.push(t); }
  const mu = new Float64Array(CELLS), sd = new Float64Array(CELLS), med = new Float64Array(CELLS), mad = new Float64Array(CELLS);
  const sortedCols = Array.from({ length: CELLS }, () => []);
  for (const t of B124) for (let c = 0; c < CELLS; c++) sortedCols[c].push(S[idx(t)][c]);
  for (let c = 0; c < CELLS; c++) {
    const v = sortedCols[c];
    mu[c] = mean(v);
    let s2 = 0; for (const x of v) s2 += (x - mu[c]) * (x - mu[c]);
    sd[c] = Math.sqrt(s2 / v.length);
    const sv = [...v].sort((a, b) => a - b);
    const m0 = sv.length % 2 ? sv[(sv.length - 1) / 2] : (sv[sv.length / 2 - 1] + sv[sv.length / 2]) / 2;
    med[c] = m0;
    const av = v.map((x) => Math.abs(x - m0)).sort((a, b) => a - b);
    mad[c] = av.length % 2 ? av[(av.length - 1) / 2] : (av[av.length / 2 - 1] + av[av.length / 2]) / 2;
  }
  const Z = S.map((row) => row.map((x, c) => (sd[c] > 0 ? (x - mu[c]) / sd[c] : 0)));
  const MD = S.map((row) => row.map((x, c) => (mad[c] > 0 ? (x - med[c]) / mad[c] : 0)));
  const statTop = (M) => (t) => {
    const pairs = [];
    for (let c = 0; c < CELLS; c++) pairs.push([M[idx(t)][c], c]);
    pairs.sort((a, b) => b[0] - a[0]);
    return mean(pairs.slice(0, 4).map(([, c]) => M[idx(t)][c]));
  };
  const ratio = (fn) => mean(AT.map(fn)) / mean(sampleTicks.map(fn));
  return {
    baseline_n: B124.length, sample_n: sampleTicks.length,
    v0_raw_ratio: ratio(statTop(S)),
    v1_z_ratio: ratio(statTop(Z)),
    v3_mad_ratio: ratio(statTop(MD)),
  };
}
// evalWindowDump verbatim except the injection store routes through an optional hook
export function evalWindowDump(seedU32, lr, tau, trainSteps, wStart, AT, amp, inject) {
  const inj = inject || ((o, i, a) => { o[i] = Math.min(1, o[i] + a); });
  const world = new World2(seedU32);
  const jepa = new Jepa3(seedU32);
  jepa.lr = lr; jepa.tau = tau;
  const jInit = new Jepa3(seedU32);
  let obs = world.observe();
  for (let t = 0; t < trainSteps; t++) { world.step(); const o1 = world.observe(); jepa.trainStep(obs, o1); obs = o1; }
  const S = []; const T = []; const T0 = [];
  let obsPrev = obs;
  for (let t = wStart; t <= wStart + 129; t++) {
    world.step();
    const obsNew = world.observe();
    if (AT.includes(t)) {
      const px = (world.bx + 8) % (GRID - 2), py = (world.by + 8) % (GRID - 2);
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
        inj(obsNew, (py + dy) * GRID + px + dx, amp);
      }
    }
    const zCtx = jepa.encode(obsPrev);
    const zPred = jepa.predict(zCtx);
    const zTgt = jepa.encodeTarget(obsNew);
    const zTgt0 = jInit.encodeTarget(obsNew);
    S.push(Array.from(perCellSurprise(zPred, zTgt)));
    T.push(Array.from(zTgt)); T0.push(Array.from(zTgt0));
    obsPrev = obsNew;
  }
  return { study: normalizerStudy(S, AT, wStart), var_ratio: varRatio(T, T0) };
}

// ---------- structural replay helpers ----------
// Replay the world trajectory only (obs are world-borne; training never touches the world
// or its xorshift streams) and record the un-injected fp32 frame + injected-cell indices
// at each anomaly tick. Validated against evalWindowDump by frame hash in the parent.
export function replayBlocks(seedU32, uptoTick) {
  const world = new World2(seedU32);
  const blocks = []; const frames = new Map();
  for (let t = 1; t <= uptoTick; t++) {
    world.step();
    if (ANOMALY_TICKS.includes(t)) {
      const px = (world.bx + 8) % (GRID - 2), py = (world.by + 8) % (GRID - 2);
      const frame = world.observe();
      const vals = [];
      for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
        const i = (py + dy) * GRID + px + dx;
        vals.push({ i, x: frame[i], u32: '0x' + f32bits(frame[i]).toString(16).padStart(8, '0') });
      }
      blocks.push({ t, px, py, vals });
      frames.set(t, frame);
    }
  }
  return { blocks, frames };
}

// Injection arithmetic per dtype at "native register" semantics: operands cast to D,
// exact sum, one rounding back to D (== IEEE D-addition of two D values).
// int8: symmetric per-tensor scale 1/127, integer add with [-128,127] saturation, dequant /127.
// fp64: exact sum, no store rounding (pure fp64 register).
export function makeInj(dt) {
  if (dt === 'fp32') return (o, i, a) => { o[i] = f32(Math.min(1, o[i] + a)); };
  if (dt === 'fp64') return (o, i, a) => { o[i] = Math.min(1, o[i] + a); };
  if (dt === 'fp16') return (o, i, a) => { o[i] = Math.min(1, f16val(f16val(o[i]) + f16val(a))); };
  if (dt === 'bf16') return (o, i, a) => { o[i] = Math.min(1, bf16val(bf16val(o[i]) + bf16val(a))); };
  if (dt === 'int8') return (o, i, a) => { const q = Math.max(-128, Math.min(127, q127(o[i]) + rhe(a * 127))); o[i] = q / 127; };
  throw new Error('unknown dtype ' + dt);
}
