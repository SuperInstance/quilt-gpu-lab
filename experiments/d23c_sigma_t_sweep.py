#!/usr/bin/env python3
"""D23c — sigma-vs-T spread sweep for the relational hidden-angle channel.

Closes the D23b caveat: single draw of 8 cells couldn't certify the 0.90
gate (one neighbor flip costs 0.125). Here: N=32 cells / 16 partner pairs,
multiple pairing draws per (sigma, T) cell, and a sigma sweep to map where
the angle channel is usable at all.

MODEL (same as D23b, scaled)
  Each partner pair k shares secret psi_k; partner qubit phases = psi_k + eps,
  eps ~ N(0, sigma). Reader estimates angles via D23 MLE (J=8 views, 512-grid),
  partners identified by nearest circular distance on the designated qubit.

SWEEP
  sigma in {0.05, 0.10, 0.15, 0.30, 0.60}, T in {10, 25, 50, 100, 200},
  5 pairing draws each; report mean partner_id_acc and the accuracy at which
  a fixed threshold-sigma channel beats 0.90.

PRE-REGISTERED GATES
  INVALID_HARNESS  null (all-uniform, sigma->inf control) mean acc >= 0.10
                   at any (T) — chance for N=32 is 1/31 ~= 0.032
  KEEP  there exists sigma >= 0.05 with mean acc >= 0.90 at T=200 AND
        mean acc >= 0.70 at T=25
  KILL  otherwise: the phase register is a weak secondary channel only.

CPU-only, deterministic, seed 2718. ~ minutes, no GPU; 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import math
import random

import numpy as np

SEED = 2718
N_CELLS = 32
N_QUBITS = 4
N_VIEWS = 8
GRIDS = 512
DRAWS = 5
SIGMAS = [0.05, 0.10, 0.15, 0.30, 0.60]
TS = [10, 25, 50, 100, 200]


def estimate_angle_batch(true_thetas, T, phis, grid, rng):
    """Per-qubit, per-view deviance minimization (D23-style, plain loop)."""
    ests = []
    for th in true_thetas:
        obs = []
        for phi in phis:
            p = (1.0 - math.cos(th - phi)) / 2.0
            obs.append(min(1.0 - 1e-3, max(1e-3, rng.binomial(T, p) / T)))
        obs = np.array(obs)
        ph = np.array(phis)
        model = (1.0 - np.cos(grid[:, None] - ph[None, :])) / 2.0
        model = np.clip(model, 1e-3, 1 - 1e-3)
        dev = (obs[None, :] * np.log(obs[None, :] / model)
               + (1 - obs[None, :]) * np.log((1 - obs[None, :]) / (1 - model))).sum(axis=1)
        ests.append(float(grid[int(np.argmin(dev))]))
    return ests


def circ_dist(a, b):
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def main():
    rng = random.Random(SEED)
    results = []
    null_accs = []
    for T in TS:
        for sigma in SIGMAS:
            accs = []
            for d in range(DRAWS):
                grid = np.linspace(-math.pi, math.pi, GRIDS)
                phis = [rng.uniform(-math.pi, math.pi) for _ in range(N_VIEWS)]
                order = list(range(N_CELLS))
                rng.shuffle(order)
                partners = [(order[2 * k], order[2 * k + 1]) for k in range(N_CELLS // 2)]
                partner_of = {}
                for a, b in partners:
                    partner_of[a] = b
                    partner_of[b] = a
                secrets = [rng.uniform(-math.pi, math.pi) for _ in partners]
                partner_qubit = 0
                nprng = np.random.default_rng(int(rng.random() * 2**53))
                est_ang = {}
                for k, (a, b) in enumerate(partners):
                    for c in (a, b):
                        ths = []
                        for q in range(N_QUBITS):
                            if q == partner_qubit:
                                ths.append((secrets[k] + nprng.normal(0, sigma) + math.pi) % (2 * math.pi) - math.pi)
                            else:
                                ths.append(rng.uniform(-math.pi, math.pi))
                        ests = estimate_angle_batch(ths, T, phis, grid, nprng)
                        est_ang[(c, partner_qubit)] = ests[partner_qubit]
                correct = 0
                for c in range(N_CELLS):
                    best, best_d = None, float("inf")
                    for d2 in range(N_CELLS):
                        if d2 == c:
                            continue
                        dist = circ_dist(est_ang[(c, partner_qubit)], est_ang[(d2, partner_qubit)])
                        if dist < best_d:
                            best, best_d = d2, dist
                    correct += (best == partner_of[c])
                accs.append(correct / N_CELLS)
            results.append({"T": T, "sigma": sigma,
                            "mean_acc": round(sum(accs) / len(accs), 4),
                            "accs": [round(a, 4) for a in accs]})
            print(f"T={T:>4} sigma={sigma:.2f}  mean_acc={results[-1]['mean_acc']:.4f}")

    # null control: sigma huge (angles ~ uniform => no shared structure)
    T = 200
    sigma_null = 6.0
    accs = []
    grid = np.linspace(-math.pi, math.pi, GRIDS)
    phis = [rng.uniform(-math.pi, math.pi) for _ in range(N_VIEWS)]
    for d in range(DRAWS):
        nprng = np.random.default_rng(int(rng.random() * 2**53))
        est_ang = [estimate_angle_batch(
            [rng.uniform(-math.pi, math.pi) for _ in range(N_QUBITS)], T, phis, grid, nprng)[0]
            for _ in range(N_CELLS)]
        # arbitrary fake pairing
        correct = 0
        for c in range(N_CELLS):
            fake = (c + 1) % N_CELLS
            best, best_d = None, float("inf")
            for d2 in range(N_CELLS):
                if d2 == c:
                    continue
                dist = circ_dist(est_ang[c], est_ang[d2])
                if dist < best_d:
                    best, best_d = d2, dist
            correct += (best == fake)
        accs.append(correct / N_CELLS)
    null_acc = sum(accs) / len(accs)
    print(f"null (sigma=6.0, T=200) mean_acc={null_acc:.4f} (chance={1/(N_CELLS-1):.4f})")

    by_key = {(r["T"], r["sigma"]): r["mean_acc"] for r in results}
    keep = (by_key[(200, 0.05)] >= 0.90 and by_key[(25, 0.05)] >= 0.70)
    verdict = "KEEP" if keep else "KILL"
    if null_acc >= 0.10:
        verdict = "INVALID_HARNESS"
    out = {"seed": SEED, "n_cells": N_CELLS, "draws": DRAWS, "sigmas": SIGMAS,
           "results": results, "null_acc": round(null_acc, 4), "verdict": verdict}
    with open("results/d23c_sigma_t_sweep.json", "w") as f:
        json.dump(out, f, indent=2)
    print("VERDICT:", verdict)


if __name__ == "__main__":
    main()
