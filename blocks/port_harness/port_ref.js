// port_ref.js — carried JS port of the pong derived law for blocks/port_harness.
//
// This is the PORT side of the port_harness self-test: a faithful float64
// reimplementation of the shipped quilt-arcade pong `ai.track` cell
// (experiments/b1_pong_law_engine.mjs, TRACK_SWITCH 'law' branch):
//
//   speed = side === 'left' ? 0.85 : 0.70
//   dead  = 1.5
//   if |ball.y - y| > dead: y += sign(ball.y - y) * min(speed, |ball.y - y| - dead)
//   y = clamp(y, 6, 54)
//
// PRECISION CONTRACT: both sides compute in IEEE-754 double (float64).
// JavaScript Numbers are doubles and Math.* here introduces no rounding beyond
// double ops, so an honest float64 port is expected to agree EXACTLY (max
// abs diff 0.0) with the numpy reference. The original B1-DISTILL receipt was
// 7.2e-07-class only because the torch side ran the net in float32; the
// harness tolerance parameter exists for exactly that mixed-precision class.
//
// Protocol (JSON lines, one object per line, mirrors b1_pong_law_engine.mjs):
//   in : {"cmd":"eval","cases":[{"row_id":i,"p":y0,"b":ballY,"side":"left"|"right"},...]}
//   out: {"ok":true,"results":[{"row_id":i,"side":s,"y":newY},...]}
//   in : {"cmd":"quit"}  -> process exits 0.
//
// Self-test only: PORT_HARNESS_BUG=deadzone_halved injects a deliberately
// wrong deadzone (0.75) so the harness can prove it detects a bad port.

'use strict';

const BUG = process.env.PORT_HARNESS_BUG || null;

const DEAD = BUG === 'deadzone_halved' ? 0.75 : 1.5;
const PH = 6, H = 60;

function trackLaw(p, b, side) {
  const speed = side === 'left' ? 0.85 : 0.70; // float64 on both sides
  let y = p;
  const d = Math.abs(b - y);
  if (d > DEAD) y += Math.sign(b - y) * Math.min(speed, d - DEAD);
  return Math.max(PH, Math.min(H - PH, y));
}

const lines = require('node:readline').createInterface({ input: process.stdin });
lines.on('line', (line) => {
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: 'bad json: ' + e.message }));
    return;
  }
  if (msg.cmd === 'quit') {
    process.exit(0);
  }
  if (msg.cmd !== 'eval') {
    console.log(JSON.stringify({ ok: false, error: 'unknown cmd: ' + msg.cmd }));
    return;
  }
  const results = msg.cases.map((c) => ({
    row_id: c.row_id,
    side: c.side,
    y: trackLaw(c.p, c.b, c.side),
  }));
  console.log(JSON.stringify({ ok: true, results }));
});
