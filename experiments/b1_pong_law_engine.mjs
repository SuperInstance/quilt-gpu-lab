// b1_pong_law_engine.mjs — lane B1-DISTILL engine harness.
//
// The Python driver owns the protocol, training and receipts; THIS process
// owns the quilt-arcade engine tick (list-form subprocess, one JSON object per
// line on stdin, one per line on stdout).
//
// Two sheets live here:
//   * PRISTINE — quilt-arcade games/pong buildSheet() UNMODIFIED. Its
//     `ai.track` is the exact derived law and is the ONLY label source.
//   * SWITCH   — the same sheet with `ai.track` swapped for a control switch
//     whose 'law' branch is character-for-character the shipped TRACK body,
//     plus 'random' and 'net' branches. The switch sheet plays the games.
//     `laweq` measures switch-law vs pristine-law on any state set; the B1
//     prereg requires bit-identical before any measured number is trusted.
//
// Commands:
//   {"cmd":"setnet","side":"left"|"right","net":{W1,b1,W2,b2,W3,b3}|null}
//   {"cmd":"newgame","seed":N,"left":M,"right":M}       M in law|random|net
//   {"cmd":"collect","seed":N,"left":M,"right":M,"ticks":T,"rngSeed":R}
//   {"cmd":"h2h","seed":N,"left":M,"right":M,"maxTicks":T}
//   {"cmd":"labels","engine":"pristine"|"switchlaw","states":[{p,b,side}]}
//   {"cmd":"laweq","states":[{p,b,side}]}
//   {"cmd":"quit"}

import { createInterface } from 'node:readline';
import { QuiltEngine } from '/home/eileen/projects/quilt-arcade/engine/index.js';
import { buildSheet } from '/home/eileen/projects/quilt-arcade/games/pong/sheet.mjs';
import { v } from '/home/eileen/projects/quilt-arcade/shared/kit.mjs';

const PH = 6, H = 60;
const SIDE_SPEED = { left: 0.85, right: 0.70 };

// The shipped TRACK body (quilt-arcade games/pong/sheet.mjs) is reproduced
// verbatim in the 'law' branch; the extras are strictly additive branches.
const TRACK_SWITCH = `
const side = input?.side;
const speed = side === 'left' ? 0.85 : 0.70;
const mode = (await runtime.get('control.' + side)).data ?? 'law';
let y = (await runtime.get('paddle.' + side)).data;
if (mode === 'net') {
  y += (await runtime.get('netdelta.' + side)).data ?? 0;
} else if (mode === 'random') {
  y += (await runtime.get('move.' + side)).data ?? 0;
} else {
  const target = (await runtime.get('ball.y')).data;
  const dead = 1.5;
  if (Math.abs(target - y) > dead) y += Math.sign(target - y) * Math.min(speed, Math.abs(target - y) - dead);
}
y = Math.max(${PH}, Math.min(${H - PH}, y));
await runtime.set('paddle.' + side, y);
return { side, y, mode };`;

function makeSwitchSheet() {
  const sheet = buildSheet();
  sheet.cells.push(v('control.left', 'law', 'left paddle controller: law|random|net'));
  sheet.cells.push(v('control.right', 'law', 'right paddle controller: law|random|net'));
  sheet.cells.push(v('move.left', 0, 'random-mode move for left paddle: -1|0|1'));
  sheet.cells.push(v('move.right', 0, 'random-mode move for right paddle: -1|0|1'));
  sheet.cells.push(v('netdelta.left', 0, 'net-mode delta for left paddle (field units)'));
  sheet.cells.push(v('netdelta.right', 0, 'net-mode delta for right paddle (field units)'));
  const t = sheet.cells.find((c) => c.id === 'ai.track');
  if (!t) throw new Error('ai.track cell missing from pong sheet');
  t.code = TRACK_SWITCH;
  return sheet;
}

const bootPristine = () => {
  const e = new QuiltEngine('b1-pristine', { eager: true });
  e.loadSheet(buildSheet());
  return e;
};
const bootSwitch = () => {
  const e = new QuiltEngine('b1-switch', { eager: true });
  e.loadSheet(makeSwitchSheet());
  return e;
};

const V = (e, id) => {
  const c = e.getCell(id);
  return c ? c.value?.data : undefined;
};

// ── deterministic RNG (mulberry32, the engine's own dialect) ────────────────
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1) >>> 0;
    t = (t + Math.imul(t ^ (t >>> 7), t | 61)) >>> 0;
    t = t ^ (t >>> 14);
    return (t >>> 0) / 4294967296;
  };
}

// ── distilled net, evaluated in JS (verified against torch in controls) ─────
function mlpForward(net, p, b, side) {
  const x = [(p - 30) / 30, (b - 30) / 30, side];
  const h1 = new Array(64);
  for (let j = 0; j < 64; j++) {
    let s = net.b1[j];
    const w = net.W1[j];
    s += w[0] * x[0] + w[1] * x[1] + w[2] * x[2];
    h1[j] = Math.tanh(s);
  }
  const h2 = new Array(64);
  for (let j = 0; j < 64; j++) {
    let s = net.b2[j];
    const w = net.W2[j];
    for (let k = 0; k < 64; k++) s += w[k] * h1[k];
    h2[j] = Math.tanh(s);
  }
  let out = net.b3[0];
  const w3 = net.W3[0];
  for (let k = 0; k < 64; k++) out += w3[k] * h2[k];
  return out;
}

const nets = { left: null, right: null };

function preState(e, sw) {
  const bx = V(e, 'ball.x'), by = V(e, 'ball.y');
  const pl = V(e, 'paddle.left'), pr = V(e, 'paddle.right');
  return {
    ballX: bx, ballY: by, ballVx: V(e, 'ball.vx'), ballVy: V(e, 'ball.vy'),
    left: pl, right: pr,
    scoreLeft: V(e, 'score.left'), scoreRight: V(e, 'score.right'),
    phase: V(e, 'phase.current'), winner: V(e, 'winner.current'),
    tick: V(e, 'tick.count'),
  };
}

let sw = bootSwitch();
let pr = bootPristine();

async function applyControls(e, left, right) {
  await e.set('control.left', left);
  await e.set('control.right', right);
  await e.set('move.left', 0);
  await e.set('move.right', 0);
  await e.set('netdelta.left', 0);
  await e.set('netdelta.right', 0);
}

// Compute the moves/deltas the given controls want for the CURRENT state, and
// write them into the sheet. 'law' needs nothing (its branch reads state).
async function primeControls(e, left, right, p, rng, lastState) {
  if (left === 'random') {
    const u = rng();
    await e.set('move.left', u < 1 / 3 ? -1 : (u < 2 / 3 ? 0 : 1));
  }
  if (right === 'random') {
    const u = rng();
    await e.set('move.right', u < 1 / 3 ? -1 : (u < 2 / 3 ? 0 : 1));
  }
  if (left === 'net') {
    await e.set('netdelta.left', mlpForward(nets.left, lastState.left, lastState.ballY, 0));
  }
  if (right === 'net') {
    await e.set('netdelta.right', mlpForward(nets.right, lastState.right, lastState.ballY, 1));
  }
}

async function labelStates(engine, states) {
  // EXECUTE the law cell; never reimplement it. engine = pristine | switchlaw
  const out = new Array(states.length);
  for (let i = 0; i < states.length; i++) {
    const st = states[i];
    const side = st.side === 'right' || st.side === 1 ? 'right' : 'left';
    const p0 = st.p;
    await engine.set('paddle.' + side, p0);
    await engine.set('ball.y', st.b);
    if (engine === sw) await engine.set('control.' + side, 'law');
    const r = await engine.call('ai.track', { side });
    if (r.status === 'error') throw new Error('ai.track error: ' + (r.error?.message ?? '?'));
    const y1 = await engine.get('paddle.' + side);
    out[i] = y1.data - p0;
  }
  return out;
}

const handlers = {
  async setnet(msg) {
    const side = msg.side;
    if (side !== 'left' && side !== 'right') return { ok: false, error: 'bad side' };
    nets[side] = msg.net ?? null;
    return { ok: true, side, installed: nets[side] !== null };
  },
  async newgame(msg) {
    await applyControls(sw, msg.left, msg.right);
    const r = await sw.call('new_game', { seed: msg.seed });
    if (r.status === 'error') return { ok: false, error: r.error?.message ?? 'new_game error' };
    return { ok: true, state: preState(sw) };
  },
  async collect(msg) {
    const left = msg.left, right = msg.right;
    await applyControls(sw, left, right);
    let r = await sw.call('new_game', { seed: msg.seed });
    if (r.status === 'error') return { ok: false, error: r.error?.message ?? 'new_game error' };
    const rng = mulberry32(msg.rngSeed ?? msg.seed);
    const samples = [];
    let over = false;
    const ticks = msg.ticks ?? 1200;
    for (let i = 0; i < ticks; i++) {
      const s = preState(sw);
      samples.push(s);
      await primeControls(sw, left, right, null, rng, s);
      const step = await sw.call('match.step');
      if (step.status === 'error') return { ok: false, error: step.error?.message ?? 'match.step error' };
      if (step.data?.over) { over = true; break; }
    }
    return { ok: true, ticks: samples.length, over, samples };
  },
  async h2h(msg) {
    const left = msg.left, right = msg.right;
    await applyControls(sw, left, right);
    let r = await sw.call('new_game', { seed: msg.seed });
    if (r.status === 'error') return { ok: false, error: r.error?.message ?? 'new_game error' };
    const maxTicks = msg.maxTicks ?? 20000;
    const rng = mulberry32((msg.seed * 2654435761) >>> 0);
    let n = 0, over = false, last = null;
    while (n < maxTicks) {
      const s = preState(sw);
      await primeControls(sw, left, right, null, rng, s);
      const step = await sw.call('match.step');
      if (step.status === 'error') return { ok: false, error: step.error?.message ?? 'match.step error' };
      last = step.data;
      n++;
      if (last?.over) { over = true; break; }
    }
    return {
      ok: true, seed: msg.seed, left, right, ticks: n, closed: over,
      winner: over ? V(sw, 'winner.current') : null,
      score: over ? { left: V(sw, 'score.left'), right: V(sw, 'score.right') } : null,
    };
  },
  async labels(msg) {
    const engine = msg.engine === 'switchlaw' ? sw : pr;
    const out = await labelStates(engine, msg.states);
    return { ok: true, deltas: out };
  },
  async netforward(msg) {
    const side = msg.side === 'right' ? 'right' : 'left';
    const net = nets[side];
    if (!net) return { ok: false, error: 'no net installed for ' + side };
    const s = side === 'left' ? 0 : 1;
    const out = msg.pairs.map(([p, b]) => mlpForward(net, p, b, s));
    return { ok: true, deltas: out };
  },
  async laweq(msg) {
    const a = await labelStates(pr, msg.states);
    const b = await labelStates(sw, msg.states);
    let maxDiff = 0, nDiff = 0;
    for (let i = 0; i < a.length; i++) {
      const d = Math.abs(a[i] - b[i]);
      if (d > 0) nDiff++;
      if (d > maxDiff) maxDiff = d;
    }
    return { ok: true, n: a.length, max_abs_diff: maxDiff, n_diff: nDiff };
  },
  async quit() {
    setTimeout(() => process.exit(0), 5);
    return { ok: true, bye: true };
  },
};

const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');
const rl = createInterface({ input: process.stdin });
let chain = Promise.resolve();
rl.on('line', (line) => {
  const s = line.trim();
  if (!s) return;
  chain = chain.then(async () => {
    let msg;
    try { msg = JSON.parse(s); } catch (err) { out({ ok: false, error: 'bad json: ' + err.message }); return; }
    const h = handlers[msg.cmd];
    if (!h) { out({ ok: false, error: 'unknown cmd: ' + msg.cmd }); return; }
    try { out(await h(msg)); }
    catch (err) { out({ ok: false, error: String(err && err.stack ? err.stack : err) }); }
  });
});
rl.on('close', () => process.exit(0));
out({ ok: true, ready: true, ph: PH, h: H });
