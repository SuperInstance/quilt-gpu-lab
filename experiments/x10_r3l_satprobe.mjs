'use strict';
// x10_r3l_satprobe.mjs — quilt-gpu-lab probe of quilt-jepa's R3L amplitude-ladder bit-exact
// saturation (round-5, run5.mjs). Read-only w.r.t. quilt-jepa: cores imported by absolute
// path, tracked files untouched. Companion checker: x10b_r3l_satprobe_dtype_check.py.
// Receipt: docs/quilt-jepa-satprobe-2026-09-28.md
//
// PART 0  bit-exact reproduction of the registered ladder vs receipts/run5.json
// PART 1  structural analysis of the as-run (fp32-register) injection: per-tick block
//         minima, analytic + scanned frame-freeze boundary, 0.9-vs-1.2 frame identity
// PART 2  register-width sweep at frame level: fp32(as-run) / fp16 / bf16 / int8(1/127)
//         — saturation boundary + quantization-grain plateau census per dtype
// PART 3  z-pipeline freeze verification per dtype (injected frames register-quantized,
//         training as-run so the model is fixed across amps within a dtype)
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { createRequire } from 'node:module';

const requireQJ = createRequire(import.meta.url);
const QJ = '/home/eileen/projects/quilt-jepa';
const { GRID, xorshift32 } = requireQJ(path.join(QJ, 'core/world2.js'));
const { World2 } = requireQJ(path.join(QJ, 'core/world2.js'));
const { CELLS, LAT } = requireQJ(path.join(QJ, 'core/jepa.js'));
const { Jepa3 } = requireQJ(path.join(QJ, 'core/jepa3.js'));

const OUT = path.join('/home/eileen/projects/quilt-gpu-lab/experiments/data', 'r3l_satprobe_2026-09-28.json');
fs.mkdirSync(path.dirname(OUT), { recursive: true });

const sha = (s) => crypto.createHash('sha256').update(s).digest('hex');
const f64bits = (x) => { const b = new Float64Array(1); b[0] = x; return new BigUint64Array(b.buffer)[0]; };
const hex64 = (x) => '0x' + f64bits(x).toString(16).padStart(16, '0');
const f32bits = (x) => { const b = new Float32Array(1); b[0] = x; return new Uint32Array(b.buffer)[0]; };
const bitsf32 = (u) => { const b = new Uint32Array(1); b[0] = u >>> 0; return new Float32Array(b.buffer)[0]; };
const f32 = (x) => Math.fround(x);
const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
const LADDER = [0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.2];
const ANOMALY_TICKS = [430, 465, 500];
const LR3 = 0.3, TAU4 = 0.99998;

// ---------- dtype cast primitives (validated bit-for-bit by x10b numpy checker) ----------
// fp16: fp32 bits -> fp16 bits, round-to-nearest-even (single rounding via the +half+lsb carry trick)
function f16bitsFromF32(u) {
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
function f16val(x) { return bitsf32bits16(f16bitsFromF32(f32bits(x))); }
function bitsf32bits16(h) {
  const sign = h & 0x8000, e = (h >>> 10) & 0x1f, m = h & 0x03ff;
  let v;
  if (e === 0) v = m * 2 ** -24;
  else if (e === 31) v = m ? NaN : Infinity;
  else v = (1 + m / 1024) * 2 ** (e - 15);
  return sign ? -v : v;
}
// bf16: fp32 bits -> RNE round of low 16 mantissa bits, back to f32 bits/value
function bf16val(x) {
  const u = f32bits(x);
  const r = (u + 0x7fff + ((u >>> 16) & 1)) & 0xffff0000;
  return bitsf32(r);
}
// int8 symmetric full-range: q = roundHalfEven(x*127) in [-128,127]; dequant q/127
function rhe(v) { const f = Math.floor(v), d = v - f; if (d > 0.5) return f + 1; if (d < 0.5) return f; return (f % 2 === 0) ? f : f + 1; }
const q127 = (x) => Math.max(-128, Math.min(127, rhe(x * 127)));

// ---------- verbatim blocks from run5.mjs (probe identity: these must stay untouched) ----------
function perCellSurprise(zPred, zTgt) {
  const out = new Float32Array(CELLS);
  for (let c = 0; c < CELLS; c++) {
    let s = 0;
    for (let k = 0; k < LAT; k++) { const d = zPred[c * LAT + k] - zTgt[c * LAT + k]; s += d * d; }
    out[c] = s;
  }
  return out;
}
function concentrated(perCell, k) { return mean(Array.from(perCell).sort((a, b) => b - a).slice(0, k)); }
function varRatio(T, T0) {
  const nT = T.length, D = T[0].length;
  const v = (rows) => { let s = 0; for (let d = 0; d < D; d++) { let m = 0, m2 = 0; for (let t = 0; t < nT; t++) { m += rows[t][d]; m2 += rows[t][d] * rows[t][d]; } m /= nT; s += m2 / nT - m * m; } return s; };
  return v(T) / Math.max(1e-30, v(T0));
}
function normalizerStudy(S, AT, wStart) {
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
  const ratio = (fn) => mean(AT.map(fn)) / mean(sampleTicks.map(fn));
  const statTop = (M) => (t) => {
    const pairs = [];
    for (let c = 0; c < CELLS; c++) pairs.push([M[idx(t)][c], c]);
    pairs.sort((a, b) => b[0] - a[0]);
    return mean(pairs.slice(0, 4).map(([, c]) => M[idx(t)][c]));
  };
  const res = { baseline_n: B124.length, sample_n: sampleTicks.length };
  res.v0_raw_ratio = ratio(statTop(S));
  res.v1_z_ratio = ratio(statTop(Z));
  res.v3_mad_ratio = ratio(statTop(MD));
  return res;
}
// evalWindowDump verbatim except the 4 injection stores route through an optional inject() hook
// (default = the as-run expression, bit-identical). PART 3 passes register-quantizing hooks.
function evalWindowDump(seedU32, lr, tau, trainSteps, wStart, AT, amp, inject) {
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

// ---------- PART 0: seed + bit-exact reproduction ----------
const seedReceipt = JSON.parse(fs.readFileSync(path.join(QJ, 'receipts/certified-seed.json'), 'utf8'));
const selJson = JSON.stringify(seedReceipt.chosen.selected);
const seedU32 = parseInt(sha(selJson).slice(0, 8), 16) >>> 0;
console.log('seedU32 =', seedU32, '(0x' + seedU32.toString(16) + ')');

const run5 = JSON.parse(fs.readFileSync(path.join(QJ, 'receipts/run5.json'), 'utf8'));
const m5 = run5.metrics || run5;
const repro = { ladder: {}, all_bit_exact: true, deterministic_recheck: null };
for (const amp of LADDER) {
  const { study } = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, amp);
  const z = study.v1_z_ratio;
  const key = 'r3l_z_' + String(amp).replace('.', '_');
  const ref = m5[key];
  const ok = z === ref;
  repro.ladder[String(amp)] = { z, z_hex: hex64(z), ref, ref_hex: ref !== undefined ? hex64(ref) : null, bit_exact: ok };
  if (!ok) repro.all_bit_exact = false;
}
for (const amp of [0.9, 1.2]) {
  const { study } = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, amp);
  for (const [nm, v] of [['raw', study.v0_raw_ratio], ['mad', study.v3_mad_ratio]]) {
    const key = `r3l_${nm}_${String(amp).replace('.', '_')}`;
    const ok = v === m5[key];
    repro.ladder[String(amp)][nm] = { v, v_hex: hex64(v), ref: m5[key], bit_exact: ok };
    if (!ok) repro.all_bit_exact = false;
  }
}
{ // determinism sanity: same amp twice
  const a = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, 0.9).study.v1_z_ratio;
  const b = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, 0.9).study.v1_z_ratio;
  repro.deterministic_recheck = a === b;
}
console.log('PART0 reproduction bit-exact:', repro.all_bit_exact, '| det recheck:', repro.deterministic_recheck);

// ---------- PART 1: as-run structural boundary ----------
// Replay world only (obs are world-borne; training only shapes weights) to the 3 anomaly ticks.
const world = new World2(seedU32);
const blocks = [];
for (let t = 1; t <= 530; t++) {
  world.step();
  if (ANOMALY_TICKS.includes(t)) {
    const px = (world.bx + 8) % (GRID - 2), py = (world.by + 8) % (GRID - 2);
    const vals = [];
    for (let dy = 0; dy < 2; dy++) for (let dx = 0; dx < 2; dx++) {
      const i = (py + dy) * GRID + px + dx;
      const f = world.observe()[i]; // fp32 register value
      vals.push({ i, x: f, u32: '0x' + f32bits(f).toString(16).padStart(8, '0') });
    }
    blocks.push({ t, px, py, vals });
  }
}
const allVals = blocks.flatMap((b) => b.vals.map((v) => v.x));
const minX = Math.min(...allVals);
const argMin = blocks.map((b) => ({ t: b.t, min: Math.min(...b.vals.map((v) => v.x)) }));
console.log('block minima per tick:', argMin.map((a) => `t${a.t}=${a.min.toFixed(6)}`).join(' '), '| global min', minX);

// as-run injected pixel: fround(min(1, x + amp)); ceiling iff x + amp >= 1 - 2^-25 (ties-to-even -> 1.0)
const AMP_SAT_FP32 = Math.max(...allVals.map((x) => 1 - 2 ** -25 - x));
const AMP_SAT_FP64 = Math.max(...allVals.map((x) => 1 - x)); // frame-level fp64 reference (no fp32 store)
console.log('as-run fp32-register frame-freeze boundary (analytic):', AMP_SAT_FP32, '| fp64 no-store reference:', AMP_SAT_FP64);

const injPix = (b) => b.vals.map((v) => v.i);
const injAsrun = (frame, b, amp) => { const g = Float32Array.from(frame); for (const { i, x } of b.vals) g[i] = f32(Math.min(1, x + amp)); return g; };
const frHash = (g) => { let h = 2166136261; const u = new Uint32Array(g.buffer, g.byteOffset, g.length); for (let k = 0; k < u.length; k++) { let x = (u[k] ^ (h & 0xffffffff)) >>> 0; h = Math.imul(x, 16777619) >>> 0; } return '0x' + h.toString(16); };
const frames = new Map(); // tick -> un-injected frame
{
  const w = new World2(seedU32);
  for (let t = 1; t <= 530; t++) { w.step(); if (ANOMALY_TICKS.includes(t)) frames.set(t, w.observe()); }
}
const frameAt = (amp) => ANOMALY_TICKS.map((t) => frHash(injAsrun(frames.get(t), blocks.find((b) => b.t === t), amp))).join(',');
const frameSat = frameAt(10);
const identical09vs12 = frameAt(0.9) === frameAt(1.2);
// scan verification of the analytic boundary + last frame change below it
let lastChange = 0;
for (let a = AMP_SAT_FP32; a > 0; a -= Math.max(2 ** -27, a * 1e-9)) { if (frameAt(a) !== frameSat) { lastChange = a; break; } }
const scanFreezeOK = frameAt(AMP_SAT_FP32) === frameSat && frameAt(AMP_SAT_FP32 + 1e-6) === frameSat && frameAt(AMP_SAT_FP32 + 0.1) === frameSat && frameAt(AMP_SAT_FP32 + 100) === frameSat;
console.log('frames 0.9 == 1.2 byte-identical:', identical09vs12, '| scan freeze OK:', scanFreezeOK, '| last frame change below boundary at amp ~', lastChange.toPrecision(12));

// z-staircase: as-run pipeline at extended amps around/below the boundary + freeze confirmation
const zExt = {};
for (const amp of [0.75, 0.76, 0.78, 0.8, 0.82, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.9, 0.925, 0.95, 1.0, 1.2, 1.5, 3.0]) {
  zExt[String(amp)] = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, amp).study.v1_z_ratio;
}
const zDistinct = [...new Set(Object.values(zExt))];
const zAboveBoundary = Object.entries(zExt).filter(([a]) => parseFloat(a) >= AMP_SAT_FP32).map(([, z]) => z);
const zFrozenAbove = new Set(zAboveBoundary).size === 1 && zAboveBoundary[0] === zExt['0.9'];
console.log('z staircase distinct values:', zDistinct.length, '| z bit-frozen for all amp >= boundary:', zFrozenAbove);

// ---------- PART 2: register-width sweep at frame level ----------
// native-register semantics: both operands cast to D; D-addition == exact fp64 sum rounded once to D.
const GRAIN = { fp32: 2 ** -24, fp16: 2 ** -11, bf16: 2 ** -8, int8: 1 / 127 };
function injFrame(dtype, amp) {
  return ANOMALY_TICKS.map((t) => {
    const b = blocks.find((bb) => bb.t === t);
    const g = Float32Array.from(frames.get(t));
    if (dtype === 'fp32') { for (const { i, x } of b.vals) g[i] = f32(Math.min(1, x + amp)); }
    else if (dtype === 'fp16') {
      const a16 = f16val(amp);
      for (const { i, x } of b.vals) { const y = f16val(f16val(x) + a16); g[i] = Math.min(1, y); }
    } else if (dtype === 'bf16') {
      const aB = bf16val(amp);
      for (const { i, x } of b.vals) { const y = bf16val(bf16val(x) + aB); g[i] = Math.min(1, y); }
    } else if (dtype === 'int8') {
      const aq = rhe(amp * 127);
      for (const { i, x } of b.vals) { const q = Math.max(-128, Math.min(127, q127(x) + aq)); g[i] = q / 127; }
    }
    return frHash(g);
  }).join(',');
}
const bound = {};
for (const dt of ['fp32', 'fp16', 'bf16', 'int8']) {
  const g = GRAIN[dt];
  const valsD = allVals.map((x) => dt === 'fp16' ? f16val(x) : dt === 'bf16' ? bf16val(x) : dt === 'int8' ? q127(x) / 127 : x);
  const halfU = dt === 'fp32' ? 2 ** -25 : dt === 'fp16' ? 2 ** -12 * 2 : dt === 'bf16' ? 2 ** -9 * 2 : 0.5 / 127;
  const thr = dt === 'int8' ? (126.5 / 127) : 1 - halfU / 2 * 2 === 1 - halfU ? 1 - halfU : 1 - halfU; // half-ulp below 1.0
  const analytic = Math.max(...valsD.map((x) => thr - x));
  const sat = injFrame(dt, 1e4);
  // verify freeze above analytic boundary, find last change below it (scan down at grain resolution)
  const ok = injFrame(dt, analytic) === sat && injFrame(dt, analytic + g / 4) === sat && injFrame(dt, analytic * 3 + 1) === sat;
  let last = 0;
  for (let a = analytic; a > 0; a -= g / 16) { if (injFrame(dt, a) !== sat) { last = a; break; } }
  // plateau census: distinct frames over [0, analytic] at grain/8 steps
  const seen = new Map();
  for (let a = 0; a <= analytic + g / 16; a += g / 8) { const h = injFrame(dt, a); seen.set(h, (seen.get(h) || 0) + 1); }
  bound[dt] = { analytic_boundary: analytic, freeze_verified: ok, last_change_below: last, grain: g, distinct_frames_below_boundary: seen.size, ceiling_hash: sat };
  console.log(`${dt}: boundary=${analytic.toPrecision(12)} verified=${ok} lastChange=${last.toPrecision(6)} distinctFrames(below)=${seen.size}`);
}

// ---------- PART 3: z-pipeline freeze per dtype (training as-run; injected frames register-quantized) ----------
const makeInj = (dt) => (o, i, a) => {
  if (dt === 'fp16') { const y = f16val(f16val(o[i]) + f16val(a)); o[i] = Math.min(1, y); }
  else if (dt === 'bf16') { const y = bf16val(bf16val(o[i]) + bf16val(a)); o[i] = Math.min(1, y); }
  else { const q = Math.max(-128, Math.min(127, q127(o[i]) + rhe(a * 127))); o[i] = q / 127; }
};
const zDtype = {};
for (const dt of ['fp32', 'fp16', 'bf16', 'int8']) {
  zDtype[dt] = {};
  const inj = dt === 'fp32' ? undefined : makeInj(dt);
  for (const amp of [0, 0.3, 0.6, 0.75, 0.8, 0.84, 0.86, 0.88, 0.89, 0.9, 0.95, 1.0, 1.2, 2.0]) {
    zDtype[dt][String(amp)] = evalWindowDump(seedU32, LR3, TAU4, 400, 401, ANOMALY_TICKS, amp, inj).study.v1_z_ratio;
  }
  const zs = Object.entries(zDtype[dt]).map(([a, z]) => [parseFloat(a), z]);
  const bnd = bound[dt].analytic_boundary;
  const above = zs.filter(([a]) => a >= bnd).map(([, z]) => z);
  bound[dt].z_frozen_above_boundary = new Set(above).size === 1;
  bound[dt].z_at_boundary = above[0];
  bound[dt].z_distinct_below_boundary = new Set(zs.filter(([a]) => a < bnd).map(([, z]) => z)).size;
  console.log(`z[${dt}]: frozen above boundary=${bound[dt].z_frozen_above_boundary} distinct-below=${bound[dt].z_distinct_below_boundary} z(0.9)=${zDtype[dt]['0.9']}`);
}

const artifact = {
  meta: { probe: 'x10_r3l_satprobe', date: '2026-09-28', repo: 'quilt-jepa', commit: 'c5712f1', gpu_note: 'RTX 4050 checked free (0 MiB used); not required — every op on the numeric path (+, min, dtype cast/store) is IEEE-specified and bit-identical CPU/GPU; z-pipeline reproduction requires the repo JS arithmetic, runs CPU' },
  seed_u32: seedU32, seed_u32_hex: '0x' + seedU32.toString(16),
  part0_reproduction: repro,
  part1_structural: {
    blocks, block_minima_per_tick: argMin, global_min_x: minX, global_min_x_hex: hex64(minX),
    amp_sat_fp32_asrun: AMP_SAT_FP32, amp_sat_fp64_reference: AMP_SAT_FP64,
    frames_09_vs_12_identical: identical09vs12, scan_freeze_ok: scanFreezeOK, last_frame_change_below: lastChange,
    z_extended_staircase: zExt, z_frozen_above_boundary: zFrozenAbove
  },
  part2_dtype_boundaries: bound,
  part3_z_per_dtype: zDtype
};
fs.writeFileSync(OUT, JSON.stringify(artifact, null, 1));
console.log('artifact written:', OUT);
