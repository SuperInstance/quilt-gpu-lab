# NIGHT SPOOL — 2026-09-30 (conductor queue; grows; each insight feeds the next)

## PROTOCOL (every wake, ~20 min timebox)
1. Read this file + `tail -40 RESULTS.md`. Check running work (`process list`), never duplicate an IN-PROGRESS item.
2. Take the top OPEN item. New experiment => pre-register in proposals/runs/ FIRST (commit+push before firing).
3. GPU python: /home/eileen/venvs/elephant-gpu/bin/python. Physics conventions: tools/qcell_sim.py (balance=min(p000,p111), angles in pi-units).
4. Book honestly in RESULTS.md (fail-loud anchors; wrong guesses get amended in place, never silently). Commit+push every landing.
5. Append findings below; add new queue items the moment an insight spawns one. Mark statuses so no wake repeats work.
6. ROTATION: after a GPU item, do a PR-SWEEP or SCOUT item next (alternate). PR sweep = `gh pr list -R SuperInstance/<repo>` + read new ones (repos: MicroMoth-quilt, delta-shape, syzygy-lattice, edge-ledger, subleq-fabric, zeroclaw-dissertation) — steal insights, cite PR#, add queue items. SCOUT = web_search for cutting-edge ideas worth rebuilding/forking into SuperInstance paradigms.
7. Do NOT message Casey (asleep). If local time >= 07:00 AKDT: book state, mark NIGHT COMPLETE, start nothing new.

## QUEUE (top = next)
- [DONE 00:0x] QG2 desert-break law: **desert is STRUCTURAL** — exact-arm 57.9% ~= shot-arm 58.2%; ~42% of streams landscape-trapped; G1 FAIL (lane fills desert 0.023 vs recorded 0.017); G2 rate caveat (reimpl 58% vs recorded 3/8; P~0.26 at N=8). results/qg2_desert_law/
- [open] qcell-oracle: train a tiny MLP on QG2 rollouts -> P(cross | champion state: len, balance, gate histogram, gen). Save tools/qcell_oracle.pt + README. First TRAINED fleet component on this substrate. Data: instrument run_lane to dump per-gen champion states + outcomes (4096 streams = 400k+ rows free).
- [open] QG1-residual: localize the 28/1920 anchor mismatches (gate-combo census of failing cells) -> either close to >=99% or name the missing convention.
- [open] PR-SWEEP #1 (see rotation).
- [open] SL-G1: syzygy-lattice e-process martingale Monte Carlo (port LR rules to torch; operating-characteristic curves: kill-on-impossible, impostor late-cross; validate truth@10/impostor@112 pins first).
- [open] SCOUT #1 (see rotation).
- [open] SF-G1: subleq VM in torch (Int32Array machines, batched) -> program-space census; validate vs subleq-fabric pins.
- [open] DS-G2: change-point GPU engine, synthetic boat telemetry first (the 5-min predictor line = trail() membrane).
- [spawned by QG2] QG3: WHY are 42% landscape-trapped? Cluster stuck streams by champion basin (genome edit-distance clustering); test deeper budget (W=8, 24 gens) — do traps open with budget? Cheap on this lane.
- [spawned by QG2] QG4: budget/gens phase diagram (W x gens grid, 1024 streams/cell) — map the crossing frontier. Directly serves "cells are dedicated; routing happens between them".

## FINDINGS (append-only)
- 00:0x CONDUCTOR-0 (main): QG2 headline above. qcell-sim gained crx + receipt-anchored selftest. Vectorized lane = gathers + bmm chains; ANCHOR-VEC 2e-34.
