#!/usr/bin/env python3
"""H1-WORLDGRAN (lane H1-WORLDGRAN) — CPU-only, 0 Wh.

Prereg: proposals/runs/H1-world-granular.md (frozen before this run).
Reuses results/h5_repair/h5_repair.py (E3 estimator + encoders + SEED/NPERM) and
results/d2_v1/{d2_v1_traces.json,d2_v1_twins_result.json} wholesale. No GPU.
"""
import json, os, sys, math, time
import numpy as np
from multiprocessing import Pool

LAB = "/home/eileen/projects/quilt-gpu-lab"
sys.path.insert(0, os.path.join(LAB, "results/d2_v1/scripts"))
sys.path.insert(0, os.path.join(LAB, "results/h5_repair"))
import d2_v1_common as C            # noqa: E402
import h5_repair as H              # noqa: E402  (det_E3, encode_pair, SEED, NPERM)

OUT = os.path.join(LAB, "results/h1_worldgran")
B_BOOT = 1000
SEED = H.SEED                      # 2718
NPERM = H.NPERM                    # 120
PER = 1000
TEST_IDS = list(range(140, 200))   # 60 held-out worlds (twins evaluated here)
PRIMARY = "policy.action"          # named by the H5 stability gate, NOT by results
WEIGHTS = ("operational", "uniform", "degenerate")
STAB_TOL = 0.15
BAR = -0.30                        # mission effect-size bar
POWER_BAR_1S = 0.318               # one-sided alpha=.05 power=.80 (n=60)
POWER_BAR_2S = 0.355               # two-sided


# ------------------------------------------------------------- statistics -----
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


def boot_ci(det, gap, rng):
    det = np.asarray(det, float); gap = np.asarray(gap, float)
    n = len(det)
    bs = np.empty(B_BOOT)
    for b in range(B_BOOT):
        idx = rng.integers(0, n, n)
        bs[b] = spearman(det[idx], gap[idx])
    if np.all(bs == bs[0]):
        lo = hi = float(bs[0])
    else:
        lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    return float(bs.std()), [lo, hi]


# -------------------------------------------------------------- per socket ----
def socket_worker(args):
    name, phi_src, psi_src, O = args
    phi = getattr(C, phi_src); psi = getattr(C, psi_src)
    T = C.load()
    real_worlds = [w["recs"] for w in T["real"]]
    sto_worlds = [w["recs"] for w in T["sto"]]

    bi_r, Bn_r = H.encode_pair([r for w in real_worlds for r in w], phi)
    bi_s, Bn_s = H.encode_pair([r for w in sto_worlds for r in w], phi)
    O_delta = 2 * O - 1

    det = {wt: np.empty(len(TEST_IDS)) for wt in WEIGHTS}
    bins = []
    for t, wid in enumerate(TEST_IDS):
        rr = real_worlds[wid]; ss = sto_worlds[wid]
        assert len(rr) == len(ss) == PER
        pr = bi_r[wid * PER:(wid + 1) * PER]
        ps = bi_s[wid * PER:(wid + 1) * PER]
        p = pr * Bn_s + ps
        _, ploc = np.unique(p, return_inverse=True)
        ploc = np.asarray(ploc, dtype=np.int64)
        yr = np.array([psi(r) for r in rr], dtype=np.int64)
        ys = np.array([psi(r) for r in ss], dtype=np.int64)
        d = ys - yr + (O - 1)
        assert d.min() >= 0 and d.max() <= O_delta - 1, "F-WG-1 delta alphabet"
        Bnw = int(ploc.max()) + 1
        bins.append(Bnw)
        for wt in WEIGHTS:
            det[wt][t] = H.det_E3(ploc, d, Bnw, O_delta, wt, SEED + wid, NPERM)
    return {"socket": name, "O": O, "O_delta": int(O_delta), "Bn_r": int(Bn_r),
            "Bn_s": int(Bn_s), "n_pair_bins_min": int(min(bins)),
            "n_pair_bins_max": int(max(bins)),
            "det": {wt: [float(v) for v in det[wt]] for wt in WEIGHTS}}


def desc(a):
    a = np.asarray(a, float)
    return {"n": int(a.size), "mean": round(float(a.mean()), 4),
            "std": round(float(a.std()), 4), "min": round(float(a.min()), 4),
            "max": round(float(a.max()), 4), "range": round(float(a.max() - a.min()), 4),
            "n_distinct": int(np.unique(np.round(a, 6)).size)}


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    units = [(S["name"], S["phi"].__name__, S["psi"].__name__, S["O"]) for S in C.SOCKETS]
    with Pool(min(6, len(units))) as pool:
        res = pool.map(socket_worker, units)
    bysock = {r["socket"]: r for r in res}
    names = [S["name"] for S in C.SOCKETS]
    print("per-world determinacy done %.1fs" % (time.time() - t0), flush=True)

    # ---- per-world transfer gap (booked twin delta; mean over 3 seeds) ----
    TW = json.load(open(os.path.join(LAB, "results/d2_v1/d2_v1_twins_result.json")))
    gap = {}
    for n in names:
        runs = TW["sockets"][n]["runs"]
        A = {c: np.array([r["nerr_per_world"] for r in runs if r["cond"] == c])
             for c in ("real", "sim")}
        gap[n] = (A["sim"] - A["real"]).mean(axis=0)          # 60 worlds
    assert all(len(gap[n]) == len(TEST_IDS) for n in names)

    rng = np.random.default_rng(SEED)

    # ---- 6-socket x world-level rho table ----
    table = {}
    for n in names:
        row = {"per_world_det_operational": desc(bysock[n]["det"]["operational"]),
               "gap": desc(gap[n]),
               "n_pair_bins_min": bysock[n]["n_pair_bins_min"],
               "n_pair_bins_max": bysock[n]["n_pair_bins_max"],
               "primary": n == PRIMARY}
        rho_w = {}
        for wt in WEIGHTS:
            r = spearman(bysock[n]["det"][wt], gap[n])
            rho_w[wt] = round(r, 4)
        table[n] = row
        table[n]["rho"] = rho_w
        # bootstrap CI on the operational weight (the D2 default)
        sd, ci = boot_ci(bysock[n]["det"]["operational"], gap[n], rng)
        table[n]["rho_operational"] = rho_w["operational"]
        table[n]["boot_std"] = round(sd, 4)
        table[n]["ci95"] = [round(ci[0], 4), round(ci[1], 4)]
        table[n]["ci_excl_0"] = bool(ci[0] > 0 or ci[1] < 0)
        table[n]["std_zero"] = bool(table[n]["per_world_det_operational"]["std"] == 0)

    # ---- primary gate ----
    P = table[PRIMARY]
    det_p = np.asarray(bysock[PRIMARY]["det"]["operational"], float)
    gap_p = gap[PRIMARY]
    std_p = float(det_p.std())
    rho_p = P["rho_operational"]
    ci_p = P["ci95"]

    if std_p == 0:
        gate = "INCONCLUSIVE"
    elif rho_p <= BAR and ci_p[1] < 0:
        gate = "PASS"
    elif rho_p >= -BAR and ci_p[0] > 0:
        gate = "SIGN-REVERSAL"
    else:
        gate = "DEATH"

    power_bar_pass = (abs(rho_p) >= POWER_BAR_1S) and P["ci_excl_0"] and rho_p < 0
    sentences = {
        "PASS": ("H1 survives at world granularity - determinacy buys transfer where "
                 "distributions are matched."),
        "SIGN-REVERSAL": ("the determinacy->transfer sign REVERSES at world granularity "
                          "(per-world determinacy predicts LARGER transfer gap)."),
        "DEATH": ("no world-level relationship either - the determinacy->transfer story is "
                  "dead at every granularity."),
        "INCONCLUSIVE": ("INCONCLUSIVE - per-world determinacy has zero variance at this "
                         "granularity; nothing to correlate (never PASS)."),
    }
    sentence = sentences[gate]

    out = {
        "task": "H1-WORLDGRAN", "lane": "H1-WORLDGRAN",
        "prereg": "proposals/runs/H1-world-granular.md",
        "cpu_only": True, "watt_hours": 0.0, "gpu_used": False,
        "seed": SEED, "nperm": NPERM, "B_boot": B_BOOT, "test_ids": TEST_IDS,
        "primary_socket": PRIMARY, "bar": BAR,
        "power": {"n": len(TEST_IDS), "alpha": 0.05, "power": 0.80,
                  "detectable_rho_two_sided": POWER_BAR_2S,
                  "detectable_rho_one_sided": POWER_BAR_1S,
                  "power_at_bar_one_sided": 0.756, "power_at_bar_two_sided": 0.647},
        "table": table,
        "primary": {"rho": rho_p, "ci95": ci_p, "std": round(std_p, 4),
                    "rho_by_weight": P["rho"], "boot_std": P["boot_std"],
                    "range": P["per_world_det_operational"]["range"],
                    "n_distinct": P["per_world_det_operational"]["n_distinct"]},
        "gate": {"G_W1": gate, "power_bar_pass": bool(power_bar_pass),
                 "sentence": sentence},
        "continuity": {"H1_corpus_rho": -0.371, "H1_corpus_ci": [-0.600, 0.486],
                       "H5_R3_corpus_rho": -0.2571},
        "wall_s": round(time.time() - t0, 1),
    }
    json.dump(out, open(os.path.join(OUT, "h1_worldgran_result.json"), "w"), indent=1)

    # ---- console report ----
    print("POWER (n=60, alpha=.05, power=.80): detectable |rho| 2-sided=%.3f 1-sided=%.3f; "
          "power@bar(-0.30) 1s=%.3f" % (POWER_BAR_2S, POWER_BAR_1S, 0.756), flush=True)
    print("\n%-16s %8s %7s %22s %6s %8s %9s" %
          ("socket", "rho_op", "det_std", "ci95", "excl0", "gap_std", "stability"), flush=True)
    for n in names:
        flag = "PRIMARY" if n == PRIMARY else "explor"
        print("%-16s %8.4f %7.4f  [%7.4f,%7.4f] %6s %8.4f %9s" %
              (n, table[n]["rho_operational"], table[n]["per_world_det_operational"]["std"],
               table[n]["ci95"][0], table[n]["ci95"][1], str(table[n]["ci_excl_0"]),
               table[n]["gap"]["std"], flag), flush=True)
    print("\nverdict: G-W1 = %s  (rho=%.4f CI %s, power-bar pass=%s)"
          % (gate, rho_p, ci_p, power_bar_pass), flush=True)
    print("books:", sentence, flush=True)
    print("wrote h1_worldgran_result.json  wall %.1fs" % (time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
