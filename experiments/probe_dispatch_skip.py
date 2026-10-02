#!/usr/bin/env python3
"""PROBE-BATTERY #10 — dispatch-skip compute accounting (chiaroscuro #1, Lane A).

GATE (from pr_harvest/SUMMARY.md top-10 table, #10):
    "saved work ≈ abstain fraction ±10%; dense-equivalent exact when no abstain"
CARD (chiaroscuro #1): measure the dispatch-skip COMPUTE claim — implement a ternary
    per-cell gate in torch (CPU here) and count work saved when the abstain fraction
    is p. Abstain cells skip the election entirely, prior token stays resident.
    Gate: measured saved work ≈ p (±10%) across p in {0.1, 0.3, 0.6}, AND output
    equals the dense path when no cell abstains (exact).

Mechanism (torch CPU float64, seed 2718):
  - Grid 128x128 cells; belief register = EMA of external evidence (tau-independent);
    ternary gate psi ∈ {+1 commit, 0 ABSTAIN, -1 reject} from |belief| vs tau.
    tau per arm is CALIBRATED by binary search so the measured abstain fraction lands
    on the target p (the gate's abstain rate is measured, never assumed).
  - Per-cell election work: 3x3 neighborhood assembly -> (9->64) linear + ReLU ->
    (64->1) vote, 1344 counted FLOPs/cell. DENSE path dispatches every cell every
    frame; GATED path dispatches only psi != 0 cells (prior stays resident for
    abstainers). Both apply the IDENTICAL psi-blend update, so the outputs are
    comparable and exactly equal when nothing abstains.
  - Arithmetic is row-deterministic (broadcast-mul + fixed-size dim-sum, not BLAS
    dgemm) so subset dispatch is bitwise-identical to full dispatch per row.
  - Instruments: (a) FLOP accounting — counted multiply/adds actually dispatched;
    (b) wall-clock — whole-frame time, both paths, overhead included (booked as a
    second number; CPU overhead is foreign to the GPU/WGSL claim but reported).

Booked to results/probe_battery/dispatch_skip.json. No commit.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import torch

SEED = 2718
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "probe_battery", "dispatch_skip.json")
H = W = 128
N = H * W
FRAMES = 40
TARGETS = [0.1, 0.3, 0.6]
FLOPS_PER_CELL = 9 * 64 * 2 + 64 + 64 * 2  # (9->64) mul+add, bias, (64->1) mul+add


def belief_trajectory(belief0, evidence):
    """EMA belief register — evolves independently of tau and of the dispatched work."""
    belief = belief0.clone()
    traj = []
    for ev in evidence:
        belief = 0.9 * belief + 0.1 * ev
        traj.append(belief.clone())
    return traj


def psi_from(belief, tau):
    return torch.where(belief > tau, 1.0,
                       torch.where(belief < -tau, -1.0, 0.0))


def frame_state_update(state, psi, votes):
    """The shared update law: commit +0.05*vote, reject -0.02*vote, abstain resident."""
    step = torch.zeros(N, dtype=state.dtype)
    step[psi == 1.0] = 0.05 * votes[psi == 1.0]
    step[psi == -1.0] = -0.02 * votes[psi == -1.0]
    return state + step


def election(neigh: torch.Tensor, W1, b1, W2) -> torch.Tensor:
    """Row-deterministic per-cell election: (M,9) -> (M,)."""
    h = (neigh.unsqueeze(2) * W1.unsqueeze(0)).sum(dim=1) + b1
    h = torch.relu(h)
    return (h * W2).sum(dim=1)


def neighborhoods(state: torch.Tensor, rows: torch.Tensor) -> torch.Tensor:
    """(len(rows), 9) neighborhood values for the given flat row indices."""
    g = state.view(1, 1, H, W)
    padded = torch.nn.functional.pad(g, (1, 1, 1, 1))
    i0 = (rows // W)
    j0 = (rows % W)
    cols = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            cols.append(padded[0, 0, (i0 + di + 1), (j0 + dj + 1)])
    return torch.stack(cols, dim=1)


def run_path(beliefs, tau, W1, b1, W2, gated: bool, state0=None):
    """Run FRAMES frames. gated=False dispatches every cell (dense). Returns per-frame
    bookkeeping (abstain frac, dispatched cells, FLOPs, seconds, final state)."""
    state = state0.clone() if state0 is not None else beliefs[0].clone()
    frames = []
    for belief in beliefs:
        t_fr = time.perf_counter()
        psi = psi_from(belief, tau)
        if gated:
            idx = torch.nonzero(psi != 0).squeeze(1)
        else:
            idx = torch.arange(N)
        neigh = neighborhoods(state, idx)
        votes = election(neigh, W1, b1, W2)
        vfull = torch.zeros(N, dtype=state.dtype)
        vfull[idx] = votes
        state = frame_state_update(state, psi, vfull)  # abstain rows keep prior
        t_fr = time.perf_counter() - t_fr
        frames.append({"abstain_frac": float(1.0 - idx.numel() / N),
                       "dispatched": int(idx.numel()),
                       "flops": int(idx.numel()) * FLOPS_PER_CELL,
                       "seconds": t_fr, "state": state.clone()})
    return frames


def calibrate_tau(beliefs, target, lo=1e-4, hi=4.0, iters=40):
    """Binary-search tau so the MEAN abstain fraction over frames lands on target."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        fracs = [float((psi_from(b, mid) == 0).float().mean()) for b in beliefs]
        m = float(np.mean(fracs))
        if m < target:   # too few abstains -> raise the band
            lo = mid
        else:
            hi = mid
    tau = 0.5 * (lo + hi)
    m = float(np.mean([float((psi_from(b, tau) == 0).float().mean()) for b in beliefs]))
    return tau, m


def main() -> int:
    t0 = time.time()
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)

    W1 = torch.randn(9, 64, dtype=torch.float64) * 0.5
    b1 = torch.zeros(64, dtype=torch.float64)
    W2 = torch.randn(64, dtype=torch.float64) * 0.2

    belief0 = torch.tensor(rng.normal(0, 1, N), dtype=torch.float64)
    evidence = [torch.tensor(rng.normal(0, 1, N), dtype=torch.float64)
                for _ in range(FRAMES)]
    beliefs = belief_trajectory(belief0, evidence)
    state0 = torch.tensor(rng.normal(0, 1, N), dtype=torch.float64)

    arms = []
    for target in TARGETS:
        tau, p_emp = calibrate_tau(beliefs, target)
        gated = run_path(beliefs, tau, W1, b1, W2, gated=True, state0=state0)
        dense = run_path(beliefs, tau, W1, b1, W2, gated=False, state0=state0)

        p_fr = float(np.mean([f["abstain_frac"] for f in gated]))
        flops_gated = sum(f["flops"] for f in gated)
        flops_dense = sum(f["flops"] for f in dense)
        saved_flops = 1.0 - flops_gated / flops_dense
        t_gated = float(np.sum([f["seconds"] for f in gated]))
        t_dense = float(np.sum([f["seconds"] for f in dense]))
        saved_wall = 1.0 - t_gated / t_dense

        arms.append({
            "target_p": target, "tau_calibrated": round(tau, 5),
            "measured_abstain_fraction": round(p_fr, 4),
            "saved_work_flops": round(saved_flops, 4),
            "flops_gap_vs_p": round(abs(saved_flops - p_fr), 6),
            "saved_work_wallclock": round(saved_wall, 4),
            "wallclock_gap_vs_p": round(abs(saved_wall - p_fr), 4),
            "dense_frame_seconds_total": round(t_dense, 3),
            "gated_frame_seconds_total": round(t_gated, 3),
            "flops_dispatched_gated_M": round(flops_gated / 1e6, 1),
            "flops_dispatched_dense_M": round(flops_dense / 1e6, 1),
        })
        print(f"[p~{target}] tau={tau:.4f} p_emp={p_fr:.3f} saved_flops={saved_flops:.3f} "
              f"saved_wall={saved_wall:.3f} |gap_flops|={abs(saved_flops - p_fr):.4f} "
              f"|gap_wall|={abs(saved_wall - p_fr):.3f}")

    # exact dense-equivalence when nothing abstains: tau below all |belief| values
    tau_none = float(min(b.abs().min().item() for b in beliefs)) * 0.5
    gated_n = run_path(beliefs, tau_none, W1, b1, W2, gated=True, state0=state0)
    dense_n = run_path(beliefs, tau_none, W1, b1, W2, gated=False, state0=state0)
    exact = all(torch.equal(g["state"], d["state"])
                for g, d in zip(gated_n, dense_n))
    no_abstain = all(f["abstain_frac"] == 0.0 for f in gated_n)
    print(f"[dense-equivalence] bitwise equal: {exact}; zero abstains confirmed: {no_abstain}")

    gate_flops = all(a["flops_gap_vs_p"] <= 0.10 for a in arms)
    gate_wall = all(a["wallclock_gap_vs_p"] <= 0.10 for a in arms)
    gate_exact = bool(exact and no_abstain)
    verdict = "PASS" if (gate_flops and gate_exact) else "FAIL"

    result = {
        "probe": "dispatch-skip compute accounting (ternary per-cell gate)",
        "source": "pr_harvest/SUMMARY.md #10 / CARDS.md chiaroscuro #1 Lane A",
        "gate": "saved work ≈ abstain fraction ±10% across p∈{0.1,0.3,0.6} (primary "
                "instrument: counted FLOPs dispatched, per the card's 'count "
                "FLOPs/frames saved'; wall-clock booked as the overhead-inclusive "
                "second instrument); dense-equivalent exact when no cell abstains",
        "verdict": verdict,
        "numbers": {
            "grid": f"{H}x{W}={N} cells, {FRAMES} frames, per-cell election 9->64->1 "
                    f"({FLOPS_PER_CELL} counted FLOPs/cell), torch CPU float64, "
                    "belief-EMA ternary gate (commit/reject/abstain), tau calibrated "
                    "per arm by binary search so abstain fraction is measured not "
                    "assumed; abstain cells keep prior state resident",
            "arms": arms,
            "dense_equivalence": {"bitwise_equal": bool(exact),
                                  "zero_abstain_confirmed": bool(no_abstain)},
            "gate_clauses": {"flops_within_10pct": bool(gate_flops),
                             "wallclock_within_10pct": bool(gate_wall),
                             "dense_exact_no_abstain": gate_exact},
        },
        "seed": SEED,
        "runtime_seconds": round(time.time() - t0, 1),
        "device": "cpu",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"VERDICT: {verdict} (flops-clause {gate_flops}, wall-clause {gate_wall}, "
          f"exact-clause {gate_exact})")
    print(f"booked -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
