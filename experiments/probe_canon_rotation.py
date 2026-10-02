#!/usr/bin/env python3
"""PROBE-BATTERY #9 — canon (lex-min rotation) invariance + fixed-boundary negative
control (edge-lab #3, #4).

GATE (from pr_harvest/SUMMARY.md top-10 table, #9):
    "naive diverges 100%; canon invariant 100% where symmetric, diverges >=95% where not"
CARDS: edge-lab #3 — naive digest of a ring trajectory is origin-sensitive (diverges
    at first rotated step); canon (lexicographic-minimum rotation of each state before
    digesting) is origin-invariant under periodic boundaries, with a non-degeneracy
    guard (>=100 distinct states). edge-lab #4 — the NEGATIVE control under fixed
    (Dirichlet, zero-flush) boundaries where rotation is NOT a dynamical symmetry:
    canon must NOT stay invariant there (>=95% divergence), or the rule erases real
    dynamical signal (overclaim). "A rule must be bounded on BOTH sides."

Implementation (numpy, seconds): rule-150 CA on a length-64 ring, T=128 steps,
    sha256-chained trajectory digest (h_t = sha256(h_{t-1} || state_t)); naive =
    chain over raw state bytes; canon = chain over lex-min rotation bytes of each
    state (batched successive-refinement lex-min over all 64 rotations).
    Periodic arm: wrap-around neighbors (rotation-equivariant). Fixed arm: zeros
    pinned outside the ring (equivariance broken).

Deterministic given seed 2718 — exactness is the point (not a seed-mean; std==0 law
n/a). Booked to results/probe_battery/canon_rotation.json. No commit.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np

SEED = 2718
L, T, N_STATES = 64, 128, 500
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "results", "probe_battery", "canon_rotation.json")


def step_periodic(S: np.ndarray) -> np.ndarray:
    """Rule 150 with periodic (wrap) boundaries — rotation-equivariant. S: (B, L)."""
    return np.bitwise_xor(np.bitwise_xor(np.roll(S, 1, axis=1), S), np.roll(S, -1, axis=1))


def step_fixed(S: np.ndarray) -> np.ndarray:
    """Rule 150 with FIXED zero (Dirichlet) boundaries — equivariance broken. S: (B, L)."""
    left = np.zeros_like(S)
    right = np.zeros_like(S)
    left[:, 1:] = S[:, :-1]     # left[0] pinned 0
    right[:, :-1] = S[:, 1:]    # right[-1] pinned 0
    return np.bitwise_xor(np.bitwise_xor(left, S), right)


def trajectory(s0: np.ndarray, stepper, t: int) -> np.ndarray:
    states = [s0]
    s = s0[None, :]
    for _ in range(t):
        s = stepper(s)
        states.append(s[0])
    return np.array(states)


def lexmin_batch(S: np.ndarray) -> np.ndarray:
    """Lexicographic-minimum rotation for each row of S (B, L) uint8 -> (B, L).
    Successive refinement over columns against all L rotations at once. The sentinel
    must live outside uint8 (256 wraps to 0 and resurrects eliminated rows)."""
    n = S.shape[1]
    rots = np.stack([np.roll(S, k, axis=1) for k in range(n)]).astype(np.int32)
    alive = np.ones((n, len(S)), dtype=bool)
    for c in range(n):
        col = np.where(alive, rots[:, :, c], 256)
        m = col.min(axis=0)
        alive &= col == m[None, :]
        if not alive.any():
            break
    idx = alive.argmax(axis=0)
    return rots[idx, np.arange(len(S)), :].astype(np.uint8)


def chain_digest(states: np.ndarray, canon: bool) -> str:
    payload = lexmin_batch(states) if canon else states
    h = hashlib.sha256(b"GENESIS_QUILT_PROBE9").digest()
    for row in payload:
        h = hashlib.sha256(h + row.tobytes()).digest()
    return h.hex()


def main() -> int:
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    states0 = rng.integers(0, 2, size=(N_STATES, L)).astype(np.uint8)
    distinct0 = len({s.tobytes() for s in states0})
    offsets = [1, 7, 31]

    for arm, stepper in (("periodic", step_periodic), ("fixed", step_fixed)):
        naive_diff = canon_same = 0
        pairs = 0
        for s in states0:
            ta = trajectory(s, stepper, T)
            for k in offsets:
                tb = trajectory(np.roll(s, k), stepper, T)
                pairs += 1
                if chain_digest(ta, canon=False) != chain_digest(tb, canon=False):
                    naive_diff += 1
                if chain_digest(ta, canon=True) == chain_digest(tb, canon=True):
                    canon_same += 1
        if arm == "periodic":
            naive_diverge_rate = naive_diff / pairs
            canon_invariant_rate = canon_same / pairs
        else:
            fix_naive_diverge_rate = naive_diff / pairs
            fix_canon_diverge_rate = 1.0 - canon_same / pairs
        print(f"[{arm}] naive diverge {naive_diff}/{pairs} canon-same {canon_same}/{pairs} "
              f"({time.time()-t0:.0f}s elapsed)")

    distinct_traj = len({chain_digest(trajectory(s, step_periodic, T), canon=False)
                         for s in states0})

    gate_naive = naive_diverge_rate == 1.0
    gate_canon = canon_invariant_rate == 1.0
    gate_nd = distinct_traj >= 100 and distinct0 >= 100
    gate_fixed = fix_canon_diverge_rate >= 0.95
    verdict = "PASS" if (gate_naive and gate_canon and gate_nd and gate_fixed) else "FAIL"

    print(f"[periodic] naive diverge {naive_diverge_rate:.1%} | canon invariant "
          f"{canon_invariant_rate:.1%}")
    print(f"[fixed-bnd] canon diverge {fix_canon_diverge_rate:.1%} | naive diverge "
          f"{fix_naive_diverge_rate:.1%}")
    print(f"[non-degeneracy] distinct initial states {distinct0}, distinct naive "
          f"trajectory digests {distinct_traj}")

    result = {
        "probe": "canon (lex-min rotation) invariance + fixed-boundary negative control",
        "source": "pr_harvest/SUMMARY.md #9 / CARDS.md quilt-edge-lab #3 + #4",
        "gate": "naive diverges 100%; canon invariant 100% where symmetric; diverges "
                ">=95% where not (fixed boundaries); non-degeneracy >=100 distinct states",
        "verdict": verdict,
        "numbers": {
            "rule": "150 (xor of self+neighbors), L=64 ring, T=128 steps, sha256 "
                    "chained from a genesis head, offsets {1,7,31}, batched lex-min "
                    "over all 64 rotations",
            "n_states": N_STATES,
            "distinct_initial_states": distinct0,
            "distinct_naive_trajectory_digests": distinct_traj,
            "periodic": {"naive_diverge_rate": round(naive_diverge_rate, 4),
                         "canon_invariant_rate": round(canon_invariant_rate, 4)},
            "fixed_boundary": {"canon_diverge_rate": round(fix_canon_diverge_rate, 4),
                               "naive_diverge_rate": round(fix_naive_diverge_rate, 4)},
            "gate_clauses": {"naive_diverges_100": bool(gate_naive),
                             "canon_invariant_100_symmetric": bool(gate_canon),
                             "non_degeneracy_ge_100": bool(gate_nd),
                             "canon_diverges_ge_95_asymmetric": bool(gate_fixed)},
            "reading": ("canonicalizing each state to its lex-min rotation makes the "
                        "trajectory digest origin-invariant exactly where the dynamics "
                        "are rotation-symmetric, and correctly REFUSES to collapse "
                        "distinct dynamics under fixed boundaries — the rule bounded on "
                        "both sides"),
        },
        "seed": SEED,
        "runtime_seconds": round(time.time() - t0, 1),
        "device": "cpu",
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(f"VERDICT: {verdict}")
    print(f"booked -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
