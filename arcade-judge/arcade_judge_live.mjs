// ARCADE JUDGE LIVE — one game with the judge actually adjudicating.
//
//   node arcade-judge/arcade_judge_live.mjs
//
// Plays a full headless tictactoe game (minimax vs minimax) on the REAL
// quilt-arcade engine (imported, unmodified) and hands EVERY referee
// verdict — including one deliberate R2 refusal probe — to the local-model
// judge sidecar (judge_local.mjs). Also calls scorePosition once per ply.
// Emits a JSON receipt beside this file. The arcade's own suites are run
// separately; nothing in quilt-arcade is modified.

import { QuiltEngine } from '../../quilt-arcade/engine/index.js';
import { buildSheet, sqName } from '../../quilt-arcade/games/tictactoe/sheet.mjs';
import { harness } from '../../quilt-arcade/shared/kit.mjs';
import { createJudgeSlot } from './judge_local.mjs';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const log = [];
const say = (line) => { console.log(line); log.push(line); };

// ── 0. health + model pick ───────────────────────────────────────────────────
let judge = createJudgeSlot({});
const health = await judge.health();
say(`judge impl: ${judge.impl}  url: ${judge.url}`);
say(`health: ${JSON.stringify(health)}`);
if (!health.ok) {
  console.error('FATAL: Ollama unreachable at ' + judge.url);
  process.exit(1);
}
if (!health.hasModel) {
  const fallback = health.models[0];
  if (!fallback) { console.error('FATAL: Ollama up but no models pulled'); process.exit(1); }
  say(`model ${judge.model} not pulled — falling back to ${fallback}`);
  judge = createJudgeSlot({ model: fallback });
}

// ── 1. shape self-validation (mirrors slots/index.mjs assertSlotsValid) ─────
const shape = (() => {
  if (judge.slot !== 'judge') return 'slot mislabeled';
  if (typeof judge.hooks !== 'object' || !judge.hooks) return 'no hooks object';
  for (const [h, fn] of Object.entries(judge.hooks)) if (typeof fn !== 'function') return `hook ${h} not async-callable`;
  if (typeof judge.credentials?.configured !== 'boolean') return 'no boolean credentials.configured';
  return null;
})();
if (shape) { console.error('FATAL: judge violates slot contract: ' + shape); process.exit(1); }
say(`slot contract: valid (slot=${judge.slot} name=${judge.name} status=${judge.status} credentials.configured=${judge.credentials.configured})`);

// ── 2. the game ──────────────────────────────────────────────────────────────
const H = harness('arcade-judge-live');
const engine = new QuiltEngine('gpu-lab-judge-live', { eager: true });
engine.loadSheet(buildSheet());

let lastSeq = 0;
const push = async (req) => {
  const seq = ++lastSeq;
  req = { ...req, seq };
  await engine.set('move.request', req);
  let verdict = (await engine.get('rules.verdict')).data;
  if (verdict?.seq !== seq) verdict = (await engine.call('move.dispatch', req)).data;
  return verdict;
};
const get = async (id) => (await engine.get(id)).data;

const adjudications = [];
const scoreCalls = [];
const review = async (move, verdict) => {
  const t0 = Date.now();
  const opinion = await judge.hooks.reviewMove(move, verdict);
  adjudications.push({ move, verdict, opinion, latencyMs: Date.now() - t0 });
  const sq = move.sq ?? sqName?.(move.r, move.c) ?? `${move.r},${move.c}`;
  say(`  JEV review ${String(sq).padEnd(3)} → ${JSON.stringify(verdict)} ⇒ agree=${opinion ? opinion.agree : 'NULL'}` +
      (opinion ? ` conf=${opinion.confidence} why="${opinion.why}" (${opinion.model}, ${Date.now() - t0}ms)` : '  (no opinion — refusal counted)'));
  return opinion;
};

await engine.call('new_game');

let refusalProbed = false;
const plies = [];
for (let ply = 1; ply <= 9; ply++) {
  if ((await get('phase.current')) !== 'play') break;
  const player = await get('turn.current');
  const grid = await get('board.grid');

  // per-ply position opinion
  const t0 = Date.now();
  const pos = await judge.hooks.scorePosition({ game: 'tictactoe', ply, turn: player, grid });
  scoreCalls.push({ ply, snapshot: { game: 'tictactoe', ply, turn: player, grid }, opinion: pos, latencyMs: Date.now() - t0 });
  say(`  JEV score  ply${ply} (${player}) ⇒ ${pos ? `score=${pos.score} why="${pos.why}"` : 'NULL (refusal counted)'}`);

  const mv = (await engine.call('ai.minimax', { player })).data;
  const sq = sqName(mv.r, mv.c);
  const verdict = await push({ r: mv.r, c: mv.c, player });
  say(`ply ${ply}: ${player} → ${sq} | referee: ${JSON.stringify(verdict)}`);
  await review({ sq, r: mv.r, c: mv.c, player, ply }, verdict);
  plies.push({ ply, player, sq, verdict });

  // one deliberate illegal-move probe (re-push the just-taken square):
  // the referee must refuse (R2), the board must not change, and the judge
  // gets to review a REFUSAL — the interesting half of the contract.
  if (!refusalProbed) {
    refusalProbed = true;
    const rv = await push({ r: mv.r, c: mv.c, player });
    say(`ply ${ply} probe: ${player} → ${sq} again (illegal) | referee: ${JSON.stringify(rv)}`);
    await review({ sq, r: mv.r, c: mv.c, player, ply: ply + 'R', illegal: true }, rv);
    plies.push({ ply: ply + 'R', player, sq, verdict: rv, probe: true });
  }
}

const winner = await get('winner.current');
const phase = await get('phase.current');
say(`game over: phase=${phase} winner=${winner}`);

// ── 3. checks ────────────────────────────────────────────────────────────────
await H.check('game completed on the real engine', async () => {
  H.eq(phase, 'over');
  H.ok(winner === 'draw' || winner === 'X' || winner === 'O', 'winner is a real outcome: ' + winner);
});

await H.check('judge was actually called (LIVING, not stub)', async () => {
  H.ok(judge.stats.calls > 0, `model calls: ${judge.stats.calls}`);
  H.ok(adjudications.length >= plies.length - 0 && adjudications.length > 0, `reviewMove adjudications: ${adjudications.length}`);
  H.ok(scoreCalls.length > 0, `scorePosition calls: ${scoreCalls.length}`);
});

await H.check('judge returned well-formed opinions (fence held)', async () => {
  for (const a of adjudications) {
    if (a.opinion === null) continue; // honest no-opinion is contract-legal
    H.ok(typeof a.opinion.agree === 'boolean', 'agree is boolean');
    H.ok(a.opinion.confidence === null || (a.opinion.confidence >= 0 && a.opinion.confidence <= 1), 'confidence in [0,1]');
  }
  for (const s of scoreCalls) {
    if (s.opinion === null) continue;
    H.ok(typeof s.opinion.score === 'number' && s.opinion.score >= -100 && s.opinion.score <= 100, 'score in [-100,100]');
  }
  const opinions = adjudications.filter((a) => a.opinion).length + scoreCalls.filter((s) => s.opinion).length;
  H.ok(opinions > 0, `total opinions delivered: ${opinions} (refusals: ${judge.stats.refusals})`);
});

await H.check('refusal probe was refused by R2 and reviewed', async () => {
  const probe = adjudications.find((a) => a.move.illegal);
  H.ok(!!probe, 'probe adjudicated');
  H.ok(probe.verdict.ok === false && probe.verdict.rule === 'R2', 'referee refused with R2');
  H.ok(probe.opinion !== null, 'judge gave an opinion on the refusal');
  if (probe.opinion) say(`  JEV on refusal: agree=${probe.opinion.agree} why="${probe.opinion.why}"`);
});

await H.check('board integrity: probe changed nothing', async () => {
  const grid = await get('board.grid');
  const count = grid.flat().filter(Boolean).length;
  H.eq(count, plies.filter((p) => !p.probe && p.verdict.ok !== false).length, 'one mark per accepted move only');
});

const { pass, fail } = await H.done();

// ── 4. receipt ───────────────────────────────────────────────────────────────
const receipt = {
  what: 'first LIVING CHECK — local model living inside quilt-arcade judge slot (JEV)',
  date: new Date().toISOString(),
  adapter: join(here, 'judge_local.mjs'),
  arcade_touched: false,
  slot_contract: {
    source: 'quilt-arcade/slots/judge.mjs (unmodified, v0.1.0 interface)',
    hooks: { scorePosition: '(snapshot) → {score, why} | null', reviewMove: '(move, verdict) → {agree, why} | null' },
    sidecar_status: judge.status,
    sidecar_version: judge.version,
    credentials: judge.credentials,
  },
  model: judge.model,
  ollama_url: judge.url,
  game: { engine: 'quilt-arcade QuiltEngine (imported unmodified)', sheet: 'games/tictactoe', phase, winner, plies },
  judge_stats: judge.stats,
  adjudications,
  score_calls: scoreCalls,
  checks: { pass, fail },
  log,
};
const receiptPath = join(here, 'arcade-judge-live-2026-09-28.json');
writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n');
say(`receipt: ${receiptPath}`);
process.exitCode = fail === 0 ? 0 : 1;
