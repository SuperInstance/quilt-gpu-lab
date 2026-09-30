# ST3 — calibrated noul cell on frozen features (pre-registration)

**Status: DRAFT-STAGED** at `~/.openclaw/workspace/staging/st3/`. Copy into
`quilt-gpu-lab/proposals/runs/ST3-calibrated-noul.md` and commit+push BEFORE
firing (see `HANDOFF.md`). Never retro-edit after fire — amendments get their
own committed diff before re-fire.

**Lineage:** ST1 (KILL — LR 3e-4 collapsed head to uniform prior, booked
f7edadb/c530f54) → ST1v2 (same gates, lr 2e-5, in flight at staging time)
→ **ST3 (this): calibration + selectivity become the pre-registered object.**

**Directives served:** Casey 10:56 (PoC training), 11:35 (new experiments +
GPU hot), 11:44 (go further), 12:25 (study fleet pushes → push the technology
with experimental development).

## Question
Can a head trained on **frozen** encoder features produce a **calibrated**,
**selective** validity judgment (noul-style graded 0..1) over quilt receipts —
and do calibration and abstention hold under distribution shift, not just
discrimination? ST1 measured discrimination (AUC) only and bolted on a post-hoc
abstain threshold that went hollow under collapse. ST3 makes the score the
prey: **a judgment that doesn't conserve evidence isn't a judgment** (proper
scoring rules; the conservation paper dH/dt ≤ 0 lens).

## Design — every choice is a mechanism mined from 24h of fleet pushes
1. **Frozen features, head-only training** (jeff recon, `proposals/jeff-recon-2026-09-30.md`:
   decision readouts are linear probes — the unlock is that labels come from our
   exact simulators). Encoder: all-MiniLM-L6-v2 **frozen**, embeddings precomputed
   once per seed. Capacity ladder: linear (PRIMARY, gated) + 1×128 MLP (reported,
   not gated). Plain torch loop — **no TrainingArguments** (transformers 5.17
   warmup trap, ST1v2 lesson).
2. **Calibration gates** (proper scoring rules): post-hoc temperature scaling on
   val (disjoint from test); test ECE ≤ 0.05 AND test Brier ≤ 0.7 × base-rate
   Brier.
3. **Selective prediction** (laya gate-presence semantics + canons "read the
   distribution, never the argmax"): full risk–coverage curve in the receipt;
   gates at fixed operating points — risk ≤ 0.10 @ coverage ≥ 0.90 and
   risk ≤ 0.15 @ coverage ≥ 0.95.
4. **Non-circular OOD abstention** (kept from ST1): 2 of 6 corruption ops held
   out of training = OOD set, split A/B — abstain threshold = p90 max-prob on
   half A, evaluated on disjoint half B: abstain ≥ 0.90 on OOD-B AND
   false-abstain ≤ 0.20 on in-dist test.
5. **Discriminating control arm** (QC-JEV doctrine: "every retrain ships a
   discriminating control in its own receipt"): same pipeline, **shuffled
   labels** → must land auc ∈ [0.45, 0.55]. If the control "wins," the harness
   is leaky — ST1's KILL suspect list made structural. Control failure ⇒ STOP,
   fix harness, no model interpretation.
6. **Real-receipt gate** (kept from ST1): ≥ 10 real `results/*/results.json`
   receipts × held-out corruptions (value_swap real-only); real_auc ≥ 0.80,
   honest_fpr ≤ 0.10 (same definition as ST1's booking — align at wire-up).
7. **LR sanity** (ST1 lesson): head-only Adam 1e-3, early-stop on val NLL,
   ≤ 20 epochs on 8000×384 embeddings. Seconds-to-minutes per seed.
8. **zeroclaw doctrine:** adaptation metrics registered before adapting — all
   gates below are frozen NOW.

## Gates (frozen; KEEP requires ALL on the primary linear arm, mean over 5 seeds 6611–6615)
- **G1** syn_auc ≥ 0.95
- **G2** real_auc ≥ 0.80 AND honest_fpr ≤ 0.10 (≥ 10 real receipts else fail-loud)
- **G3** test ECE ≤ 0.05 AND test Brier ≤ 0.7 × base-rate Brier (post-TS)
- **G4** risk ≤ 0.10 @ cov ≥ 0.90 AND risk ≤ 0.15 @ cov ≥ 0.95
- **G5** OOD abstain ≥ 0.90 (half B) AND false-abstain ≤ 0.20 (in-dist)
- **G6** control arm (shuffled labels) auc ∈ [0.45, 0.55]

## Pre-registered KILL interpretation (no post-hoc rescue)
- G1/G2 fail → features carry no validity signal ⇒ jeff-features arm (below)
  becomes primary candidate; corpus/harness survive.
- G3 fails alone → discrimination WITHOUT calibration ⇒ still a WIN for the
  router lane: route raw scores through a calibrator; pre-approved amendment =
  add Platt/isotonic (commit before re-fire).
- G4/G5 fail alone → threshold selection wrong ⇒ sweep operating points on
  VAL only, never test; re-fire as amendment.
- G6 fails → harness leak ⇒ STOP. Fix harness. This control arm exists to
  catch exactly what ST1's post-mortem suspected.

## Arm 2 (reported, NOT gated): jeff last-hidden-state features
If `/home/eileen/scratch/external/jeff-checkpoints/jeff-0.8b` holds complete
weights (model.safetensors non-empty), extract last hidden states (1024-d,
bf16, GPU) for the same receipts and fit the same heads. This tests the REAL
jeff substrate. Numbers booked as observation; DECIDE-1's reader ladder remains
the jeff-native evaluation.

## Protocol
1. Wire `load_corpus()` in `st3_calibrated_noul.py` to ST1's generator
   (self-diagnosing fail-loud import — one-line fix at smoke time). Keep
   corpus/ops IDENTICAL to ST1: 8000 synthetic, 6 corruption ops, dual render
   styles, real receipts from `results/*/results.json`.
2. Copy script → `quilt-gpu-lab/experiments/st3_calibrated_noul.py`, this file
   → `proposals/runs/ST3-calibrated-noul.md`. **`git add` BOTH PATHS
   EXPLICITLY (never -A).** Commit "ST3 pre-registration (calibrated noul,
   frozen features)" + push.
3. `--smoke` on GPU: 400 receipts, 1 seed. Asserts: toy-calibration selftest
   (ECE < 0.05 on a known-calibrated synthetic), control-arm divergence,
   shapes, JSON schema round-trip.
4. Full fire (background session): 5 seeds × {linear, mlp128, control-shuffled,
   jeff-arm-if-available}. Out: `results/st3_calibrated_noul/results.json`
   (schema `st3-calibrated-noul/v1`: per-seed + mean metrics, gates, verdict,
   full risk–coverage curves, threshold echoes, wall_s).
5. Book honestly (RESULTS.md row) → re-seal manifest → receipts 6/6 → push.
6. On KEEP: wire cell-v0 as the CANON pre-filter in front of RESULTS.md
   bookings — first food: retro-run it over the ST1/ST1v2 receipts. Escalation
   thresholds become principled (pinch when the cell abstains or p < τ_cal;
   per-engine τ learned later per laya's engine-local doctrine).
