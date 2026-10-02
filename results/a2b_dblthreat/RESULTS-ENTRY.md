# A2B-DBLTHREAT — designed double-threat boards: is the composition contrast now executable?

- lane: **A2B-DBLTHREAT** (`quilt-gpu-lab`) — the **A2-HARVEST booked fix #1** (A2's own §5.1:
  "generated double-threat boards … the only design that makes COMPOSED-B's chance well below 1")
- date: 2026-10-01 · **CPU only** (`torch` CPU tensors, **no CUDA call**) · **0 Wh** · seed **2718** everywhere
- pre-registration: `results/a2b_dblthreat/PREREG.md` (frozen **before** this lane's measured run)
- reads (read-only, disk is truth): `results/a2_ga4444/dataset.jsonl` (66,297 our-turn gravity boards,
  exact set-valued labels, `dataset_fnv1a64 = 0x98219e9d0dd0d382`) and A2's arms
  (`smoke_mlp_metrics.json`, `smoke_linear_metrics.json`)
- **not committed — keeper folds.**

## 0. VERDICT (two lines, no goalpost migration)

- **G-A2b1 (frozen, literal formula) → FAIL.** The paired differential
  `S̄ = mean[(MLP_D* − MLP_S) − (LIN_D* − LIN_S)] = **−0.1327**` (bootstrap CI95
  `[−0.2041, −0.0612]`, **excludes 0**; per-fold std `0.0841` ≠ 0). The MLP's composed−single gap
  (**+0.0357**) does **not** exceed the linear's (**+0.1684**) — the reverse. Dual declared reading
  (A1's convention, `Δ_LIN − Δ_MLP`): **+0.1327**, CI `[0.0612, 0.2041]` — the differential is real and
  large, but it is an **advantage** differential, **not a penalty**: **no arm is worse on COMPOSED than on
  its matched single sibling.**
- **G-A2b2 (the set has signal) → PASS.** `LINEAR-full`: `D* acc 0.9490 ± 0.0370` vs chance **0.8163**
  (Δ **+0.1327**, CI `[0.0969, 0.1692]` excludes 0, per-fold std ≠ 0); on the must-convert core `D**`
  (88): `0.8864 ± 0.0587` vs chance **0.5909** (Δ **+0.2955**, CI `[0.2254, 0.3580]`). **The designed set
  is executable — A2's emptiness is fixed by design.** (Caveat booked below: the `MLP-full` column is at
  the ceiling 1.0000 with `std == 0` on every designed partition, so the signal gate rests on the linear
  arm alone.)

**The sentence this books:** *designed double-threat boards cure A2's degenerate test — a designed set
carries real signal (linear 0.949 vs chance 0.816 on D*, 0.886 vs 0.591 on the 88-board core) — but the
**composition-collapse construct still does not reproduce**: composition is an **advantage** for both arms
(MLP +0.036, LINEAR +0.168 over matched single-task siblings), so the frozen G-A2b1 fails as written even
though the MLP-vs-linear architecture differential it targets is real (+0.133, CI excl 0, std 0.084). The
construct is now **measurable and measurably not a collapse**. No third strike is warranted on emptiness;
the second strike is on the **collapse sign**, not on the data.*

## 1. Recon (before any measured number of this lane) — three corrections

| finding | number |
|---|---|
| mission's literal rule `D` = ≥2 immediate winning threats for the mover (A2 `imm_wins≥2`) | **763** (strata: stacked-column **6** · split-column **623** · cross-quadrant **134**) |
| …of which chance = 1.000 (every legal move optimal) | **675 / 763 = 88.4%** → mean chance **0.9528** (reproduces A2's 0.9696-class degeneracy) |
| the discriminator: **chance < 1 ⟺ the opponent also has ≥1 immediate win** | exact coincidence, **88/88** |
| **D\*** = ≥2 mover threats **AND** ≥1 opponent threat ("convert or lose") | **196** (stacked 6 · split 190 · cross-quadrant **0**) |
| **D\*\*** = `D*` with chance < 1 | **88**, chance ∈ {0.50, 0.67}, mean **0.5909** |
| matched single-threat controls `S` (exactly 1 mover threat, matched on ply / n_legal / opp-flag) | **196** of 13,762 available, mean chance **0.4082** |

- **R1 (structural law, booked).** Under gravity each column has exactly one legal drop ⇒ a **same-column
  double threat is impossible**; the gravity analogue of "stacked-column" is a pair of **vertical** threat
  lines (observed n=6). The mission's stratum of that name is therefore **n=6, not a large class**.
- **R2 (structural law, booked — the real blocker).** ≥2 immediate wins for the mover need **≥6 own stones**
  (two 3-segments sharing ≤1 cell) ⇒ **ply ≥ 12 of 16** ⇒ **≤4 empty cells** ⇒ chance ≥ 2/4 = **0.5**, and
  `|opt| ≡ 2` on every `D*` board. **The 4×4-gravity composition class is structurally late-game**: a
  raw-accuracy "composition penalty" (COMPOSED below SIMPLE) is bounded by the chance gap, because the
  composed board carries an *extra winning move* by construction. This — not sampling — is why A2's
  contrast was empty, and why a designed set still cannot host a *collapse*.
- **R3 (target, fail loud).** The mission target **200–500 items** is met by `D` (763, complete class) and
  `D*` (196); it is **unreachable for `D**` = 88** — the complete gravity graph contains exactly 88 such
  our-turn positions; no sampling can exceed a complete class. Also: natural walk **does** produce the
  discriminant class (88, and 196 under the weaker opponent-threat flag), contrary to "never" — it is
  simply **0.13–0.30%** of the corpus.

## 2. Construction rules (verbatim — as pre-registered)

- **Threat / probe:** for a board with mover `m` and occupancy `occ`, enumerate **every legal drop**
  (gravity: lowest empty cell of a non-full column) — no search; a drop `c` is a **threat** iff placing `m`
  at `c` completes a 4-in-line for `m` **immediately**. `n_threats`, `n_opp_threats` = counts.
- **Strata (verbatim):** from the two winning threat cells `(r1,c1),(r2,c2)` and their line orientations —
  `stacked-column` = both lines vertical; `cross-quadrant` = not both vertical and row-half differs **and**
  column-half differs; `split-column` = everything else.
- **`D`** = `{n_threats ≥ 2}` on A2's 66,297. **`D*`** = `D ∩ {n_opp_threats ≥ 1}`.
  **`D**`** = `D* ∩ {chance < 1}`. **`S`** = `{n_threats = 1}`, greedy pair-match to `D*` on
  **(ply, n_legal, opp-flag)**, without replacement, seeded 2718 (equal stone count, equal `|empty|`,
  equal legal-move count).
- **Chance** = `mean_board(|Opt| / n_legal)`, **computed**, never assumed.

## 3. Arms (A2's exact arms at their booked checkpoints; read from `results/a2_ga4444/`)

`MLP` = `Linear(16,64)→ReLU→Linear(64,4)` · `LINEAR` = `Linear(16,4)` · Adam lr 1e-3, batch 1024,
**120 epochs**, set-valued loss, seed 2718, 5-fold board-disjoint CV (`(fnv1a64>>32) mod 5`).

- `MLP-full` / `LIN-full` — trained on the whole 66,297 corpus (**PRIMARY**, A2's booked configuration);
  out-of-fold evaluated on `D*`, `D**`, `S`, `D`, and A2's original partitions (**continuity**).
- `MLP-design` / `LIN-design` — identical config trained only on `D* ∪ S` (392 rows) (**SECONDARY**).

## 4. Results — out-of-fold top-1 (mean over folds ± std), chance computed per set

| arm | D* (n=196, ch .8163) | D** (n=88, ch .5909) | S (n=196, ch .4082) | D (n=763, ch .9528) |
|---|---|---|---|---|
| `MLP-full` | **1.0000 ± 0.0000** | **1.0000 ± 0.0000** | 0.9643 ± 0.0506 | **1.0000 ± 0.0000** |
| `LINEAR-full` | **0.9490 ± 0.0370** | **0.8864 ± 0.0587** | 0.7806 ± 0.0560 | 0.9869 ± 0.0109 |
| `MLP-design` (392 rows) | 0.9898 ± 0.0109 | — | 0.8980 ± 0.0488 | — |
| `LINEAR-design` (392 rows) | 0.9490 ± 0.0342 | — | 0.7959 ± 0.0227 | — |

**Headroom filled** `(acc − chance)/(1 − chance)`: `MLP-full` D* **1.000** / S 0.940 · `LINEAR-full`
D* **0.722** / S 0.629 · `MLP-design` D* 0.945 / S 0.828 · `LINEAR-design` D* 0.722 / S 0.655.
**Per stratum on `D*`:** stacked-column (n=6, chance 0.500) MLP 1.000, LINEAR 1.000; split-column
(n=190, chance 0.8263) MLP 1.000, LINEAR 0.9474.

## 5. Gates (frozen; no goalpost migration)

| gate | result |
|---|---|
| **G-A2b1** `S̄ > 0.05` AND CI excludes 0 | **FAIL** — `S̄ = −0.1327`, CI `[−0.2041, −0.0612]`, std 0.0841, n_pairs 196. (Secondary `MLP-design` arm: `S̄ = −0.0612`, CI `[−0.1276, +0.0102]` — CI includes 0.) **Dual declared reading (A1 direction): +0.1327, CI excl 0.** |
| **G-A2b2** ∃ arm with `acc − chance ≥ 0.05`, CI excl 0 | **PASS** — `LINEAR-full` on `D*` Δ **+0.1327** (`[0.0969, 0.1692]`, std 0.0370) and on `D**` Δ **+0.2955** (`[0.2254, 0.3580]`, std 0.0587); `MLP-design` also passes (`D*` Δ +0.1735) with std ≠ 0. `MLP-full` is at the **ceiling with `std == 0`** on every designed partition — recorded, not hidden (its own signal is unmeasurable; the gate stands on the arms with non-zero fold variance). |

## 6. What it means (both halves, honestly)

1. **The design fix works where A2's data failed.** A designed double-threat set **has signal** (G-A2b2
   PASS) and, for the linear arm, a **non-degenerate reading** at both the 196-board class and the 88-board
   must-convert core — the first time this construct has had an executable positive instance at any rung.
2. **The collapse does not appear.** Neither arm is penalised on composed; both improve over matched
   single-task siblings (MLP +0.036, LINEAR +0.168). The architecture differential the gate targets is
   **real and large** (+0.133, CI excl 0) — the MLP fills 100% of `D*` headroom, the linear arm 72% — but it
   is an **advantage** differential, so A1's "linear collapses on COMPOSED" **still does not replicate** at
   4×4, now on a *designed* set rather than a sampled one. A1's linear half takes its second, designed-set
   falsification; the residual nonlinear help is a **capacity** statement (A2's reading), not a composition one.
3. **Why — the structural law (R2).** A double threat at 4×4 gravity is a **late-game** object (≥6 stones,
   ≤4 empties, `|opt| ≥ 2`). Composition there is not harder for any local rule: it is *easier*, because it
   carries an extra winning move. The construct needs a rung where a double threat does not force
   near-terminality (free placement, or 5×5/Connect-4 where two threats need ≈8 of 25 cells).

## 7. Controls / receipts / house laws

- **Continuity check (CPU re-run of A2's booked config, ±0.02 tolerance): PASS.** `MLP-full` overall
  **0.9723 ± 0.0043** (A2 booked 0.9712 ± 0.0036; Δ +0.0011) · COMPOSED_B **1.0000** (1.0000) · SIMPLE_B
  0.9720 (0.9708) · COMPOSED_A 0.9804 (0.9791) · SIMPLE_A 0.9673 (0.9663). `LINEAR-full` overall
  **0.8130 ± 0.0021** (**exact** match) · COMPOSED_B **0.9869** (0.9872) · SIMPLE_B **0.8110** (0.8110);
  `Δ_linear = −0.1759` vs A2's booked −0.1762. The harness reproduces the booked arms.
- **Solver ground truth (rule 5, different path):** the repo's independent C solver `gt4444 --probe`
  (list-form subprocess, never `shell=True`) re-solved a 100-board sample of the designed corpus —
  **100/100 agreement, 0 disagreements**. All other labels are the exact set-valued labels in the A2 dataset.
- artifacts (all in `results/a2b_dblthreat/`): `PREREG.md`, `a2b_dblthreat.py` (corpus + arms + gates),
  `a2b_metrics.json` (all numbers above), `design.jsonl` (the constructed set: D + D* + D** + matched S),
  `analyze_geom.py`, `analyze_opp.py`, `analyze_recon3.py` (recon), `run_a2b.log`.
- **Energy:** CPU-only, **no CUDA call → 0 Wh**; no G7 receipt is issued for a 0 J run (recorded as such).
  wall 125.9 s (2 × full-corpus 5-fold × 120-epoch arms + 2 × design arms).
- seed 2718 · fail loud · `std == 0 → INCONCLUSIVE, never PASS` (applied to the `MLP-full` column) ·
  no `shell=True` · no commit · other lanes' lines untouched.
