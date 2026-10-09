# PROP-1 — Randomized property test over the eproc verdict law (pre-registration)

Spawned by SCOUT-86 (cf-native-backend randomized real-git-fork conflict-theorem search,
mutation-verified; steal). Target: `tools/eproc.py` `witness()` / `kill_gate()` — the QO6
kill-evidence instrument whose booked verdicts (QO6, QO6s) cite it.

## Property under test (frozen words)
**P1 (H0 safety):** For iid N(0, sigma) increments (no drift), the anytime-valid witness
fires `WITNESSED` at rate ≤ delta = 0.05, up to binomial sampling tolerance. Ville's bound
says the TRUE rate is ≤ delta; the test asserts the observed rate over N=400 series of
length T=60 is ≤ 0.09 (Wilson 95% upper ceiling on 5% at N=400, pre-fixed BEFORE running).

**P2 (H1 power sanity):** For iid N(mu=sigma, sigma) increments (true decrease, sign=-1),
witness fires at rate ≥ 0.80. A safety-only gate that never fires is useless.

**P3 (mutation-verified 2/2):** The property test must FAIL (detect) both seeded mutations:
  M1: sign flip (witness DECREASES with sign=+1) — P2 must break.
  M2: mixture collapsed to point mass mu_grid=[0.4] — P1 must break (overconfident point
      mixture fires on pure noise more often).
If the suite passes with either mutation in place, the suite is vacuous → RED.

## Gates
- G1: P1 observed fire-rate on H0 ≤ 0.09 (pre-fixed ceiling).
- G2: P2 observed fire-rate on H1 ≥ 0.80.
- G3: M1 run → G2-style check FAILS; M2 run → G1-style check FAILS; both mutations caught (2/2).
- G4: cost ≤ ~2 min CPU; deterministic seed (0xC0FFEE) so the booking is reproducible.

## Verdict mapping
All gates pass → GREEN (eproc verdict law holds under randomized property testing).
Any gate fail → RED with the failing gate named; STOP, no re-roll (protocol).

## Instruments
- tools/eproc.py (pinned: QO6 booking lineage 61b9e04/aad90ac5).
- experiments/prop1_eproc_property.py (new; self-contained, seed pinned, fail-loud asserts).

Fired only after this file is committed and pushed.
