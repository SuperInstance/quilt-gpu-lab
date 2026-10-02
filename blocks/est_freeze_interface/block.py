"""est_freeze_interface — determinacy estimators behind ONE validated interface.

Harvested from results/est_freeze/{estimators.py, crossval.py, analysis2.py}
(lane EST-FREEZE, 2026-10-01); receipts of record: RESULTS.md
"[DONE 15:4x EST-FREEZE]" + "[KEEPER FOLD 15:2x EST-FREEZE]".

THE FROZEN INTERFACE (verbatim from the lane; seed default 0 is part of
the frozen contract — "fix the permutation seed (seed=0) so C2 is exactly
0 by construction"; this block's own self-test data draws use the house
seed 2718):

    score(records, spec, est="E3", weight="operational", seed=0, nperm=120)
        -> float in [0,1]

    records : list of per-tick dicts (any shape; the spec's callables read it)
    spec    : {"inp": callable(record)->hashable   (input channel phi),
               "out": callable(record)->hashable   (output symbol psi),
               "O": int declared output alphabet size,
               "rule": callable(record)->hashable  (optional declared atom)}
    weight  : "operational" | "uniform" | "degenerate" (bin weighting)
    est     : "E0".."E5"

SIX independent estimators (all behind that one signature):
    E0 plug-in conditional entropy + Miller-Madow   (the prereg formula)
    E1 excess mode-agreement vs permutation floor
    E2 effective-alphabet / coverage-width
    E3 permutation-exact normalized MI, bias-corrected  (1 - Hcond/Hcond_null)
    E4 split-half predictive consistency (tick-parity, TV), seed-invariant
    E5 per-bin purity, Wilson lower bound (pure bin -> exact 1.0)

THE FINDINGS this interface produced (booked):
    - FROZEN-V1 = NONE: criterion C3 (spread <= 0.15 across
      operational/uniform/degenerate on real sockets) is UNSATISFIABLE for
      all six — but the stationary-truth synthetic control (identical true
      determinacy across the three input distributions) shows the good
      estimators contribute <= ~0.04 spread (E3 0.003-0.039): the real
      spread is genuine socket INPUT-DISTRIBUTION SENSITIVITY, not
      estimator bias. H5 as written conflated the two.
    - Measure pair frozen: E3 primary (smallest stationary instability +
      smallest |bias|@O2, exact atoms, interface-identical), E0 reserve.
    - The D2 build A/B disagreement was the ENCODER, not the estimator
      (same math reproduced both builds' numbers exactly); with declared
      frozen encoders the H6 range is 1.000 - 0.352 = 0.648 >= 0.5.
    - Estimator x test verdicts: E0/E3 pass all but C3; E1 bias fail;
      E2 C3+C4 fail; E4 disqualified (atoms 0.998, bias 0.564); E5
      bias+stat fail.

This block: the six estimators verbatim + the validation battery as
importable functions (synthetic atoms, analytic-truth noisy channels,
stationary-truth control, an input-sensitivity socket that reproduces the
C3 unsatisfiability on synthetic material, and the frozen_v1 criterion).

Standalone: stdlib + numpy only, no repo-internal imports, CPU-only,
seconds. Fail loud: unknown est/weight raises ValueError (as at source).

House contracts: final stdout line of the self-test is exactly one JSON
object with exactly one top-level "verdict" (PASS/KILL/INCONCLUSIVE);
exit 0 iff PASS; cross-seed std == 0 on a gated seed-mean => INCONCLUSIVE,
never PASS.
"""
from __future__ import annotations

import json
import math
import sys
from typing import Dict, List, Sequence, Tuple

import numpy as np

LOG2 = math.log(2.0)

SEED = 2718            # house seed (self-test data draws)
SCORE_SEED = 0         # frozen score() permutation seed (EST-FREEZE law)
NPERM = 120
ESTIMATORS = ("E0", "E1", "E2", "E3", "E4", "E5")
WEIGHTS = ("operational", "uniform", "degenerate")
FROZEN_PAIR = ("E3", "E0")   # keeper fold: E3 primary, E0 reserve
C3_BAR = 0.15                # the unsatisfiable frozen spread bar
H6_RANGE_BAR = 0.5           # reflex - episodic with declared encoders


# ---------------------------------------------------------------- encoding ---
def _encode(records, spec):
    """-> (binidx int array, yidx int array, B, O_obs) with stable symbol ordering."""
    inp_fn, out_fn = spec["inp"], spec["out"]
    raw_b = [inp_fn(r) for r in records]
    raw_y = [out_fn(r) for r in records]
    bmap, ymap = {}, {}
    binidx = np.empty(len(raw_b), dtype=np.int64)
    yidx = np.empty(len(raw_y), dtype=np.int64)
    for i, b in enumerate(raw_b):
        if b not in bmap:
            bmap[b] = len(bmap)
        binidx[i] = bmap[b]
    for i, y in enumerate(raw_y):
        if y not in ymap:
            ymap[y] = len(ymap)
        yidx[i] = ymap[y]
    return binidx, yidx, len(bmap), len(ymap)


def _counts(binidx, yidx, B, O):
    c = np.zeros((B, O), dtype=np.float64)
    np.add.at(c, (binidx, yidx), 1.0)
    return c


def _bin_weights(counts, weight):
    n_b = counts.sum(axis=1)
    n = n_b.sum()
    if n <= 0:
        return np.zeros_like(n_b)
    if weight == "operational":
        return n_b / n
    if weight == "uniform":
        live = n_b > 0
        w = np.zeros_like(n_b)
        w[live] = 1.0 / live.sum()
        return w
    if weight == "degenerate":
        w = np.zeros_like(n_b)
        w[int(np.argmax(n_b))] = 1.0
        return w
    raise ValueError(weight)


def _row_entropy_nat(counts):
    n_b = counts.sum(axis=1, keepdims=True)
    p = np.divide(counts, n_b, out=np.zeros_like(counts), where=n_b > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(p > 0, p * np.log(p), 0.0)
    return -plogp.sum(axis=1)  # nats


def _mm_correction_nat(counts):
    n_b = counts.sum(axis=1)
    K_b = (counts > 0).sum(axis=1)
    corr = np.where((n_b > 0) & (K_b > 1), (K_b - 1) / (2.0 * n_b), 0.0)
    return corr


def _wilson_lb(p, n, z=1.96):
    if n <= 0:
        return 0.0
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, min(1.0, center - half))


# ------------------------------------------------------------- estimators ---
def score(records, spec, est="E3", weight="operational", seed=0, nperm=120,
          tv_norm=None, n_min=1):
    """THE frozen interface. records + spec in, determinacy in [0,1] out."""
    if len(records) == 0:
        return float("nan")
    binidx, yidx, B, O_obs = _encode(records, spec)
    O_decl = int(spec.get("O", O_obs))
    return _score_core(binidx, yidx, B, O_decl, O_obs, est, weight, seed,
                       nperm, tv_norm, n_min)


def _score_core(binidx, yidx, B, O_decl, O_obs, est, weight, seed, nperm,
                tv_norm, n_min):
    counts = _counts(binidx, yidx, B, O_obs)
    w = _bin_weights(counts, weight)
    if est == "E0":
        H = _row_entropy_nat(counts) + _mm_correction_nat(counts)
        Hcond = float((w * H).sum())
        return _clamp(1.0 - Hcond / math.log(O_decl))
    if est == "E1":
        A_obs = float((w * (counts.max(axis=1) / np.maximum(counts.sum(axis=1), 1))).sum())
        rng = np.random.default_rng(seed)
        A_null = 0.0
        for _ in range(nperm):
            yp = rng.permutation(yidx)
            cp = _counts(binidx, yp, B, O_obs)
            A_null += float((w * (cp.max(axis=1) / np.maximum(cp.sum(axis=1), 1))).sum())
        A_null /= nperm
        if A_null >= 1.0:
            return 0.0
        return _clamp((A_obs - A_null) / (1.0 - A_null))
    if est == "E2":
        k_b = np.exp(_row_entropy_nat(counts))  # effective outcome count in [1,O]
        det_b = (O_decl - k_b) / (O_decl - 1.0)
        return _clamp(float((w * det_b).sum()))
    if est == "E3":
        Hcond = _row_entropy_nat(counts) + _mm_correction_nat(counts)
        Hcond_obs = float((w * Hcond).sum())
        rng = np.random.default_rng(seed)
        Hc_null = 0.0
        for _ in range(nperm):
            yp = rng.permutation(yidx)
            cp = _counts(binidx, yp, B, O_obs)
            hp = _row_entropy_nat(cp) + _mm_correction_nat(cp)
            Hc_null += float((w * hp).sum())
        Hc_null /= nperm
        if Hc_null <= 0:
            return 1.0 if Hcond_obs <= 0 else 0.0
        return _clamp(1.0 - Hcond_obs / Hc_null)
    if est == "E4":
        # deterministic tick-parity split -> seed invariant
        idx = np.arange(len(yidx))
        c_even = _counts(binidx[idx % 2 == 0], yidx[idx % 2 == 0], B, O_obs)
        c_odd = _counts(binidx[idx % 2 == 1], yidx[idx % 2 == 1], B, O_obs)
        alpha = 0.5
        p_e = (c_even + alpha) / (c_even.sum(axis=1, keepdims=True) + alpha * O_obs)
        p_o = (c_odd + alpha) / (c_odd.sum(axis=1, keepdims=True) + alpha * O_obs)
        TV = 0.5 * np.abs(p_e - p_o).sum(axis=1)
        tmax = (1.0 - 1.0 / O_decl) if tv_norm is None else tv_norm
        det_b = np.clip(1.0 - TV / tmax, 0.0, 1.0)
        return _clamp(float((w * det_b).sum()))
    if est == "E5":
        mode = counts.max(axis=1)
        n_b = counts.sum(axis=1)
        det_b = np.zeros(B)
        for b in range(B):
            if n_b[b] <= 0:
                continue
            if n_b[b] < n_min:
                continue
            if mode[b] >= n_b[b]:
                det_b[b] = 1.0  # exact pure bin
            else:
                det_b[b] = _wilson_lb(mode[b] / n_b[b], n_b[b])
        return _clamp(float((w * det_b).sum()))
    raise ValueError(est)


def _clamp(x):
    if x != x:  # nan
        return x
    return max(0.0, min(1.0, float(x)))


# ------------------------------------------------------- validation battery ---
def synthetic_atoms(n: int = 999) -> Dict[int, Tuple[list, dict]]:
    """C1 (crossval.py): deterministic maps over 17 cycling bins, O=2..6.
    Every estimator should read exactly 1.000 (E4 booked 0.998 — the
    disqualified one)."""
    m = 17
    bins = [i % m for i in range(n)]
    atoms = {}
    for K in range(2, 7):
        recs = [{"b": b} for b in bins]
        spec = {"inp": lambda r: r["b"],
                "out": lambda r, K=K: (r["b"] * 7 + 3) % K, "O": K}
        atoms[K] = (recs, spec)
    return atoms


def noisy_channels(n: int = 999, seed: int = SEED) -> Dict[Tuple[int, float], Tuple[list, dict, float]]:
    """Analytic-truth stochastic channels (crossval.py): keep the atom's
    true symbol with prob q, else redraw uniformly (redraw may coincide).
    Truth: p_true = q + (1-q)/K, others (1-q)/K -> truth = 1 - H/ln K."""
    m = 17
    bins = [i % m for i in range(n)]
    out = {}
    for K in (2, 3, 6):
        for qq in (0.9, 0.75, 0.6):
            rng = np.random.default_rng(seed + K * 10 + int(qq * 100))
            ys = []
            for b in bins:
                y = (b * 7 + 3) % K
                if rng.random() > qq:
                    y = int(rng.integers(0, K))
                ys.append(y)
            recs = [{"b": b, "y": y} for b, y in zip(bins, ys)]
            spec = {"inp": lambda r: r["b"], "out": lambda r: r["y"], "O": K}
            p = (1.0 - qq) / K
            H = -(qq + p) * math.log(qq + p) - (K - 1) * p * math.log(p) if p > 0 else 0.0
            out[(K, qq)] = (recs, spec, 1.0 - H / math.log(K))
    return out


def stationary_control(K: int, p_main: float, n: int = 999, nbins: int = 40,
                       seed: int = SEED) -> Dict[str, dict]:
    """analysis2.py's stationary-truth control: the SAME conditional p(y|b)
    for every bin, sampled under three input distributions. True
    determinacy is identical across dists, so each estimator's op/uni/deg
    spread is PURE estimator instability (the synthetic floor H5 must
    subtract)."""
    rng = np.random.default_rng(seed)
    p = np.full(K, (1.0 - p_main) / (K - 1)) if K > 1 else np.array([1.0])
    p[0] = p_main
    H = -sum(pi * math.log(pi) for pi in p if pi > 0)
    truth = 1.0 - H / math.log(K)

    def sample(bin_w):
        b = rng.choice(nbins, size=n, p=bin_w)
        y = np.array([rng.choice(K, p=p) for _ in range(n)])
        return [{"b": int(bb), "y": int(yy)} for bb, yy in zip(b, y)]

    zipf = 1.0 / (np.arange(1, nbins + 1) ** 1.2)
    zipf /= zipf.sum()
    uni = np.full(nbins, 1.0 / nbins)
    deg = np.zeros(nbins)
    deg[0] = 1.0
    recs = {"operational": sample(zipf), "uniform": sample(uni),
            "degenerate": sample(deg)}
    spec = {"inp": lambda r: r["b"], "out": lambda r: r["y"], "O": K}
    row: Dict[str, dict] = {"truth": round(truth, 4)}
    for e in ESTIMATORS:
        vs = [score(recs[w], spec, est=e, weight=w, seed=SCORE_SEED, nperm=NPERM)
              for w in WEIGHTS]
        row[e] = {"op": round(vs[0], 4), "uni": round(vs[1], 4),
                  "deg": round(vs[2], 4), "spread": round(max(vs) - min(vs), 4)}
    return row


def sensitivity_socket(n: int = 2000, nbins: int = 20, seed: int = SEED):
    """A socket whose TRUE per-bin determinacy DIFFERS by bin (even bins:
    deterministic atom; odd bins: uniform noise). Per-bin truth is fixed,
    so any op/uni/deg spread an estimator reports is genuine
    input-distribution sensitivity — the H5 conflation, on synthetic
    material. Returns (records per weight, spec)."""
    rng = np.random.default_rng(seed)

    def draw(bin_w):
        b = rng.choice(nbins, size=n, p=bin_w)
        recs = []
        for bb in b:
            y = (bb * 7 + 3) % 2 if bb % 2 == 0 else int(rng.integers(0, 2))
            recs.append({"b": int(bb), "y": int(y)})
        return recs

    op_w = 0.8 / (nbins // 2) if nbins // 2 else None
    w_op = np.array([op_w if b % 2 == 0 else 0.2 / (nbins // 2)
                     for b in range(nbins)])
    w_op = w_op / w_op.sum()
    uni = np.full(nbins, 1.0 / nbins)
    deg = np.zeros(nbins)
    deg[1] = 1.0   # one ODD (pure-noise) bin: degenerate leg sees noise only
    spec = {"inp": lambda r: r["b"], "out": lambda r: r["y"], "O": 2}
    return ({"operational": draw(w_op), "uniform": draw(uni),
             "degenerate": draw(deg)}, spec)


def frozen_v1(battery_by_est: Dict[str, dict], bar: float = C3_BAR) -> dict:
    """The frozen criterion, honestly and CONJUNCTIVELY: an estimator
    qualifies only if it is exact on atoms, within the bias bar, has the
    small stationary floor, AND has C3 spread <= bar on the socket. On
    real (and sensitivity-socket) material NOTHING qualifies — the
    shortlist E0/E3 pass everything BUT C3, the rest fail the other
    criteria — so FROZEN-V1 = NONE. That is the booked finding, not a
    failure of this function."""
    rows = {}
    for e, r in battery_by_est.items():
        rows[e] = {"atoms": bool(r["atoms"]), "bias": bool(r["bias"]),
                   "stationary": bool(r["stationary"]),
                   "c3_spread": float(r["c3_spread"]),
                   "c3": float(r["c3_spread"]) <= bar}
        rows[e]["qualifies"] = all(rows[e][k] for k in ("atoms", "bias",
                                                        "stationary", "c3"))
    winners = [e for e, r in rows.items() if r["qualifies"]]
    return {"FROZEN_V1": winners[0] if len(winners) == 1 else (winners or "NONE"),
            "c3_bar": bar, "battery": rows,
            "note": "C3 unsatisfiable by the otherwise-qualified pair => NONE "
                    "by the frozen criterion; the stationary control "
                    "attributes the spread to input sensitivity, not "
                    "estimator bias"}


# ---------------------------------------------------------------------------
# Self-test: the C1/bias/stationary/sensitivity battery on synthetic material.
# ---------------------------------------------------------------------------
def self_test() -> dict:
    checks: Dict[str, bool] = {}
    report: Dict[str, object] = {}

    # (1) C1 atoms: the frozen pair is EXACT on deterministic maps, O=2..6.
    atoms = synthetic_atoms()
    c1 = {str(K): {e: round(score(recs, spec, est=e, seed=SCORE_SEED,
                                  nperm=NPERM), 6)
                   for e in ESTIMATORS}
          for K, (recs, spec) in atoms.items()}
    checks["c1_frozen_pair_exact"] = all(
        c1[str(K)][e] == 1.0 for K in atoms for e in FROZEN_PAIR)
    checks["c1_others_near_one"] = all(
        c1[str(K)][e] >= 0.99 for K in atoms for e in ESTIMATORS)
    report["C1_atoms"] = c1

    # (2) bias vs analytic truth: frozen pair within 0.15 everywhere
    #     (booked 0.049 at O2, n=999, nperm=120); E1/E5 booked worse.
    bias: Dict[str, dict] = {}
    worst = {e: 0.0 for e in ESTIMATORS}
    for (K, q), (recs, spec, truth) in noisy_channels().items():
        row = {"truth": round(truth, 4)}
        for e in ESTIMATORS:
            b = score(recs, spec, est=e, seed=SCORE_SEED, nperm=NPERM) - truth
            row[e] = round(b, 4)
            worst[e] = max(worst[e], abs(b))
        bias[f"O{K}_q{q}"] = row
    checks["bias_frozen_pair_within_015"] = all(
        worst[e] <= 0.15 for e in FROZEN_PAIR)
    report["bias_worst_abs_by_est"] = {e: round(worst[e], 4) for e in ESTIMATORS}
    report["bias_table"] = bias

    # (3) stationary-truth control: the frozen pair's spread is the small
    #     synthetic floor (booked E3 0.003-0.039, E0 <= 0.065); gated as a
    #     3-data-seed seed-mean with the frost law applied.
    spreads = {e: [] for e in FROZEN_PAIR}
    for s in (SEED, SEED + 1, SEED + 2):
        row = stationary_control(2, 0.80, seed=s)
        for e in FROZEN_PAIR:
            spreads[e].append(row[e]["spread"])
    mean_spread = {e: float(np.mean(v)) for e, v in spreads.items()}
    std_spread = {e: float(np.std(v)) for e, v in spreads.items()}
    checks["stationary_floor_small"] = all(mean_spread[e] <= 0.08 for e in FROZEN_PAIR)
    report["stationary_control_O2_p08"] = {
        "per_seed_spread": {e: v for e, v in spreads.items()},
        "mean": {e: round(m, 4) for e, m in mean_spread.items()},
        "std": {e: round(sd, 6) for e, sd in std_spread.items()}}
    row37 = stationary_control(3, 0.70, seed=SEED + 3)
    report["stationary_control_O3_p07"] = {e: row37[e] for e in FROZEN_PAIR}

    # (4) the H5 conflation, demonstrated: per-bin truth fixed, spread HUGE
    #     for the otherwise-qualified pair; then the CONJUNCTIVE frozen
    #     criterion over the whole battery -> FROZEN-V1 = NONE.
    recs_s, spec_s = sensitivity_socket()
    c3 = {}
    for e in ESTIMATORS:
        vs = [score(recs_s[w], spec_s, est=e, weight=w, seed=SCORE_SEED,
                    nperm=NPERM) for w in WEIGHTS]
        c3[e] = round(max(vs) - min(vs), 4)
    battery = {e: {"atoms": all(c1[str(K)][e] == 1.0 for K in atoms),
                   "bias": worst[e] <= 0.15,
                   # stationary leg measured for the frozen pair (the
                   # shortlist the keeper froze); other estimators carry
                   # their booked disqualifications from atoms/bias, so the
                   # missing leg cannot flip them to qualified.
                   "stationary": (mean_spread[e] <= 0.08
                                  if e in FROZEN_PAIR else False),
                   "c3_spread": c3[e]}
              for e in ESTIMATORS}
    fv = frozen_v1(battery)
    checks["sensitivity_spread_large"] = c3["E3"] > C3_BAR
    checks["frozen_v1_none_reproduced"] = fv["FROZEN_V1"] == "NONE"
    report["sensitivity_socket_c3"] = c3
    report["frozen_v1"] = fv

    # (5) H6 with a declared encoder: deterministic channel vs a noisy
    #     episodic-like channel — range >= 0.5 (booked 0.648 at source).
    recs_det, spec_det = atoms[2]
    noisy = noisy_channels()
    recs_epi, spec_epi, _truth = noisy[(2, 0.6)]   # ~mid determinacy
    h6 = {e: round(score(recs_det, spec_det, est=e, seed=SCORE_SEED, nperm=NPERM)
                   - score(recs_epi, spec_epi, est=e, seed=SCORE_SEED, nperm=NPERM), 4)
          for e in FROZEN_PAIR}
    checks["h6_range_with_declared_encoder"] = all(v >= H6_RANGE_BAR
                                                   for v in h6.values())
    report["h6_range_reflex_minus_episodic"] = h6

    # (6) interface contracts: deterministic under the frozen seed; the
    #     E0/E2 branch has no rng at all; unknown est/weight raise loud.
    a = score(recs_det, spec_det, est="E3", seed=SCORE_SEED, nperm=NPERM)
    b = score(recs_det, spec_det, est="E3", seed=SCORE_SEED, nperm=NPERM)
    checks["frozen_seed_deterministic"] = a == b
    loud = False
    try:
        score(recs_det, spec_det, est="E9")
    except ValueError:
        loud = True
    checks["unknown_est_fails_loud"] = loud
    loud = False
    try:
        score(recs_det, spec_det, est="E3", weight="sandwich")
    except ValueError:
        loud = True
    checks["unknown_weight_fails_loud"] = loud

    # frost law on the gated seed-mean (stationary spread across data seeds)
    verdict = "PASS" if all(checks.values()) else "KILL"
    reason = ("frozen pair E3/E0: exact atoms, bias <= 0.15, stationary "
              "floor <= 0.08, C3 unsatisfiable reproduced (FROZEN-V1 NONE), "
              "H6 range >= 0.5 with declared encoder")
    if any(std_spread[e] == 0.0 for e in FROZEN_PAIR):
        verdict = "INCONCLUSIVE"
        reason = ("stationary-spread cross-seed std == 0 — repeats are not "
                  "varying; the floor estimate is meaningless")

    return {
        "verdict": verdict,
        "reason": reason,
        "checks": checks,
        "seed": SEED,
        "frozen_pair": list(FROZEN_PAIR),
        "frozen_measure_law": "E3 primary / E0 reserve (keeper fold, 2026-10-01)",
        **report,
        "provenance": "RESULTS.md EST-FREEZE (2026-10-01): FROZEN-V1 = NONE; "
                      "the encoder, not the formula, was the blocker",
    }


def main() -> int:
    try:
        summary = self_test()
    except ValueError as exc:
        summary = {"verdict": "KILL",
                   "reason": f"booked exception ValueError: {exc}"}
    print(json.dumps(summary))
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
