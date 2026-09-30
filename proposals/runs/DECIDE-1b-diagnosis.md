# DECIDE-1b — G2 FAIL diagnosis (balance-edit lane, jeff-0.8b decision cell)

Spawned by DECIDE-1 (see RESULTS.md; G2 lane 5/64 = 0.078 BELOW chance, zero-shot and shipped
trained readouts giving identical predictions). This is a diagnosis run, not a re-roll: same test
set (make_questions(64, seed=202), same margin filter), same reader stack, no re-sampling of the
physics. Goal: name the failure mode before any further lane work.

## Pre-registered probes (fail-loud, all on the SAME 64 questions)

- **P1 argMIN inversion**: accuracy of the arg-*min*-probability pick, and separately: fraction of
  questions where the *predicted* candidate is the argMIN-balance candidate (is the model selecting
  the worst edit?). INVERTED verdict: argmin-prob accuracy >= 0.5 (CP95 lower bound > 0.25).
- **P2 position census**: histogram of predicted letters A/B/C/D on the lane + histogram of *label*
  letters (sanity: labels should be ~uniform). POSITIONAL-BIAS verdict: any predicted letter share
  > 0.5. Also census of edit-type (insert/delete/replace) of predictions vs labels.
- **P3 shuffle content-vs-position**: re-render each question with a fixed permutation of options
  (rng seed 7) and re-decide. Letter-stickiness = fraction where prediction keeps the same LETTER;
  content-following = fraction where prediction keeps the same CANDIDATE. If letter-stickiness >
  content-following by a wide margin, the cell reads position, not content, on this family.
- **P4 label rank**: mean rank (0=best) of the true label in the predicted probability order —
  quantifies "how wrong" (uniform random => mean rank 1.5).

## Honesty notes
- P3 doubles the forward passes (64+128 ≈ 192, ~54 ms each) — trivial GPU budget.
- No temperature fitting, no head retraining, no question re-sampling in this run. If none of the
  verdicts fire, the honest landing is "offset is subtler than position/inversion" and the next
  spawned item is a token-level prompt diff (DECIDE-1c), not a retry of these probes.
