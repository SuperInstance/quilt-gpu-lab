# REPORTER-DEFAULT — abort/skip fall-through audit of committed gate/verdict paths (CPU, read-only + injection probes)

Spawned by SCOUT-23 (2026-10-02 1840Z) from canons e7b3d79 mechanism #3: guard fires,
reporter defaults PASS on the unattributed abort. BLOCKS the next gate-bearing booking.

## Question
Can any COMMITTED verdict path behind a BOOKED result fall through to a PASS-class
verdict when a guard aborts, a check is skipped, or an input is abort-shaped
(missing keys, None, empty evidence)?

## Scope (booked gate/verdict sites; GATE-MARGIN list + verdict-function census)
1. `tools/verdict_gate.py` `finalize` — central reporter (11 existing pins).
2. `experiments/comp2_itemlocal.py` `gate()` — degenerate→INCONCLUSIVE branch claimed.
3. `experiments/c2_probe_skip_tower.py` `verdict_of` + harness-level gate.
4. `experiments/c3_probe.py` `verdict_of` — default branch claimed NO_ANCHORING.
5. `experiments/cg1b_elicitation.py` inline `verdict` — None-guard booleans.
6. `experiments/w5a_reobserve_vs_trace.py` `verdict` — `mu==0.0: continue` silent-skip path.
7. `experiments/e24_dial_momentum.py` `verdict_for` — fall-through tail claimed INCONCLUSIVE.
8. `experiments/e25_fold_phase_transition.py` verdict mapper (+ G0e self-test).
9. `experiments/e27_hidden_angle.py` `verdict_of` — final fall-through claimed KILL.
10. QG6 `delta_lb` (unconditional CI arithmetic), QO1/QO3/QO6 (assert-gated drivers).
11. Census pass: grep all committed experiments/tools for PASS-class default branches
    reachable from abort/skip; env-fragile fixture assumptions (init.defaultBranch,
    branch names, cwd).

## Gates (pre-registered, words)
- G1: for every IMPORTABLE verdict function above, injected abort-shaped inputs
  (missing dict keys, None metrics, empty primary list) must yield a FAIL/ERROR/
  INCONCLUSIVE/VOID/KILL/INVALID-class outcome — never PASS/KEEP/CONFIRM/REPLICATED.
  Any PASS-class output from an abort-shaped input = RED at that site.
- G2: `tools/verdict_gate.finalize` abort path — completeness=None/False, missing
  gate values, inherited status must all stay non-PASS (already pinned; re-run pins).
- G3: guard-the-guard — each RED-able site must be covered by a test exercising a
  NON-synthetic (abort-shaped) input; uncovered sites listed, no code changes this
  slice beyond adding failing-first pins if a site is both RED and unpinned.
- G4: env-fragile census — zero hits expected (canons e7b3d79 class); any hit = RED.
- STOP rule: a RED at any site that could flip a BOOKED verdict → amend the booking
  in place, stop the slice, no re-runs.

## Cost
CPU-only, ~15 min; zero GPU-Wh; read-only + `tools/reporter_default_audit.py` (new,
committed with this prereg).
