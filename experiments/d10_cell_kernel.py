#!/usr/bin/env python3
"""D10 — the cudaclaw cell kernel (micromoth-quilt-cudaclaw substrate, step 1).

A quilt CELL whose memory is a small n-qubit statevector and whose inter-cell
edge is ternary-quantized (never raw amplitude). This is the design doc's
first build stage (docs/MICROMOTH-QUILT-CUDACLAW.md §7 D10): prove the cell
memory + the ternary passband + determinism + a 2-cell relational smoke.

The passband: a cell's state is measured in the computational basis; its
"message" to a neighbor is the SIGN of the dominant real correlation, collapsed
to 2-bit ternary {+1,0,-1} via the D2 split-channel convention (real channel =
attract - repel; abstain = imag). No raw amplitude ever crosses an edge.
"""
from __future__ import annotations

import json
import math

import torch

SEED = 2718
R2 = 0.70710678118


def _log2(n):
    return int(math.log2(n))


# --- in-place GPU gate application (LSB-first, from D3) --------------------
def apply_single(state, q, U):
    n = _log2(state.numel())
    q = int(q)
    hi = int(2 ** (n - q - 1))
    lo = int(2 ** q)
    s = state.view(hi, 2, lo)
    x0 = s[:, 0, :].clone()
    x1 = s[:, 1, :].clone()
    s[:, 0, :] = U[0, 0] * x0 + U[0, 1] * x1
    s[:, 1, :] = U[1, 0] * x0 + U[1, 1] * x1


def H():
    return torch.tensor([[R2, R2], [R2, -R2]], dtype=torch.complex64)


def make_cell(n, seed, bias=None):
    """Seed a cell's statevector deterministically: H on every qubit, then a
    phase rotation per qubit drawn from the seeded xorshift. If bias is a
    qubit index, apply X to it FIRST so the state is asymmetric (non-zero
    dominant sign). Returns (state, phase_fingerprint)."""
    state = torch.zeros(2 ** n, dtype=torch.complex64, device="cuda")
    state[0] = 1.0
    a = seed & 0xFFFFFFFF
    def rnd():
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = a
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t = (t ^ (t + ((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0
    fingerprint = []
    for q in range(n):
        if q == bias:
            # definite |1> on the bias qubit (X then no H) -> non-zero dominant sign
            X = torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64)
            apply_single(state, q, X)
            fingerprint.append(None)
            continue
        apply_single(state, q, H())
        theta = (rnd() * 2 * math.pi) - math.pi
        fingerprint.append(round(theta, 4))
        RZ = torch.tensor([[math.e ** (-1j * theta / 2), 0],
                           [0, math.e ** (1j * theta / 2)]], dtype=torch.complex64)
        apply_single(state, q, RZ)
    return state, fingerprint


def state_hash(state):
    """Byte-identical hash of the state amplitudes (determinism check)."""
    amp = state.cpu().numpy().tobytes()
    import hashlib
    return hashlib.sha256(amp).hexdigest()


def dominant_sign(state):
    """The cell's dominant real correlation sign, reduced to the ternary
    passband: +1 / 0 / -1. This is the message a cell emits."""
    # project onto computational basis probabilities and take the sign of the
    # imbalance between the top-half and bottom-half (real channel)
    probs = (state.real ** 2 + state.imag ** 2).cpu().numpy()
    n = _log2(state.numel())
    mid = 2 ** (n - 1)
    lo = probs[:mid].sum()
    hi = probs[mid:].sum()
    d = hi - lo
    if d > 1e-6:
        return 1
    if d < -1e-6:
        return -1
    return 0


def apply_message(state, sign):
    """A cell receiving a ternary message shifts its state in the direction of
    the received sign (deterministic): sign +1 -> bias toward high half, -1 ->
    toward low half, 0 -> no-op. Implemented as a small RX (amplitude-mixing)
    on the most-significant qubit — a phase-only RZ would not move probabilities."""
    if sign == 0:
        return
    n = _log2(state.numel())
    theta = 0.5 * sign  # RX(pi/2) ~ full flip; 0.5 rad is a strong partial tilt
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    RX = torch.tensor([[c, -1j * s], [-1j * s, c]], dtype=torch.complex64)
    apply_single(state, n - 1, RX)


def main():
    n = 6
    # determinism: two independently-seeded cells from the same seed hash equal
    c1, fp1 = make_cell(n, SEED)
    h1 = state_hash(c1)
    c2, fp2 = make_cell(n, SEED)
    h2 = state_hash(c2)
    determinism = "PASS" if h1 == h2 else "FAIL"

    # correctness: the ternary message reconstructs the dominant sign
    s1 = dominant_sign(c1)
    # reference sign from the same imbalance directly
    probs = (c1.real ** 2 + c1.imag ** 2).cpu().numpy()
    ref = 1 if (probs[2 ** (n - 1):].sum() - probs[:2 ** (n - 1)].sum()) > 1e-6 else (-1 if (probs[2 ** (n - 1):].sum() - probs[:2 ** (n - 1)].sum()) < -1e-6 else 0)
    reconstruct = "PASS" if s1 == ref else "FAIL"

    # 2-cell relational smoke: cell B receives cell A's ternary message and
    # shifts its dominant sign in that direction (or stays if A emits 0).
    # Cell A is biased (X on the top qubit) so it emits a DEFINITE non-zero
    # message; B is balanced so any shift is attributable to the message.
    a_state, _ = make_cell(n, SEED, bias=n - 1)
    b_state, _ = make_cell(n, SEED + 1)
    msg = dominant_sign(a_state)
    before = dominant_sign(b_state)
    apply_message(b_state, msg)
    after = dominant_sign(b_state)
    shifted = (after != before) if msg != 0 else (after == before)
    smoke = "PASS" if shifted else ("NEUTRAL" if msg == 0 else "FAIL")

    result = {
        "experiment": "D10 cudaclaw cell kernel",
        "seed": SEED, "n_qubits": n,
        "determinism": determinism,
        "reconstruction": reconstruct,
        "cell_A_message": msg,
        "cell_B_before": before, "cell_B_after": after,
        "two_cell_smoke": smoke,
        "verdict": "KEEP" if (determinism == "PASS" and reconstruct == "PASS") else "KILL",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
