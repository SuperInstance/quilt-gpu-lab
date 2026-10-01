#!/usr/bin/env python3
"""EST-FREEZE — second pass: in-scope socket view, full declared reflex channel,
and a STATIONARY-TRUTH synthetic spread test (separates estimator bias from a
socket genuinely being input-distribution-sensitive). CPU only."""
import json, math, sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import estimators as E

BUILD = "/home/eileen/projects/quilt-gpu-lab/results/d2_build"
ESTS = ["E0", "E1", "E2", "E3", "E4", "E5"]
WEIGHTS = ["operational", "uniform", "degenerate"]


def q(v, K, lo, hi):
    x = (v - lo) / (hi - lo)
    return int(min(K - 1, max(0, math.floor(x * K))))


def salx(r):
    return int(round(r["sal"] * 1000))


def sallevel(r):
    return 0 if r["sal"] <= 0 else (1 if salx(r) <= 800 else 2)


def load_mini():
    return json.load(open(f"{BUILD}/mini_traces.json"))


def load_fb():
    d = json.load(open(f"{BUILD}/fb_traces.json"))
    out = {"real": [], "sto": []}
    for arm in ("real", "sto"):
        for w in d[arm]:
            out[arm].append({"i": w["i"], "recs": [
                {"x": a[0], "y": a[1], "sal": a[2], "fire": a[3], "ringB": a[4],
                 "sem": a[5], "rl": a[6], "win": a[7:]} for a in w["recs"]]})
    return out


def pool(a):
    return [r for w in a for r in w["recs"]]


def stationary_spread(K, p_main, n=999, nbins=40, seed=0):
    """Fixed conditional p(y|b) for ALL bins; sample under 3 input dists.
    True determinacy is identical across dists -> spread is pure estimator bias."""
    rng = np.random.default_rng(seed)
    p = np.full(K, (1.0 - p_main) / (K - 1)) if K > 1 else np.array([1.0])
    p[0] = p_main
    H = -sum(pi * math.log(pi) for pi in p if pi > 0)
    truth = 1.0 - H / math.log(K)
    # input distributions
    def sample(bin_w):
        b = rng.choice(nbins, size=n, p=bin_w)
        y = np.array([rng.choice(K, p=p) for _ in range(n)])
        return [{"b": int(bb), "y": int(yy)} for bb, yy in zip(b, y)]
    zipf = 1.0 / (np.arange(1, nbins + 1) ** 1.2)
    zipf /= zipf.sum()
    uni = np.full(nbins, 1.0 / nbins)
    deg = np.zeros(nbins); deg[0] = 1.0
    specs = {"operational": sample(zipf), "uniform": sample(uni), "degenerate": sample(deg)}
    spec = {"inp": lambda r: r["b"], "out": lambda r: r["y"], "O": K}
    row = {"truth": round(truth, 4)}
    for e in ESTS:
        vs = [E.score(specs[w], spec, est=e, weight=w, nperm=120) for w in WEIGHTS]
        row[e] = {"op": round(vs[0], 4), "uni": round(vs[1], 4), "deg": round(vs[2], 4),
                  "spread": round(max(vs) - min(vs), 4)}
    return row


def main():
    mini, fb = load_mini(), load_fb()
    mini_real, mini_sto = pool(mini["real"]), pool(mini["sto"])
    fb_real = pool(fb["real"])
    out = {}

    # 1) full declared reflex channel on build A's traces (sal x1000 | vision window)
    winchan = {"inp": lambda r: (salx(r), tuple(r.get("win", ()))), "out": lambda r: r["fire"], "O": 2}
    out["reflex_winchan_fb"] = {}
    for e in ESTS:
        vs = [E.score(fb_real, winchan, est=e, weight=w, nperm=120) for w in WEIGHTS]
        out["reflex_winchan_fb"][e] = {"op": round(vs[0], 4), "uni": round(vs[1], 4),
                                       "deg": round(vs[2], 4), "spread": round(max(vs) - min(vs), 4)}

    # 2) in-scope 6 sockets, canonical alphabets, op/uni/deg raw (mini sto)
    inscope = {
        "reflex.orient(salx)": ({"inp": salx, "out": lambda r: r["fire"], "O": 2}),
        "sensors.vision(6)": ({"inp": lambda r: (r["x"], r["y"]), "out": lambda r: q(r["sal"], 6, 0, 1), "O": 6}),
        "world.surprise(6)": ({"inp": lambda r: (r["x"], r["y"]), "out": lambda r: q(r["eta"], 6, 0, 1000), "O": 6}),
        "policy.action(5)": ({"inp": lambda r: (salx(r), r["food"]), "out": lambda r: int(round(r["act"])) + 1, "O": 5}),
        "memory.semantic(6)": ({"inp": lambda r: (r["x"], r["y"]), "out": lambda r: q(r["sem"], 6, 0, 600), "O": 6}),
        "memory.episodic(32)": ({"inp": lambda r: (r["x"], r["y"]), "out": lambda r: int(r["ringB"]), "O": 32}),
    }
    out["inscope_sto"] = {}
    for name, spec in inscope.items():
        row = {}
        for e in ESTS:
            vs = [E.score(mini_sto, spec, est=e, weight=w, nperm=120) for w in WEIGHTS]
            row[e] = {"op": round(vs[0], 4), "uni": round(vs[1], 4), "deg": round(vs[2], 4),
                      "spread": round(max(vs) - min(vs), 4),
                      "spread_opuni": round(abs(vs[0] - vs[1]), 4)}
        out["inscope_sto"][name] = row

    # 3) stationary-truth synthetic spread (pure estimator instability floor)
    out["stationary_spread"] = {
        "O2_p0.8": stationary_spread(2, 0.80, seed=1),
        "O3_p0.7": stationary_spread(3, 0.70, seed=2),
        "O6_p0.6": stationary_spread(6, 0.60, seed=3),
    }

    # 4) stable-fraction summaries on in-scope set (spread <= 0.15)
    summ = {}
    for e in ESTS:
        sp = [out["inscope_sto"][n][e]["spread"] for n in inscope]
        spou = [out["inscope_sto"][n][e]["spread_opuni"] for n in inscope]
        summ[e] = {"inscope_stable_3dist": sum(s <= 0.15 for s in sp), "of": len(sp),
                   "inscope_stable_opuni": sum(s <= 0.15 for s in spou),
                   "max_spread": round(max(sp), 4)}
    out["inscope_summary"] = summ

    with open(f"{HERE}/est_freeze_pass2.json", "w") as f:
        json.dump(out, f, indent=1)

    print("=== reflex on FULL declared channel (fb traces, sal|win) ===")
    for e, r in out["reflex_winchan_fb"].items():
        print(f"  {e}: op={r['op']} uni={r['uni']} deg={r['deg']} spread={r['spread']}")
    print("=== in-scope 6 sockets, sto, op/uni/deg spread (mini) ===")
    hdr = "socket".ljust(22) + " | " + " | ".join(e for e in ESTS)
    print(hdr)
    for n, row in out["inscope_sto"].items():
        print(n.ljust(22) + " | " + " | ".join(f"{row[e]['spread']:.3f}" for e in ESTS))
    print("=== STATIONARY-TRUTH spread (pure estimator bias; truth identical across dists) ===")
    for k, row in out["stationary_spread"].items():
        print(f"  {k} truth={row['truth']}: " + "  ".join(
            f"{e}={row[e]['spread']:.3f}" for e in ESTS))
    print("=== in-scope stable fraction (spread<=0.15) ===")
    for e in ESTS:
        print(f"  {e}: {out['inscope_summary'][e]}")
    print("wrote", f"{HERE}/est_freeze_pass2.json")


if __name__ == "__main__":
    main()
