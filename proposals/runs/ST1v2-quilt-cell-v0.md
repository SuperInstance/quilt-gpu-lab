# ST1v2 — quilt-cell-v0 at the corrected LR (new pre-registration)

Pre-registered: 2026-09-30 ~11:36 AKDT, BEFORE fire. Supersedes the config of ST1
(which fired and booked an honest KILL at its registered lr 3e-4).

## Why a NEW pre-reg instead of editing ST1
ST1's gates were frozen with lr 3e-4 and fired; it KILLed with a *diagnosed*
harness fault: MiniLM's features collapsed to the uniform prior within the first
steps (per-seed OOD thresholds all ≈0.50; gate coverage flipping 0.0/1.0;
smoke train loss ≈ ln 2). 3e-4 is ~10× the standard fine-tune LR for a 6-layer
encoder. You do not retro-edit a fired run's config — you register the corrected
config as a new run and let the SAME frozen gates judge it.

## Identical to ST1 (deliberately — the only moving part is the LR)
- Same corpus pipeline: 8000 synthetic receipts from the booking schema, six
  corruption ops (sign_flip, wins_over, verdict_flip, tau_off, seed_drop,
  denom_swap), dual render styles (template + compact JSON).
- Same real-gate set: every `results/**/results.json` (except ST1's own), each
  with up to 4 held-out corruptions (value_swap real-only). Fail-loud if <10.
- Same seeds 6611-6615, same abstention design (OOD A/B non-circular split:
  threshold = p90 max-softmax on half A, gate measured on half B).
- **Same frozen gates: syn_auc ≥ 0.95 · real_auc ≥ 0.80 · honest_fpr ≤ 0.10 ·
  ood_abstain ≥ 0.90.** Gate thresholds are untouched between ST1 and ST1v2 —
  that is the point of the pair.

## The single changed factor
- lr **3e-4 → 2e-5**, warmup_ratio **0.0 → 0.1**, epochs **4 → 3**
  (cost-neutral; warmup protects the encoder during the first updates).

## Interpretation rules (fixed now, before the result exists)
- **v2 KEEP** ⇒ the collapse diagnosis was right and the task is learnable by a
  22.7M cell; proceed to wire cell-v0 as a CANON pre-filter and to ST2 (router).
- **v2 KILL at 2e-5** ⇒ the diagnosis was incomplete; the failure is not LR.
  Next suspects in order: (a) label/format leakage check (does the corrupt
  variant differ from the clean one by a *detectable* token in EVERY op? audit
  op-by-op), (b) corpus size/epochs, (c) head capacity. Registered now so the
  post-hoc story cannot drift.
- Either way: no gate edits, no re-rolls; results land in their own dir
  (`results/st1_quilt_cell_v0/results.json` is overwritten ONLY by a run with
  `smoke:false`; v2 writes `results/st1v2_quilt_cell_v0/results.json` via a
  copied runner or an `--out` flag added pre-fire).

## Cost
GPU-only, local; MiniLM already cached. No API spend.
