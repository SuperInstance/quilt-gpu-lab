#!/usr/bin/env python3
"""board_disjoint_cv — hash-based disjoint k-fold splitter + fold statistics.

Harvested from the A1-PIE lane (results/a1_pie/a1_pie_closure.py, 2026-10-01)
and its 4x4 follow-up A2-GA4444 (results/a2_ga4444/, 2026-10-01).

THE LOW-BIT TRAP (checked invariant — the lane's booked instrument bug):
FNV-1a-64's low bits are weakly mixed. Every 3x3 our-to-move board byte-encodes
to an even number of odd bytes ({0xFF, 0, 1} per cell; an our-turn board has
equal us/them stone counts, hence an even number of non-zero cells), and
multiplication by an odd prime preserves the low bit, so EVERY such board
hashes ODD. `fnv1a64(board) % 10` therefore only ever hits {1,3,5,7,9} —
bucket 0 is EMPTY. The first A1-PIE attempt did exactly this, produced an
empty test set, and was VOIDed before any number existed
(receipt g7-wr-a1-pie-closure-1790891323.json, kept deliberately). The proven
scheme uses the HIGH 32 bits — the well-mixed ones — modulo k
(A1-PIE: % 10 -> train 2186 / test 237, bucket sizes 217-261 over 2,423
boards; A2-GA4444: % 5 over 66,297 boards). This module bakes the fix in as
an invariant: ANY empty fold is a fail-loud exception (EmptyFoldError) with a
booked reason, never a silent degenerate split.

House contracts: seed 2718 is the house default for any randomized consumer of
these folds; fail loud; single JSON verdict line on stdout; std == 0 over fold
scores -> verdict INCONCLUSIVE; stdlib-only; CPU-only; no subprocess
(list-form only, ever, in consumers — this block needs none); never prints
secrets.

Self-test (__main__): synthetic 2,423-key corpus of 9-char strings over
'0','1','2' with an EVEN count of '1' (the alphabet's only lowbit-odd char,
mirroring the real boards' even-stone parity invariant) -> proven high-32
scheme gives 5 healthy disjoint folds; the deliberately weak raw-low-bit
variant reproduces the VOID trap and the empty-fold assertion fires (booked
as expected behaviour); fold_report maps constant scores to INCONCLUSIVE and
varying scores to measured (checked against the A1-PIE plateau CV receipt
numbers 0.9392 +/- 0.0094).
"""
from __future__ import annotations

import json
import statistics
import sys
from itertools import product

SEED = 2718  # house default (results/a1_pie/PREREG.md), pinned everywhere

FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME = 0x100000001B3
MASK64 = 0xFFFFFFFFFFFFFFFF


class EmptyFoldError(Exception):
    """Fail-loud split failure with a booked reason. Raised when any fold is
    empty (the A1-PIE VOID trap), when coverage is incomplete, or when folds
    overlap. Never silently produce a degenerate split."""


def fnv1a64(data: bytes) -> int:
    """FNV-1a-64, stdlib-only. Own copy — blocks are standalone; do not import
    the sibling block for this."""
    h = FNV_OFFSET
    for c in data:
        h ^= c
        h = (h * FNV_PRIME) & MASK64
    return h


def _assign(items: list[str], k: int, fold_of) -> list[list[int]]:
    folds: list[list[int]] = [[] for _ in range(k)]
    for i, item in enumerate(items):
        folds[fold_of(item)].append(i)
    # fail-loud invariants, checked here so no consumer can skip them:
    sizes = [len(f) for f in folds]
    empties = [b for b, s in enumerate(sizes) if s == 0]
    if empties:
        raise EmptyFoldError(
            f"EMPTY FOLD(S) {empties} (sizes {sizes} over {len(items)} items) — "
            "the split key never landed there. Booked reason (A1-PIE VOID, "
            "g7-wr-a1-pie-closure-1790891323): FNV-1a-64 low bits are weak — "
            "every our-to-move board hashes ODD, so raw low-bit %% k with even k "
            "leaves all even buckets empty. Use the HIGH-32 scheme "
            "(make_folds), never raw low bits.")
    total = sum(sizes)
    if total != len(items):
        raise EmptyFoldError(f"coverage failure: {total} assigned != {len(items)} items")
    seen: set[int] = set()
    for f in folds:
        for i in f:
            if i in seen:
                raise EmptyFoldError(f"disjointness failure: index {i} in two folds")
            seen.add(i)
    if seen != set(range(len(items))):
        raise EmptyFoldError("coverage failure: fold indices != item indices")
    return folds


def make_folds(items: list[str], k: int) -> list[list[int]]:
    """PROVEN scheme: fold(key) = (fnv1a64(key) >> 32) % k.

    items: distinct string keys (e.g. blocks/exact_minimax_labels to_key()).
    Returns fold -> list of item INDICES (not copies). Folds are disjoint and
    fully covering BY CONSTRUCTION (same key -> same fold); the invariants are
    asserted anyway (fail loud). Any empty fold raises EmptyFoldError.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not items:
        raise ValueError("make_folds: empty item list")
    for it in items:
        if not isinstance(it, str):
            raise TypeError(f"make_folds: items must be str, got {type(it).__name__}")
    return _assign(items, k, lambda s: (fnv1a64(s.encode("utf-8")) >> 32) % k)


def make_folds_lowbits(items: list[str], k: int) -> list[list[int]]:
    """UNSAFE — the VOIDed first attempt, kept ONLY so the trap stays
    detectable and testable: fold(key) = fnv1a64(key) % k on the RAW low bits.
    On even-parity key distributions (all-odd hashes) this leaves every even
    bucket empty and raises EmptyFoldError. Never use for a real split."""
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if not items:
        raise ValueError("make_folds_lowbits: empty item list")
    return _assign(items, k, lambda s: fnv1a64(s.encode("utf-8")) % k)


def fold_report(fold_scores: list[float]) -> dict:
    """mean +/- std over DATA FOLDS (population std, ddof=0 — the numpy
    convention used in the A1-PIE / A2-GA4444 receipts), plus the house
    verdict: std == 0 -> INCONCLUSIVE (a fold variance of exactly zero is a
    degeneracy, not a measurement — PREREG §2 rule 2), else 'measured'."""
    if not fold_scores:
        raise ValueError("fold_report: empty fold_scores")
    for s in fold_scores:
        if isinstance(s, bool) or not isinstance(s, (int, float)):
            raise TypeError(f"fold_report: scores must be numbers, got {s!r}")
    mean = statistics.fmean(fold_scores)
    std = statistics.pstdev(fold_scores)  # population std, matches np.std
    return {"mean": mean, "std": std,
            "verdict": "INCONCLUSIVE" if std == 0 else "measured"}


# ----------------------------------------------------------------------------
# SELF-TEST — <10 s CPU, single JSON verdict line.
# ----------------------------------------------------------------------------
def _synthetic_keys(n: int = 2423) -> list[str]:
    """9-char strings over '0','1','2' with an EVEN number of '1' chars —
    '1' is the only lowbit-odd char of the alphabet, so an even count mirrors
    the real boards' even-stone parity (every real our-to-move board hashes
    ODD under FNV-1a-64). Deterministic: sorted, first n."""
    all9 = ("".join(p) for p in product("012", repeat=9))
    even = sorted(k for k in all9 if k.count("1") % 2 == 0)
    if len(even) < n:
        raise AssertionError(f"synthetic corpus too small: {len(even)} < {n}")
    return even[:n]


def _self_test() -> int:
    keys = _synthetic_keys(2423)
    assert len(keys) == 2423 and len(set(keys)) == 2423

    # 0. checked invariant: on this corpus every FNV-1a-64 hash is ODD, which
    #    is exactly the mechanism of the booked low-bit trap.
    assert all(fnv1a64(k.encode("utf-8")) & 1 == 1 for k in keys)
    print(f"parity invariant OK: all {len(keys)} synthetic keys hash ODD "
          "(mirrors the real 3x3 corpus's even-stone parity)")

    # 1. proven high-32 scheme, k=5: non-empty, disjoint, fully covering.
    folds = make_folds(keys, 5)
    assert len(folds) == 5
    sizes = [len(f) for f in folds]
    assert all(s > 0 for s in sizes), f"empty fold (sizes {sizes})"
    flat = [i for f in folds for i in f]
    assert len(flat) == len(set(flat)) == 2423, "folds overlap or miss items"
    assert set(flat) == set(range(2423)), "folds do not cover all items"
    lo, hi = min(sizes), max(sizes)
    assert 400 <= lo <= hi <= 560, f"bucket imbalance {sizes}"
    print(f"high-32 mod 5 OK: sizes {sizes} (all non-empty, disjoint, covering)")

    # 2. the trap: raw low bits % 10 on the odd-only distribution leaves every
    #    even bucket empty -> EmptyFoldError must fire and be booked here.
    trap_fired = False
    try:
        make_folds_lowbits(keys, 10)
    except EmptyFoldError as e:
        trap_fired = True
        booked = str(e).split(" — ")[0]
        assert "EMPTY FOLD" in booked
        print(f"low-bit trap OK: EmptyFoldError fired and booked as expected ({booked})")
    assert trap_fired, "low-bit trap did NOT fire — the invariant is broken"

    # 3. fold_report: std == 0 -> INCONCLUSIVE; varying -> measured, and the
    #    numbers reproduce against the A1-PIE plateau 5-fold CV receipt.
    const = fold_report([0.9, 0.9, 0.9, 0.9, 0.9])
    assert const["verdict"] == "INCONCLUSIVE" and const["std"] == 0, const
    print(f"fold_report constant -> {const}")
    cv = fold_report([0.9289, 0.9288, 0.9407, 0.944, 0.9534])  # A1-PIE receipt folds
    assert cv["verdict"] == "measured", cv
    assert round(cv["mean"], 4) == 0.9392 and round(cv["std"], 4) == 0.0094, cv
    print(f"fold_report A1-PIE plateau folds -> mean={round(cv['mean'],4)} "
          f"std={round(cv['std'],4)} verdict={cv['verdict']} (matches receipt "
          "0.9392 +/- 0.0094)")

    print(json.dumps({"verdict": "PASS"}))
    return 0


if __name__ == "__main__":
    sys.exit(_self_test())
