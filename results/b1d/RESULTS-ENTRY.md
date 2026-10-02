# B1D — CAPACITY FLOOR: the tanh-head floor is > 64 at 40ep; ramp is the residue

Lane **B1D-CAPACITY-FLOOR** (prereg `proposals/runs/B1D-capacity-floor.md`, frozen
2026-10-01 16:2x AKDT, before fire). 2026-10-01. **NOT COMMITTED.**

## Verdict: **PARTIAL** — no sweep arm clears; reweighting lowers the deficit, not the floor

B1C booked a PASS for its `cap` arm (`3-128-128-128-1` ReLU, **linear** head) at
40ep and named the open question: *what is the MINIMUM capacity that clears, and
does loss reweighting lower it?* B1D ran the frozen sweep — B1C **body** shape
(3 hidden ReLU layers) with the width swept {24, 32, 48, 64}, a **bounded tanh
head** (`raw = 1.05·tanh(z)`, as the lane brief froze), × {plain, reweight} × 3
seeds, **40ep only**.

**Answer, honest and specific:**

1. **No tanh-head arm clears BOTH regions at any width ≤ 64** → under the frozen
   (tanh-head) architecture the **capacity floor is > 64 at 40ep**, for *both*
   plain and reweight. (Floor bracketed: >64 here; the width-128 **linear**-head
   control = B1C's cap arm PASSes — see controls.)
2. **Reweighting does NOT lower a floor that isn't reached, but it demonstrably
   lowers the deficit**: it is a **mechanism win at w48 (+0.367 deadzone /
   +0.272 ramp) and w64 (+0.283 / +0.215)** vs same-width plain. `reweight_w48`
   (0.6965 / 0.5139) is the best tanh-head arm — still short of 0.90.
3. **The deadzone is fully closable by an interface, the ramp is not (yet)**:
   the optional **hybrid head** (regression + deadzone atom gate) at w64 drives
   deadzone to **0.9998 ± 0.0002** (an exact atom, std > 0, non-degenerate) but
   leaves **ramp 0.8042** — so at the floor width the **ramp is the sole binding
   region**.

## Per-region table (held-out, 3-seed mean ± std) — the headline

Holdout n = 90,930; region fractions **identical to B1C/B1b**: clamp 0.13 %,
deadzone 7.80 %, saturation 88.39 %, ramp 3.69 %.

| arm | width | params | deadzone @5e-2 | ramp @5e-2 | sat @5e-2 | dz @1e-2 | ramp @1e-2 | agg @5e-2 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| plain | 24 | 1,321 | 0.1692 ± 0.0107 | 0.1733 ± 0.0109 | 0.9421 | 0.0477 | 0.0365 | 0.8536 | FAIL |
| plain | 32 | 2,273 | 0.1712 ± 0.0136 | 0.1744 ± 0.0131 | 0.9417 | 0.0487 | 0.0361 | 0.8534 | FAIL |
| plain | 48 | 4,945 | 0.3295 ± 0.1915 | 0.2415 ± 0.0640 | 0.9615 | 0.0539 | 0.0452 | 0.8857 | FAIL |
| plain | 64 | 8,641 | 0.2441 ± 0.1213 | 0.2137 ± 0.0407 | 0.9525 | 0.0541 | 0.0428 | 0.8701 | FAIL |
| reweight | 24 | 1,321 | 0.2055 ± 0.0033 | 0.1539 ± 0.0021 | 0.8856 | 0.0625 | 0.0298 | 0.8058 | FAIL |
| reweight | 32 | 2,273 | 0.2628 ± 0.0712 | 0.2467 ± 0.1001 | 0.9144 | 0.0547 | 0.0545 | 0.8390 | FAIL |
| **reweight** | **48** | 4,945 | **0.6965 ± 0.3464** | **0.5139 ± 0.2776** | 0.9587 | 0.1214 | 0.1161 | 0.9219 | FAIL (best sweep arm; mech win) |
| reweight | 64 | 8,641 | 0.5275 ± 0.3338 | 0.4288 ± 0.3514 | 0.9392 | 0.2772 | 0.1436 | 0.8884 | FAIL (mech win) |
| hybrid (gate) | 64 | 8,706 | **0.9998 ± 0.0002** | **0.8042 ± 0.1290** | 0.9982 | 0.9551 | 0.2155 | 0.9911 | FAIL (deadzone PASS, ramp short) |
| **_CONTROL_ anchor_cap128** *(linear head = B1C cap, C6)* | 128 | 33,665 | **0.9957 ± 0.0061** | **0.9186 ± 0.1109** | 0.9992 | 0.6013 | 0.2597 | 0.9959 | **PASS** |

Mechanism bar (reweight − plain at same width; needs ≥ +0.15 dz AND ≥ +0.20 ramp):

| width | Δ deadzone | Δ ramp | mechanism win |
|---|---|---|---|
| 24 | +0.0363 | −0.0194 | no |
| 32 | +0.0916 | +0.0723 | no |
| **48** | **+0.3670** | **+0.2724** | **yes** |
| **64** | **+0.2834** | **+0.2152** | **yes** |

## Findings

1. **At the tanh head, capacity is not the binding lever over 24→64 at 40ep.**
   Plain arms barely move with width (deadzone 0.169→0.244, ramp 0.173→0.214 —
   and **non-monotone**, w48 > w64) with seed stds up to 0.19 that swamp the
   width effect. Compare B1C's *linear*-head `relu_ref` (width-64) at 40ep:
   deadzone 0.4951 / ramp 0.3205 — i.e. the **head, not the width**, dominates
   in this range. **Booked confound:** the brief froze the tanh head, so B1D
   measures the tanh-head floor, not the B1C (linear-head) capacity floor; the
   two heads are not arithmetically comparable (see BOOKED below).
2. **Reweighting is a real lever on the deficit, directionally as B1C found.**
   At w48 it lifts deadzone +0.367 and ramp +0.272 (B1C's width-64 lift was
   +0.260 / +0.375). Both minority regions move together (the weights are
   deadzone ×4.76, ramp ×9.65, saturation ×0.37) — consistent with the dilution
   hypothesis. But even `reweight_w48` lands 0.696/0.514: **reweighting shrinks
   the deficit ~3× and still does not clear it at ≤64.**
3. **The deadzone is an interface problem; the ramp is the real floor.** The
   hybrid head's atom gate (trained by BCE on the closed-form deadzone label
   `|b−p| ≤ 1.5`) nails the deadzone atom at **0.9998** — at the same width (64)
   where plain tanh gets 0.244 — yet ramp only reaches **0.8042**. This is a
   clean replication of B1C's binned-head lesson in the opposite direction:
   the binned head fixed the atom and destroyed the ramp; the hybrid fixes the
   atom and *keeps* a continuous ramp (0.804 ≫ binned's 0.120 at 40ep) — but the
   continuous ramp still needs more than width-64-at-40ep to clear 0.90.
4. **No degeneracy anywhere.** Every gated cell has std > 0 (the smallest is
   the hybrid's deadzone std 0.00018 — still > 0, so the frozen rule books it a
   genuine PASS on that region). No `INCONCLUSIVE` in this lane: unlike B1C's
   300ep regime, nothing saturated to a std == 0 ceiling.
5. **Aggregate would have hidden the structure again** — and here it *inverts*
   the story: `reweight_w64` has the **worst** @1e-2 aggregate (0.4658) yet a
   *better* ramp than `plain_w64`; `hybrid_w64` has the best aggregate
   (0.9911) but fails. Per-region remains mandatory.

## The capacity floor (deliverable)

| weighting | min width clearing BOTH regions @5e-2, 40ep |
|---|---|
| plain (tanh head) | **not reached ≤ 64** (floor > 64) |
| reweight (tanh head) | **not reached ≤ 64** (floor > 64) |
| linear head (CONTROL, = B1C cap) | **≤ 128** (PASS at 128; 24–64 not run — outside the frozen tanh-head design) |

So the floor is **bracketed (64, 128]** for the *linear* head and **> 64** for the
frozen tanh head. The decisive variable in this range is the **head**, not the
width. See NEXT.

## Controls (all pass)

- **C1 law equivalence** — `laweq` max|Δ| = 0 (n = 4,000).
- **C4 frame cross-check** — regenerated holdout vs **B1C**, **B1b-runB** AND
  **B1**: `max|ΔX| = max|ΔY| = max|ΔMETA| = 0.0` for all three. The reuse is on
  the prereg's bit-identical frame.
- **C6 anchor reproduction** — the width-128, depth-3, **linear**-head plain
  body (= B1C's `cap` arm by construction) reproduces B1C's **booked**
  `cap@ep40` per-region means with **max|Δ| = 4.7e-05** (tol 0.05): deadzone
  0.9957, ramp 0.9186 — effectively exact. The whole pipeline (frame →
  training → scoring) is proven deterministic and B1C-reproducible. **This is a
  control, NOT an arm of the floor sweep** — the lane verdict excludes it (a
  first-fire code bug that counted the anchor as a passing arm was caught and
  fixed; the corrected verdict is PARTIAL, re-emitted by `--resume`).
- *(No C2 JS↔torch port: h2h is out of scope for B1D, as it was for B1C's gate.)*

## Guard / receipt

`Guard(task_id="B1D-capacity-floor", seed=2718, receipt_dir=results/b1d/guard)`.
Two sealed windows (fire + `--resume` re-emit, 30 nets reused, 0 retrained):

- `g7-wr-b1d-capacity-floor-1790901068` — **valid, PASS**; 6.7905 Wh, 382.1 GPU-s.
- `g7-wr-b1d-capacity-floor-1790901166` — **valid, PASS**; 0.4152 Wh, 17.4 GPU-s.
- **Lane total: 7.21 Wh measured ≤ 18 Wh envelope** (33.3 kJ). Peak VRAM
  122.7 MB (ceiling 1500, device 6 GB); min free VRAM **1820 MiB** ≥ 1024;
  max temp **≤ 79 °C** ≤ 80. Co-tenant 7B seat + pong grind held the card
  throughout; notes are tiny and ran beside them.

### ⚠ Booked discrepancies (no silent passes)

- **Receipt-window artifact wrinkle:** both Guard objects share `receipt_dir`,
  so the resume window's `guard_summary.json` **overwrote** the fire window's;
  receipt `…068`'s `state_digest` therefore no longer resolves to the on-disk
  summary (it bound the pre-overwrite bytes). Both receipts remain schema-valid
  and PASS; energy is booked as the **sum of both receipts** (7.21 Wh), and the
  **authoritative** receipt is the resume one (`…1166`). Booked, not hidden.
- **Prereg-interpretation risk (frozen before fire):** the brief's
  *"Architecture otherwise identical to B1C cap arm (body width varied, tanh
  head)"* was read literally: B1C **body** shape + **tanh** head. B1C's cap arm
  actually used a **linear** head, so B1D's absolute cells are **not** comparable
  to B1C's booked cells; the cross-lane tie is carried by control C6, not by
  arithmetic. The linear-head width sweep (24–64) was **not** run — it is
  outside the frozen design — so the *B1C-family* capacity floor remains open
  (bracketed by C6's 128-PASS).

## Artifacts (`results/b1d/`)

`run_config.json`, `traces_meta.json`, `holdout_samples.npz`, 30 nets
`model_{anchor_cap128,plain_w{24,32,48,64},reweight_w{24,32,48,64},hybrid_w64}_seed{2718,2719,2720}_ep40.pt`,
`regions.json` (the headline table), `agreement.json` (full curve),
`controls.json` (C1/C4/C6), `result.json` (verdict + floor + resume ledger),
`guard/{two g7 receipts, guard_summary.json, ledger.jsonl}`. Code:
`experiments/b1d_capacity_floor.py` (imports the B1C driver for frame/regions/
engine; the B1C engine `experiments/b1c_value_fidelity_engine.mjs` is reused
**unchanged**). B1/B1b/B1C artifacts untouched. Prereg:
`proposals/runs/B1D-capacity-floor.md`.

## Next question

- **Linear-head capacity sweep at 40ep, widths {24, 32, 48, 64}** (B1C's
  architecture verbatim, no tanh head): the *actual* capacity floor of the B1C
  recipe. C6 gives the 128 anchor (PASS) and B1C gives 64 (FAIL) — this fills
  the bracket and isolates head vs width. Cheap (~12 nets, ~4 Wh).
- Then: does the **ramp** close with capacity alone at the linear head, or does
  it need the same region-reweight that lifts deadzone? (B1D shows ramp is the
  harder region under every knob tried.)
- Interface: ship the **hybrid** only if a width clears ramp — its deadzone atom
  is already near-exact (0.9998) and it keeps a continuous ramp (unlike binned).
