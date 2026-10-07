# ST1-AUDIT — op-by-op leakage/detectability audit (SCOUT-6 / 12:1x spawn)

## Question
Does a trivial mechanical (byte-level/regex-only, no learning) discriminator separate
clean from corrupt for each of the 6 ST1 synthetic corruption ops — i.e. is the ST1
synthetic task solvable by surface artifacts rather than corruption semantics?
This audits the ST1v2 KILL's registered next-suspect (a): op-by-op leakage.

## Method
Reuse the COMMITTED generator in `experiments/st1_quilt_cell_v0.py`
(`make_example`, `corrupt_example`, `render`, `honest_verdict`) verbatim.
For each op, draw 600 clean + 600 corrupted examples (seed 2718, 50/50, both render
styles) and score each with a mechanical check that sees ONLY the rendered text:

- sign_flip  → verdict/mri consistency: regex-extract `verdict` and
  `mean_rel_improvement`, recompute the booked verdict rule, flag mismatch.
- verdict_flip → same check (it is the same invariant).
- wins_over  → wins > n_pairs (regex).
- denom_swap → wins > n_pairs (regex, same invariant).
- tau_off    → tau outside the declared grid [0.40, 0.60] (regex).
- seed_drop  → `seeds` field absent (regex).

Score = 1.0 if the mechanical flag fires else 0.0 (ties allowed; AUC handles them).

## Frozen gates (pre-registered, in words)
- For each op: AUC(mechanical score vs corrupt label) computed on the 1200-example
  arm. **LEAKY iff AUC >= 0.95.**
- **KEEP-AUDIT** iff >=1 op is LEAKY AND the flagged set's direction is consistent
  with the ST1v2 syn/real gap (syn solvable ⇒ syn AUC inflated). Otherwise **CLEAN**
  (⇒ ST1v3 suspects (b) corpus size / (c) head capacity become primary).
- DEGENERATE guard: if any op's clean arm is all-identical renders such that the
  score has zero variance on one side, mark that op DEGENERATE (never PASS), per
  the fleet murmuration law.

## Cost
CPU only, minutes, no API spend, no GPU. Existing committed generator only.

## Honest scope
This audits the SYNTHETIC lane of ST1 only; the real-gate receipts are untouched.
The discriminators are allowed knowledge of the op inventory (white-box audit by
design — the question is whether the TASK is white-box-solvable, not whether a
blind attacker can solve it).
