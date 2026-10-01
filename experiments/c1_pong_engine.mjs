// c1_pong_engine.mjs — interactive Pong engine harness for the C1 local-playtester
// experiment (lane C1-PLAYTEST). The Python driver owns the match loop, the model
// calls and the receipts; this process owns the quilt-arcade engine tick.
//
// Protocol: one JSON object per line on stdin, one JSON object per line on stdout.
//   {"cmd":"new_game","seed":N,"left":"law"|"model","right":"law"|"model"}
//   {"cmd":"step","moves":{"left":-1|0|1,"right":-1|0|1}}
//   {"cmd":"quit"}
//
// The sheet is quilt-arcade games/pong EXACTLY as shipped (buildSheet()), with a
// SINGLE substitution: the `ai.track` derived-law cell is replaced by a program
// that reads a per-side control mode. In 'law' mode it applies the derived law
// verbatim (track ball.y at side speed, deadzone 1.5, clamp to [6,54]). In
// 'model' mode the same movement budget (side speed, same clamp) is applied to a
// direction the driver supplies — so both paddles move at identical speed limits
// and the ONLY difference between arms is which policy chooses the direction.
// No other engine/game code is touched.

import { createInterface } from 'node:readline';
import { QuiltEngine } from '/home/eileen/projects/quilt-arcade/engine/index.js';
import { buildSheet } from '/home/eileen/projects/quilt-arcade/games/pong/sheet.mjs';
import { v } from '/home/eileen/projects/quilt-arcade/shared/kit.mjs';

// Derived-law port with a control switch. 'law' branch is character-for-character
// the shipped TRACK law (speed/deadzone/clamp); 'model' branch spends the same
// per-tick movement budget on a supplied direction.
const TRACK_SWITCH = `
const side = input?.side;
const speed = side === 'left' ? 0.85 : 0.70;
const mode = (await runtime.get('control.' + side)).data ?? 'law';
let y = (await runtime.get('paddle.' + side)).data;
if (mode === 'model') {
  let mv = (await runtime.get('move.' + side)).data ?? 0;
  mv = mv > 0 ? 1 : (mv < 0 ? -1 : 0);
  y += mv * speed;
} else {
  const target = (await runtime.get('ball.y')).data;
  const dead = 1.5;
  if (Math.abs(target - y) > dead) y += Math.sign(target - y) * Math.min(speed, Math.abs(target - y) - dead);
}
y = Math.max(6, Math.min(54, y));
await runtime.set('paddle.' + side, y);
return { side, y, mode };`;

const PH = 6, H = 60;

function makeSheet() {
  const sheet = buildSheet();
  sheet.cells.push(v('control.left', 'law', 'left paddle controller: law|model'));
  sheet.cells.push(v('control.right', 'law', 'right paddle controller: law|model'));
  sheet.cells.push(v('move.left', 0, 'model move for left paddle: -1|0|1'));
  sheet.cells.push(v('move.right', 0, 'model move for right paddle: -1|0|1'));
  const t = sheet.cells.find((c) => c.id === 'ai.track');
  if (!t) throw new Error('ai.track cell missing from pong sheet');
  t.code = TRACK_SWITCH;
  return sheet;
}

const boot = () => {
  const e = new QuiltEngine('c1-pong', { eager: true });
  e.loadSheet(makeSheet());
  return e;
};

const V = (e, id) => {
  const c = e.getCell(id);
  return c ? c.value?.data : undefined;
};

// The derived law expressed as an action letter on ANY state: the law moves the
// paddle toward ball.y and the direction it would spend this tick is exactly the
// sign of (ball.y - paddle.y) outside the 1.5 deadzone. This is the letter the
// law would emit on the identical (ball, own-paddle) state — the agreement probe.
function lawLetter(paddleY, ballY) {
  const d = ballY - paddleY;
  if (Math.abs(d) <= 1.5) return 'S';
  return d > 0 ? 'D' : 'U';
}

function stateOf(e) {
  const bx = V(e, 'ball.x'), by = V(e, 'ball.y');
  const pl = V(e, 'paddle.left'), pr = V(e, 'paddle.right');
  return {
    ballX: bx, ballY: by, ballVx: V(e, 'ball.vx'), ballVy: V(e, 'ball.vy'),
    left: pl, right: pr,
    scoreLeft: V(e, 'score.left'), scoreRight: V(e, 'score.right'),
    phase: V(e, 'phase.current'), winner: V(e, 'winner.current'),
    tick: V(e, 'tick.count'), fired: V(e, 'rules.fired'),
    lawLetterLeft: lawLetter(pl, by), lawLetterRight: lawLetter(pr, by),
  };
}

let engine = boot();
const out = (o) => process.stdout.write(JSON.stringify(o) + '\n');

const handlers = {
  async new_game(msg) {
    await engine.set('control.left', msg.left === 'model' ? 'model' : 'law');
    await engine.set('control.right', msg.right === 'model' ? 'model' : 'law');
    await engine.set('move.left', 0);
    await engine.set('move.right', 0);
    const r = await engine.call('new_game', { seed: msg.seed });
    if (r.status === 'error') return { ok: false, error: r.error?.message ?? 'new_game error' };
    return { ok: true, state: stateOf(engine) };
  },
  async step(msg) {
    const mv = msg.moves ?? {};
    await engine.set('move.left', mv.left ?? 0);
    await engine.set('move.right', mv.right ?? 0);
    const r = await engine.call('match.step');
    if (r.status === 'error') return { ok: false, error: r.error?.message ?? 'match.step error' };
    const d = r.data;
    return { ok: true, over: d?.over === true, point: d?.point ?? null, state: stateOf(engine) };
  },
  async quit() {
    setTimeout(() => process.exit(0), 5);
    return { ok: true, bye: true };
  },
};

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
