# COMP0 — federation of dedicated micro-trunks with between-cell routing

**Pre-registered 2026-10-01 15:16 AKDT, before any COMP0 run.** Lane
COMPOSITE-0, the decomposational-growth probe. Status: scoped + fired in one
session under the 40-minute build+run budget.

## Thesis under test

> A federation of DEDICATED micro-trunks with BETWEEN-cell routing beats both
> a joint trunk and best-single at matched parameter budget.

This is the direct composition of three booked pieces:

1. **IE3 (DILUTION_CONFIRMS)** — A-joint and B-sequential shared-trunk arms
   dilute; C-split-trunk specialists hit r2_blob 0.987 / r2_direction 0.984 at
   density 32. Specialists need dedicated trunks.
2. **D1b (look-again, FULL-SCALE)** — look-again 0.8569 vs best-single
   0.6884 (+0.168). When the first reader's evidence is short-reach (low
   confidence margin), buying an independent-reach second read pays.
3. **D13d (shared-key discovery)** — correlation between cell keys finds the
   right partner at 1.0 where three reward-trained variants (Hebbian,
   confidence-weighted, REINFORCE) failed. Routing primitive = correlation,
   not reward.

Composite question: do the three compose into one harness on the D5 text
foundry — dedicated trunk per regime (IE3), correlation router between cells
(D13d), look-again escape hatch to the second-choice cell (D1b)?

## Corpus (frozen)

Reuse the D5 probe foundry artifacts on disk (`probes.jsonl`, 215 items,
seed 2718, content-addressed sha256, hash-split nibble>=12 → 149 train /
66 held-out). Two regimes by `kind`: `semantic` (paraphrase vs entity-swap)
and `counting-address` (count-word match vs mismatch). Labels: canon /
distortion (binary). **K = 2** — one micro-trunk per regime. If probes.jsonl
is absent, regenerate via `experiments.d5_probe_foundry` (seed 2718) — do not
invent a new grammar.

Featurization (frozen): word-level count BoW (lowercase, tf counts) hashed
to **D=64** dims, L2-normalized. Claim and evidence concatenated. Deterministic
sha1-based hashing (no python `hash()` salt).

## Arms (4, at matched TOTAL parameter budget)

Cell architecture: MLP D→32→1, sigmoid, BCE. Per-cell params:
64·32+32 + 32·1+1 = **2113**.

| Arm | What | Params |
|---|---|---|
| 1 JOINT | one MLP 64→64→1 trained on ALL train items | 64·64+64+64+1 = **4225** |
| 2 BEST-SINGLE | ONE cell (64→32→1) trained on ALL train items | **2113** |
| 3 FED | K=2 cells, each trained ONLY on its regime slice; correlation router picks the answering cell | 2×2113 = **4226** |
| 4 FED+LA | same cells as FED; look-again: if routed cell's confidence margin \|p−0.5\| < τ, the second-choice cell re-reads and its answer wins iff its margin is larger | 2×2113 + router 0 = **4226** |

Budget match: JOINT 4225 vs FED 4226 — matched within 1 param (0.02%),
stated here rather than hidden. Router is **parameter-free**: each trunk's
key = L2-normalized centroid of its TRAIN-slice features; routing score =
Pearson correlation between item vector and key (D13d mechanism — no reward,
no gradient). τ for look-again calibrated on TRAIN only (20th percentile of
routed-cell confidence margins on train items). No test leakage anywhere in
routing or τ.

BEST-SINGLE definition (frozen): the single micro-trunk of exactly cell size
trained on the full mixed training set — "one dedicated cell tries to be
general". Not "best specialist on its own slice" (that arm would score ~0.5
off-regime by construction and is not interesting).

## Training (frozen)

Adam lr 1e-3, BCE, batch 16, 300 epochs, fp32 on CUDA (RTX 4050, runs BESIDE
the resident 7B seat lane — tiny nets, <100 MB VRAM). INSTRUMENT-01 ramp
receipt: ≥0.6 s sustained synced matmul burn before any timed readout; wall
times are single-draw statistics.

## Seeds & stats

3 seeds: 2718, 2719, 2720 (corpus hash-split FIXED by sha256 — identical board
across seeds; seeds vary init/batching only). Report mean±std per arm on the
held-out board. Full board + per-regime sub-boards.

## Frozen gates (stated NOW, before building)

Chance baseline is COMPUTED, not assumed: majority-class accuracy on the
held-out board, reported in the result JSON.

- **G1 (federation > best-single):** mean(FED) − mean(BEST-SINGLE) ≥ **+0.05**
  accuracy on the held-out board.
- **G2 (look-again > federation):** mean(FED+LA) − mean(FED) ≥ **+0.01**.
- Secondary readout (thesis's other half, same bar): mean(FED) − mean(JOINT) ≥ +0.05.
- **Degeneracy rule:** if the across-seed std of any arm in a deciding pair is
  exactly 0.0 → that gate is INCONCLUSIVE, never PASS (verdict-lattice
  DEGENERATE class). Truncated/incomplete 3-seed output → INCONCLUSIVE, never
  PASS (TRUNC-B).
- **Verdict:** KEEP iff G1 AND G2 PASS. G1 PASS + G2 fail → report as
  SPLIT_KEEP_GATE1 (honest partial). Neither → KILL/INCONCLUSIVE per bands.

## GPU protocol

guard.py Guard, task_id `COMP0-federation`, receipt_dir `results/comp0/guard`.
Preflight: if free VRAM < 1 GB, retry once after 60 s; refused twice → book
NOT-RUN + VOID receipt, do not force. G7 watt receipt required — no receipt →
run VOID. Keeper commits; this lane does not commit.

## Artifacts

`results/comp0/` — results JSON (per-seed, per-arm, per-board, router audit,
ramp receipt, guard summary), guard receipt. RESULTS.md entry + QUEUE.md line.
