#!/usr/bin/env python3
"""H1B-VISION (lane H1B-VISION, arm (i) of the H1-WORLDGRAN resurrection fork) — CPU-only, 0 Wh.

Prereg: proposals/runs/H1B-vision.md (frozen before fire).
Reuses results/d2_v1/{d2_v1_traces.json,d2_v1_twins_result.json} + frozen encoders
(results/d2_v1/scripts/d2_v1_common.py) + R3 machinery (results/h5_repair/h5_repair.py). No GPU.

G0 = H5-stability gate on sensors.vision per-world determinacy (resample width <= 0.10 AND
     family definition-spread <= 0.15).  G1 = rho(candidate, per-world vision gap) <= -0.30 with
     CI excluding 0.  rho is NOT tested unless G0 is green.
"""
import json, os, sys, math, time
import numpy as np

LAB = "/home/eileen/projects/quilt-gpu-lab"
sys.path.insert(0, os.path.join(LAB, "results/d2_v1/scripts"))
sys.path.insert(0, os.path.join(LAB, "results/h5_repair"))
import d2_v1_common as C            # noqa: E402
import h5_repair as H               # noqa: E402

OUT = os.path.join(LAB, "results/h1b_vision")
SEED = H.SEED                       # 2718
NPERM = H.NPERM                     # 120
B_BOOT = 1000                       # G0 resample bootstrap
B_RHO = 2000                        # G1 rho bootstrap
PER = 1000
TEST_IDS = list(range(140, 200))    # 60 held-out worlds
SOCK = "sensors.vision"
O = 512
O_DELTA = 2 * O - 1                 # 1023
WIDTH_TOL = 0.10                    # G0 resample-width bar (n-adjusted H5)
DEF_TOL = 0.15                      # G0 definition-spread bar (H5's own)
BAR = -0.30                         # G1 effect-size bar
POWER_BAR_1S = 0.318
POWER_BAR_2S = 0.355
F_GATE = ["e3_op", "e3_uni", "e1_acc", "nmi", "rank"]          # gating family (same target)
F_DIAG = ["e3_deg", "bits", "perch", "coarse"]                 # reported, non-gating
CHUNK = 30                          # permutation block (caps peak RAM)


# ------------------------------------------------------------ rank helpers ----
def avg_ranks(x):
    x = np.asarray(x, float)
    o = np.argsort(x, kind="mergesort")
    r = np.empty(len(x), float)
    sx = x[o]; n = len(x); i = 0
    while i < n:
        j = i
        while j + 1 < n and sx[j + 1] == sx[i]:
            j += 1
        r[o[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return r


def spearman(a, b):
    ra = avg_ranks(a); rb = avg_ranks(b)
    ra = ra - ra.mean(); rb = rb - rb.mean()
    d = math.sqrt(float(ra @ ra) * float(rb @ rb))
    return float(ra @ rb / d) if d > 0 else 0.0


# -------------------------------------------- count-based E3/E1/MI wiring -----
def _weights(c, weight):
    nb = c.sum(axis=1); n = nb.sum()
    if n <= 0:
        return np.zeros_like(nb)
    if weight == "operational":
        return nb / n
    if weight == "uniform":
        live = nb > 0; w = np.zeros_like(nb); w[live] = 1.0 / live.sum(); return w
    if weight == "degenerate":
        w = np.zeros_like(nb); w[int(np.argmax(nb))] = 1.0; return w
    raise ValueError(weight)


def _rowH(c):
    nb = c.sum(axis=1, keepdims=True)
    p = np.divide(c, nb, out=np.zeros_like(c), where=nb > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(p > 0, p * np.log(p), 0.0)
    Hx = -plogp.sum(axis=1)
    K = (c > 0).sum(axis=1)
    mm = np.where((nb[:, 0] > 0) & (K > 1), (K - 1) / (2.0 * np.maximum(nb[:, 0], 1)), 0.0)
    return Hx + mm


def counts_and_nulls(ploc, d, Bn, Oo, seed, nperm):
    """One joint-count pass per world -> observed counts + per-permutation null vectors.

    Returns c (Bn,Oo), nullE3 (Bn,) = mean over perms of (Hper+mmper),
            nullE1 (Bn,) = mean over perms of agreement, MI_null scalar, MI_obs scalar,
            Hd_obs scalar, and the permutation matrix P (nperm,N).
    Identical RNG usage to h5_repair.det_E3/det_E1 (rng.permutation in block order).
    """
    N = len(d)
    c = np.bincount(ploc * Oo + d, minlength=Bn * Oo).astype(np.float64).reshape(Bn, Oo)
    rng = np.random.default_rng(seed)
    P = np.empty((nperm, N), dtype=np.int64)
    for k in range(nperm):
        P[k] = rng.permutation(d)
    sumH = np.zeros(Bn); sumA = np.zeros(Bn); sumMI = 0.0
    ar = np.arange(0, nperm)
    for s in range(0, nperm, CHUNK):
        e = min(s + CHUNK, nperm); m = e - s
        idx = (ploc[None, :] * Oo + P[s:e]) + (ar[:m, None] * (Bn * Oo))
        cp = np.bincount(idx.ravel(), minlength=m * Bn * Oo).astype(np.float64).reshape(m, Bn, Oo)
        nb = cp.sum(axis=2, keepdims=True)
        p = np.divide(cp, nb, out=np.zeros_like(cp), where=nb > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            plogp = np.where(p > 0, p * np.log(p), 0.0)
        Hper = -plogp.sum(axis=2)
        Kper = (cp > 0).sum(axis=2)
        nb1 = nb[:, :, 0]
        mmper = np.where((nb1 > 0) & (Kper > 1), (Kper - 1) / (2.0 * np.maximum(nb1, 1)), 0.0)
        sumH += (Hper + mmper).sum(axis=0)
        sumA += (cp.max(axis=2) / np.maximum(cp.sum(axis=2), 1)).sum(axis=0)
        # MI per perm (sample-uniform joint)
        pj = cp.sum(axis=1, keepdims=True) / N          # m,Bn,1  (input marginal)
        pk = cp.sum(axis=2, keepdims=True) / N          # m,1,Oo  (output marginal)
        pj = np.broadcast_to(pj, cp.shape); pk = np.broadcast_to(pk, cp.shape)
        pt = cp / N
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(pt > 0, pt / (pj * pk), 1.0)
            lg = np.where(pt > 0, np.log(ratio), 0.0)
        sumMI += float((pt * lg).sum())
    nullE3 = sumH / nperm
    nullE1 = sumA / nperm
    MI_null = sumMI / nperm
    # observed MI + H(d)
    pt = c / N
    pj = c.sum(axis=1, keepdims=True) / N
    pk = c.sum(axis=0, keepdims=True) / N
    pjb = np.broadcast_to(pj, c.shape); pkb = np.broadcast_to(pk, c.shape)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(pt > 0, pt / (pjb * pkb), 1.0)
        lg = np.where(pt > 0, np.log(ratio), 0.0)
    MI_obs = float((pt * lg).sum())
    pk1 = c.sum(axis=0) / N
    nz = pk1 > 0
    Hd_obs = float(-np.sum(pk1[nz] * np.log(pk1[nz])))
    return c, nullE3, nullE1, MI_null, MI_obs, Hd_obs, P


def det_e3(c, nullE3, weight):
    w = _weights(c, weight)
    obs = float((w * _rowH(c)).sum())
    nn = float((w * nullE3).sum())
    if nn <= 0:
        return 1.0 if obs <= 0 else 0.0
    return max(0.0, min(1.0, 1.0 - obs / nn))


def det_e1(c, nullE1, weight):
    w = _weights(c, weight)
    a_obs = float((w * (c.max(axis=1) / np.maximum(c.sum(axis=1), 1))).sum())
    a_null = float((w * nullE1).sum())
    if a_null >= 1.0:
        return 0.0
    return max(0.0, min(1.0, (a_obs - a_null) / (1.0 - a_null)))


def det_nmi(MI_obs, MI_null, Hd_obs):
    den = Hd_obs - MI_null
    if den <= 0:
        return 0.0
    return max(0.0, min(1.0, (MI_obs - MI_null) / den))


def det_rank(ploc, d, P, Bn):
    """Threshold-free rank-based delta determinacy: within-bin rank dispersion vs permutation null."""
    r = avg_ranks(d)
    nb = np.bincount(ploc, minlength=Bn).astype(np.float64)
    live = nb > 0
    S1 = np.bincount(ploc, weights=r, minlength=Bn)
    S2 = np.bincount(ploc, weights=r * r, minlength=Bn)
    W_obs = float(S2.sum() - np.sum(np.where(live, S1 ** 2 / np.maximum(nb, 1), 0.0)))
    Ws = np.empty(P.shape[0])
    for k in range(P.shape[0]):
        rp = r[P[k]]
        s1 = np.bincount(ploc, weights=rp, minlength=Bn)
        s2 = np.bincount(ploc, weights=rp * rp, minlength=Bn)
        Ws[k] = s2.sum() - np.sum(np.where(live, s1 ** 2 / np.maximum(nb, 1), 0.0))
    W_null = float(Ws.mean())
    if W_null <= 0:
        return 1.0 if W_obs <= 0 else 0.0
    return max(0.0, min(1.0, 1.0 - W_obs / W_null))


# ------------------------------------------------------------------ main -----
def desc(a):
    a = np.asarray(a, float)
    return {"n": int(a.size), "mean": round(float(a.mean()), 4), "std": round(float(a.std()), 4),
            "min": round(float(a.min()), 4), "max": round(float(a.max()), 4),
            "range": round(float(a.max() - a.min()), 4),
            "n_distinct": int(np.unique(np.round(a, 6)).size)}


def world_scalars(chans, real_worlds, sto_worlds, bi_r, bi_s, Bn_s, wid):
    rr = real_worlds[wid]; ss = sto_worlds[wid]
    pr = bi_r[wid * PER:(wid + 1) * PER]; ps = bi_s[wid * PER:(wid + 1) * PER]
    p = pr * Bn_s + ps
    _, ploc = np.unique(p, return_inverse=True)
    ploc = np.asarray(ploc, dtype=np.int64)
    yr = np.array([C.psi_vision(r) for r in rr], dtype=np.int64)
    ys = np.array([C.psi_vision(r) for r in ss], dtype=np.int64)
    d = ys - yr + (O - 1)
    assert d.min() >= 0 and d.max() <= O_DELTA - 1, "F-H1B-1 delta alphabet"
    Bnw = int(ploc.max()) + 1
    out = {}
    c, nE3, nE1, MIn, MIo, Hd, P = counts_and_nulls(ploc, d, Bnw, O_DELTA, SEED + wid, NPERM)
    out["e3_op"] = det_e3(c, nE3, "operational")
    out["e3_uni"] = det_e3(c, nE3, "uniform")
    out["e3_deg"] = det_e3(c, nE3, "degenerate")
    out["e1_acc"] = det_e1(c, nE1, "uniform")
    out["nmi"] = det_nmi(MIo, MIn, Hd)
    out["rank"] = det_rank(ploc, d, P, Bnw)
    # per-output-bit (9 bits) delta determinacy, uniform weight
    bvals = []
    for b in range(9):
        yrb = (yr >> b) & 1; ysb = (ys >> b) & 1
        db = (ysb - yrb + 1).astype(np.int64)
        cb = np.bincount(ploc * 3 + db, minlength=Bnw * 3).astype(np.float64).reshape(Bnw, 3)
        rng = np.random.default_rng(SEED + wid)
        Pb = np.empty((NPERM, PER), dtype=np.int64)
        for k in range(NPERM):
            Pb[k] = rng.permutation(db)
        sumH = np.zeros(Bnw); sumA = np.zeros(Bnw)
        for s in range(0, NPERM, CHUNK):
            e = min(s + CHUNK, NPERM); m = e - s
            idx = (ploc[None, :] * 3 + Pb[s:e]) + (np.arange(0, m)[:, None] * (Bnw * 3))
            cpb = np.bincount(idx.ravel(), minlength=m * Bnw * 3).astype(np.float64).reshape(m, Bnw, 3)
            nbb = cpb.sum(axis=2, keepdims=True)
            pp = np.divide(cpb, nbb, out=np.zeros_like(cpb), where=nbb > 0)
            with np.errstate(divide="ignore", invalid="ignore"):
                plogp = np.where(pp > 0, pp * np.log(pp), 0.0)
            sumH += (-plogp.sum(axis=2)).sum(axis=0)
            sumA += (cpb.max(axis=2) / np.maximum(cpb.sum(axis=2), 1)).sum(axis=0)
        bvals.append(det_e3(cb, sumH / NPERM, "uniform"))
    out["bits"] = float(np.mean(bvals))
    # per-input-channel delta before aggregation (dx-only, dy-only), uniform
    pcv = []
    for (bx_r, bx_s, Bns) in chans:
        q = bx_r[wid * PER:(wid + 1) * PER] * Bns + bx_s[wid * PER:(wid + 1) * PER]
        _, qloc = np.unique(q, return_inverse=True)
        qloc = np.asarray(qloc, dtype=np.int64)
        Bnq = int(qloc.max()) + 1
        cq, nq, _, _, _, _, _ = counts_and_nulls(qloc, d, Bnq, O_DELTA, SEED + wid, NPERM)
        pcv.append(det_e3(cq, nq, "uniform"))
    out["perch"] = float(np.mean(pcv))
    # coarse delta sign (O=3)
    dc = (np.sign(ys - yr) + 1).astype(np.int64)
    cc = np.bincount(ploc * 3 + dc, minlength=Bnw * 3).astype(np.float64).reshape(Bnw, 3)
    rng = np.random.default_rng(SEED + wid)
    Pc = np.empty((NPERM, PER), dtype=np.int64)
    for k in range(NPERM):
        Pc[k] = rng.permutation(dc)
    sumH = np.zeros(Bnw)
    for s in range(0, NPERM, CHUNK):
        e = min(s + CHUNK, NPERM); m = e - s
        idx = (ploc[None, :] * 3 + Pc[s:e]) + (np.arange(0, m)[:, None] * (Bnw * 3))
        cpc = np.bincount(idx.ravel(), minlength=m * Bnw * 3).astype(np.float64).reshape(m, Bnw, 3)
        nbb = cpc.sum(axis=2, keepdims=True)
        pp = np.divide(cpc, nbb, out=np.zeros_like(cpc), where=nbb > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            plogp = np.where(pp > 0, pp * np.log(pp), 0.0)
        sumH += (-plogp.sum(axis=2)).sum(axis=0)
    out["coarse"] = det_e3(cc, sumH / NPERM, "uniform")
    out["_Bnw"] = Bnw
    return out


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    T = C.load()
    real_worlds = [w["recs"] for w in T["real"]]
    sto_worlds = [w["recs"] for w in T["sto"]]
    phi = C.phi_vision
    phi_x = lambda r: (r[0],)          # noqa: E731
    phi_y = lambda r: (r[1],)          # noqa: E731
    bi_r, Bn_r = H.encode_pair([r for w in real_worlds for r in w], phi)
    bi_s, Bn_s = H.encode_pair([r for w in sto_worlds for r in w], phi)
    flat_r = [r for w in real_worlds for r in w]
    flat_s = [r for w in sto_worlds for r in w]
    chans = []
    for ph in (phi_x, phi_y):
        bx_r, _ = H.encode_pair(flat_r, ph)
        bx_s, Bxs = H.encode_pair(flat_s, ph)
        chans.append((bx_r, bx_s, Bxs))

    # ---- WIRING GATE: count-based det_E3/det_E1 must match h5_repair on world 140 ----
    wid0 = TEST_IDS[0]
    rr = real_worlds[wid0]; ss = sto_worlds[wid0]
    pr = bi_r[wid0 * PER:(wid0 + 1) * PER]; ps = bi_s[wid0 * PER:(wid0 + 1) * PER]
    p = pr * Bn_s + ps
    _, ploc0 = np.unique(p, return_inverse=True); ploc0 = np.asarray(ploc0, dtype=np.int64)
    yr0 = np.array([C.psi_vision(r) for r in rr], dtype=np.int64)
    ys0 = np.array([C.psi_vision(r) for r in ss], dtype=np.int64)
    d0 = ys0 - yr0 + (O - 1)
    Bnw0 = int(ploc0.max()) + 1
    c0, nE3_0, nE1_0, _, _, _, _ = counts_and_nulls(ploc0, d0, Bnw0, O_DELTA, SEED + wid0, NPERM)
    wiring = {}
    for wt in ("operational", "uniform", "degenerate"):
        a = det_e3(c0, nE3_0, wt); b = H.det_E3(ploc0, d0, Bnw0, O_DELTA, wt, SEED + wid0, NPERM)
        wiring["E3_" + wt] = abs(a - b)
        a1 = det_e1(c0, nE1_0, wt); b1 = H.det_E1(ploc0, d0, Bnw0, O_DELTA, wt, SEED + wid0, NPERM)
        wiring["E1_" + wt] = abs(a1 - b1)
    wiring_max = max(wiring.values())
    wiring_pass = wiring_max < 1e-12
    print("WIRING max|delta| = %.3e  pass=%s" % (wiring_max, wiring_pass), flush=True)
    if not wiring_pass:
        json.dump({"task": "H1B-VISION", "wiring_fail": wiring, "wiring": wiring},
                  open(os.path.join(OUT, "h1b_vision_result.json"), "w"), indent=1)
        print("WIRING-FAIL -> booking nothing"); return

    # ---- per-world scalars for all variants ----
    ALL = F_GATE + F_DIAG
    scal = {k: np.empty(len(TEST_IDS)) for k in ALL}
    bns = []
    for t, wid in enumerate(TEST_IDS):
        o = world_scalars(chans, real_worlds, sto_worlds, bi_r, bi_s, Bn_s, wid)
        bns.append(o["_Bnw"])
        for k in ALL:
            scal[k][t] = o[k]
        if t % 10 == 0:
            print("  world %d/%d  %.1fs" % (t + 1, len(TEST_IDS), time.time() - t0), flush=True)

    # ---- per-world transfer gap (booked twin delta, mean over 3 seeds) ----
    TW = json.load(open(os.path.join(LAB, "results/d2_v1/d2_v1_twins_result.json")))
    runs = TW["sockets"][SOCK]["runs"]
    A = {c: np.array([r["nerr_per_world"] for r in runs if r["cond"] == c]) for c in ("real", "sim")}
    gap = (A["sim"] - A["real"]).mean(axis=0)
    assert len(gap) == len(TEST_IDS)

    rng = np.random.default_rng(SEED)
    agg, width, wstd = {}, {}, {}
    for k in ALL:
        x = scal[k]
        agg[k] = float(x.mean()); wstd[k] = float(x.std())
        bs = np.array([x[rng.integers(0, len(x), len(x))].mean() for _ in range(B_BOOT)])
        width[k] = float(np.percentile(bs, 97.5) - np.percentile(bs, 2.5))

    D_gate = max(agg[k] for k in F_GATE) - min(agg[k] for k in F_GATE)
    D_full = max(agg[k] for k in ALL) - min(agg[k] for k in ALL)
    D_triple = max(agg[k] for k in ("e3_op", "e3_uni", "e3_deg")) - min(agg[k] for k in ("e3_op", "e3_uni", "e3_deg"))

    passers = [k for k in F_GATE if wstd[k] > 0 and width[k] <= WIDTH_TOL]
    g0_green = bool(len(passers) > 0 and D_gate <= DEF_TOL)

    # ---- winner rule ----
    winner = None; rho_block = {}
    if g0_green:
        med = float(np.median([agg[k] for k in F_GATE]))
        winner = sorted(passers, key=lambda k: (width[k], abs(agg[k] - med)))[0]
        for k in passers:                       # rho for every passing V
            r = spearman(scal[k], gap)
            bs = np.array([spearman(scal[k][i], gap[i])
                           for i in (rng.integers(0, len(gap), len(gap)) for _ in range(B_RHO))])
            lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
            rho_block[k] = {"rho": round(r, 4), "ci95": [round(lo, 4), round(hi, 4)],
                            "boot_std": round(float(bs.std()), 4),
                            "ci_excl_0": bool(lo > 0 or hi < 0)}
        gp = gap
        rho_block["gap_floor"] = {"mean": round(float(gp.mean()), 4), "std": round(float(gp.std()), 4),
                                  "sem": round(float(gp.std() / math.sqrt(len(gp))), 4)}
        R = rho_block[winner]
        g1_green = bool(R["rho"] <= BAR and R["ci95"][1] < 0)
    else:
        g1_green = None

    if not g0_green:
        verdict, sentence = "G0-RED-TERMINAL", (
            "No H5-stable per-world vision determinacy exists - the measure thread closes PERMANENTLY.")
    elif g1_green:
        verdict, sentence = "G1-GREEN", "H1 RESURRECTED on a stable measure with a real gap."
    else:
        verdict, sentence = "G1-RED", (
            "Death booking STANDS at higher confidence: the floor confound was removed and the null persisted.")

    out = {
        "task": "H1B-VISION", "lane": "H1B-VISION", "prereg": "proposals/runs/H1B-vision.md",
        "cpu_only": True, "watt_hours": 0.0, "gpu_used": False,
        "socket": SOCK, "O": O, "O_delta": O_DELTA, "test_ids": TEST_IDS,
        "seed": SEED, "nperm": NPERM, "B_boot_g0": B_BOOT, "B_boot_rho": B_RHO,
        "width_tol": WIDTH_TOL, "def_tol": DEF_TOL, "bar": BAR,
        "wiring": {"max_abs_delta": wiring_max, "pass": True, "detail": wiring,
                   "pair_bins_min": int(min(bns)), "pair_bins_max": int(max(bns))},
        "power": {"n": len(TEST_IDS), "alpha": 0.05, "power": 0.80,
                  "detectable_rho_two_sided": POWER_BAR_2S, "detectable_rho_one_sided": POWER_BAR_1S,
                  "power_at_bar_one_sided": 0.756, "power_at_bar_two_sided": 0.647},
        "candidates": {k: {"per_world": [round(float(v), 6) for v in scal[k]],
                           "agg": round(agg[k], 6), "world_std": round(wstd[k], 6),
                           "resample_width": round(width[k], 6),
                           "gating": k in F_GATE} for k in ALL},
        "G0": {"D_gate": round(D_gate, 6), "D_full": round(D_full, 6),
               "D_triple_opunideg": round(D_triple, 6), "passers": passers,
               "green": g0_green, "winner": winner},
        "G1": {"green": g1_green, "rho": rho_block},
        "verdict": {"outcome": verdict, "sentence": sentence},
        "wiring_pass": True,
        "wall_s": round(time.time() - t0, 1),
    }
    json.dump(out, open(os.path.join(OUT, "h1b_vision_result.json"), "w"), indent=1)

    print("\n--- per-variant aggregate / world-std / resample width ---", flush=True)
    for k in ALL:
        print("  %-8s agg=%.4f  world_std=%.4f  width=%.4f  %s" %
              (k, agg[k], wstd[k], width[k], "GATE" if k in F_GATE else "diag"), flush=True)
    print("\nD_gate=%.4f  D_full=%.4f  D_triple(op/uni/deg)=%.4f" % (D_gate, D_full, D_triple), flush=True)
    print("G0 green=%s  passers=%s  winner=%s" % (g0_green, passers, winner), flush=True)
    print("gap floor: mean=%.4f std=%.4f sem=%.4f" % (gap.mean(), gap.std(), gap.std() / math.sqrt(60)), flush=True)
    print("G1 green=%s  rho block=%s" % (g1_green, json.dumps(rho_block)), flush=True)
    print("VERDICT %s :: %s" % (verdict, sentence), flush=True)
    print("wrote h1b_vision_result.json  wall %.1fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
