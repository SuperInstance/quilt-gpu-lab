#!/usr/bin/env python3
"""D2-V1 — analysis + gate assembly (CPU).  E3 perm-exact norm-MI determinacy
(results/est_freeze/estimators.py), frozen declared encoders (d2_v1_common),
bootstrap-over-worlds CIs, H1-H6 per prereg AS AMENDED by the EST-FREEZE fold.
"""
import json, os, sys, math
import numpy as np

LAB = "/home/eileen/projects/quilt-gpu-lab"
sys.path.insert(0, os.path.join(LAB, "results/d2_v1/scripts"))
sys.path.insert(0, os.path.join(LAB, "results/est_freeze"))
import d2_v1_common as C          # noqa: E402
from estimators import score     # noqa: E402

OUT = os.path.join(LAB, "results/d2_v1")
B = 1000
SYNTH_FLOOR = 0.04                # EST-FREEZE synthetic stationary-truth floor (E3 0.003-0.039)
rng = np.random.default_rng(2718)


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    d = math.sqrt((ra @ ra) * (rb @ rb))
    return float(ra @ rb / d) if d > 0 else 0.0


def determinacy(records, phi, psi, O, weight):
    return score(records, {"inp": phi, "out": psi, "O": O}, est="E3",
                 weight=weight, seed=0, nperm=120)


def ks(a, b):
    A = np.sort(np.asarray(a)); Bb = np.sort(np.asarray(b))
    allv = np.concatenate([A, Bb])
    d = 0.0
    for v in allv:
        d = max(d, abs(np.mean(A <= v) - np.mean(Bb <= v)))
    en = math.sqrt(len(A) * len(Bb) / (len(A) + len(Bb)))
    lam = (en + 0.12 + 0.11 / en) * d
    p = sum(2 * (-1) ** (k - 1) * math.exp(-2 * k * k * lam * lam) for k in range(1, 101))
    return {"D": float(d), "p": float(max(0.0, min(1.0, p)))}


def main():
    T = C.load()
    TW = json.load(open(os.path.join(OUT, "d2_v1_twins_result.json")))
    WR = json.load(open(os.path.join(OUT, "d2_v1_world_report.json")))

    sto_recs = [r for w in T["sto"] for r in w["recs"]]
    real_recs = [r for w in T["real"] for r in w["recs"]]

    det = {}
    for S in C.SOCKETS:
        n, phi, psi, O = S["name"], S["phi"], S["psi"], S["O"]
        op = determinacy(sto_recs, phi, psi, O, "operational")
        un = determinacy(sto_recs, phi, psi, O, "uniform")
        dg = determinacy(sto_recs, phi, psi, O, "degenerate")
        ro = determinacy(real_recs, phi, psi, O, "operational")
        spread = max(op, un, dg) - min(op, un, dg)
        excess = max(0.0, spread - SYNTH_FLOOR)
        det[n] = {"operational": round(op, 4), "uniform": round(un, 4), "degenerate": round(dg, 4),
                  "real_operational": round(ro, 4), "O": O, "log2O": round(math.log2(O), 3),
                  "spread": round(spread, 4), "spread_excess_over_synth_floor": round(excess, 4),
                  "h5_amended_stable": bool(excess <= 0.15),
                  "degenerate_role": "F4 diagnostic only (per amendment)"}
        print(f"det {n:16s} op={op:.3f} uni={un:.3f} deg={dg:.3f} real={ro:.3f} "
              f"spread={spread:.3f} excess={excess:.3f}", flush=True)

    # ---- gaps + per-socket bootstrap CI over held-out REAL test worlds ----
    per_socket = {}
    gaps_mean, dets = [], []
    for S in C.SOCKETS:
        n = S["name"]; R = TW["sockets"][n]
        runs = R["runs"]
        seedy = sorted({r["seed"] for r in runs})
        def arr(cond):
            return np.array([r["nerr_per_world"] for r in runs if r["cond"] == cond])  # seeds x worlds
        A = {c: arr(c) for c in ["real", "sim", "sim_mis"]}
        gsim = A["sim"] - A["real"]        # seeds x worlds
        gmis = A["sim_mis"] - A["real"]
        gap_sim = float(gsim.mean()); gap_mis = float(gmis.mean())
        nW = gsim.shape[1]
        bs_sim = np.array([gsim[:, rng.integers(0, nW, nW)].mean() for _ in range(B)])
        bs_mis = np.array([gmis[:, rng.integers(0, nW, nW)].mean() for _ in range(B)])
        per_socket[n] = {
            "nerr_real_mean": R["runs"] and float(A["real"].mean()),
            "nerr_sim_mean": float(A["sim"].mean()),
            "nerr_sim_mis_mean": float(A["sim_mis"].mean()),
            "gap_sim": round(gap_sim, 4),
            "gap_sim_ci95": [round(float(np.percentile(bs_sim, 2.5)), 4),
                             round(float(np.percentile(bs_sim, 97.5)), 4)],
            "gap_sim_mis": round(gap_mis, 4),
            "gap_sim_mis_ci95": [round(float(np.percentile(bs_mis, 2.5)), 4),
                                 round(float(np.percentile(bs_mis, 97.5)), 4)],
            "gap_seed_std": R["gap_seed_std"], "seed_law": R["seed_law"],
            "determinacy_operational": det[n]["operational"],
            "h5_amended_stable": det[n]["h5_amended_stable"],
            "_gsim": gsim,
        }
        gaps_mean.append(gap_sim); dets.append(det[n]["operational"])
        print(f"gap {n:16s} sim={gap_sim:+.4f} {per_socket[n]['gap_sim_ci95']} "
              f"mis={gap_mis:+.4f} seedstd={R['gap_seed_std']:.4f} {R['seed_law']}", flush=True)

    # ---- H1 correlation + rho bootstrap (resample worlds; determinacy held fixed) ----
    dets_a = np.array(dets); gaps_a = np.array(gaps_mean)
    rho = spearman(dets_a, gaps_a)
    nW = per_socket[C.SOCKETS[0]["name"]]["_gsim"].shape[1]
    rho_bs = []
    for _ in range(B):
        idx = rng.integers(0, nW, nW)
        gb = np.array([per_socket[S["name"]]["_gsim"][:, idx].mean() for S in C.SOCKETS])
        rho_bs.append(spearman(dets_a, gb))
    rho_bs = np.array(rho_bs)
    rho_ci = [round(float(np.percentile(rho_bs, 2.5)), 4), round(float(np.percentile(rho_bs, 97.5)), 4)]
    h1 = {"rho": round(rho, 4), "rho_ci95": rho_ci,
          "gate": "PASS" if (rho <= -0.60 and rho_ci[1] < 0) else "FAIL"}

    # ---- H2 near-1 transfer ----
    hi = [S["name"] for S in C.SOCKETS if det[S["name"]]["operational"] >= 0.80]
    h2 = {"near1_sockets": hi,
          "mean_gap_sim": round(float(np.mean([per_socket[n]["gap_sim"] for n in hi])), 4) if hi else None,
          "gate": ("PASS" if hi and float(np.mean([per_socket[n]["gap_sim"] for n in hi])) <= 0.05
                   else ("FAIL" if hi else "N/A (no det>=0.8 socket)"))}

    # ---- H3 control widens ----
    mg = float(np.mean([per_socket[n]["gap_sim"] for n in per_socket]))
    mm = float(np.mean([per_socket[n]["gap_sim_mis"] for n in per_socket]))
    h3 = {"mean_gap_sim": round(mg, 4), "mean_gap_sim_mis": round(mm, 4),
          "delta": round(mm - mg, 4), "gate": "PASS" if mm >= mg + 0.05 else "FAIL"}

    # ---- H4 / F3 from world report ----
    h4 = dict(WR["h4"])
    # ---- H5 amended ----
    offenders = [n for n in det if not det[n]["h5_amended_stable"]]
    h5 = {"spreads": {n: det[n]["spread"] for n in det},
          "excess_over_synth_floor": {n: det[n]["spread_excess_over_synth_floor"] for n in det},
          "offenders": offenders, "n_sockets": len(det),
          "gate": "PASS" if len(offenders) <= len(det) / 3 else "INCONCLUSIVE"}
    # ---- H6 range ----
    rng_ = max(dets) - min(dets)
    h6 = {"range": round(rng_, 4), "gate": "PASS" if rng_ >= 0.5 else "FAIL"}

    # ---- F6 KS pre-gate (mismatch must reject equality) ----
    sal_real = [r[2] for r in real_recs]
    sal_sim = [r[2] for r in sto_recs]
    sal_mis = [max(0.0, min(1.0, s / 1000.0 * 1.6 + 0.15)) * 1000 for s in sal_sim]
    f6 = {"ks_sim_vs_real": ks(sal_sim, sal_real), "ks_mismatch_vs_real": ks(sal_mis, sal_real)}
    f6["gate"] = "PASS" if f6["ks_mismatch_vs_real"]["p"] <= 0.05 else "FAIL"

    # ---- F8 reflex A/B across the stochastic patch ----
    f8 = {"reflex_det_real": det["reflex.orient"]["real_operational"],
          "reflex_det_sto": det["reflex.orient"]["operational"],
          "delta": round(det["reflex.orient"]["operational"] - det["reflex.orient"]["real_operational"], 4)}
    f8["gate"] = "PASS" if f8["delta"] >= -0.05 else "VOID (patch leaks into reflex socket)"

    # ---- H-GROWTH ----
    hgrowth = dict(WR["hgrowth"])
    hgrowth["booked"] = ("R2 SURVIVES stochastic worlds" if hgrowth["gated_frac"] >= 0.8 and hgrowth["unguided_frac"] <= 0.2
                         else ("R2 COLLAPSES (gated<50%)" if hgrowth["gated_frac"] < 0.5
                               else "R2 DOES NOT SURVIVE (unguided grows too — seed-vacuity confirmed)"))

    # ---- mechanical verdict ----
    gates = {"H1": h1["gate"], "H2": h2["gate"], "H3": h3["gate"], "H4": h4["gate"],
             "H5": h5["gate"], "H6": h6["gate"]}
    if all(gates[g] == "PASS" for g in gates):
        verdict = "KEEP"
    elif gates["H3"] == "PASS" and gates["H4"] == "PASS" and gates["H5"] == "PASS" and gates["H6"] == "PASS" and rho >= 0:
        verdict = "KILL"
    else:
        verdict = "INCONCLUSIVE"
    seed_law_offenders = [n for n in per_socket if per_socket[n]["seed_law"] != "PASS"]

    # ---- 1000-world extension trigger ----
    ci_w = rho_ci[1] - rho_ci[0]
    ext = {"h4_pass": h4["gate"] == "PASS", "rho_ci_width": round(ci_w, 4),
           "triggers": bool(h4["gate"] == "PASS" and ci_w > 0.40)}
    ext["decision"] = ("FIRE x5 extension (H4 pass + CI width %.2f > 0.40)" % ci_w) if ext["triggers"] \
        else ("DO NOT FIRE (H4 %s / CI width %.2f)" % (h4["gate"], ci_w))

    out = {"task": "D2-V1", "lane": "D2-V1", "prereg": "proposals/runs/D2-stochastic-worlds-prereg.md",
           "amendments": ["estimator E3 (perm-exact norm-MI) primary, E0 reserve — E3 used",
                          "encoders declared+frozen per socket; determinacy on FULL-CHANNEL path only",
                          "H5 re-derived: gate on operational; per-socket spread is a DATUM with the "
                          "synthetic floor (%.2f) subtracted; degenerate input = F4 diagnostic" % SYNTH_FLOOR,
                          "reflex twin target/input FIXED (operational delivered channel) so seeds are distinguishable",
                          "H6 re-adjudicated under frozen encoders (bar 0.648 >= 0.5 already booked)"],
           "verdict": verdict, "gates": gates, "H1": h1, "H2": h2, "H3": h3, "H4": h4,
           "H5": h5, "H6": h6, "H-GROWTH": hgrowth, "F6": f6, "F8": f8,
           "determinacy": det, "per_socket": {k: {kk: vv for kk, vv in v.items() if kk != "_gsim"}
                                              for k, v in per_socket.items()},
           "seed_law_offenders": seed_law_offenders,
           "extension": ext, "bootstrap_B": B,
           "bootstrap_note": "resample held-out REAL test worlds (n=60) for gaps; determinacy held at pooled operational value",
           "world_report": {"f3": WR["f3"], "h4": WR["h4"], "pct_grown_sto": WR["pct_grown_sto"]}}
    json.dump(out, open(os.path.join(OUT, "d2_v1_result.json"), "w"), indent=1)
    print("\n==== D2-V1 VERDICT:", verdict, "====")
    for g in gates:
        print(f"  {g}: {gates[g]}")
    print("  rho", h1["rho"], h1["rho_ci95"], "| H2", h2, "| H3", h3["delta"])
    print("  H-GROWTH:", hgrowth["booked"], "| seed-law offenders:", seed_law_offenders)
    print("  extension:", ext["decision"])
    print("wrote d2_v1_result.json")


if __name__ == "__main__":
    main()
