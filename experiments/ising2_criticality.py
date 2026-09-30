#!/usr/bin/env python3
"""ISING-2 — criticality with a statistic that can carry the claim.

Parent ISING-1 returned MARGINAL but diagnosed its own estimator: one 300-sweep
sample per T gave a non-unimodal chi curve (chi=0.00 at T=1.6). This round:
8 independent runs/T with error bars, a Binder cumulant, and a PRE-REGISTERED
unimodality gate that fails loud (ESTIMATOR_UNSTABLE) instead of reporting a Tc.

Gates frozen in proposals/runs/ISING-2-plan.md, pushed before this run.
Receipt: results/ising2_criticality.json (does NOT overwrite ISING-1's).

Run: /home/eileen/venvs/elephant-gpu/bin/python experiments/ising2_criticality.py
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
RUNS = 8
SWEEP_EQ = 300
SWEEP_MEAS = 300
TC_ANALYTIC = 2.0 / math.log(1.0 + math.sqrt(2.0))  # 2.269185...


def log(msg):
    print("[ising2] %s" % msg, flush=True)


def metropolis_sweep(spins, beta, gen):
    for shift in (0, 1):  # checkerboard sublattices keep it vectorized
        nb = (torch.roll(spins, 1, 0) + torch.roll(spins, -1, 0)
              + torch.roll(spins, 1, 1) + torch.roll(spins, -1, 1))
        dE = 2.0 * J * spins * nb
        idx = torch.arange(N, device=spins.device)
        mask = ((idx[:, None] + idx[None, :]) % 2) == shift
        accept = torch.rand(N, N, device=spins.device, generator=gen) < torch.exp(
            torch.clamp(-beta * dE, max=0.0))
        spins = torch.where(mask & accept, -spins, spins)
    return spins


def one_run(dev, gen, T):
    """One independent sample: fresh random init -> eq -> measure. Returns (mabs, chi, binder)."""
    beta = 1.0 / T
    spins = torch.where(torch.rand(N, N, device=dev, generator=gen) < 0.5, 1.0, -1.0)
    assert spins.dtype.is_floating_point, "spins must be float: %s" % spins.dtype
    for _ in range(SWEEP_EQ):
        spins = metropolis_sweep(spins, beta, gen)
    s1 = s2 = s4 = 0.0
    for _ in range(SWEEP_MEAS):
        spins = metropolis_sweep(spins, beta, gen)
        m = spins.mean().abs().item()
        s1 += m
        s2 += m * m
        s4 += m ** 4
    n = SWEEP_MEAS
    m1, m2, m4 = s1 / n, s2 / n, s4 / n
    chi = N * N * (m2 - m1 * m1) / T
    binder = 1.0 - m4 / (3.0 * m2 * m2) if m2 > 0 else float("nan")
    return m1, chi, binder


def mean_std(xs):
    n = len(xs)
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return mu, math.sqrt(var)


def fabric_demo(dev, gen):
    """Illustrative only: 9 live board cells as spins, real links as couplings."""
    cells = {
        "A1": [4688, 9844], "B1": [10000, 2812, 2344, 9688], "C1": [200, 5550],
        "D1": [400, 8766], "E1": [3, 2, 0], "F1": [0],
        "G1": [44, 23, 5, 14], "H1": [14, 8920], "A2": [2, 5],
    }
    links = [("A1", "B1"), ("A2", "B1"), ("B1", "H1"), ("C1", "D1"),
             ("C1", "H1"), ("E1", "H1"), ("G1", "H1")]
    med = {}
    for i in range(max(len(v) for v in cells.values())):
        vals = sorted(v[i] for v in cells.values() if len(v) > i)
        med[i] = vals[len(vals) // 2]
    spins = {a: (-1.0 if d[0] < med[0] else 1.0) for a, d in cells.items()}
    nbr = {a: [] for a in cells}
    for a, b in links:
        nbr[a].append(b)
        nbr[b].append(a)
    out = {}
    for T in (0.5, 2.0):
        beta = 1.0 / T
        s = dict(spins)
        for _ in range(200):
            for a in list(s):
                field = sum(s[b] for b in nbr[a])
                dE = 2.0 * J * s[a] * field
                if torch.rand(1, device=dev, generator=gen).item() < math.exp(min(0.0, -beta * dE)):
                    s[a] = -s[a]
        out["T=%.1f" % T] = round(abs(sum(s.values())) / len(s), 4)
    return out


def main():
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    gen = torch.Generator(device=dev).manual_seed(20260930)
    log("device=%s N=%d J=%.1f RUNS=%d sweeps=%d+%d" % (dev, N, J, RUNS, SWEEP_EQ, SWEEP_MEAS))
    t0 = time.time()

    temps = [round(1.5 + 0.1 * i, 1) for i in range(21)]
    curve = []
    for T in temps:
        mabs, chis, binders = [], [], []
        for _ in range(RUNS):
            m, c, u = one_run(dev, gen, T)
            if m != m or c != c:
                sys.exit("[ising2] FATAL: NaN at T=%.1f — INVALID_HARNESS" % T)
            mabs.append(m)
            chis.append(c)
            binders.append(u)
        mm, ms = mean_std(mabs)
        cm, cs = mean_std(chis)
        um, _ = mean_std(binders)
        curve.append({"T": T, "m_mean": round(mm, 5), "m_std": round(ms, 5),
                      "chi_mean": round(cm, 2), "chi_std": round(cs, 2),
                      "binder": round(um, 5)})
        log("T=%.1f  |m|=%.4f+-%.4f  chi=%.1f+-%.1f  U=%.4f" % (T, mm, ms, cm, cs, um))

    chis = [c["chi_mean"] for c in curve]
    k = chis.index(max(chis))
    # pre-registered unimodality gate: peak must clear both ends by 2x
    ends = (chis[0], chis[-1])
    unimodal = (max(chis) >= 2.0 * max(ends)) and (0 < k < len(chis) - 1)
    if not unimodal:
        verdict = "ESTIMATOR_UNSTABLE"
        tc = None
    else:
        y0, y1, y2 = chis[k - 1], chis[k], chis[k + 1]
        d = (y0 - 2 * y1 + y2)
        delta = 0.5 * (y0 - y2) / d if d != 0 else 0.0
        tc = round(temps[k] + 0.1 * max(-1.0, min(1.0, delta)), 4)
        err = round(abs(tc - TC_ANALYTIC), 4)
        verdict = "REPLICATED" if err <= 0.15 else ("MARGINAL" if err <= 0.4 else "DEVIATES")

    receipt = {
        "experiment": "ISING-2", "device": dev, "N": N, "J": J, "runs": RUNS,
        "sweeps": [SWEEP_EQ, SWEEP_MEAS], "curve": curve,
        "tc_est": tc, "tc_analytic": round(TC_ANALYTIC, 4),
        "tc_err": round(abs(tc - TC_ANALYTIC), 4) if tc else None,
        "unimodality_gate_pass": unimodal, "peak_index": k,
        "verdict": verdict, "fabric_demo_abs_m": fabric_demo(dev, gen),
        "gate_source": "proposals/runs/ISING-2-plan.md (frozen, pushed pre-run)",
        "parent": "ISING-1 (MARGINAL; estimator diagnosis only)",
        "wall_s": round(time.time() - t0, 1),
    }
    out = os.path.join(LAB, "results", "ising2_criticality.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(receipt, fh, indent=1)
    log("unimodal=%s peak@T=%s tc=%s err=%s -> %s (%.0fs)"
        % (unimodal, temps[k], tc, receipt["tc_err"], verdict, receipt["wall_s"]))
    log("receipt -> %s" % out)


if __name__ == "__main__":
    main()
