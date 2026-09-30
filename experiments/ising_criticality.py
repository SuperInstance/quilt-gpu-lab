#!/usr/bin/env python3
"""ISING-1 — criticality on the lattice (GPU Metropolis; gates frozen in
proposals/runs/ISING-1-plan.md, pushed BEFORE this run — this script executes).

2D Ising 128x128, checkerboard Metropolis on torch (CUDA), T sweep 1.5..3.5.
Estimator: susceptibility peak chi = N*(<m^2> - <|m|>^2)/T, parabolic refine.
Gates: |Tc - 2.269| <= 0.15 REPLICATED / <= 0.4 MARGINAL / else DEVIATES.

Plus the fleet-fabric demo: the 9 live board cells as spins, real links as
couplings — ordered at T=0.5, disordered at T=2.0 (a demo, not the science).

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/ising_criticality.py
"""
import json
import math
import os
import sys
import time

import torch

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
N = 128
J = 1.0
SWEEP_EQ = 300
SWEEP_MEAS = 300
TC_ANALYTIC = 2.0 / math.log(1.0 + math.sqrt(2.0))  # 2.269185...


def log(msg):
    print("[ising] %s" % msg, flush=True)


def metropolis_sweep(spins, beta, gen):
    """One checkerboard Metropolis sweep, vectorized. spins: {+1,-1}^(N,N)."""
    for shift in (0, 1):  # the two sublattices
        nb = (torch.roll(spins, 1, 0) + torch.roll(spins, -1, 0)
              + torch.roll(spins, 1, 1) + torch.roll(spins, -1, 1))
        dE = 2.0 * J * spins * nb
        mask = ((torch.arange(N, device=spins.device)[:, None]
                 + torch.arange(N, device=spins.device)[None, :]) % 2) == shift
        accept = torch.rand(N, N, device=spins.device, generator=gen) < torch.exp(
            torch.clamp(-beta * dE, max=0.0))
        spins = torch.where(mask & accept, -spins, spins)
    return spins


def run_temperature(dev, gen, T):
    beta = 1.0 / T
    spins = torch.where(torch.rand(N, N, device=dev, generator=gen) < 0.5, 1.0, -1.0)
    assert spins.dtype.is_floating_point, (
        "spins must be float — Long breaks mean() (first ISING-1 fire died here): got %s" % spins.dtype)
    for _ in range(SWEEP_EQ):
        spins = metropolis_sweep(spins, beta, gen)
    m2, mabs, n = 0.0, 0.0, 0
    for _ in range(SWEEP_MEAS):
        spins = metropolis_sweep(spins, beta, gen)
        m = spins.mean().abs().item()
        mabs += m
        m2 += m * m
        n += 1
    return mabs / n, N * N * (m2 / n - (mabs / n) ** 2) / T


def fabric_demo(dev, gen):
    """The 9 live board cells: spins from dial sign vs channel median, real links."""
    cells = {
        "A1": [4688, 9844], "B1": [10000, 2812, 2344, 9688], "C1": [200, 5550],
        "D1": [400, 8766], "E1": [3, 2, 0], "F1": [0],
        "G1": [44, 23, 5, 14], "H1": [14, 8920], "A2": [2, 5],
    }
    links = [["A1", "B1"], ["A2", "B1"], ["B1", "H1"], ["C1", "D1"],
             ["C1", "H1"], ["E1", "H1"], ["G1", "H1"]]
    medians = {}
    for i in range(max(len(v) for v in cells.values())):
        vals = sorted(v[i] for v in cells.values() if len(v) > i)
        medians[i] = vals[len(vals) // 2]
    spins = {a: (-1 if d[0] < medians[0] else 1) for a, d in cells.items()}
    out = {}
    for T in (0.5, 2.0):
        beta = 1.0 / T
        s = dict(spins)
        for _ in range(50):
            for a, b in links:
                field = s[a] + s[b]
                if torch.rand(1, device=dev, generator=gen).item() < math.exp(min(0.0, -2.0 * beta * J * field)):
                    weak = a if abs(s[a]) <= abs(s[b]) else b
                    s[weak] = -s[weak]
        out["T=%.1f" % T] = round(abs(sum(s.values())) / len(s), 4)
    return out


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    gen = torch.Generator(device=dev).manual_seed(20260929)
    log("device=%s N=%d J=%.1f sweeps=%d+%d" % (dev, N, J, SWEEP_EQ, SWEEP_MEAS))
    t0 = time.time()

    temps = [round(1.5 + 0.1 * i, 1) for i in range(21)]
    mags, chis = [], []
    for T in temps:
        m, c = run_temperature(dev, gen, T)
        mags.append(round(m, 5))
        chis.append(round(c, 2))
        log("T=%.1f  |m|=%.4f  chi=%.1f" % (T, m, c))
        if not (m == m and c == c):  # NaN guard
            sys.exit("[ising] FATAL: NaN in sweep — INVALID_HARNESS")

    k = chis.index(max(chis))
    if 0 < k < len(temps) - 1:  # parabolic refine on the peak triplet
        y0, y1, y2 = chis[k - 1], chis[k], chis[k + 1]
        d = (y0 - 2 * y1 + y2)
        delta = 0.5 * (y0 - y2) / d if d != 0 else 0.0
        tc = round(temps[k] + 0.1 * max(-1.0, min(1.0, delta)), 4)
    else:
        tc = temps[k]
    err = round(abs(tc - TC_ANALYTIC), 4)

    verdict = "REPLICATED" if err <= 0.15 else ("MARGINAL" if err <= 0.4 else "DEVIATES")

    demo = fabric_demo(dev, gen)
    receipt = {
        "experiment": "ISING-1", "device": dev, "N": N, "J": J,
        "sweeps": [SWEEP_EQ, SWEEP_MEAS], "temps": temps, "abs_m": mags, "chi": chis,
        "tc_est": tc, "tc_analytic": round(TC_ANALYTIC, 4), "tc_err": err,
        "verdict": verdict, "fabric_demo_abs_m": demo,
        "gate_source": "proposals/runs/ISING-1-plan.md (frozen, pushed pre-run)",
        "wall_s": round(time.time() - t0, 1),
    }
    out = os.path.join(LAB, "results", "ising_criticality.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(receipt, fh, indent=1)
    log("Tc_est=%.4f analytic=%.4f err=%.4f -> %s" % (tc, TC_ANALYTIC, err, verdict))
    log("fabric demo |m|: %s" % demo)
    log("receipt -> %s" % out)


if __name__ == "__main__":
    main()
