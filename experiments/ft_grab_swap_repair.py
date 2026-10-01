#!/usr/bin/env python3
"""ft_grab_swap_repair — three pure primitives grabbed from SuperInstance/fleet-triage.

WHY THIS FILE EXISTS (lane QG1d, 2026-10-01; read-only recon of fleet-triage).
fleet-triage's experiments/ and root expose three small mechanisms we have never
source-read. Each is cell-shaped in the sense our contract cares about: pure
input->output, deterministic (no clock, no RNG), no I/O, receiptable — so they can
be dropped into a cell without a wrapper. They are NOT verbatim copies; each is the
minimal extraction of a contract that lives inside a larger, index/network-bound
file. Provenance is cited per function.

  kish_n_eff(corr)        <- synergy.py:69-79. THE degeneracy MECHANISM: "max over
                             k learners" is only a max over k EFFECTIVE votes; when
                             members agree, n_eff << k and the max-selection ranks
                             noise. fleet-triage published "max over 4 learners at
                             n_eff = 1.48" and retracted it (BOARD.md:23,59,83).
  spread_vs_gap(...)      <- CORRECTION-PROJECTION.md:26-40. The RULE that turns
                             n_eff into a verdict: "No gap smaller than the spread
                             is a finding." (their +0.0112 gap sat inside a 0.3209
                             spread and reversed under median).
  repair_label(...)       <- resolver.py:652-733 (_suffix_match) + 829-856
                             (_near_miss). The REPAIR LADDER: given a broken
                             pointer and candidate matches, emit the nearest valid
                             target WITH an explicit confidence label, and never
                             silently upgrade an ambiguous match to "resolved".
  control_beam(...)       <- lanes.py:91-105 (beam_control) + 143-157 (the
                             control-tautology guard). The INSTRUMENT our XP-A grid
                             lacks: audits whether a check was ever SHOWN to fail,
                             and refuses a control whose command equals its repro.

HOUSE LAW note: no subprocess, no shell, no RNG in the primitives; the self-test
uses the fixed SEED below if it needs any sampling. list-form only (no shell=True)
everywhere in this lab.
"""
from __future__ import annotations

SEED = 2718  # lab seed; unused by the pure primitives, pinned for the self-test


def kish_n_eff(corr):
    """Kish effective sample size, 1 / normalised correlation mass.

    corr is a k x k matrix of pairwise correlations in [0,1] (use |r|; a negative
    correlation is dependence too — pass abs). Diagonal is 1. Returns k/Σ(1 if i==j
    else corr[i][j]) — k when members are independent, ->1 as they become copies.
    This is the number that makes a max-selection honest: "max over 4" with
    n_eff=1.48 is max over ~1.5 votes. Deterministic; pure.
    """
    k = len(corr)
    if k == 0:
        return 0.0
    total = 0.0
    for i in range(k):
        for j in range(k):
            total += 1.0 if i == j else max(0.0, corr[i][j])
    return k / total if total else 0.0


def spread_vs_gap(gap, spread, labels=("A", "B")):
    """Gate a reported gap against the spread it was selected from.

    Returns (is_finding, verdict, detail). RULE (fleet-triage, after retracting their
    own +0.0112): any gap smaller than the across-arm spread is not a finding — it is
    within the noise of which arm you happen to pick. Also flags DEGENERATE when the
    spread is zero AND the gap is zero (zero-variance statistic: our verdict_gate
    DEGENERATE class). Pure.
    """
    if spread == 0.0 and gap == 0.0:
        return (False, "DEGENERATE", "zero variance AND zero gap: no signal to gate")
    if abs(gap) < spread:
        return (False, "NOT_A_FINDING",
                "gap %.4f < spread %.4f (%s vs %s): selection artifact"
                % (gap, spread, labels[0], labels[1]))
    return (True, "FINDING", "gap %.4f >= spread %.4f" % (gap, spread))


def repair_label(cited, candidates, generic_segs=frozenset()):
    """The repair ladder: broken pointer -> nearest valid target + confidence label.

    `candidates` is an iterable of (repo, relpath) the resolver found by suffix or
    basename match. Outcomes, mirroring resolver.py's ladder:
      EXACT              the cited path is itself a candidate (no repair needed)
      REPAIRED_PRECISE   exactly one candidate: name it, label it PRECISE_ONLY
      AMBIGUOUS          several candidates: refuse to name one
      MISSING            none: the pointer does not resolve
    The load-bearing rule (resolver.py:652-733): never upgrade AMBIGUOUS to
    REPAIRED. A repair that names the wrong target is exactly the "well-formed,
    checkable, wrong" artifact class. Deterministic; pure.
    """
    def norm(c):
        return (None, c) if isinstance(c, str) else (c[0], c[1])
    cands = list(dict.fromkeys(norm(c) for c in candidates))
    if any(rel == cited for _, rel in cands):
        return ("EXACT", cited, "cited path is a candidate")
    if len(cands) == 1:
        return ("REPAIRED_PRECISE", cands[0], "one candidate; cited path was shallower")
    if len(cands) > 1:
        return ("AMBIGUOUS", None, "%d candidates: %s"
                % (len(cands), sorted(rel for _, rel in cands)[:4]))
    return ("MISSING", None, "no candidate matched")


def control_beam(repro_rc, control_rc, repro_cmd, control_cmd, expect_rc=0):
    """Did this check ever fail? lanes.py:91-105 + the 143-157 tautology guard.

    A check is only a check if it was shown RED on deliberately-broken input.
      CONTROL_UNFAILABLE  the control succeeded on broken input (control_rc == expect)
      CONTROL_TAUTOLOGY   control_cmd == repro_cmd: agreement is by construction
      CONTROL_OK          the control correctly exited non-zero (the GOOD outcome)
    Returns (ok, state, detail). Pure.
    """
    if list(control_cmd) == list(repro_cmd):
        return (False, "CONTROL_TAUTOLOGY",
                "control_cmd == repro_cmd: cannot falsify itself")
    if control_rc == expect_rc:
        return (False, "CONTROL_UNFAILABLE",
                "control succeeded on broken input: the check cannot fail")
    return (True, "CONTROL_OK", "control correctly failed on broken input")


def _demo():
    # n_eff: 4 members, two families at r=0.8 -> the fleet's degeneracy shape
    corr = [[1.0 if i == j else 0.8 for j in range(4)] for i in range(4)]
    eff = kish_n_eff(corr)
    print("  n_eff over 4 correlated learners = %.2f (of k=4)" % eff)
    print("  their retraction: %s" % (spread_vs_gap(0.0112, 0.3209, ("L0", "L1"))[1],))
    print("  exact-path ladder :", repair_label("a/b.py", [("r", "a/b.py")])[0])
    print("  one-candidate     :", repair_label("b.py", [("r", "src/deep/b.py")])[0])
    print("  ambiguous         :", repair_label("a/b.py", [("r1", "deep/a/b.py"),
                                                            ("r2", "other/a/b.py")])[0])
    print("  unfailable control:", control_beam(0, 0, ["x"], ["y"])[1])
    print("  tautology control :", control_beam(0, 0, ["x"], ["x"])[1])
    print("  honest control    :", control_beam(0, 1, ["x"], ["y"])[1])


if __name__ == "__main__":
    _demo()
