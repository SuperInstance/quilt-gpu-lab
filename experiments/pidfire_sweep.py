#!/usr/bin/env python3
"""pidfire_sweep.py — PIDFIRE-1 phase 0: fixed-rule (p,q) sweep + corner freeze + refine.

Frozen in proposals/runs/PIDFIRE-1-servo-soc.md:
  coarse 21x21: p = linspace(0.05, 1.0, 21), q = logspace(1e-4, 1e-1, 21),
  cell seeds 10_000 + cell_index, rho0 = 0.5 (stationary measurement; declared here),
  T = 60k (transient 10k), quiet-gated lightning f_step = 1/150.
  Cell-SOC gate (as amended, annotated above): n >= 100 AND self-KS <= 0.10 AND tau in [1.0, 1.4].
  Corner: argmin self-KS among gate-passing, tie-break larger n.
  Corner-area fraction = passing coarse cells / 441  (gate C2 uses this).
  Refine (report-only): 5x5 at 0.1x coarse spacing around corner, seeds 20_000 + idx.

Usage: python3 experiments/pidfire_sweep.py --phase coarse|refine
O(chunk): one JSONL row per cell, flushed; nothing else held.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pidfire_common import N_CELLS, fit_powerlaw, run_fixed  # noqa: E402

LAB = Path(__file__).resolve().parent.parent
OUT = LAB / "results" / "pidfire_sweep"

PS = np.linspace(0.05, 1.0, 21)
QS = np.logspace(-4, -1, 21)
RHO0 = 0.5  # declared: stationary measurement, transient 10k burns off the IC


def cell_row(p: float, q: float, seed: int):
    sizes, mean_burn, mean_rho = run_fixed(p, q, seed, RHO0)
    tau, s_min, d_ks, n_tail = fit_powerlaw(sizes)
    n = len(sizes)
    gate = (n >= 100) and math.isfinite(d_ks) and (d_ks <= 0.10) and (1.0 <= tau <= 1.4)
    return {
        "p": round(float(p), 6), "q": float(q), "seed": seed, "n_sizes": n,
        "tau": None if not math.isfinite(tau) else round(float(tau), 4),
        "s_min": int(s_min), "self_ks": None if not math.isfinite(d_ks) else round(float(d_ks), 4),
        "n_tail": n_tail, "mean_burn_frac": round(float(mean_burn), 8),
        "mean_density": round(float(mean_rho), 4), "soc_gate": bool(gate),
    }


def phase_coarse():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "coarse.jsonl"
    rows = []
    t0 = time.time()
    with path.open("w") as f:
        for i, p in enumerate(PS):
            for j, q in enumerate(QS):
                seed = 10_000 + i * 21 + j
                row = cell_row(p, q, seed)
                f.write(json.dumps(row) + "\n")
                f.flush()
                rows.append(row)
            print(f"[coarse] p-row {i + 1}/21 done ({time.time() - t0:.0f}s)", flush=True)

    passing = [r for r in rows if r["soc_gate"]]
    freeze = {
        "experiment": "PIDFIRE-1 phase0 coarse",
        "n_cells": len(rows),
        "n_passing": len(passing),
        "corner_area_fraction": round(len(passing) / len(rows), 6),
        "corner_rule": "argmin self_ks among soc_gate cells, tie-break larger n_sizes",
    }
    if passing:
        corner = min(passing, key=lambda r: (r["self_ks"], -r["n_sizes"]))
        corner_sizes, _, _ = run_fixed(corner["p"], corner["q"], corner["seed"], RHO0)
        freeze.update({
            "corner": corner,
            "reference_sizes": corner_sizes,
            "q_corner": corner["q"],
            "p_corner": corner["p"],
            "tau_ref": corner["tau"],
            "sp_mean_burn_frac": corner["mean_burn_frac"],
        })
    (OUT / "phase0_freeze.json").write_text(json.dumps(freeze, indent=1))
    print(json.dumps({k: v for k, v in freeze.items() if k != "reference_sizes"}, indent=1))


def phase_refine():
    freeze = json.loads((OUT / "phase0_freeze.json").read_text())
    if "corner" not in freeze:
        print("no corner — refine impossible (booked as-is)")
        return
    pc, qc = freeze["p_corner"], freeze["q_corner"]
    dp = 0.1 * (PS[1] - PS[0])
    dl = 0.1 * (math.log10(QS[1]) - math.log10(QS[0]))
    ps = [min(1.0, max(0.05, pc + (k - 2) * dp)) for k in range(5)]
    qs = [min(1e-1, max(1e-4, qc * 10 ** ((k - 2) * dl))) for k in range(5)]
    path = OUT / "refine.jsonl"
    t0 = time.time()
    rows = []
    with path.open("w") as f:
        for i, p in enumerate(ps):
            for j, q in enumerate(qs):
                row = cell_row(p, q, 20_000 + i * 5 + j)
                f.write(json.dumps(row) + "\n")
                f.flush()
                rows.append(row)
        print(f"[refine] 25 cells done ({time.time() - t0:.0f}s)", flush=True)
    print(json.dumps({
        "refine_passing": sum(1 for r in rows if r["soc_gate"]), "refine_total": len(rows),
        "report_only": True,
    }, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True, choices=["coarse", "refine"])
    a = ap.parse_args()
    (phase_coarse if a.phase == "coarse" else phase_refine)()
