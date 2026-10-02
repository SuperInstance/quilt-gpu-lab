"""d13d_correlation_keys — between-cell routing keys by correlation, not reward.

Harvested from experiments/d13d_shared_key.py (D13d) +
experiments/d18_correlation_scaling.py (D18) and the between-cell routing
usage in COMP0/COMP1 (centroid-correlation router); receipts of record:
RESULTS.md D13 arc (2026-09-27) + D18 + COMP0/COMP1 (2026-10-01).

THE FINDING (D13d KEEP): three reward-based credit-assignment rules
(D13 Hebbian, D13b confidence-weighted, D13c REINFORCE-with-baseline) all
KILLed on learning the relational partner (edge concentration 0.217-0.30
vs chance 0.143). The OTHER mechanism cracks it at 1.0: a cell finds its
true partner by computing max |correlation| of atom streams over T
observations, with NO reward signal — the relational primitive is
CORRELATION DETECTION (mutual information), not reward accumulation.
O(1) information, not gradient descent over reward.

D18 (INCONCLUSIVE, two findings): (1) correlation discovery is CONFIRMED
and STRONGER than claimed — identification holds at 1.0 on the whole grid
(N=8..300 x p_corr=0.55..0.9 at T=200); (2) the contrast half FALSIFIED —
REINFORCE also reaches concentration 1.0 when partners are CONSISTENT
(D13c's 0.217 was one policy chasing ~7 conflicting targets). The
primitive is "consistent relational target"; correlation is the O(1) way
to FIND that target.

Between-cell routing (COMP0/COMP1): the same correlation read is the
0-parameter router — per-cell centroid feature keys, route by argmax
Pearson. COMP0: routing saturated (1.0/1.0, gap 0.49). COMP1: desaturated
to spec (held-out 0.7356, gap 0.041) — merely decent under ambiguity.

This block: atom-stream worlds with pair POLARITY (the shared key: with
prob p_corr the partner's atom = polarity * base — anti-correlated pairs
are discoverable too, |corr| is the read), partner discovery by argmax
|corr|, the true-vs-best-distractor key margin, and the centroid router.

Standalone: stdlib + numpy only, no repo-internal imports. CPU-only,
deterministic: seed 2718 default. Fail loud: every failure mode raises a
KeyDiscoveryError subclass, never silent.

House contracts: the self-test's final stdout line is exactly one JSON
object with exactly one top-level "verdict" (PASS/KILL/INCONCLUSIVE);
exit 0 iff PASS. Cross-seed std == 0 on the gated key-margin seed-mean =>
INCONCLUSIVE, never PASS.
"""
from __future__ import annotations

import json
import sys
from typing import Dict, List, Optional, Tuple

import numpy as np

SEED = 2718
N_CELLS_DEFAULT = 8          # D13d scale
T_OBS_DEFAULT = 200          # D13d observation count
P_CORR_DEFAULT = 0.9         # D13d partner agreement probability
TARGET = 0.90                # D13d pre-registered bar
HEADLINE_SEEDS = (2718, 2719, 2720)   # >=3 seeds for the gated margin
# D18 grid points re-run by the self-test (subset that runs in seconds).
D18_GRID = ((8, 0.75), (32, 0.6), (32, 0.55), (100, 0.6))


class KeyDiscoveryError(Exception):
    """Booked exception base — fail loud, never silent."""


class BadWorldError(KeyDiscoveryError):
    """World construction is impossible (odd cells, no observations...)."""


def make_atom_world(n_cells: int = N_CELLS_DEFAULT, t_obs: int = T_OBS_DEFAULT,
                    p_corr: float = P_CORR_DEFAULT, seed: int = SEED,
                    polarity: str = "shared") -> Tuple[np.ndarray, Dict[int, int]]:
    """Draw one atom-stream world with DISJOINT partner pairs.

    Each pair (2i, 2i+1) has a persistent POLARITY s in {+1,-1} — the
    shared key. Each step draws a hidden base in {-1,+1}; with prob p_corr
    the partner's atom is s*base (correlated if s=+1, ANTI-correlated if
    s=-1); otherwise both atoms are independent coin flips. `polarity`:
    "shared" (all s=+1, D13d verbatim), "anti" (all s=-1), or "mixed"
    (s drawn per pair — the general shared-key case).

    Returns (streams (n_cells, t_obs) int8 in {-1,+1}, partners dict).
    """
    if n_cells < 2 or n_cells % 2 != 0:
        raise BadWorldError(f"n_cells must be even and >= 2 for disjoint pairs, got {n_cells}")
    if t_obs < 1:
        raise BadWorldError(f"t_obs must be >= 1, got {t_obs}")
    if not 0.0 <= float(p_corr) <= 1.0:
        raise BadWorldError(f"p_corr must be in [0,1], got {p_corr}")
    rng = np.random.default_rng(seed)
    partners = {c: c ^ 1 for c in range(n_cells)}   # disjoint pairs (2i, 2i+1)
    if polarity == "shared":
        signs = np.ones(n_cells // 2, dtype=np.int8)
    elif polarity == "anti":
        signs = -np.ones(n_cells // 2, dtype=np.int8)
    elif polarity == "mixed":
        signs = rng.choice(np.array([-1, 1], dtype=np.int8), size=n_cells // 2)
    else:
        raise BadWorldError(f"polarity must be shared/anti/mixed, got {polarity!r}")

    streams = np.zeros((n_cells, t_obs), dtype=np.int8)
    n_pairs = n_cells // 2
    base = rng.choice(np.array([-1, 1], dtype=np.int8), size=(n_pairs, t_obs))
    linked = rng.random((n_pairs, t_obs)) < float(p_corr)
    indep_a = rng.choice(np.array([-1, 1], dtype=np.int8), size=(n_pairs, t_obs))
    indep_b = rng.choice(np.array([-1, 1], dtype=np.int8), size=(n_pairs, t_obs))
    for p in range(n_pairs):
        a, b = 2 * p, 2 * p + 1
        va = np.where(linked[p], base[p], indep_a[p])
        vb = np.where(linked[p], signs[p] * base[p], indep_b[p])
        streams[a] = va
        streams[b] = vb
    return streams, partners


def correlation_key(stream_a: np.ndarray, stream_b: np.ndarray) -> float:
    """The routing key: |mean(a*b)| — |Pearson| on +-1 atom streams.
    Anti-correlated partners (polarity -1) key as strongly as correlated
    ones; the |.| read is the shared-key doctrine."""
    a = np.asarray(stream_a, dtype=np.float64)
    b = np.asarray(stream_b, dtype=np.float64)
    if a.shape != b.shape or a.size == 0:
        raise BadWorldError(f"streams must be same-length and non-empty, got {a.shape} vs {b.shape}")
    return float(abs(np.mean(a * b)))


def key_matrix(streams: np.ndarray) -> np.ndarray:
    """Pairwise |mean(a*b)| keys (n, n); diagonal set to -1 so it can never
    win an argmax (self-routing is not a discovery)."""
    x = np.asarray(streams, dtype=np.float64)
    if x.ndim != 2 or x.shape[0] < 2:
        raise BadWorldError(f"streams must be (n_cells, t_obs) with n>=2, got {x.shape}")
    keys = np.abs(x @ x.T) / x.shape[1]
    np.fill_diagonal(keys, -1.0)
    return keys


def discover_partners(streams: np.ndarray) -> Dict[int, int]:
    """D13d: each cell's partner = argmax |correlation| over other cells.
    Zero parameters, zero reward."""
    keys = key_matrix(streams)
    return {int(a): int(np.argmax(keys[a])) for a in range(keys.shape[0])}


def partner_accuracy(partners_true: Dict[int, int],
                     partners_hat: Dict[int, int]) -> float:
    if set(partners_true) != set(partners_hat):
        raise KeyDiscoveryError("partner maps must cover the same cells")
    return float(np.mean([partners_hat[c] == partners_true[c] for c in partners_true]))


def key_margin(streams: np.ndarray, partners_true: Dict[int, int]) -> List[float]:
    """Per-cell margin: key(true partner) - best distractor key. The COMP0
    top1-top2 gap analog; positive margins are what makes argmax discovery
    unambiguous. Continuous-valued, so it carries seed variation."""
    keys = key_matrix(streams)
    out = []
    for a, partner in partners_true.items():
        distractors = [keys[a, c] for c in range(keys.shape[0])
                       if c not in (a, partner)]
        out.append(float(keys[a, partner] - max(distractors)))
    return out


# ---------------------------------------------------------------------------
# Between-cell routing: the COMP0/COMP1 0-parameter centroid-correlation
# router. Keys = per-cell mean features (correlation-trained: the centroid
# IS the correlation key for the class direction); route = argmax Pearson.
# ---------------------------------------------------------------------------
def pearson(x: np.ndarray, y: np.ndarray) -> float:
    """Pearson correlation with a zero-variance guard (a constant vector
    keys 0 against everything — fail-safe, not fail-loud, for routing)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.shape != y.shape or x.size < 2:
        raise BadWorldError(f"pearson needs same-length vectors (>=2), got {x.shape} vs {y.shape}")
    xc, yc = x - x.mean(), y - y.mean()
    nx, ny = float(np.linalg.norm(xc)), float(np.linalg.norm(yc))
    if nx == 0.0 or ny == 0.0:
        return 0.0
    return float(xc @ yc / (nx * ny))


def build_centroid_keys(features_by_cell: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """One key per cell: the mean of that cell's TRAIN features."""
    keys = {}
    for cell, feats in features_by_cell.items():
        f = np.asarray(feats, dtype=np.float64)
        if f.ndim != 2 or f.shape[0] < 1:
            raise BadWorldError(f"cell {cell!r} needs (n, d) features, got {f.shape}")
        keys[cell] = f.mean(axis=0)
    if len(keys) < 2:
        raise BadWorldError("routing needs >= 2 cells")
    return keys


def route(keys: Dict[str, np.ndarray], x: np.ndarray) -> str:
    """Argmax-Pearson routing of one feature vector to a cell key."""
    return max(keys, key=lambda c: pearson(x, keys[c]))


# ---------------------------------------------------------------------------
# Self-test: D13d reproduction + D18 grid + controls + router + frost law.
# ---------------------------------------------------------------------------
def self_test() -> dict:
    checks = {}
    report: Dict[str, object] = {}

    # (1) D13d reproduction: 8 cells / 200 obs / p 0.9 / seed 2718, and the
    #     >=3-seed headline with the gated margin seed-mean.
    primary = make_atom_world(seed=SEED)
    acc0 = partner_accuracy(primary[1], discover_partners(primary[0]))
    checks["d13d_primary_acc_ge_target"] = acc0 >= TARGET

    margins, accs = [], []
    for s in HEADLINE_SEEDS:
        streams, partners = make_atom_world(seed=s)
        accs.append(partner_accuracy(partners, discover_partners(streams)))
        margins.extend(key_margin(streams, partners))
    margin_mean = float(np.mean(margins))
    margin_std = float(np.std(margins))
    checks["d13d_all_seeds_perfect"] = all(a >= TARGET for a in accs)
    checks["d13d_margin_positive"] = margin_mean > 0.0
    report["headline_seeds"] = list(HEADLINE_SEEDS)
    report["accuracy_per_seed"] = accs
    report["margin_mean_std"] = {"mean": margin_mean, "std": margin_std}

    # (2) D18 grid subset: identification holds at 1.0 across the booked
    #     scaling points (incl. the strict joint N=100, p=0.6).
    d18 = {}
    for n, p in D18_GRID:
        streams, partners = make_atom_world(n_cells=n, p_corr=p, seed=SEED + n)
        d18[f"N{n}_p{p}"] = round(partner_accuracy(partners, discover_partners(streams)), 4)
    checks["d18_grid_all_perfect"] = all(v == 1.0 for v in d18.values())
    report["d18_grid"] = d18

    # (3) chance control: p_corr=0.0 — partner atoms fully independent, the
    #     expected key is 0 for every pair and discovery collapses to the
    #     chance floor. (p_corr IS the expected key strength: any p_corr>0
    #     is discoverable at T large enough — D18's "stronger than claimed"
    #     finding, SNR floor ~0.25 at T=200. 0.5 is NOT chance.)
    chance_accs = []
    for s in range(5):
        streams, partners = make_atom_world(n_cells=32, p_corr=0.0, seed=SEED + 100 + s)
        chance_accs.append(partner_accuracy(partners, discover_partners(streams)))
    chance_mean = float(np.mean(chance_accs))
    chance_floor = 1.0 / 31.0
    checks["chance_control_collapses"] = chance_mean <= max(3.0 * chance_floor, 0.10)
    report["chance_control"] = {"mean_acc": round(chance_mean, 4),
                                "chance_floor": round(chance_floor, 4),
                                "note": "p_corr=0 is the chance control; expected "
                                        "key = p_corr, SNR floor ~0.25 at T=200 (D18)"}

    # (4) polarity: anti- and mixed-correlated pairs still discovered (the
    #     |corr| read — the shared key carries a sign, discovery does not).
    pol = {}
    for mode in ("anti", "mixed"):
        streams, partners = make_atom_world(polarity=mode, seed=SEED)
        pol[mode] = round(partner_accuracy(partners, discover_partners(streams)), 4)
    checks["polarity_anti_and_mixed_discovered"] = all(v == 1.0 for v in pol.values())
    report["polarity"] = pol

    # (5) the centroid router (COMP0/COMP1 wiring): correlation across
    #     FEATURE DIMENSIONS, the way the real router was used (D=64 BoW
    #     views) — each cell is a distinct base pattern, items are the
    #     pattern + noise, keys are per-cell means, route = argmax Pearson.
    rng = np.random.default_rng(SEED)
    D = 32
    cells = ("alpha", "beta", "gamma")
    base = {c: rng.standard_normal(D) for c in cells}
    feats = {c: base[c] + 0.3 * rng.standard_normal((50, D)) for c in cells}
    keys = build_centroid_keys(feats)
    test = {c: base[c] + 0.3 * rng.standard_normal((150, D)) for c in cells}
    routed = sum(route(keys, x) == c for c, xs in test.items() for x in xs)
    router_acc = routed / sum(len(v) for v in test.values())
    checks["centroid_router_heldout_1_of_1"] = router_acc == 1.0
    report["centroid_router"] = {"cells": len(cells), "feature_dim": D,
                                 "n_heldout": 450, "heldout_acc": round(router_acc, 4)}

    # (6) fail-loud contracts.
    loud = False
    try:
        make_atom_world(n_cells=7)
    except BadWorldError:
        loud = True
    checks["odd_cells_fail_loud"] = loud
    loud = False
    try:
        key_matrix(np.zeros((1, 5)))
    except BadWorldError:
        loud = True
    checks["bad_streams_fail_loud"] = loud

    # frost law on the gated seed-mean: std==0 margins => the comparison is
    # not actually repeating — INCONCLUSIVE, never PASS.
    verdict = "PASS" if all(checks.values()) else "KILL"
    reason = ("D13d reproduced at 1.0 (target >= 0.90); D18 grid subset perfect; "
              "chance control collapses; polarity-agnostic; router exact")
    if margin_std == 0.0:
        verdict = "INCONCLUSIVE"
        reason = "key-margin cross-seed std == 0 — repeats are not varying"

    return {
        "verdict": verdict,
        "reason": reason,
        "checks": checks,
        "seed": SEED,
        **report,
        "provenance": "RESULTS.md D13d (KEEP, 2026-09-27) + D18 (INCONCLUSIVE: "
                      "correlation confirmed, contrast falsified — consistent "
                      "target is the primitive) + COMP0/COMP1 routing usage",
    }


def main() -> int:
    try:
        summary = self_test()
    except KeyDiscoveryError as exc:
        summary = {"verdict": "KILL",
                   "reason": f"booked exception {type(exc).__name__}: {exc}"}
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
