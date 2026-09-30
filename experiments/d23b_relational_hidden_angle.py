#!/usr/bin/env python3
"""D23b — do hidden angles encode RELATIONAL (partner) knowledge?

Follows D23 (KEEP: angles are readable via rotated-basis marginals, R2>0.99 at
T>=25). The open question from that entry: is the angle register the cell's
private memory, or can it carry CROSS-CELL knowledge — specifically partner
identity — as predicted by the correlation-key verdict in D12e/D13d?

MODEL
  8 cells, 4 hidden partner pairs. Each pair k gets a shared secret angle
  psi_k ~ U(-pi, pi). Partner cells bake phases theta_q = psi_k + eps
  (eps ~ N(0, sigma)) into a designated partner qubit; all other qubits get
  uniform phases. Non-partner cells are fully uniform.
  An external reader estimates every cell's qubit angles exactly as in D23
  (J=8 rotated views, T shots, 512-grid MLE), then identifies each cell's
  partner as the OTHER cell minimizing mean circular distance of the partner
  qubits' estimated angles.

PRE-REGISTERED GATES
  INVALID_HARNESS  shuffled-control partner_id >= 0.25 (labels not destroyed)
  KEEP   partner_id_acc >= 0.90 (7/8 correct) at T=200 AND >= 0.50 at T=25
         (chance = 1/7 ~= 0.143)
  KILL   partner_id_acc < 0.50 at T=200: angles carry private knowledge only;
         the correlation-key mechanism must live in the ternary atom streams,
         not the phase register.

CPU-only, deterministic, seed 2718, seconds. No GPU, 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import math
import random

import numpy as np

SEED = 2718
N_CELLS = 8
N_QUBITS = 8
N_VIEWS = 8
GRIDS = 512
SIGMA = 0.15  # radians of shared-angle noise between partners


def p1(theta: float, phi: float) -> float:
    return (1.0 - math.cos(theta - phi)) / 2.0


def estimate_angles(thetas, T, phis, grid):
    """D23 MLE: per-qubit 512-grid deviance minimization over J views."""
    ph = np.array(phis)
    model = (1.0 - np.cos(grid[:, None] - ph[None, :])) / 2.0
    model = np.clip(model, 1e-3, 1 - 1e-3)
    ests = []
    for th in thetas:
        obs = np.array([
            sum(1 for _ in range(T) if random.random() < p1(th, phi)) / T
            for phi in phis
        ])
        obs = np.clip(obs, 1e-3, 1 - 1e-3)
        dev = (obs * np.log(obs / model) + (1 - obs) * np.log((1 - obs) / (1 - model))).sum(axis=1)
        ests.append(float(grid[int(np.argmin(dev))]))
    return ests


def circ_dist(a, b):
    d = abs((a - b + math.pi) % (2 * math.pi) - math.pi)
    return d


def run_T(T: int, rng: random.Random) -> dict:
    random.seed(rng.random())
    grid = np.linspace(-math.pi, math.pi, GRIDS)
    phis = [rng.uniform(-math.pi, math.pi) for _ in range(N_VIEWS)]
    labels = list(range(N_CELLS))

    # ground truth: 4 partner pairs among 8 cells
    partners = [(0, 1), (2, 3), (4, 5), (6, 7)]
    partner_of = {}
    for a, b in partners:
        partner_of[a] = b
        partner_of[b] = a
    secrets = [rng.uniform(-math.pi, math.pi) for _ in partners]

    true_angles = {}   # (cell, qubit) -> theta
    partner_qubit = 0  # designated relational qubit per cell
    for k, (a, b) in enumerate(partners):
        psi = secrets[k]
        for c in (a, b):
            for q in range(N_QUBITS):
                if q == partner_qubit:
                    # wrap psi+eps into [-pi, pi)
                    th = (psi + rng.gauss(0, SIGMA) + math.pi) % (2 * math.pi) - math.pi
                else:
                    th = rng.uniform(-math.pi, math.pi)
                true_angles[(c, q)] = th

    # reader estimates all angles
    est = {}
    for c in range(N_CELLS):
        ths = [true_angles[(c, q)] for q in range(N_QUBITS)]
        ests = estimate_angles(ths, T, phis, grid)
        for q, e in enumerate(ests):
            est[(c, q)] = e

    # partner identification on the designated qubit only (reader knows which
    # qubit is relational — same assumption as D12e: the passband is fixed)
    correct = 0
    for c in range(N_CELLS):
        best, best_d = None, float("inf")
        for d in range(N_CELLS):
            if d == c:
                continue
            dist = circ_dist(est[(c, partner_qubit)], est[(d, partner_qubit)])
            if dist < best_d:
                best, best_d = d, dist
        correct += (best == partner_of[c])

    # control: permute the ESTIMATED angles among cells (destroys pairing,
    # keeps noise); if accuracy survives, the harness is faking it.
    est_ctrl = {}
    perm = labels[:]
    random.shuffle(perm)
    for c in range(N_CELLS):
        for q in range(N_QUBITS):
            est_ctrl[(c, q)] = est[(perm[c], q)]
    ctrl_correct = 0
    for c in range(N_CELLS):
        best, best_d = None, float("inf")
        for d in range(N_CELLS):
            if d == c:
                continue
            dist = circ_dist(est_ctrl[(c, partner_qubit)], est_ctrl[(d, partner_qubit)])
            if dist < best_d:
                best, best_d = d, dist
        ctrl_correct += (best == partner_of[c])
    return {"T": T, "partner_id_acc": round(correct / N_CELLS, 4),
            "control_acc": round(ctrl_correct / N_CELLS, 4)}


def main():
    rng = random.Random(SEED)
    results = [run_T(T, rng) for T in (5, 10, 25, 50, 100, 200)]
    verdict = "KEEP"
    for r in results:
        if r["control_acc"] >= 0.25:
            verdict = "INVALID_HARNESS"
    if verdict == "KEEP":
        r200 = next(r for r in results if r["T"] == 200)
        r25 = next(r for r in results if r["T"] == 25)
        verdict = "KEEP" if (r200["partner_id_acc"] >= 0.90 and r25["partner_id_acc"] >= 0.50) else "KILL"
    out = {"seed": SEED, "n_cells": N_CELLS, "n_qubits": N_QUBITS,
           "sigma": SIGMA, "results": results, "verdict": verdict}
    with open("results/d23b_relational_hidden_angle.json", "w") as f:
        json.dump(out, f, indent=2)
    for r in results:
        print(f"T={r['T']:>4}  partner_id={r['partner_id_acc']:.4f}  ctrl={r['control_acc']:.4f}")
    print("VERDICT:", verdict)


if __name__ == "__main__":
    main()
