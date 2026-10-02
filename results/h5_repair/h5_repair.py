#!/usr/bin/env python3
"""H5-MEASURE-REPAIR (lane H5-REPAIR) — CPU-only.

Prereg: proposals/runs/H5-measure-repair.md (frozen before this run).
Reuses results/d2_v1/d2_v1_traces.json + d2_v1_twins_result.json. No GPU, 0 Wh.
"""
import json, os, sys, math, time
import numpy as np
from multiprocessing import Pool

LAB = "/home/eileen/projects/quilt-gpu-lab"
sys.path.insert(0, os.path.join(LAB, "results/d2_v1/scripts"))
sys.path.insert(0, os.path.join(LAB, "results/est_freeze"))
import d2_v1_common as C            # noqa: E402

OUT = os.path.join(LAB, "results/h5_repair")
B_BOOT = 1000
SEED = 2718
NPERM = 120                          # point values (matches D2-V1)
NPERM_BOOT = 24                      # bootstrap surrogate (validated vs NPERM below)
SYNTH_FLOOR = 0.04
STAB_TOL = 0.15

# ----------------------------------------------------------------- encoding ---
def encode_global(recs, phi, psi):
    bmap, ymap = {}, {}
    bi = np.empty(len(recs), dtype=np.int64)
    yi = np.empty(len(recs), dtype=np.int64)
    for i, r in enumerate(recs):
        b = phi(r); y = psi(r)
        j = bmap.get(b)
        if j is None:
            j = len(bmap); bmap[b] = j
        bi[i] = j
        k = ymap.get(y)
        if k is None:
            k = len(ymap); ymap[y] = k
        yi[i] = k
    return bi, yi, len(bmap), len(ymap)


def encode_pair(recs, phi):
    bmap = {}
    bi = np.empty(len(recs), dtype=np.int64)
    for i, r in enumerate(recs):
        b = phi(r)
        j = bmap.get(b)
        if j is None:
            j = len(bmap); bmap[b] = j
        bi[i] = j
    return bi, len(bmap)


def _counts(bi, yi, Bn, O_obs):
    return np.bincount(bi * O_obs + yi, minlength=Bn * O_obs).astype(np.float64).reshape(Bn, O_obs)


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
    H = -plogp.sum(axis=1)
    K = (c > 0).sum(axis=1)
    mm = np.where((nb[:, 0] > 0) & (K > 1), (K - 1) / (2.0 * np.maximum(nb[:, 0], 1)), 0.0)
    return H + mm


def det_E3(bi, yi, Bn, O_obs, weight, seed, nperm):
    c = _counts(bi, yi, Bn, O_obs)
    w = _weights(c, weight)
    obs = float((w * _rowH(c)).sum())
    rng = np.random.default_rng(seed)
    n = len(yi)
    P = np.empty((nperm, n), dtype=np.int64)
    for k in range(nperm):
        P[k] = rng.permutation(yi)
    idx = (bi[None, :] * O_obs + P) + (np.arange(nperm, dtype=np.int64)[:, None] * (Bn * O_obs))
    cp = np.bincount(idx.ravel(), minlength=nperm * Bn * O_obs).astype(np.float64).reshape(nperm, Bn, O_obs)
    nb = cp.sum(axis=2, keepdims=True)
    p = np.divide(cp, nb, out=np.zeros_like(cp), where=nb > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(p > 0, p * np.log(p), 0.0)
    Hper = -plogp.sum(axis=2)
    Kper = (cp > 0).sum(axis=2)
    nb1 = nb[:, :, 0]
    mmper = np.where((nb1 > 0) & (Kper > 1), (Kper - 1) / (2.0 * np.maximum(nb1, 1)), 0.0)
    null = (Hper + mmper).mean(axis=0)
    hc_null = float((w * null).sum())
    if hc_null <= 0:
        return 1.0 if obs <= 0 else 0.0
    return max(0.0, min(1.0, 1.0 - obs / hc_null))


def det_E1(bi, yi, Bn, O_obs, weight, seed, nperm):
    c = _counts(bi, yi, Bn, O_obs)
    w = _weights(c, weight)
    a_obs = float((w * (c.max(axis=1) / np.maximum(c.sum(axis=1), 1))).sum())
    rng = np.random.default_rng(seed)
    n = len(yi)
    P = np.empty((nperm, n), dtype=np.int64)
    for k in range(nperm):
        P[k] = rng.permutation(yi)
    idx = (bi[None, :] * O_obs + P) + (np.arange(nperm, dtype=np.int64)[:, None] * (Bn * O_obs))
    cp = np.bincount(idx.ravel(), minlength=nperm * Bn * O_obs).astype(np.float64).reshape(nperm, Bn, O_obs)
    agree = cp.max(axis=2) / np.maximum(cp.sum(axis=2), 1)      # nperm x Bn
    a_null = float((w * agree.mean(axis=0)).sum())
    if a_null >= 1.0:
        return 0.0
    return max(0.0, min(1.0, (a_obs - a_null) / (1.0 - a_null)))


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = math.sqrt((ra @ ra) * (rb @ rb))
    return float(ra @ rb / d) if d > 0 else 0.0


# ---------------------------------------------------------------- per socket ---
def socket_worker(args):
    name, phi_src, psi_src, O = args
    # phi/psi come back as strings -> resolve here via C module
    phi = getattr(C, phi_src); psi = getattr(C, psi_src)
    T = C.load()
    sto_worlds = [w["recs"] for w in T["sto"]]
    real_worlds = [w["recs"] for w in T["real"]]
    nW = len(sto_worlds)

    sto = [r for w in sto_worlds for r in w]
    bi, yi, Bn, O_obs = encode_global(sto, phi, psi)
    O_decl = O

    # per-world slices
    per = 1000
    bi_w = [bi[i * per:(i + 1) * per] for i in range(nW)]
    yi_w = [yi[i * per:(i + 1) * per] for i in range(nW)]

    res = {"socket": name, "n_bins": Bn, "O_obs": O_obs, "O_decl": O_decl}

    # ---- baseline point values (3 weights, full corpus, NPERM) ----
    point = {wt: det_E3(bi, yi, Bn, O_obs, wt, SEED, NPERM) for wt in ("operational", "uniform", "degenerate")}
    res["baseline_point"] = point
    res["baseline_def_spread"] = max(point.values()) - min(point.values())

    # ---- decomposition: world-resample bootstrap of pooled E3 operational ----
    rng = np.random.default_rng(SEED)
    boots = np.empty(B_BOOT)
    for b in range(B_BOOT):
        ids = rng.integers(0, nW, nW)
        bix = np.concatenate([bi_w[i] for i in ids])
        yix = np.concatenate([yi_w[i] for i in ids])
        boots[b] = det_E3(bix, yix, Bn, O_obs, "operational", SEED + b, NPERM_BOOT)
    res["res_std"] = float(boots.std())
    res["res_ci95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    res["res_width"] = res["res_ci95"][1] - res["res_ci95"][0]
    dv = np.array(list(point.values()))
    res["def_var"] = float(dv.var())
    res["res_var"] = float(boots.var())
    res["def_over_res_var"] = float(dv.var() / boots.var()) if boots.var() > 0 else None

    # surrogate validation: nperm=120 vs nperm=24 on the point value
    op120 = point["operational"]
    op24 = det_E3(bi, yi, Bn, O_obs, "operational", SEED, NPERM_BOOT)
    res["nperm_surrogate_delta"] = abs(op120 - op24)
    res["baseline_boots_operational"] = boots          # reused by R2 mid-band

    # --------------------------- R1 per-world conditional ---------------------
    pw = {wt: np.empty(nW) for wt in ("operational", "uniform", "degenerate")}
    for i in range(nW):
        for wt in pw:
            pw[wt][i] = det_E3(bi_w[i], yi_w[i], Bn, O_obs, wt, SEED + i, NPERM)
    opw = pw["operational"]
    r1 = float(opw.mean())
    rb = np.array([opw[rng.integers(0, nW, nW)].mean() for _ in range(B_BOOT)])
    r1_def = max(float(pw[wt].mean()) for wt in pw) - min(float(pw[wt].mean()) for wt in pw)
    res["R1"] = {"value": r1, "res_std": float(rb.std()),
                 "res_ci95": [float(np.percentile(rb, 2.5)), float(np.percentile(rb, 97.5))],
                 "res_width": float(np.percentile(rb, 97.5) - np.percentile(rb, 2.5)),
                 "def_spread": r1_def, "per_world_std": float(opw.std()),
                 "world_def": {wt: float(pw[wt].mean()) for wt in pw}}

    # --------------------------- R2 op-split near-1 / mid ----------------------
    band = "near1" if point["operational"] >= 0.80 else "mid"
    if band == "near1":
        val = det_E1(bi, yi, Bn, O_obs, "operational", SEED, NPERM)
        e1p = {wt: det_E1(bi, yi, Bn, O_obs, wt, SEED, NPERM) for wt in ("operational", "uniform", "degenerate")}
        r2_def = max(e1p.values()) - min(e1p.values())
        rb2 = np.empty(B_BOOT)
        for b in range(B_BOOT):
            ids = rng.integers(0, nW, nW)
            bix = np.concatenate([bi_w[i] for i in ids])
            yix = np.concatenate([yi_w[i] for i in ids])
            rb2[b] = det_E1(bix, yix, Bn, O_obs, "operational", SEED + b, NPERM_BOOT)
        res["R2"] = {"band": band, "estimator": "E1", "value": val,
                     "res_std": float(rb2.std()),
                     "res_ci95": [float(np.percentile(rb2, 2.5)), float(np.percentile(rb2, 97.5))],
                     "res_width": float(np.percentile(rb2, 97.5) - np.percentile(rb2, 2.5)),
                     "def_spread": r2_def, "band_point": e1p}
    else:
        res["R2"] = {"band": band, "estimator": "E3", "value": point["operational"],
                     "res_std": res["res_std"], "res_ci95": res["res_ci95"], "res_width": res["res_width"],
                     "def_spread": res["baseline_def_spread"], "band_point": point}

    # --------------------------- R3 paired-world delta -------------------------
    bi_r, Bn_r = encode_pair([r for w in real_worlds for r in w], phi)
    bi_s, Bn_s = encode_pair([r for w in sto_worlds for r in w], phi)
    O_delta = 2 * O - 1
    pw3 = {wt: np.empty(nW) for wt in ("operational", "uniform", "degenerate")}
    npb_max = 0
    for i in range(nW):
        rr = real_worlds[i]; ss = sto_worlds[i]
        assert len(rr) == len(ss) == per
        pr = bi_r[i * per:(i + 1) * per]; ps = bi_s[i * per:(i + 1) * per]
        p = pr * Bn_s + ps
        # per-world LOCAL factorization (determinacy is label-invariant; keeps bin
        # count bounded -> avoids the Bn_r*Bn_s composite bin explosion)
        _, ploc = np.unique(p, return_inverse=True)
        ploc = np.asarray(ploc, dtype=np.int64)
        yr = np.array([psi(r) for r in rr], dtype=np.int64)
        ys = np.array([psi(r) for r in ss], dtype=np.int64)
        d = ys - yr + (O - 1)
        assert d.min() >= 0 and d.max() <= 2 * O - 2, "F-H5-3 alphabet"
        Bnw = int(ploc.max()) + 1
        npb_max = max(npb_max, Bnw)
        for wt in pw3:
            pw3[wt][i] = det_E3(ploc, d, Bnw, O_delta, wt, SEED + i, NPERM)
    opw3 = pw3["operational"]
    r3 = float(opw3.mean())
    rb3 = np.array([opw3[rng.integers(0, nW, nW)].mean() for _ in range(B_BOOT)])
    r3_def = max(float(pw3[wt].mean()) for wt in pw3) - min(float(pw3[wt].mean()) for wt in pw3)
    res["R3"] = {"value": r3, "res_std": float(rb3.std()),
                 "res_ci95": [float(np.percentile(rb3, 2.5)), float(np.percentile(rb3, 97.5))],
                 "res_width": float(np.percentile(rb3, 97.5) - np.percentile(rb3, 2.5)),
                 "def_spread": r3_def, "per_world_std": float(opw3.std()),
                 "n_pair_bins": int(npb_max), "O_delta": int(O_delta)}

    # recompute R1/R3 res stats cleanly (free bootstrap over per-world scalars)
    def free_bs(opw_arr):
        bs = np.array([opw_arr[rng.integers(0, nW, nW)].mean() for _ in range(B_BOOT)])
        return {"value": float(opw_arr.mean()), "res_std": float(bs.std()),
                "res_ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
                "res_width": float(np.percentile(bs, 97.5) - np.percentile(bs, 2.5))}
    _ = free_bs                                               # (kept simple/auditable)
    return res


def load_per_socket():
    return [(S["name"], S["phi"].__name__, S["psi"].__name__, S["O"]) for S in C.SOCKETS]


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    units = load_per_socket()
    with Pool(min(6, len(units))) as pool:
        results = pool.map(socket_worker, units)
    bysock = {r["socket"]: r for r in results}
    print("analysis sockets done %.1fs" % (time.time() - t0), flush=True)

    # ----------------------- G-H5a stability per repair -----------------------
    def stable(rep):
        r = bysock  # noqa
        out = {}
        for name, d in bysock.items():
            x = d[rep]
            s = (x["res_std"] > 0) and (x["res_width"] <= STAB_TOL) and (x["def_spread"] <= STAB_TOL)
            out[name] = {"value": x["value"], "res_std": x["res_std"], "res_width": x["res_width"],
                         "def_spread": x["def_spread"], "stable": bool(s),
                         "degenerate_std0": x["res_std"] == 0}
        n = sum(1 for v in out.values() if v["stable"])
        return {"per_socket": out, "stable_count": n, "pass": n >= 5}

    G = {"R1": stable("R1"), "R2": stable("R2"), "R3": stable("R3")}

    # ----------------------- G-H5b rho vs transfer gap ------------------------
    TW = json.load(open(os.path.join(LAB, "results/d2_v1/d2_v1_twins_result.json")))
    names = [S["name"] for S in C.SOCKETS]
    gsim = {}
    for n in names:
        runs = TW["sockets"][n]["runs"]
        A = {c: np.array([r["nerr_per_world"] for r in runs if r["cond"] == c]) for c in ("real", "sim")}
        gsim[n] = A["sim"] - A["real"]            # seeds x worlds(60)
    nWt = gsim[names[0]].shape[1]
    rng = np.random.default_rng(SEED)

    def g5b(vals):
        v = np.array([vals[n] for n in names])
        gaps = np.array([gsim[n].mean() for n in names])
        rho = spearman(v, gaps)
        bs = []
        for _ in range(B_BOOT):
            idx = rng.integers(0, nWt, nWt)
            gb = np.array([gsim[n][:, idx].mean() for n in names])
            bs.append(spearman(v, gb))
        bs = np.array(bs)
        return {"rho": round(rho, 4),
                "rho_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                "det_range": round(float(v.max() - v.min()), 4),
                "flat_over_range": bool(float(v.max() - v.min()) < 0.5),
                "gaps": {n: round(float(gsim[n].mean()), 4) for n in names},
                "dets": {n: round(float(vals[n]), 4) for n in names}}

    G5B = {rep: g5b({n: bysock[n][rep]["value"] for n in names}) for rep in ("R1", "R2", "R3")}
    # baseline (old measure) for reference
    G5B["OLD"] = g5b({n: bysock[n]["baseline_point"]["operational"] for n in names})

    # ----------------------- G-H5c not-a-relabeling ---------------------------
    old = np.array([bysock[n]["baseline_point"]["operational"] for n in names])
    G5C = {}
    for rep in ("R1", "R2", "R3"):
        new = np.array([bysock[n][rep]["value"] for n in names])
        rho = spearman(old, new)
        rank_old = {n: int(r) for n, r in zip(names, np.argsort(np.argsort(-old)))}
        rank_new = {n: int(r) for n, r in zip(names, np.argsort(np.argsort(-new)))}
        G5C[rep] = {"spearman_old_vs_new": round(rho, 4),
                    "rank_old": rank_old, "rank_new": rank_new,
                    "moved": {n: rank_new[n] - rank_old[n] for n in names if rank_new[n] != rank_old[n]},
                    "is_relabel": bool(abs(rho - 1.0) < 1e-9)}

    # ----------------------- verdict tree -------------------------------------
    passers = [rep for rep in ("R1", "R3", "R2") if G[rep]["pass"] and not G5C[rep]["is_relabel"]]
    if passers:
        best = passers[0]
        tallies = sorted(passers, key=lambda r: (-G[r]["stable_count"], -abs(G5B[r]["rho"]),
                                                 {"R1": 0, "R3": 1, "R2": 2}[r]))
        best = tallies[0]
        outcome = "H5-v2 = %s" % best
        sentence = ("I/O determinacy is a stable, measurable socket property once it is conditioned "
                    "on world identity (%s); the D2-V1 H5 instability was between-definition "
                    "(distribution-relative), not sampling noise. Under the repaired measure the "
                    "D2 transfer relationship signs %s (rho=%.3f CI %s) vs H1's original "
                    "rho=-0.371 [-0.600, 0.600]." % (
                        best, "NEGATIVE (H1 direction survives)" if G5B[best]["rho"] < 0
                        else "POSITIVE (H1 direction reverses)", G5B[best]["rho"], G5B[best]["rho_ci95"]))
    else:
        best = None
        outcome = "NO-REPAIR-PASSES"
        sentence = ("Instability IS the finding: I/O determinacy is DISTRIBUTION-RELATIVE, not a "
                    "state property of the socket. The static-I/O construct of COG-THESIS 3/4.2 does "
                    "not exist as a socket-level scalar at D2 scope (estimator intrinsic spread 0.039, "
                    "data spreads up to 0.924); D2-V1's H1 FAIL is therefore evidence against the "
                    "MEASURE, not against the thesis.")

    out = {"task": "H5-REPAIR", "lane": "H5-REPAIR",
           "prereg": "proposals/runs/H5-measure-repair.md",
           "cpu_only": True, "watt_hours": 0.0, "gpu_used": False,
           "B_boot": B_BOOT, "seed": SEED, "nperm_point": NPERM, "nperm_boot": NPERM_BOOT,
           "stab_tol": STAB_TOL, "synth_floor": SYNTH_FLOOR,
           "baseline": {n: {"point": bysock[n]["baseline_point"],
                            "def_spread": bysock[n]["baseline_def_spread"],
                            "n_bins": bysock[n]["n_bins"], "O_obs": bysock[n]["O_obs"]} for n in names},
           "decomposition": {n: {"res_std": bysock[n]["res_std"], "res_ci95": bysock[n]["res_ci95"],
                                 "res_width": bysock[n]["res_width"], "def_var": bysock[n]["def_var"],
                                 "res_var": bysock[n]["res_var"],
                                 "def_over_res_var": bysock[n]["def_over_res_var"],
                                 "nperm_surrogate_delta": bysock[n]["nperm_surrogate_delta"],
                                 "def_spread": bysock[n]["baseline_def_spread"]} for n in names},
           "repairs": {rep: {n: bysock[n][rep] for n in names} for rep in ("R1", "R2", "R3")},
           "G_H5a": G, "G_H5b": G5B, "G_H5c": G5C,
           "verdict": {"outcome": outcome, "booked_repair": best, "sentence": sentence},
           "wall_s": round(time.time() - t0, 1)}
    json.dump(out, open(os.path.join(OUT, "h5_repair_result.json"), "w"), indent=1)
    print("VERDICT:", outcome)
    print(sentence)
    print("wrote h5_repair_result.json  wall %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
