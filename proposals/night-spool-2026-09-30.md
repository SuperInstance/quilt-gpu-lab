# NIGHT SPOOL — 2026-09-30 (conductor queue; grows; each insight feeds the next)

## PROTOCOL (every wake, ~20 min timebox)
1. Read this file + `tail -40 RESULTS.md`. Check running work (`process list`), never duplicate an IN-PROGRESS item.
2. Take the top OPEN item. New experiment => pre-register in proposals/runs/ FIRST (commit+push before firing).
3. GPU python: /home/eileen/venvs/elephant-gpu/bin/python. Physics conventions: tools/qcell_sim.py (balance=min(p000,p111), angles in pi-units).
4. Book honestly in RESULTS.md (fail-loud anchors; wrong guesses get amended in place, never silently). Commit+push every landing.
5. Append findings below; add new queue items the moment an insight spawns one. Mark statuses so no wake repeats work.
6. ROTATION: after a GPU item, do a PR-SWEEP or SCOUT item next (alternate). PR sweep = `gh pr list -R SuperInstance/<repo>` + read new ones (repos: MicroMoth-quilt, delta-shape, syzygy-lattice, edge-ledger, subleq-fabric, zeroclaw-dissertation) — steal insights, cite PR#, add queue items. SCOUT = web_search for cutting-edge ideas worth rebuilding/forking into SuperInstance paradigms.
7. Do NOT message Casey (asleep). If local time >= 07:00 AKDT: book state, mark NIGHT COMPLETE, start nothing new.

## DOCKSIDE (do this FIRST on the next wake)
- **FIRE DECIDE-1** the moment the weights land: `cd /home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b && ls -la model.safetensors.part` (~1.7 GB, curl in background since 00:37, ETA ~01:10). If complete: `mv model.safetensors.part model.safetensors`, then `cd /home/eileen/projects/quilt-gpu-lab && /home/eileen/venvs/elephant-gpu/bin/python experiments/decide1.py`. Book results/decide1/decide1_results.json into RESULTS.md and push. Frozen gates G1 (control >= 0.75), G2 (lane > 0.25, p<0.01), G3 (VRAM<=6GB + latency), G4 (reader ladder zero-shot vs +temperature vs fitted head). If G1 FAILS: STOP, diagnose the readout (token ids / marker / template) — never re-roll.
- If the download stalled again, retry: `curl -sL --retry 5 -C - -o model.safetensors.part https://huggingface.co/mstrasser/Jeff-Qwen3.5-0.8B/resolve/main/model.safetensors`.

## QUEUE (top = next)
- [DONE 00:0x] **DECIDE-1 pre-reg + tool + driver WRITTEN** (`tools/decision_cell.py`, `experiments/decide1.py`, `proposals/runs/DECIDE-1-decision-cell.md` + AMENDMENT 1): jeff mechanism fully reverse-engineered — 255x1024 readout head, temperature 1.1289, exact prompt template, answer formulas. Firing blocked only on the 1.7 GB weight download.\n- [DONE 00:0x] **Recons landed**: `proposals/physicalcoding-recon-2026-09-30.md` (1288w) + `proposals/jeff-recon-2026-09-30.md` (1004w + addendum).\n- [DONE 00:0x] QC: `tools/qcell_sim.py` gained the missing `crx` gate + receipt-anchored selftest (k4 champion 0.4268).\n- [DONE 00:0x] QG2 desert-break law: **desert is STRUCTURAL** — exact-arm 57.9% ~= shot-arm 58.2%; ~42% of streams landscape-trapped; G1 FAIL (lane fills desert 0.023 vs recorded 0.017); G2 rate caveat (reimpl 58% vs recorded 3/8; P~0.26 at N=8). results/qg2_desert_law/
- [open] qcell-oracle: train a tiny MLP on QG2 rollouts -> P(cross | champion state: len, balance, gate histogram, gen). Save tools/qcell_oracle.pt + README. First TRAINED fleet component on this substrate. Data: instrument run_lane to dump per-gen champion states + outcomes (4096 streams = 400k+ rows free).
- [open] QG1-residual: localize the 28/1920 anchor mismatches (gate-combo census of failing cells) -> either close to >=99% or name the missing convention.
- [DONE 00:2x PR-SWEEP #1] see FINDINGS.
- [open] SL-G1: syzygy-lattice e-process martingale Monte Carlo (port LR rules to torch; operating-characteristic curves: kill-on-impossible, impostor late-cross; validate truth@10/impostor@112 pins first).
- [open] SCOUT #1 (see rotation).
- [open] SF-G1: subleq VM in torch (Int32Array machines, batched) -> program-space census; validate vs subleq-fabric pins.
- [open] DS-G2: change-point GPU engine, synthetic boat telemetry first (the 5-min predictor line = trail() membrane).
- [spawned by QG2] QG3: WHY are 42% landscape-trapped? Cluster stuck streams by champion basin (genome edit-distance clustering); test deeper budget (W=8, 24 gens) — do traps open with budget? Cheap on this lane.
- [spawned by QG2] QG4: budget/gens phase diagram (W x gens grid, 1024 streams/cell) — map the crossing frontier. Directly serves "cells are dedicated; routing happens between cells".
- [spawned by PR-SWEEP #1] RECEIPT-CITE: amend QG1/QG2 receipts (proposals/runs/*.md) to cite SuperInstance repos by name (weight law; see MicroMoth-quilt PR #29). Docs-only, no re-run.

## FINDINGS (append-only)
- 00:0x CONDUCTOR-0 (main): QG2 headline above. qcell-sim gained crx + receipt-anchored selftest. Vectorized lane = gathers + bmm chains; ANCHOR-VEC 2e-34.
- 00:2x PR-SWEEP #1 (conductor): 6 repos swept; only MicroMoth-quilt active. **PR #29 OPEN** — docs-only provenance: qcells lab canonical home = SuperInstance/micrograd-quilt; cite repo not local path in receipts. Clean (fail-first pins, 248/249; 1 pre-existing main-tip manifest drift, remedy already in PR #25 stack). Merged highlights: #28 exp022 train-visible crossing census (tie-break-invariant), #27 rate-not-wall + desert-extends-to-cloud, #26 tie-band-diversity replicated, #25 archive-assembly + manifest regen, #24 fitness desert at birth cloud (29/31/37). **Steals:** (a) weight-law by-name citation -> spawned RECEIPT-CITE item; (b) exp018 desert-at-birth-cloud independently corroborates QG2 structural-desert — desert is upstream of selection, now two lanes agreeing; (c) note bookkeeping discipline: my first spool edit clobbered the QG4 queue line; caught + restored same wake. Always re-read the file after structural edits.
\n- 00:45 CONDUCTOR-0 (main): PhysicalCoding + jeff recons landed; DECIDE-1 armed behind the weight download; qcell_sim crx fix (tool had been missing a gate the telemetry uses since QG1 — caught by the QG2 anchor).\n