#!/usr/bin/env node
// farm_runner.mjs — the always-at-capacity keeper (Casey, 09-30 21:06: "a farm that's
// always at capacity and your job is to keep it fruitful").
//
// Loop: GPU free? → fire the next QUEUED experiment whose pre-reg is committed.
// Doctrine enforced by the scheduler: an entry without a COMMITTED pre-reg path never
// fires — pre-registration is not a suggestion, it is a gate in the code.
// When nothing big is ready → run a filler (dataset builds, evals, renders, embeddings).
// Every fire/exit/receipt appends to farm/RECEIPTS.md (append-only) and farm/state.json.
//
// zero deps · list-form spawn only (red lines) · fail-loud · single instance via lock.
import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.dirname(path.dirname(new URL(import.meta.url).pathname)); // quilt-gpu-lab/
const FARM = path.join(ROOT, 'farm');
const QUEUE = path.join(FARM, 'queue.json');
const RECEIPTS = path.join(FARM, 'RECEIPTS.md');
const STATE = path.join(FARM, 'state.json');
const LOCK = '/tmp/quilt-farm.lock';
const NVIDIASM = '/usr/lib/wsl/lib/nvidia-smi';
const TICK_S = Number(process.env.FARM_TICK_S || 60);
const FARM_LOG = process.env.FARM_LOG || '/tmp/quilt-farm.log';

const log = (m) => { fs.appendFileSync(FARM_LOG, `${new Date().toISOString()} ${m}\n`); };
const receipt = (m) => { fs.appendFileSync(RECEIPTS, `- ${new Date().toISOString()} ${m}\n`); };

if (fs.existsSync(LOCK)) {
  const pid = Number(fs.readFileSync(LOCK, 'utf8').trim());
  try { process.kill(pid, 0); console.error(`farm already running (pid ${pid})`); process.exit(1); }
  catch { log('stale lock removed'); }
}
fs.writeFileSync(LOCK, String(process.pid));
process.on('SIGTERM', () => { fs.rmSync(LOCK, { force: true }); process.exit(0); });

const readJSON = (f, dflt) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return dflt; } };
const gpuBusy = () => {
  try {
    const out = execFileSync(NVIDIASM, ['--query-compute-apps=pid', '--format=csv,noheader'], { timeout: 10000 }).toString().trim();
    return out.length > 0;
  } catch { return false; } // no GPU visible → treat as free, runner experiments will fail loud if they need it
};
const preregCommitted = (rel) => {
  try { execFileSync('git', ['-C', ROOT, 'log', '-1', '--format=%H', '--', rel], { timeout: 10000 }); return true; }
  catch { return false; }
};
const writeState = (s) => fs.writeFileSync(STATE, JSON.stringify(s, null, 1) + '\n');

// fire one entry: spawn detached-ish, stream to farm/logs/<id>.log, on exit receipt + mark
function fire(entry) {
  const logf = path.join(FARM, 'logs', `${entry.id}.log`);
  fs.mkdirSync(path.dirname(logf), { recursive: true });
  const t0 = Date.now();
  receipt(`FIRE ${entry.id} (${entry.kind}) → ${entry.cmd.join(' ')} cwd=${entry.cwd}`);
  log(`firing ${entry.id}`);
  const p = spawn(entry.cmd[0], entry.cmd.slice(1), { cwd: entry.cwd, stdio: ['ignore', fs.openSync(logf, 'a'), fs.openSync(logf, 'a')] });
  return new Promise((resolve) => {
    p.on('exit', (code, sig) => {
      const mins = ((Date.now() - t0) / 60000).toFixed(1);
      const status = code === 0 ? 'DONE' : `EXIT-${code ?? 'sig' + sig}`;
      entry.status = code === 0 ? 'done' : 'failed';
      entry.last_exit = { code, mins, at: new Date().toISOString() };
      receipt(`${status} ${entry.id} in ${mins}min — log: farm/logs/${entry.id}.log`);
      resolve();
    });
  });
}

log(`farm runner up (pid ${process.pid}), tick ${TICK_S}s`);
let current = null;
while (true) {
  try {
    const q = readJSON(QUEUE, { queue: [], fillers: [] });
    if (!current) {
      current = q.queue.find((e) => e.status === 'running') || null; // adopt externally-started (e.g. av1-train)
      if (current) receipt(`ADOPT ${current.id} (already running outside the farm)`);
    }
    if (!current && !gpuBusy()) {
      const next = q.queue.find((e) => e.status === 'queued' && e.prereg && preregCommitted(e.prereg));
      if (next) {
        next.status = 'running'; current = next;
        fs.writeFileSync(QUEUE, JSON.stringify(q, null, 1) + '\n');
        fire(next).then(() => { fs.writeFileSync(QUEUE, JSON.stringify(q, null, 1) + '\n'); current = null; });
      } else {
        const blocked = q.queue.filter((e) => e.status === 'queued' && (!e.prereg || !preregCommitted(e.prereg)));
        const filler = q.fillers.find((f) => f.status !== 'running' && (!f.last_run || Date.now() - f.last_run > (f.cooldown_min || 240) * 60000));
        if (filler) {
          filler.status = 'running'; filler.last_run = Date.now();
          receipt(`FILLER ${filler.id} → ${filler.cmd.join(' ')}`);
          await fire({ ...filler, kind: 'filler' }).then(() => { filler.status = 'done'; });
        }
        writeState({ at: new Date().toISOString(), gpu_busy: gpuBusy(), running: current?.id ?? null,
          queue: q.queue.map((e) => ({ id: e.id, status: e.status, prereg: e.prereg || null })),
          blocked_needs_prereg: blocked.map((e) => e.id), fillers_today: q.fillers.filter((f) => Date.now() - (f.last_run || 0) < 86400000).map((f) => f.id) });
      }
    }
    if (current) writeState({ at: new Date().toISOString(), gpu_busy: gpuBusy(), running: current.id, queue: q.queue.map((e) => ({ id: e.id, status: e.status })) });
  } catch (e) { log('tick error: ' + e.message); receipt(`TICK-ERROR ${e.message}`); }
  await new Promise((r) => setTimeout(r, TICK_S * 1000));
}
