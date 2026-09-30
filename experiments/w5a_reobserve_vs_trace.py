#!/usr/bin/env python3
"""W5a — re-observation vs trace-reading (frozen pre-reg: proposals/runs/W5a-reobserve-vs-trace.md).

Four arms, SAME detector, different data:
  trace     recorded (quantized+subsampled) harness log
  rawsame   raw values at the same recorded positions
  fresh     fresh raw draws from the same world, count-matched (pure re-observation)
  freshfull fresh raw draws, all T positions (upper bound)
QO6 predicts fresh < trace error. REFUTED if trace matches fresh (<=2pp, no direction).
"""
import argparse
import json
import zlib
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "results" / "w5a_reobserve_vs_trace"

SIGMA, T, T0 = 1.0, 200, 50
MUS = [0.0, 0.2, 0.5, 1.0]          # 0.0 = no-drift cells (detection = false alarms)
SIGNS = [1, -1]
QS = [0.5, 1.0]                      # trace quantization (sigma units)
KS = [1, 4]                          # trace subsampling
REPS, SEEDS = 200, [1101, 1102, 1103]
DEC_THRESH = 0.2                     # frozen detection threshold (sigma units)
T0_TOL = 10
ARMS = ["trace", "rawsame", "fresh", "freshfull"]


def positions(k):
    return np.arange(0, T, k)


def detector(x, pos):
    """Frozen matched detector on samples at `pos` (values x, aligned to pos)."""
    best_s, best_v = 0, 0.0
    for s in pos[1:-1]:
        before = x[pos < s]
        after = x[pos >= s]
        if len(before) < 5 or len(after) < 5:
            continue
        v = after.mean() - before.mean()
        if abs(v) > abs(best_v):
            best_s, best_v = int(s), float(v)
    detected = abs(best_v) >= DEC_THRESH
    sign = int(np.sign(best_v)) if detected else 0
    return detected, sign, best_s


def diagnose(values, pos):
    detected, sign, t0_hat = detector(values, pos)
    return detected, sign, t0_hat


def run(reps, seeds, tag):
    """Returns per-cell arm error rates (paired per world)."""
    cells = []
    for mu in MUS:
        for sgn in SIGNS:
            if mu == 0.0 and sgn == -1:
                continue
            for q in QS:
                for k in KS:
                    cells.append((mu, sgn, q, k))
    tally = {c: {a: {"det_err": 0, "sign_err": 0, "t0_err": 0} for a in ARMS} for c in cells}
    n = reps * len(seeds)
    for seed in seeds:
        for rep in range(reps):
            for (mu, sgn, q, k) in cells:
                cell_seed = zlib.crc32(f"{seed}|{rep}|{mu}|{sgn}|{q}|{k}".encode())
                rng = np.random.default_rng(cell_seed)
                pos = positions(k)
                # world (two independent noise streams: one gets recorded, one is fresh)
                z_rec = rng.standard_normal(T)
                z_fresh = rng.standard_normal(T)
                mu_t = np.where(np.arange(T) >= T0, sgn * mu * SIGMA, 0.0)
                x_rec = mu_t + SIGMA * z_rec
                x_fresh = mu_t + SIGMA * z_fresh
                trace = np.round(x_rec / (q * SIGMA)) * (q * SIGMA)
                data = {
                    "trace": trace[pos], "rawsame": x_rec[pos],
                    "fresh": x_fresh[pos], "freshfull": x_fresh,
                }
                posmap = {"trace": pos, "rawsame": pos, "fresh": pos,
                          "freshfull": np.arange(T)}
                truth_det = mu > 0.0
                for a in ARMS:
                    det, sgn_hat, t0_hat = diagnose(data[a], posmap[a])
                    if det != truth_det:
                        tally[(mu, sgn, q, k)][a]["det_err"] += 1
                    if truth_det:
                        if det and sgn_hat != sgn:
                            tally[(mu, sgn, q, k)][a]["sign_err"] += 1
                        if det and abs(t0_hat - T0) > T0_TOL:
                            tally[(mu, sgn, q, k)][a]["t0_err"] += 1
    rates = {}
    for c, v in tally.items():
        rates[str(c)] = {a: {m: cnt / n for m, cnt in vv.items()} for a, vv in v.items()}
    return rates, n, tag


def verdict(rates):
    primary = []
    for c, arms in rates.items():
        (mu, sgn, q, k) = eval(c)
        if mu == 0.0:
            continue
        primary.append((c, arms["trace"]["det_err"], arms["fresh"]["det_err"]))
    diffs = [t - f for _, t, f in primary]
    overall = float(np.mean(diffs))
    wins = sum(1 for d in diffs if d > 0.02)
    worst = min(diffs)  # most negative = trace beating fresh
    if wins >= 8 and worst > -0.02:
        v = "CONFIRM"
    elif abs(overall) <= 0.02 and wins <= 7:
        v = "REFUTED"
    else:
        v = "MIXED"
    return {"verdict": v, "overall_pp": round(overall * 100, 2),
            "cells_fresh_wins_gt2pp": wins, "n_primary_cells": len(primary),
            "worst_cell_pp": round(worst * 100, 2),
            "per_cell_pp": {c: round((t - f) * 100, 2) for c, t, f in primary}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    reps, seeds = (10, [1101]) if args.smoke else (REPS, SEEDS)
    OUT.mkdir(parents=True, exist_ok=True)
    rates, n, tag = run(reps, seeds, "smoke" if args.smoke else "full")
    res = {"n_worlds_per_cell": n, "arms": ARMS, "rates": rates,
           "verdict": verdict(rates) if not args.smoke else "smoke-only"}
    (OUT / ("smoke_results.json" if args.smoke else "results.json")).write_text(
        json.dumps(res, indent=2))
    if args.smoke:
        c = str((0.5, 1, 1.0, 4))
        print("smoke cell 0.5/+1/q=1.0/k=4:", json.dumps(rates[c], indent=1)[:400])
        print("SMOKE OK")
    else:
        print(json.dumps(res["verdict"], indent=2)[:600])
        print("WROTE", OUT / "results.json")


if __name__ == "__main__":
    main()
