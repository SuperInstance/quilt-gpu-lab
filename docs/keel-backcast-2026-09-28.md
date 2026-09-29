# KEEL BACKCAST — the far-future receipt for the delta-native transformer

*2026-09-28 19:19 AKDT · lane: keel-backcast · recipe: `docs/bmad-mechanics-2026-09-28.md` §6 (the fusion recipe) · directive: Casey 19:07 — "the breakthrough transformer using a mix of far future reverse-actualization and BMAD"*

---

## 0. What this artifact is (and is not)

**This is a BACKCAST ARTIFACT.** §1 is written as if June 2027 already happened. It is the
acceptance test written before the code exists — the PRFAQ move applied to our ledger. Nothing in
§1 is evidence; only the fields marked `REAL` cite receipts that already sit in RESULTS.md. The
recipe's own law applies: *if you cannot write a specific future receipt, the target is not yet an
experiment — it's a vibe.* This file exists to make the keel an experiment.

- **The far future supplies the why** (§1, the receipt).
- **BMAD supplies the how** (§2 gate-set → §3 ticket ladder → §4 first run under the worker contract).
- **The manifest supplies the true** (§5: the retro judges the ledger against this receipt).

---

## 1. THE FAR-FUTURE RESULTS ENTRY (written FIRST, 2026-09-28)

## K0 — keel-stack: the delta-native transformer lands (BACKCAST ARTIFACT · far date 2027-06-15 · written first 2026-09-28 19:19 AKDT)
- ran: **NOT YET — acceptance test written before the code exists.** Outstanding receipts: K1, K2, K3, K4 (§3). Fields marked REAL cite existing ledger entries.
- verdict (TARGET): **KEEP**
- result (TARGET, except where marked REAL): ```json
{
  "experiment": "K0 keel-stack (predict differences, not states — token × target × latent × composition)",
  "device": "cuda (RTX 4050 6GB) + fleet lane",
  "seeds": [42, 1337],
  "backcast": { "artifact": true, "written_first": "2026-09-28T19:19:00-08:00", "target_date": "2027-06-15" },
  "levels": {
    "token": {
      "paired_val_bpb_delta_mean": -0.02899,
      "new_params": 0,
      "status": "REAL — D2 (−0.029315 @ seed 42) + D3 (−0.028642 @ seed 1337), agreement within 0.0007; seed noise ~0.005",
      "verdict": "KEEP×2"
    },
    "target": {
      "changed_cell_x_life": 3.5,
      "changed_cell_x_mandelbrot": 2.6,
      "status": "REAL — G4 diff-mask tripled-to-quadrupled dynamics on every source; replicated at seed 1337 (G10)",
      "verdict": "KEEP + REPLICATED"
    },
    "latent": {
      "heldout_gap_rel_win_vs_state_target": 0.18,
      "heldout_gap_rel_win_vs_persistence": 0.31,
      "paired_seed_agreement": "|win(42) − win(1337)| <= 0.02",
      "status": "TARGET — the K1/K2 gate values below, not yet fired (gem #1, Diff-JEPA)"
    },
    "composition": {
      "latent_composite_vs_best_parent_rel": 0.08,
      "stacked_vs_best_single_min_win": 0.0,
      "status": "TARGET — K3/K4: state-base + delta-correction composite (the G5 move at latent level) beats both parents; the token+latent stack is never worse than best single"
    }
  },
  "pre_registered_gate_passed": "the keel gate (K-G0..K-G4, §2) — all four levels KEEP at pre-registered margins, never loosened",
  "falsified_alternatives": {
    "more_data": "G6 KILL — starvation bought nothing; hard dynamics are capacity/bias-bound, not data-bound",
    "more_time": "G8 SATURATION — second doubling of budget bought +0.028 where the first bought +0.224",
    "more_params": "G9/G9b/G9c BOXED — five honest deaths; width/depth/heads couple on this skeleton, and params were not the binding constraint anyway",
    "state_target_latents": "K1's control arm — state-target JEPA prediction at matched budget loses the transition gap (TARGET: the receipt's own control)",
    "reward_accumulation_addressing": "D13/D13b/D13c KILL — Hebbian, confidence-weighted, and REINFORCE-with-baseline all fail; D18 corrects the confound: consistent relational targets + correlation detection (O(1)) is the real primitive",
    "correlated_dense_voters": "D1 — correlated votes are dead weight (−0.076 at k=4); independent reach is what lifts ceilings"
  },
  "verdict": "KEEP"
}
```
- note (what this will have cracked): **"predict differences, not states" stopped being a speedrun
  mutation (D2) and a loss-mask trick (G4) and became a measured principle** — the same
  zero-parameter difference operator wins at token scale (bpb), target scale (changed-cell),
  latent scale (transition gap), and composes (state-base + delta-correction beats either parent
  alone). The reader-class lesson (E13b/X9: the reader determines learnability — the battery
  contained the presence signal all along; the ridge couldn't extract it) is baked into every
  gate: no latent-level claim passes on a linear reader alone. The nursery has its first
  principle, and the fleet has its keel: the spine every later mutation stacks onto.

*If the ledger lands here, this entry stops being a backcast and becomes a receipt with a paper
trail. If it doesn't, §3's whole-backcast falsifier fires and the delta between this receipt and
the ledger is itself the mined finding (§5).*

---

## 2. THE GATE-SET EXTRACTED BACKWARD (PRD-as-gate-set / SPOOL entry v2)

**Why:** three independent KEEP receipts (token: D2/D3; target: G4/G5/G10; relational-transition:
D19/D20 where ternarized *differences* beat both Markov state features and the continuous-diff
oracle) all point at one claim: the difference operator carries structure the absolute state
doesn't, at zero parameter cost. The keel is the claim that this is a **family**, not a trick —
which stands or falls at the one level not yet tested: the latent level (gem #1, Diff-JEPA).

**Capabilities + success conditions (each gate KEEP-iff / KILL-iff, frozen, never loosened):**

| Gate | What is measured | Baselines | KEEP-iff | KILL-iff | Falsifier status |
|---|---|---|---|---|---|
| **K-G0** token level | paired val_bpb at fixed 300s budget, climbmix shards 0/1 + val shard_06542 | stock skeleton @ same seed/budget | delta < baseline, ≥2 seeds, zero new params | delta ≥ baseline at either seed | **PASSED** — D2 (−0.029315@42), D3 (−0.028642@1337) |
| **K-G1** latent level | held-out transition gap of a matched-capacity predictor over frozen V-JEPA 2 latents (see §4 K1 spec) | state-target arm (same arch/budget/seeds); persistence (ẑ=z_t); linear probe | diff-target beats state-target by ≥0.05 relative at **both** seeds, both arms beat persistence | state-target ≥ diff-target on the pooled paired estimate with a healthy harness (both arms > persistence) | **OPEN — gem #1, first run** |
| **K-G2** latent replication | K1 at seed 1337 + one source-family swap (the D3 discipline) | K1's own seed-42 numbers | replication within pre-registered band | paired win inverts sign at the second seed | **OPEN** |
| **K-G3** latent composition | persistence-base + diff-head corrections, change-gated (the G5 move at latent level), threshold-calibrated | both single-target parents | composite ≥ best parent at the calibrated operating point, retains correction capacity | composite < both parents | **OPEN** |
| **K-G4** cross-scale stack | free-delta attention (token) + latent diff-target, each on its home bench, at equal params | best single parent per bench | stack ≥ best single on **both** benches (non-negative composition) | stack < best single anywhere | **OPEN** |
| **K-G5** reader class (standing rule, not a rung) | every latent-level read under ridge AND the per-fold LBFGS MLP (hidden 16, α 0.1) | — | a "win" counts only if it survives the nonlinear reader | a win that exists only under the linear reader is downgraded INCONCLUSIVE | **STANDING** — E13b/X9 lesson, pre-wired into K1/K2 eval |

**Constraints:** 4050 6 GB (working budget ~4.5–5 GB, guard.py floor 1 GB free / 80 °C); token-lane
budget 300s fixed; K1 ≤ 2h wall; seeds {42, 1337}; frozen encoders only (V-JEPA 2 ViT-L,
cached — E7/E15 pattern); no budget increases to manufacture wins (matched wall-clock is the
comparator); serialized GPU lanes (the D2 discipline).

**Non-goals (confounds refused, E2's lesson made structural):** no cross-source pair-mixing in
eval metrics; no cross-encoder comparisons of raw gap numbers (within-metric only, the E8 caveat);
no single-seed claims anywhere; no new-parameter arms dressed as zero-param (delta heads are
row-slices of existing weights, period); no state-target strawman (the control arm gets identical
architecture, tuning attention, and budget).

**Success signal (the verdict rule, one line):** the keel receipt K0 lands **KEEP** iff K-G0 (done),
K-G1, K-G2, K-G3, K-G4 all KEEP at the frozen margins — three scales plus composition. Partial
lands revise the receipt downward honestly; the delta between receipt and ledger is mined either
way (§5).

---

## 3. THE DERIVED LADDER (from the far future backward — each rung a checkable claim)

| Rung | When | Checkable claim (gate pointer) | Status |
|---|---|---|---|
| **4 — the receipt** | ~2027-06 | K0 KEEP: all levels + composition, per K-G0..K-G4 | target |
| **3 — six months** | ~2027-03 | The stack composes: K-G3 (latent composite beats both parents) and K-G4 (token+latent stack never worse than best single) both KEEP at ≥2 seeds; the recipe has survived one distribution shift (pixel-latent bench AND text nursery). *Falsifies rung 3:* composition flat or negative on both benches. | open |
| **2 — one month** | ~2026-10-28 | The latent level replicates: K-G2 KEEP (seed 1337 + family swap inside the pre-registered band), K1's corpus extended (≥6 source families, both reader classes per K-G5). *Falsifies rung 2:* the paired win inverts at seed 1337. | open |
| **1 — next week** | ~2026-10-05 | **K1 fires and lands KEEP/KILL (not muddy INCONCLUSIVE):** diff-target vs state-target over frozen V-JEPA 2 latents, gate frozen (§4), receipt sealed in RESULTS.md. Either verdict moves the program; only mud wastes it. | open — THE FIRST RUN, specced below |
| **0 — already stood on** | 2026-09-28 | Token level (D1 KILL → D2/D3 KEEP×2, −0.029 bpb paired, zero params) and target level (G4 KILL-by-registered-gate → G5 composite KEEP → G10 replicated). The first rung of the ladder is not speculation; it is the day's receipts. | **DONE** |

**THE WHOLE-BACKCAST FALSIFIER (what kills everything above):** if the latent level lands a clean
K-G1 **KILL** — state-target ≥ diff-target at matched budget on a healthy harness (both arms beat
persistence), replicated at both seeds — then "predict differences, not states" is **not a
family**. The keel demotes to "a token/target-level win on small corpora" (still two hardened
receipts, but no principle), rungs 2–4 evaporate, and the far-future receipt is unreachable as
written. Secondary falsifier: diff-target wins everywhere but composition never beats its parents
(rungs 3–4 die even with K-G1 KEEP) — the operator is real but does not compose into an
architecture. Either way the finding is booked honestly; a falsified backcast with sealed receipts
is worth more than a vibe that was never fired.

---

## 4. THE FIRST RUN SPEC — **K1: latent diff-target vs state-target (gem #1, ≤2h on the 4050)**

**One concrete experiment that fires the lowest unfired rung.** (The token-level first run is
already fired — D1/D2/D3 are its receipts. K1 is the first rung with no receipt.)

- **Latents:** frozen **V-JEPA 2 ViT-L** (`facebook/vjepa2-vitl-fpc16-256-ssv2`, cached, E7's
  loader verbatim), 16-frame windows @ 256px, **stride 8**, over the lavfi source families the
  G-lane already knows: `life`, `mandelbrot`, `testsrc2`, `smptehdbars` (+`testsrc`, `hue`,
  `rgbtestsrc`, `gradients` to reach 8) — 40s per source, seed 2718. Latents cached to disk once
  (z ∈ R^1024 per window), so all training passes are tiny.
- **Task:** next-window prediction z_{t+1} from z_t. **Arms (identical architecture, capacity,
  budget, seeds — only the loss target differs):**
  - **state-target:** loss = MSE(ẑ, z_{t+1})
  - **diff-target:** loss = MSE(d̂, z_{t+1} − z_t); evaluate ẑ = z_t + d̂
  - Predictor: 4-layer residual MLP, hidden 1024 (~4.2M params), same init scheme both arms.
- **Baselines:** persistence (ẑ = z_t — the mandatory floor); linear state map (degenerate-class
  control). Metrics: held-out transition MSE + cosine, reported **persistence-normalized**
  (1 − MSE_arm/MSE_persistence); leave-one-source-out splits within family (no cross-source pair
  mixing — non-goal); eval under ridge AND the per-fold LBFGS MLP reader (K-G5).
- **Budget (GPU-honest):** latent caching ~25 min (encoder forward, one pass, cached) + 4
  arm-runs × 20 min (2 arms × seeds 42/1337) = 80 min + eval ~5 min + buffer = **≤2h**, serialized
  lane, guard.py wrapped, peak VRAM well under the E7 envelope (~5 GB).
- **THE GATE (FROZEN — K-G1):**
  - **KEEP** iff diff-target beats state-target on held-out persistence-normalized gap by **≥0.05
    relative at BOTH seeds** AND |win(42) − win(1337)| ≤ 0.02 AND **both** arms beat persistence.
  - **KILL** iff state-target ≥ diff-target on the pooled paired estimate **with a healthy
    harness** (both arms > persistence by ≥0.05).
  - **INCONCLUSIVE** otherwise (incl. seed disagreement) → revise the SPOOL entry and re-derive
    (regenerate from the broken layer — adopt #10; never re-run the same code hoping for noise).
  - **INVALID_HARNESS** if either arm fails to beat persistence → the task is degenerate, fix the
    windowing/stride first, re-register, re-run.
- **Worker contract wiring (BMAD adopt #2–#5):** SPOOL entry `K1` pre-registered from this
  document verbatim → run plan `proposals/runs/K1-plan.md` with `baseline_revision` pinned at
  claim → status machine `ready-for-run → running → judging → built` → any mid-run halt stashes
  `proposals/runs/K1-attempted.patch` → receipt lands in RESULTS.md as
  `## K1 — latent diff-target (Diff-JEPA gem #1)` with manifest-sealed JSON. Runner never loosens
  the gate; the pre-registered gate is the standing approval.
- **Command sketch:**
  `K1_SOURCES=life,mandelbrot,testsrc2,smptehdbars,testsrc,hue,rgbtestsrc,gradients K1_STRIDE=8 K1_SEEDS=42,1337 K1_TIME_BUDGET=1200 python -m experiments.k1_latent_diff_target`
  (script + self-test must exist and pass before QUEUE wiring, per house convention; `K1b`
  reserved for the seed-1337-family-swap replication, K-G2.)

---

## 5. THE RETRO CLAUSE (how this artifact gets judged — recipe step 7)

At the lane's close (K1–K4 resolved or the timebox expires), one retro doc answers the
reverse-actualization loop-closer: **"is the ledger converging on the receipt we wrote, or did the
future move?"** If the future moved, the delta between §1's receipt and the actual ledger is
itself a mined abstraction for GEMS.md — the backcast's error is data about how *we* miss, which
is exactly the kind of finding the falsifier campaign was built to keep.
