#!/usr/bin/env node
// av1_extract_pairs.mjs — stage-0 pair builder for AV1 (proposals/runs/AV1-ascii-to-video.md)
// video → (ascii.txt, frame.png) pairs. Glyph engine only (the porter lane owns the rest).
// Zero deps. ffmpeg via list-form spawn (red lines: never shell-string).
// usage: node av1_extract_pairs.mjs <video> <outdir> [--fps 10] [--duration 5] [--seek 0] [--cols 100]
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const RAMP = " .:-=+*#%@"; // classic 1970s ramp; glyph engine contract (chiaroscuro §6)
const [video, outdir] = process.argv.slice(2);
const arg = (name, dflt) => { const i = process.argv.indexOf('--' + name); return i > 0 ? Number(process.argv[i + 1]) : dflt; };
const fps = arg('fps', 10), duration = arg('duration', 5), seek = arg('seek', 0), cols = arg('cols', 100);
if (!video || !outdir) { console.error('usage: node av1_extract_pairs.mjs <video> <outdir> [--fps 10] [--duration 5] [--seek 0] [--cols 100]'); process.exit(2); }
if (!fs.existsSync(video)) { console.error('FAIL: no such video ' + video); process.exit(2); }
fs.mkdirSync(outdir, { recursive: true });
const FFMPEG = '/home/eileen/.local/bin/ffmpeg';
const ASPECT = 0.5; // terminal cell aspect (char height ≈ 2× width) — chiaroscuro §14

// pass 1: extract exactly duration*fps frames at cols resolution, grayscale raw
// (fail-loud: ffmpeg non-zero exit → stderr excerpt; no ffprobe dependency)
const rows = Math.round(cols * ASPECT);
const args = ['-hide_banner', '-ss', String(seek), '-i', video, '-frames:v', String(Math.round(fps * duration)), '-vf', `scale=${cols}:${rows}`, '-f', 'rawvideo', '-pix_fmt', 'gray', '-'];
const raw = (() => { try { return execFileSync(FFMPEG, args, { maxBuffer: 1 << 30 }); }
  catch (e) { console.error('FAIL: ffmpeg could not read video\n' + e.stderr?.toString().split('\n').slice(-4).join('\n')); process.exit(2); } })();
const frameBytes = cols * rows;
const n = Math.floor(raw.length / frameBytes);
if (n === 0) { console.error('FAIL: 0 frames extracted (raw ' + raw.length + 'B)'); process.exit(2); }

// pass 3: PNG frames for the dataset side of the pairs
execFileSync(FFMPEG, ['-hide_banner', '-ss', String(seek), '-i', video, '-frames:v', String(n), '-vf', `scale=${cols * 4}:${rows * 4}`, path.join(outdir, 'frame%04d.png')]);

let manifest = { schema: 'av1-pairs/v0', video, fps, duration, seek, cols, rows, n, ramp: RAMP, frames: [] };
for (let f = 0; f < n; f++) {
  const lines = [];
  for (let r = 0; r < rows; r++) {
    let line = '';
    for (let c = 0; c < cols; c++) {
      const v = raw[f * frameBytes + r * cols + c];       // 0..255 luminance
      line += RAMP[Math.min(RAMP.length - 1, Math.floor((v / 256) * RAMP.length))];
    }
    lines.push(line);
  }
  const txt = lines.join('\n');
  const name = `pair%04d`.replace('%04d', String(f).padStart(4, '0'));
  fs.writeFileSync(path.join(outdir, name + '.txt'), txt + '\n');
  manifest.frames.push({ i: f, ascii: name + '.txt', frame: name.replace('pair', 'frame') + '.png' });
}
fs.writeFileSync(path.join(outdir, 'pairs-manifest.json'), JSON.stringify(manifest, null, 1) + '\n');
console.log(JSON.stringify({ ok: true, n, cols, rows, outdir, bytes: raw.length }));
