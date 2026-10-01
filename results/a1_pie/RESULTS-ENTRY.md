# A1-PIE — pie-minimax closure: does a nonlinear local rule close the minimax gap?

- lane: **A1-PIE** (`quilt-gpu-lab`; worklist item **A1** in `fleet-triage/docs/RTX4050-WORKLIST.md`)
- date: 2026-10-01 · device: `cuda:0 (RTX 4050 Laptop, 6 GB)` · torch 2.14.0+cu126
- seed **2718** everywhere · reference clone `~/projects/pie-minimax` **read-only**
- pre-registration: `results/a1_pie/PREREG.md` (written **before** training, same dir)
- **not committed — keeper folds. NOT appended to RESULTS.md (parallel lanes live).**

## 0. VERDICT (two lines, no goalpost migration)

- **Frozen gate on the PRIMARY spec** (9→64→9, lr 1e-3, batch 1024, **20 epochs**): **INCONCLUSIVE** —
  `overall = 0.3502` sits *inside* the predicted `[0.25, 0.40]`, **but** `MLP_composed (0.5714)` is
  **not <** the linear reference's composed (`0.2857`–`0.3571`), so the CONFIRM branch fails.
- **Declared CONVERGENCE CONTROL** (pre-registered in PREREG §3 *before* running): **KILL-of-prediction** —
  the same net run to plateau reaches `overall = 0.9494` (5-fold board-disjoint `0.9392 ± 0.0094`),
  `composed = 0.9643` (CV `0.9790 ± 0.0092`). **Nonlinearity does NOT "close only a little" (0.25–0.40),
  and it does NOT collapse on the ≥2-win COMPOSED partition. Their prediction is falsified.**

The 20-epoch spec is **underfit** (train top-1 fit `0.3998`, train loss `1.57` vs plateau `0.9881`/`0.135`).
The frozen INCONCLUSIVE *is* the finding: a 60-step budget measures the optimiser, not capacity —
the exact confound the repo warns about ("a result that flips with learning rate is a measurement of
my optimiser"). The pre-registered control supplies the honest number.

## 1. Recon corrections (before any number is trusted)

| claim | what the data says |
|---|---|
| "180,361 exact states" | **180,361 is the PATH-ROW count** (the walk re-visits each board once per move order → ~75× duplication). **2,423 distinct our-to-move boards.** Verified: `len(enumerate_reachable())=180361`, `len(set(boards))=2423`. |
| README "CORRECTION": *180,361 is impossible, `3⁹=19,683`* | **that correction is itself a miscorrection** — it misreads a path-row count as a distinct-state count. Both counts are recorded with every number. |
| "≥2-simultaneous-win states" | **two non-equivalent partitions exist.** `≥2 immediate WINNING MOVES` = **320** boards; the repo `ceiling2` `threat_count ≥ 2` = **1230** boards; they agree on **1513/2423**. Both are reported for every arm. |

**Instrument bug found and booked (fail loud).** The first split attempt used raw
`fnv1a64(board) % 10`, which **returned an empty test set**: FNV-1a-64 low bits are weak, every
3×3 board hashes **odd**, so `mod 10` only ever hits `{1,3,5,7,9}`. That attempt **VOIDed**
(`g7-wr-a1-pie-closure-1790891323.json`, 0 J, no model trained) before any number existed. Fixed to
the **high 32 bits** (validated bucket counts 217–261 over 2,423 boards).

## 2. Protocol (frozen, PREREG §2–§3)

- labels **exact + set-valued** (`M[r,m]=1 ⇔ m∈optimal(board)`), loss `−log Σ_{m∈Opt} softmax(z)_m`
- **PRIMARY split:** board-disjoint **FNV-1a-64 HIGH-32 mod 10**, bucket 0 = test → **train 2186 / test 237** (28 composed-imm, 209 simple)
- **variance:** 5-fold board-disjoint CV (std across **data folds**, not seeds — the repo showed seed std ≡ 0)
- arms: MLP `9→64→9` ReLU (1225 params) and **matched** linear `9→9` (81 params) under the *same* optimiser/split;
  plus their own `linear_expert` as a fair, well-fit linear reference
- chance = `mean(|optimal| / |empty|)`; floor = random empty cell

## 3. Results — board-disjoint test (n=237 boards), chance overall **0.5566**

| arm | overall | COMPOSED (≥2 wins, n=28) | SIMPLE | COMPOSED (threat_count≥2) | train-fit |
|---|---|---|---|---|---|
| MLP 9-64-9, lr1e-3, **20 ep** (frozen PRIMARY) | **0.3502** | 0.5714 | 0.3206 | 0.3226 | 0.3998 |
| LINEAR 9×9 matched, 20 ep | 0.2363 | 0.3571 | 0.2201 | 0.2339 | 0.2534 |
| MLP 9-64-9, lr1e-3, **plateau** (control) | **0.9494** | **0.9643** | 0.9474 | 0.9677 | 0.9881 |
| LINEAR 9×9 matched, plateau | 0.2954 | 0.1429 | 0.3158 | 0.1855 | 0.3532 |
| MLP 9-64-9, lr1e-2, plateau (supp.) | 0.9789 | 0.9643 | 0.9809 | 0.9758 | 1.0000 |
| `linear_expert` (their code) on this test set | 0.2911 | 0.2857 | 0.2919 | 0.2177 | — |

**5-fold board-disjoint CV (variance is the point — rule 2):**

| arm | top-1 mean ± std | COMPOSED (≥2 wins) | COMPOSED (threat_count≥2) |
|---|---|---|---|
| MLP 20 ep | 0.3443 ± 0.0195 | 0.3711 ± 0.0469 | 0.2621 ± 0.0129 |
| LINEAR 20 ep | 0.2068 ± 0.0252 | 0.2514 ± 0.0302 | 0.1660 ± 0.0243 |
| **MLP plateau** | **0.9392 ± 0.0094** | **0.9790 ± 0.0092** | **0.9343 ± 0.0099** |

`std ≠ 0` everywhere → the result is a measurement, not a degeneracy. Identical `overall = 0.3502`
across three independent PASS runs → reproducibility receipt.

**Headroom fills** (fraction of the gap from chance to 1.0 closed; universe chance: all 0.5865,
comp-imm 0.7875, simp-imm 0.5559, comp-thr 0.6585, simp-thr 0.5122) — *derived post-hoc, CPU, same corpus*:

| arm | comp-imm | simp-imm | comp-thr | simp-thr |
|---|---|---|---|---|
| MLP plateau | 0.832 | 0.882 | 0.905 | 0.855 |
| MLP 20 ep | −1.02 | −0.53 | −0.98 | −0.27 |
| LINEAR matched | ≤ 0 | ≤ −0.5 | ≤ 0 | ≤ −0.2 |

**The partitioned prediction is false for the MLP:** normalised, its COMPOSED fills (0.83–0.91) are
**indistinguishable from**—and slightly *above*—its SIMPLE fills. The composition penalty **is real
for the linear/additive arm** (linear plateau: comp 0.143 vs simp 0.316; `linear_expert`: comp-thr
0.218 vs simp-thr 0.372), which is exactly the repo's own CEILING finding.

**Scale:** their decision-tree ceiling `0.7879` (their single-move-label protocol) and exact solver
`1.0000`. The MLP at `0.9494` **does not exceed the solver** and is not a leak — labels are the exact
computation and `top-1 ≤ 1.0` trivially; the tree's lower number is the repo's own documented
tie-break label problem plus depth. Cross-lane corroboration: the reference clone's receipt
(`receipts/pie_minimax_closure.json`, a prior attempt) got `0.9996` on a leaky same-corpus split and
`0.9798` on 5-fold held-out boards — consistent with my `0.9392–0.9494`.

## 4. What this means (both halves, honestly)

1. **The linear half of their story survives.** A sum of 81 local votes cannot represent a *count over
   separate lines*: the linear arms collapse on COMPOSED (0.14–0.36) relative to SIMPLE. `0.1807`
   was always "a *linear* map is bad at minimax".
2. **The nonlinear half is falsified.** "Local voting can't count threats" is a claim about
   **additivity**, not about locality. A 1,225-param ReLU net — still a purely *local* board→scores
   rule with no search and no tree — absorbs minimax composition to **~0.94 board-disjoint**, with
   **no COMPOSED collapse**. The proposed mechanism does not survive as a general local-rule limit.
3. **Transferable lesson (the repo's own §0 rules earn their keep):** an accuracy measured under a
   fixed, tiny step budget is a *statement about the optimiser*. The frozen 0.25–0.40 band was
   reachable at 60 steps and abandoned at 1,200 — so any "nonlinearity doesn't help/helps only a
   little" reading of a short run is unsafe, and a **pre-registered convergence control is the
   difference between a finding and an artefact**.

## 5. Receipts / energy / artefacts

- G7: **`results/a1_pie/g7-wr-a1-pie-closure-1790891506.json`** — `g7-watt-receipt@1`, gate **PASS**,
  schema validator exit 0 (also 3 earlier PASS/1 VOID in `ledger.jsonl`).
- energy: final run **106.5 J = 0.0296 Wh**; **all attempts total 0.386 Wh** (22.94 GPU-seconds),
  measured `power.draw` (mean 23.8 W) — `source: "measured"`, idle floor not subtracted.
- artifacts (all in `results/a1_pie/`): `PREREG.md`, `a1_pie_closure.py` (orchestrator + worker),
  `a1_pie_metrics.json` (all numbers above), `a1_pie_model.pt` (**16 KB** — MLP-20ep, MLP-plateau,
  LINEAR-20ep state dicts), `guard_summary.json`, `ledger.jsonl`, 5× `g7-wr-*.json`.
- INSTRUMENT-01 ramp receipt: 0.604 s sustained synced CUDA load before any timing.
- **VOID-of-record:** the empty-test-set attempt (`g7-wr-…-1790891323.json`) is kept deliberately —
  a fail-loud instrument bug, not hidden.
