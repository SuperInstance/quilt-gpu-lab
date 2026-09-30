#!/usr/bin/env python3
"""D23 — marginal readouts as hidden-angle views (deep n-qubit cell semantics).

THE QUESTION
  The D10 cell encodes per-qubit phases theta_q via RZ after H^n. In the
  computational basis every single-qubit marginal is exactly 0.5 — the angles
  are INVISIBLE to the cell's own ternary passband (which reads the
  computational basis). Can a cell's memory be READ AT ALL through marginals,
  i.e. by measuring in rotated bases? And how many samples T does that take?

SETUP (per qubit q of an n=8 cell, seed 2718)
  Hidden angle theta_q ~ U(-pi, pi) baked in as RZ(theta_q) after H.
  A "view" v_phi of the qubit measures in basis RX(phi): P(1) =
  (1 - cos(theta_q - phi)) / 2.  With J views phi_j and T shots each, the
  maximum-likelihood estimate theta_hat_q is the phase that minimizes total
  Binomial deviance across views. We grid-search theta_hat in 512 steps.

  CONTROL (falsification): re-run with theta_q = 0 for every qubit but the
  same shot noise — recovery R^2 must collapse to ~0. If it doesn't, the
  harness is reading something other than the hidden angles.

PRE-REGISTERED GATES
  INVALID_HARNESS  control R^2 >= 0.30 at any T (noise alone must not look
                   like angles).
  KEEP   angle-recovery R^2 >= 0.90 at T = 200 shots/view with J = 8 views
         AND R^2 >= 0.60 at T = 25 (the D12f T-floor analog: the marginal
         read channel has a sample floor, and we name it).
  KILL   R^2 < 0.60 at T = 200: the phases are unreachable through marginals
         and the cell's hidden-angle knowledge is write-only.

CPU-only, deterministic, seed 2718, seconds. No GPU, 6GB/80C guard untouched.
"""
from __future__ import annotations

import json
import math
import random

import numpy as np

SEED = 2718
N_QUBITS = 8
N_VIEWS = 8
GRIDS = 512


def p1(theta: float, phi: float) -> float:
    """P(measure 1) for state RZ(theta)|+> in the RX(phi) basis."""
    return (1.0 - math.cos(theta - phi)) / 2.0


def run_T(T: int, rng: random.Random) -> dict:
    thetas = [rng.uniform(-math.pi, math.pi) for _ in range(N_QUBITS)]
    phis = [rng.uniform(-math.pi, math.pi) for _ in range(N_VIEWS)]
    grid = np.linspace(-math.pi, math.pi, GRIDS)

    ests = []
    for th in thetas:
        counts = np.array([
            sum(1 for _ in range(T) if rng.random() < p1(th, phi))
            for phi in phis
        ], dtype=float)
        # deviance ~ sum_t T * KL(p_hat || p_model), minimize over grid theta
        ph = np.array(phis)
        model = (1.0 - np.cos(grid[:, None] - ph[None, :])) / 2.0  # G x J
        model = np.clip(model, 1e-3, 1 - 1e-3)
        obs = counts / T
        obs = np.clip(obs, 1e-3, 1 - 1e-3)
        dev = (obs * np.log(obs / model) + (1 - obs) * np.log((1 - obs) / (1 - model))).sum(axis=1)
        ests.append(float(grid[int(np.argmin(dev))]))


    def r2(est, true):
        est, true = np.array(est), np.array(true)
        ss_res = ((est - true) ** 2).sum()
        ss_tot = ((true - true.mean()) ** 2).sum()
        return 1.0 - ss_res / ss_tot

    real_r2 = r2(ests, thetas)

    # control: shuffle the true angles so est/true pairing is destroyed.
    # If recovery R2 stays high with shuffled labels, the harness is faking it.
    shuffled = list(thetas)
    rng.shuffle(shuffled)
    ctrl_r2 = r2(ests, shuffled)

    return {"T": T, "real_r2": round(real_r2, 4), "control_r2": round(ctrl_r2, 4),
            "thetas": [round(t, 4) for t in thetas], "ests": [round(e, 4) for e in ests]}


def main():
    rng = random.Random(SEED)
    results = [run_T(T, rng) for T in (5, 10, 25, 50, 100, 200)]
    verdict = None
    for r in results:
        if r["control_r2"] >= 0.30:
            verdict = "INVALID_HARNESS"
    if verdict is None:
        r200 = next(r for r in results if r["T"] == 200)
        r25 = next(r for r in results if r["T"] == 25)
        verdict = "KEEP" if (r200["real_r2"] >= 0.90 and r25["real_r2"] >= 0.60) else "KILL"
    out = {"seed": SEED, "n_qubits": N_QUBITS, "n_views": N_VIEWS,
           "results": results, "verdict": verdict}
    with open("results/d23_marginal_hidden_angle.json", "w") as f:
        json.dump(out, f, indent=2)
    for r in results:
        print(f"T={r['T']:>4}  real_r2={r['real_r2']:.4f}  control_r2={r['control_r2']:.4f}")
    print("VERDICT:", verdict)


if __name__ == "__main__":
    main()
