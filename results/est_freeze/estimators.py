#!/usr/bin/env python3
"""EST-FREEZE — D2 determinacy estimators with one shared interface.

Prereg: proposals/runs/EST-freeze.md (frozen before this file was run).

    score(records, spec, est=..., weight=..., seed=0, nperm=120) -> float in [0,1]

`records` : list of per-tick dicts (canonical D2 trace record).
`spec`    : dict with keys
              inp  : callable(record)->hashable   (input channel phi)
              out  : callable(record)->hashable   (output symbol psi)
              O    : int   declared output alphabet size
              rule : callable(record)->hashable   (optional declared atom)
`weight`  : 'operational' | 'uniform' | 'degenerate'
`est`     : 'E0'..'E5'

Estimators (all independent code paths):
  E0 plug-in conditional entropy (the prereg formula) + Miller-Madow
  E1 excess mode-agreement vs permutation floor
  E2 effective-alphabet / coverage-width
  E3 bias-corrected normalized MI (permutation-exact)  == 1 - Hcond/mean(Hcond_null)
  E4 split-half predictive consistency (tick-parity, TV), seed-invariant
  E5 per-bin purity, Wilson lower bound (pure bin -> exact 1.0)
"""
import math
import numpy as np

LOG2 = math.log(2.0)


# ---------------------------------------------------------------- encoding ---
def _encode(records, spec):
    """-> (binidx int array, yidx int array, B, O) with stable symbol ordering."""
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
    n = counts.sum()
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
