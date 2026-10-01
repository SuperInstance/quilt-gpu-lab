#!/usr/bin/env node
// farm_runner.mjs — the always-at-capacity keeper (Casey, 09-30 21:06: "a farm that's
// always at capacity and your job is to keep it fruitful").
//
// Loop: GPU free (nvidia-smi is the ONLY fire gate)? → fire the next QUEUED experiment
// whose pre-reg is committed. The doctrine is a gate in the code: an entry without a
// COMMITTED pre-reg path never fires — push-before-fire is the scheduler, not a convention.
// Nothing big ready → run a filler (dataset builds, evals, renders, embeddings).
//
// v2 (2026-09-30 21:14 bug, fixed same night): external runs (started outside the farm,
// e.g. subagent lanes) are NOTED, never PINNED — a stale "running" entry can no longer
// starve the queue (the ADOPT bug). Filler + experiment state persists in queue.json
// across restarts. Orphaned farm-fired entries from a dead runner life are marked,
// not auto-refired.
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
const saveQueue = (q) => fs.writeFileSync(QUEUE, JSON.stringify(q, null, 1) + '\n');
const writeState = (s) => fs.writeFileSync(STATE, JSON.stringify(s, null, 1) + '\n');
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

// fire one entry: stream to farm/logs/<id>.log, on exit receipt; caller owns entry.status
const HOME = process.env.HOME || '/home/eileen';
const expandTilde = (a) => a.startsWith('~/') ? path.join(HOME, a.slice(2)) : a;
function fire(entry) {
  const logf = path.join(FARM, 'logs', `${entry.id}.log`);
  fs.mkdirSync(path.dirname(logf), { recursive: true });
  const t0 = Date.now();
  receipt(`FIRE ${entry.id} (${entry.kind}) → ${entry.cmd.join(' ')} cwd=${entry.cwd}`);
  log(`firing ${entry.id}`);
  const argv = entry.cmd.map(expandTilde); // node spawn does not shell-expand ~
  const p = spawn(argv[0], argv.slice(1), { cwd: entry.cwd, stdio: ['ignore', fs.openSync(logf, 'a'), fs.openSync(logf, 'a')] });
  return new Promise((resolve) => {
    let settled = false;
    const fin = (r) => { if (!settled) { settled = true; resolve(r); } };
    p.on('exit', (code, sig) => {
      const mins = ((Date.now() - t0) / 60000).toFixed(1);
      receipt(`${code === 0 ? 'DONE' : `EXIT-${code ?? 'sig' + sig}`} ${entry.id} in ${mins}min — log: farm/logs/${entry.id}.log`);
      fin({ ok: code === 0, code, sig });
    });
    p.on('error', (err) => { // spawn ENOENT etc. — must not hang the fire promise
      receipt(`SPAWN-ERROR ${entry.id}: ${err.message}`);
      fin({ ok: false, code: null, sig: 'spawn-error' });
    });
  });
}

log(`farm runner up (pid ${process.pid}), tick ${TICK_S}s`);
let current = null;                // what THIS runner life fired; the only pin that can gate
const notedExternal = new Set();   // receipt-once per life per external entry
while (true) {
  try {
    const q = readJSON(QUEUE, { queue: [], fillers: [] });

    // reconcile entries this life does not own
    for (const e of q.queue) {
      if (e.status === 'running' && e.farm_fired && current?.id !== e.id) {
        e.status = 'orphaned'; e.farm_fired = false;
        receipt(`ORPHAN ${e.id} — fired by a dead runner life; marked, NOT auto-refired`);
      } else if (e.status === 'running' && !e.farm_fired && !notedExternal.has(e.id)) {
        notedExternal.add(e.id);
        receipt(`NOTE ${e.id} running outside the farm — noted, never pinned`);
      }
    }
    const blocked = q.queue
      .filter((e) => e.status === 'queued' && (!e.prereg || !preregCommitted(e.prereg)))
      .map((e) => e.id);

    if (!current && !gpuBusy()) {
      const next = q.queue.find((e) => e.status === 'queued' && e.prereg && preregCommitted(e.prereg));
      if (next) {
        next.status = 'running'; next.farm_fired = true; current = next;
        saveQueue(q);
        fire(next).then((r) => {
          next.status = r.ok ? 'done' : 'failed'; // v2.1: v2 never set status on exit — crashed runs stayed 'running' forever
          next.farm_fired = false;
          saveQueue(q);
          current = null;
          log(`experiment ${next.id} finished: ${r.ok ? 'done' : `exit ${r.code ?? r.sig}`}`);
        });
      } else {
        const filler = q.fillers.find((f) => f.status !== 'running' && (!f.last_run || Date.now() - f.last_run > (f.cooldown_min || 240) * 60000));
        if (filler) {
          filler.status = 'running'; filler.last_run = Date.now();
          saveQueue(q);
          receipt(`FILLER ${filler.id} → ${filler.cmd.join(' ')}`);
          const r = await fire({ ...filler, kind: 'filler' });
          filler.status = r.ok ? 'done' : 'failed';
          saveQueue(q); // filler state persists across restarts (runbook 21:14)
          log(`filler ${filler.id} finished: ${r.ok ? 'done' : `exit ${r.code ?? r.sig}`}`);
        }
      }
    }

    writeState({
      at: new Date().toISOString(),
      gpu_busy: gpuBusy(),
      running: current?.id ?? null,
      external_running: q.queue.filter((e) => e.status === 'running' && !e.farm_fired).map((e) => e.id),
      queue: q.queue.map((e) => ({ id: e.id, status: e.status, prereg: e.prereg || null })),
      blocked_needs_prereg: blocked,
      fillers: q.fillers.map((f) => ({ id: f.id, status: f.status, last_run: f.last_run ? new Date(f.last_run).toISOString() : null })),
    });
  } catch (e) { log('tick error: ' + e.message); receipt(`TICK-ERROR ${e.message}`); }
  await new Promise((r) => setTimeout(r, TICK_S * 1000));
}
