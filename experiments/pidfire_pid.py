#!/usr/bin/env python3
"""pidfire_pid.py — PIDFIRE-1 phase 1: calibration + 200-IC evaluation of the servo arm.

Frozen (pre-reg + annotation): PID at p = p_corner; deadband = 0.25*SP; Ilim = 1.0;
alpha = 0.2; kd = 1.0; k_shadow = 128; q_t = clip(g_scale*I, 0, q_cap);
calib grid kp in {1,2,5} x ki in {5e-4,2e-3} x q_cand in {0.5,2.0}*q_corner (12 combos),
CAL seeds 900_000..900_007, objective RMSE(PV,SP) over measure window, deadlock dq
(mean density < 0.01 => RMSE=inf), tie-break |mean PV - SP|;
eval seeds 1_000_000..1_000_199; rho_IC = 0.05+0.9*u(seed+5e6) (declared);
reaches-SOC = n>=100 AND KS D vs REFERENCE <= max(0.10, 1.358*sqrt((n1+n2)/(n1*n2)))
              AND |tau_IC - tau_ref| <= 0.15;
borderline |D-D_gate| <= 0.15*D_gate => seeds +1e6/+2e6, majority vote.
Gates: C1 frac>=0.90; C2 0<corner_area_fraction<0.05; C3 |median tau - tau_ref|<=0.10.

Usage: python3 experiments/pidfire_pid.py --phase calib|eval
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pidfire_common import (  # noqa: E402
    T_TRANSIENT, fit_powerlaw, ks_two_sample, ks_two_sample_gate, run_pid,
)

LAB = Path(__file__).resolve().parent.parent
OUT = LAB / "results" / "pidfire_pid"
FREEZE = LAB / "results" / "pidfire_sweep" / "phase0_freeze.json"

KPS = (1.0, 2.0, 5.0)
KIS = (5e-4, 2e-3)
QFACS = (0.5, 2.0)
KD = 1.0
ALPHA = 0.2
ILIM = 1.0
K_SHADOW = 128
DEADBAND_FAC = 0.25
CAL_SEEDS = list(range(900_000, 900_008))
EVAL_SEEDS = list(range(1_000_000, 1_000_200))
RHO_OFF = 5_000_000


def rho_of(seed: int) -> float:
    return 0.05 + 0.9 * float(np.random.default_rng(seed + RHO_OFF).random())


def sim_one(combo: dict, freeze: dict, seed: int, rho: float):
    return run_pid(
        p=freeze["p_corner"], kp=combo["kp"], ki=combo["ki"], kd=KD,
        deadband=DEADBAND_FAC * freeze["sp_mean_burn_frac"], ilim=ILIM, alpha=ALPHA,
        g_scale=combo["g_scale"], q_cap=2.0 * combo["q_cand"], k_shadow=K_SHADOW,
        sp=freeze["sp_mean_burn_frac"], seed=seed, rho=rho,
    )


def phase_calib():
    freeze = json.loads(FREEZE.read_text())
    if "corner" not in freeze:
        print("calibration impossible without phase-0 corner — booked FAIL path")
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "calib.json").write_text(json.dumps({"status": "NO_CORNER"}))
        return
    combos = []
    for kp in KPS:
        for ki in KIS:
            for fac in QFACS:
                qc = fac * freeze["q_corner"]
                combos.append({"kp": kp, "ki": ki, "q_cand": qc, "g_scale": qc / ILIM})
    rows = []
    t0 = time.time()
    for c in combos:
        rmses, pvs, dqs = [], [], 0
        for seed in CAL_SEEDS:
            sizes, mean_burn, mean_rho, rmse, n_ign, n_sh = sim_one(c, freeze, seed, rho_of(seed))
            if mean_rho < 0.01:
                dqs += 1
                rmses.append(float("inf"))
            else:
                rmses.append(rmse)
            pvs.append(mean_burn)
        mean_rmse = statistics.fmean(rmses)
        rows.append({
            **{k: (round(v, 10) if isinstance(v, float) else v) for k, v in c.items()},
            "mean_rmse": None if math.isinf(mean_rmse) else round(mean_rmse, 8),
            "dq_count": dqs, "mean_pv": round(statistics.fmean(pvs), 8),
        })
        print(f"[calib] kp={c['kp']} ki={c['ki']} qc={c['q_cand']:.2e} "
              f"rmse={rows[-1]['mean_rmse']} dq={dqs} ({time.time() - t0:.0f}s)", flush=True)
    live = [r for r in rows if r["mean_rmse"] is not None]
    if live:
        best = min(live, key=lambda r: (r["mean_rmse"], abs(r["mean_pv"] - freeze["sp_mean_burn_frac"])))
        status = "OK"
    else:
        best = None
        status = "ALL_DEADLOCK"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "calib.json").write_text(json.dumps({
        "status": status, "winner": best, "rows": rows, "sp": freeze["sp_mean_burn_frac"],
    }, indent=1))
    print(json.dumps({"status": status, "winner": best}, indent=1))


def eval_ic(winner: dict, freeze: dict, seed: int, ref_sizes):
    sizes, mean_burn, mean_rho, rmse, n_ign, n_sh = sim_one(winner, freeze, seed, rho_of(seed))
    tau, s_min, d_self, _ = fit_powerlaw(sizes)
    n = len(sizes)
    if n > 0 and len(ref_sizes) > 0:
        d = ks_two_sample(sizes, ref_sizes)
        d_gate = ks_two_sample_gate(n, len(ref_sizes))
    else:
        d, d_gate = float("inf"), float("inf")
    tau_ref = freeze["tau_ref"]
    reaches = (n >= 100) and (d <= d_gate) and (
        math.isfinite(tau) and abs(tau - tau_ref) <= 0.15)
    return {
        "seed": seed, "rho": round(rho_of(seed), 4), "n_sizes": n,
        "tau": None if not math.isfinite(tau) else round(float(tau), 4),
        "ks_d": None if not math.isfinite(d) else round(float(d), 4),
        "d_gate": None if not math.isfinite(d_gate) else round(float(d_gate), 4),
        "reaches_soc": bool(reaches), "mean_pv": round(mean_burn, 8),
        "mean_density": round(mean_rho, 4), "rmse": round(rmse, 8),
        "n_ign": n_ign, "n_sh": n_sh, "sizes": sizes,
    }


def phase_eval():
    freeze = json.loads(FREEZE.read_text())
    calib = json.loads((OUT / "calib.json").read_text())
    winner = calib["winner"]
    if winner is None:
        print("ALL_DEADLOCK calibration — C1 FAIL booked in summary")
    ref_sizes = freeze["reference_sizes"]
    rows = []
    t0 = time.time()
    with (OUT / "eval.jsonl").open("w") as f:
        for seed in EVAL_SEEDS:
            row = eval_ic(winner, freeze, seed, ref_sizes)
            d, dg = row["ks_d"], row["d_gate"]
            borderline = (d is not None and dg is not None
                          and abs(d - dg) <= 0.15 * dg)
            votes = [row["reaches_soc"]]
            seeds_used = [seed]
            if borderline:
                for off in (1_000_000, 2_000_000):
                    r2 = eval_ic(winner, freeze, seed + off, ref_sizes)
                    votes.append(r2["reaches_soc"])
                    seeds_used.append(seed + off)
                row["reaches_soc"] = sum(votes) * 2 > len(votes)
            row["borderline"] = bool(borderline)
            row["votes"] = votes
            row["seeds_used"] = seeds_used
            rows.append(row)
            slim = {k: v for k, v in row.items() if k != "sizes"}
            f.write(json.dumps(slim) + "\n")
            f.flush()
            if (seed - EVAL_SEEDS[0]) % 20 == 19:
                print(f"[eval] {seed - EVAL_SEEDS[0] + 1}/200 done ({time.time() - t0:.0f}s)", flush=True)

    taus = [r["tau"] for r in rows if r["tau"] is not None]
    frac = (sum(1 for r in rows if r["reaches_soc"]) / len(rows)) if rows else 0.0
    med_tau = statistics.median(taus) if taus else None
    caf = freeze.get("corner_area_fraction")
    c1 = frac >= 0.90
    c2 = (caf is not None) and (0.0 < caf < 0.05)
    c3 = (med_tau is not None) and abs(med_tau - freeze["tau_ref"]) <= 0.10
    verdict = "PASS" if (c1 and c2 and c3) else "FAIL"
    if winner is None:
        verdict = "FAIL"
    summary = {
        "experiment": "PIDFIRE-1",
        "winner_combo": winner,
        "n_eval_ics": len(rows),
        "reach_fraction": round(frac, 4),
        "median_tau_eval": med_tau,
        "tau_ref": freeze["tau_ref"],
        "corner_area_fraction": caf,
        "C1_pid_reach": bool(c1),
        "C2_fixed_corner": bool(c2),
        "C3_exponent": bool(c3),
        "claim_verdict": verdict,
        "n_borderline": sum(1 for r in rows if r["borderline"]),
    }
    (OUT / "eval_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["calib", "eval"])
    a = ap.parse_args()
    (phase_calib if a.phase == "calib" else phase_eval)()
