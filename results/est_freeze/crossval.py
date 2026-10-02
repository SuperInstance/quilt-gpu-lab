#!/usr/bin/env python3
"""EST-FREEZE cross-validation — run estimators.py on identical D2 material.

Reads results/d2_build/{mini,fb}_traces.json (16 real + 16 sto worlds, both builds),
applies the C1-C5 protocol frozen in proposals/runs/EST-freeze.md, writes
results/est_freeze/est_freeze_crossval.json + bias_table.json.
CPU only. No GPU. No commits.
"""
import json
import os
import math
import sys
import numpy as np
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import estimators as E  # noqa: E402

BUILD = "/home/eileen/projects/quilt-gpu-lab/results/d2_build"
ESTS = ["E0", "E1", "E2", "E3", "E4", "E5"]
WEIGHTS = ["operational", "uniform", "degenerate"]

# --- frozen declared encoder ranges (frozen in EST-freeze.md §2) ---
RANGE = {"sal": (0.0, 1.0), "ringB": (0.0, 32.0), "sem": (0.0, 600.0),
         "eta": (0.0, 1000.0), "en": (0.0, 100.0), "act": (-1.0, 3.0),
         "food": (0.0, 8.0)}


def q(v, K, lo, hi):
    x = (v - lo) / (hi - lo)
    return int(min(K - 1, max(0, math.floor(x * K))))


def salx(r):
    return int(round(r["sal"] * 1000))


def sallevel(r):
    return 0 if r["sal"] <= 0 else (1 if salx(r) <= 800 else 2)


def load_mini():
    d = json.load(open(f"{BUILD}/mini_traces.json"))
    return d


def load_fb():
    """compact rec = [x,y,sal,fire,rb,sem,rl, *win(9)] -> dict."""
    d = json.load(open(f"{BUILD}/fb_traces.json"))
    out = {"n_train": d["n_train"], "evals": d["evals"], "real": [], "sto": []}
    for arm in ("real", "sto"):
        for w in d[arm]:
            recs = []
            for a in w["recs"]:
                recs.append({"x": a[0], "y": a[1], "sal": a[2], "fire": a[3],
                             "ringB": a[4], "sem": a[5], "rl": a[6],
                             "win": a[7:]})
            out[arm].append({"i": w["i"], "recs": recs})
    return out


# ------------------------------------------------------------- socket specs ---
def socket(s):
    """s = (name, out_fn, inp_fn, O_decl, rule_fn|None)"""
    return {"name": s[0], "out": s[1], "inp": s[2], "O": s[3],
            "rule": (s[4] if len(s) > 4 else None)}


def derived_family():
    fam = {}
    for K in range(2, 7):
        fam[f"episodic.ring{K}"] = socket(
            (f"episodic.ring{K}", lambda r, K=K: q(r["ringB"], K, *RANGE["ringB"]),
             lambda r: (r["x"], r["y"]), K))
        fam[f"semantic.sem{K}"] = socket(
            (f"semantic.sem{K}", lambda r, K=K: q(r["sem"], K, *RANGE["sem"]),
             lambda r: (r["x"], r["y"]), K))
        fam[f"surprise.eta{K}"] = socket(
            (f"surprise.eta{K}", lambda r, K=K: q(r["eta"], K, *RANGE["eta"]),
             lambda r: (r["x"], r["y"]), K))
        fam[f"energy.en{K}"] = socket(
            (f"energy.en{K}", lambda r, K=K: q(r["en"], K, *RANGE["en"]),
             lambda r: (r["x"], r["y"]), K))
        fam[f"vision.sal{K}"] = socket(
            (f"vision.sal{K}", lambda r, K=K: q(r["sal"], K, *RANGE["sal"]),
             lambda r: (r["x"], r["y"]), K))
    fam["reflex.orient"] = socket(("reflex.orient", lambda r: r["fire"],
                                   salx, 2, lambda r: 1 if salx(r) > 800 else 0))
    fam["reflex.rule"] = socket(("reflex.rule",
                                 lambda r: 1 if salx(r) > 800 else 0, salx, 2))
    fam["reflex.sallevel"] = socket(("reflex.sallevel", lambda r: r["fire"],
                                     sallevel, 2))
    fam["reflex.winchan"] = socket(("reflex.winchan", lambda r: r["fire"],
                                    lambda r: (salx(r), tuple(r.get("win", ()))), 2))
    fam["policy.act"] = socket(("policy.act", lambda r: int(round(r["act"])) + 1,
                                lambda r: (salx(r), r["food"]), 5))
    return fam


def pool(arm):
    return [r for w in arm for r in w["recs"]]


def per_world(arm):
    return [w["recs"] for w in arm]


# ------------------------------------------------------------------- C1 ------
def synthetic_atoms(n=999):
    """deterministic + noisy synthetic functions; unknown-truth bias table."""
    m = 17
    bins = [i % m for i in range(n)]
    truth_atoms, noise = {}, {}
    for K in range(2, 7):
        recs = [{"b": b} for b in bins]
        spec = {"inp": lambda r: r["b"], "out": lambda r, K=K: (r["b"] * 7 + 3) % K, "O": K}
        truth_atoms[K] = (recs, spec)
        for qq in (1.0, 0.9, 0.75, 0.6):
            rng = np.random.default_rng(0)
            ys = []
            for b in bins:
                y = (b * 7 + 3) % K
                if rng.random() > qq:
                    y = int(rng.integers(0, K))
                ys.append(y)
            recs2 = [{"b": b} for b in bins]
            spec2 = {"inp": lambda r: r["b"], "out": lambda r, ys=ys: r["_i"], "O": K}
            for i, r in enumerate(recs2):
                r["_i"] = ys[i]
            # analytic truth: p_true = qq+(1-qq)/K, others (1-qq)/K
            p = (1.0 - qq) / K
            H = -(qq + p) * math.log(qq + p) - (K - 1) * p * math.log(p) if p > 0 else 0.0
            if qq >= 1.0:
                H = 0.0
            truth = 1.0 - H / math.log(K)
            noise[(K, qq)] = (recs2, spec2, truth)
    return truth_atoms, noise


def run_pooled(recs, spec, est, weight, seed=0, nperm=120):
    return E.score(recs, spec, est=est, weight=weight, seed=seed, nperm=nperm)


def main():
    mini = load_mini()
    fb = load_fb()
    fam = derived_family()
    report = {"prereg": "proposals/runs/EST-freeze.md", "material": {
        "mini": f"{BUILD}/mini_traces.json", "fb": f"{BUILD}/fb_traces.json"},
        "n_worlds": 16, "evals": 1000}

    # ---- reproduce the two builds' disagreement (E0, different channels) ----
    repro = {}
    mini_real, mini_sto = pool(mini["real"]), pool(mini["sto"])
    fb_real = pool(fb["real"])
    repro["buildB_sallevel_ops_real"] = run_pooled(mini_real, fam["reflex.sallevel"], "E0", "operational")
    repro["buildB_sallevel_ops_sto"] = run_pooled(mini_sto, fam["reflex.sallevel"], "E0", "operational")
    repro["buildB_fine_ops_sto"] = run_pooled(mini_sto, fam["reflex.orient"], "E0", "operational")
    repro["buildB_fine_ops_real"] = run_pooled(mini_real, fam["reflex.orient"], "E0", "operational")
    repro["buildA_winchan_ops_real"] = run_pooled(fb_real, fam["reflex.winchan"], "E0", "operational")
    report["build_reproduction_E0"] = {k: round(v, 4) for k, v in repro.items()}

    # ---- det-arm atom purity diagnostic ----
    pure = sum(1 for r in mini_real if r["fire"] == (1 if salx(r) > 800 else 0))
    report["det_arm_reflex_purity_fire_given_salx"] = round(pure / len(mini_real), 6)

    # ---- C1 synthetic atoms (exactness) + bias table ----
    atoms, noise = synthetic_atoms()
    c1 = {}
    for K in range(2, 7):
        recs, spec = atoms[K]
        c1[str(K)] = {e: round(E.score(recs, spec, est=e, nperm=120), 6) for e in ESTS}
    report["C1_atom_scores_should_be_1"] = c1
    bias = {}
    for (K, qq), (recs, spec, truth) in noise.items():
        if qq >= 1.0:
            continue
        key = f"O{K}_q{qq}"
        bias[key] = {"truth": round(truth, 4)}
        for e in ESTS:
            bias[key][e] = round(E.score(recs, spec, est=e, nperm=120) - truth, 4)
    report["bias_table_est_minus_truth"] = bias

    # ---- C2 seed invariance (det arm, pooled) ----
    c2 = {}
    for name in ["reflex.orient", "episodic.ring2", "episodic.ring6",
                 "semantic.sem4", "reflex.sallevel"]:
        spec = fam[name]
        vals = defaultdict(list)
        for seed in range(5):
            for e in ESTS:
                vals[e].append(E.score(mini_real, spec, est=e, weight="operational",
                                       seed=seed, nperm=120))
        c2[name] = {e: round(max(v) - min(v), 6) for e, v in vals.items()}
    report["C2_seed_spread_det_arm"] = c2

    # ---- C3 cross-distribution spread at smallest alphabet ----
    c3 = {}
    for name, spec in fam.items():
        row = {}
        for e in ESTS:
            vs = [E.score(mini_sto, spec, est=e, weight=w, nperm=120) for w in WEIGHTS]
            row[e] = {"op": round(vs[0], 4), "uni": round(vs[1], 4),
                      "deg": round(vs[2], 4), "spread": round(max(vs) - min(vs), 4)}
        c3[name] = row
    report["C3_weight_spread_sto"] = c3
    # summary: how many sockets have spread <= 0.15 at each est (all O, then O=2 only)
    smallO = [n for n in fam if n.endswith("2") or n.startswith("reflex") or n == "reflex.sallevel"]
    summ = {}
    for e in ESTS:
        alls = [c3[n][e]["spread"] <= 0.15 for n in fam]
        smalls = [c3[n][e]["spread"] <= 0.15 for n in smallO]
        summ[e] = {"frac_stable_allO": round(sum(alls) / len(alls), 3),
                   "frac_stable_smallO": round(sum(smalls) / len(smalls), 3),
                   "max_spread_allO": round(max(c3[n][e]["spread"] for n in fam), 4)}
    report["C3_summary"] = summ

    # ---- C4 ordering reflex vs episodic(O=32) ----
    c4 = {}
    for e in ESTS:
        r = E.score(mini_sto, fam["reflex.orient"], est=e, weight="operational", nperm=120)
        epi = E.score(mini_sto, socket(("episodic.ring32",
                       lambda r: int(r["ringB"]), lambda r: (r["x"], r["y"]), 32)),
                      est=e, weight="operational", nperm=120)
        c4[e] = {"reflex": round(r, 4), "episodic32": round(epi, 4),
                 "range": round(r - epi, 4), "range_pass_ge_0.5": (r - epi) >= 0.5,
                 "reflex_ge_0.80": r >= 0.80}
    report["C4_ordering_sto"] = c4

    # ---- det-arm (real) determinacy per estimator for the canonical sockets ----
    detarm = {}
    for e in ESTS:
        detarm[e] = {
            "reflex.orient": round(E.score(mini_real, fam["reflex.orient"], est=e, nperm=120), 4),
            "reflex.rule": round(E.score(mini_real, fam["reflex.rule"], est=e, nperm=120), 4),
            "episodic.ring32": round(E.score(mini_real, socket(("e32",
                                lambda r: int(r["ringB"]), lambda r: (r["x"], r["y"]), 32)),
                                est=e, nperm=120), 4),
        }
    report["det_arm_real_scores"] = detarm

    with open(f"{HERE}/est_freeze_crossval.json", "w") as f:
        json.dump(report, f, indent=1)

    # ---- console summary ----
    print("=== build reproduction (E0) ===")
    for k, v in report["build_reproduction_E0"].items():
        print(f"  {k:34s} {v}")
    print("  det reflex purity fire|salx =", report["det_arm_reflex_purity_fire_given_salx"])
    print("=== C1 atom scores (must be 1.000) ===")
    for K, row in c1.items():
        print(f"  O={K}: " + "  ".join(f"{e}={row[e]:.3f}" for e in ESTS))
    print("=== bias @O=2 (est - truth) ===")
    for k, row in bias.items():
        if k.startswith("O2_"):
            print(f"  {k}: truth={row['truth']:.3f} " + " ".join(f"{e}={row[e]:+.3f}" for e in ESTS))
    print("=== C2 seed spread (must be 0) ===")
    for n, row in c2.items():
        print(f"  {n}: " + " ".join(f"{e}={row[e]:.4f}" for e in ESTS))
    print("=== C3 weight spread summary (sto) ===")
    for e in ESTS:
        print(f"  {e}: {summ[e]}")
    print("=== C4 ordering ===")
    for e in ESTS:
        print(f"  {e}: {c4[e]}")
    print("wrote", f"{HERE}/est_freeze_crossval.json")


if __name__ == "__main__":
    main()
