# A2-ga4444-4x4 — 4×4 composition + capacity: does A1's "nonlinear absorbs composition" scale?

- lane: **A2-HARVEST** (`quilt-gpu-lab`; worklist item **A2**, `fleet-triage/docs/RTX4050-WORKLIST.md`)
- date: 2026-10-01 · device: `cuda:0` (RTX 4050 Laptop, 6 GB) · torch 2.14.0+cu126
- seed **2718** everywhere · clone `/tmp/ga4444` **read-only** · **one smoke arm** (MLP) + its frozen matched contrast (LINEAR)
- pre-registration: `proposals/runs/A2-ga4444-4x4.md` (written **before** the measured run)
- **not committed — keeper folds.**

## 0. VERDICT (no goalpost migration)

- **Frozen gate → INCONCLUSIVE.** Rule 2 fires: the MLP sits at the **ceiling 1.0000 with `std == 0.0`** on
  COMPOSED-B (5/5 folds), so no PASS-class verdict is bookable. Recorded, not hidden.
- **Declared secondary reading (frozen `Δ_linear` row, non-degenerate) → BREAKS.** The
  **linear/additive arm shows NO composition penalty at 4×4**: `Δ_linear = top1_SIMPLE-B − top1_COMPOSED-B =
  0.8110 − 0.9872 = **−0.1762**` (it is *better* on COMPOSED, `std ≠ 0` on both columns). **A1's "linear
  collapses on COMPOSED" does NOT carry one rung up.** This confirms `ga4444/PARTITION-44.md` §4's
  wave-63 pre-finding, now with a complete ground-truth dataset and a matched optimiser.

**Why the two readings coexist, and the finding underneath both.** COMPOSED-B's **computed chance is 0.9696**:
on a 4×4 board with ≥2 *immediate winning drops*, a uniformly random legal move is already optimal 97% of the
time. The class is **near-degenerate by construction** — it cannot discriminate local-voting from composition,
at either rung (3×3: `n=22`, all trivial; 4×4: floor 0.97). The composition-collapse test has **no executable
positive instance** at 3×3 or 4×4 as sampled. That is the real result of this lane.

## 1. Recon corrections (found before any measured number)

| claim in the repo | what the data says |
|---|---|
| `gt4444_ground_truth.txt` = 3,338 positions, the complete tree | **the C `walk()` is an INCOMPLETE walk** — `if (has_won(pos|mv, m2)) return;` sits inside the column loop and `return` prunes the remaining columns (should be `continue`). Its **values** are exact; its **enumeration** is not. The repo's own `verify_maxmin.py` reports **161,029 reachable states**; this lane's complete non-terminal BFS is **139,625** (139,625 + 21,404 terminal = 161,029 — exact agreement). |
| "4×4 four-in-a-row" (one game) | the repo holds **two**: `ga4444.py` = **free placement** (`legal_moves` allows gaps) — measured reachable non-terminal graph **> 8×10⁶** states, labels capped at `MAX_PLY=9`; `gt4444.c` = **gravity**. Not the same game, not the same values. |
| **scope (frozen)** | this lane = **gravity**, built its **own complete enumeration** (66,297 our-turn non-terminal boards). Free placement is **out of scope** (>8M) — no number here is a free-placement result. |

## 2. Data + provenance

- complete our-turn (p0-to-move, non-terminal) gravity set, **no sampling**:
  **66,297 boards**, `dataset_fnv1a64 = 0x98219e9d0dd0d382`, gen **3.5 s** (5 parallel list-form shard subprocesses).
- ply histogram `{0:1, 2:16, 4:160, 6:1128, 8:5036, 10:14352, 12:24710, 14:20894}`;
  **multi-optimal 47.8%** (set-valued labels matter — A1's lesson carries).
- labels **exact + set-valued**, memoized full-depth negamax written here. **Differential control (rule 5):**
  the repo's independent C solver `gt4444 --probe` on 500 sampled boards → **500/500, 0 disagreements**;
  `verify_maxmin.py` (plain max-min, different bit layout) → **200/200**. `control.json`.

## 3. Results — 5-fold board-disjoint CV (FNV-1a-64 **high-32** mod 5), seed 2718, = **mean ± std over folds**

chance is **computed per fold per partition** (`mean(|opt|/|legal|)`), never assumed:

| arm | overall | COMPOSED-B (≥2 own imm. wins) | SIMPLE-B | COMPOSED-A (≥2 own 3-threat lines) | SIMPLE-A |
|---|---|---|---|---|---|
| **MLP 16→64→16**, lr 1e-3, 120 ep (SMOKE) | **0.9712 ± 0.0036** | **1.0000 ± 0.0000** | 0.9708 ± 0.0037 | 0.9791 ± 0.0037 | 0.9663 ± 0.0037 |
| **LINEAR 16→16**, matched | **0.8130 ± 0.0021** | **0.9872 ± 0.0109** | 0.8110 ± 0.0022 | 0.8191 ± 0.0034 | 0.8091 ± 0.0029 |
| chance (computed) | 0.7698 | **0.9696** | 0.7673 | 0.7660 | 0.7721 |

Test-fold sizes 13,034 / 13,245 / 13,324 / 13,558 / 13,136; COMPOSED-B n per fold 159 / 146 / 149 / 166 / 143
(**total 763 — above the n≥50 power line**; PARTITION-44's LOW_POWER caveat does not apply).

`Δ_linear = 0.8110 − 0.9872 = **−0.1762**` · `Δ_mlp = 0.9708 − 1.0000 = **−0.0292**`.

**Normalised headroom filled** `(acc − chance)/(1 − chance)`:

| arm | SIMPLE-B | COMPOSED-B |
|---|---|---|
| MLP | 0.875 | **1.000** (ceiling) |
| LINEAR | 0.188 | **0.579** |

Both arms fill **more** of the COMPOSED-B headroom than of SIMPLE-B — the opposite of a collapse. But the
COMPOSED-B headroom is only `1 − 0.9696 = 0.0304` wide, so "0.579 vs 1.000" is a statement about a 3-point band.

## 4. What this means (both halves)

1. **A1's linear half does not replicate at 4×4** — with complete ground truth, an additive map is *penalised
   less on COMPOSED than on SIMPLE*. Recorded as a **correction carried up**, matching PARTITION-44.
2. **Neither does the test.** The predicted "accuracy collapses on COMPOSED" is unfalsifiable as constructed:
   the floor on that class is 0.97. The pre-registered contrast is **not executable** at 4×4 natural-walk
   sampling — the same defect PARTITION-44 found at 3×3 (`n=22`, trivial). Fixed by design, not by more data.
3. **Nonlinearity still helps overall** (MLP 0.9712 vs LINEAR 0.8130, +0.158, non-degenerate) — but that is a
   capacity statement, not a composition statement, and A1 had already shown it.

## 5. Follow-up the full scale needs (in order)

1. **Generated double-threat boards** (PARTITION-44 §4's own recommendation): construct positions with ≥2 open
   immediate wins **by design**, matched against single-threat controls at **equal stone count and equal |empty|** —
   the only design that makes COMPOSED-B's chance well below 1. This lane should have pre-registered THAT.
2. **The convergence-to-plateau control** (A1's lesson) and a **capacity sweep** (hidden ∈ {0,32,64,128,256},
   epochs to plateau) — today is one 120-epoch smoke configuration only.
3. **Multi-seed grid** (≥5) over the arms, and the **DEF-A/DEF-C cross-partition sweep**.
4. **Free-placement game** (`ga4444.py`), which needs the >8M state space — sharded data-gen + checkpointing, or
   the horizon-capped labels honestly declared at `MAX_PLY`.
5. A **`return`→`continue` fix (or a note) upstream in `gt4444.c`'s export walk**, if the repo wants a genuinely
   complete export.

## 6. Receipts / energy / artifacts — all in `results/a2_ga4444/`

- G7: **`g7-wr-a2-ga4444-4x4-1790893502.json`** — `g7-watt-receipt@1`, gate **PASS**, schema validator exit 0
  (`ledger.jsonl`). Preflight attempt 1 clean (free VRAM 1820 MiB ≥ 1024 floor, 68 °C).
- energy: **13,917.53 J = 3.866 Wh**, **213.73 GPU-seconds**, `source: "measured"` (mean 46.5 W across the window,
  **includes** the resident 7B ollama seat's share — co-tenancy NOT subtracted; idle floor not subtracted).
- artifacts: `a2_ga4444.py` (game + solver + sharded data-gen + arms), `run_a2.py` (guard driver + gate),
  `dataset.jsonl` (66,297 boards, 11.9 MB), `dataset_summary.json`, `control.json` (500/500 + 200/200),
  `smoke_mlp_metrics.json`, `smoke_linear_metrics.json`, `gate.json`, `shards/`, `guard_summary.json`, `ledger.jsonl`.
- INSTRUMENT note: no timing claim is made; the receipt is a watt/energy receipt only.
