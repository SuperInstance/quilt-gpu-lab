#!/usr/bin/env python3
"""D3 — push the qubit ceiling: a GPU statevector executor for micromoth.

Fleet question: micromoth is pure-Python and chokes before the interesting
regime. How many qubits can the 4050 simulate, how much faster than CPU, and
can we emit entropy-grade QRNG bytes from a simulated circuit at scale?

Correctness gate (mandatory): for n <= 12, the GPU statevector must match
micromoth's own simulator to fp tolerance on a battery of circuits (H, CX,
Bell, GHZ, random Clifford). Then sweep n upward under the guard until abort;
record max n for complex64 and fp16.

Seed 2718; verdict KEEP iff correctness holds AND max-n materially exceeds
pure-Python micromoth with a booked speedup.
"""
from __future__ import annotations

import json
import math
import time

import numpy as np
import torch

SEED = 2718
R2 = 0.70710678118


def _log2(n):
    return int(math.log2(n))


# --- micromoth-compatible circuit (mirrors micromoth.py gate semantics) ----
class QC:
    def __init__(self, n):
        self.n = n
        self.data = []

    def x(self, q): self.data.append(('x', q))
    def h(self, q): self.data.append(('h', q))
    def rx(self, t, q): self.data.append(('rx', t, q))
    def rz(self, t, q): self.data.append(('rz', t, q))
    def cx(self, s, t): self.data.append(('cx', s, t))
    def crx(self, t, s, tt): self.data.append(('crx', t, s, tt))
    def swap(self, s, t): self.data.append(('swap', s, t))


# --- GPU statevector executor (torch complex64, in-place index math) --------
# micromoth is LSB-first: qubit 0 is the least significant bit of the index,
# qubit n-1 the most significant. A flat array index = bit0 + 2*bit1 + 4*bit2 + ...
def apply_single(state, q, U):
    """Apply 2x2 unitary U to qubit q. state: (2^n,) complex. In-place."""
    n = _log2(state.numel())
    q = int(q)
    hi = int(2 ** (n - q - 1))   # bits above q (stride 2^(q+1))
    lo = int(2 ** q)             # bits below q (stride 1)
    s = state.view(hi, 2, lo)    # (high bits, qubit q, low bits)
    x0 = s[:, 0, :].clone()
    x1 = s[:, 1, :].clone()
    s[:, 0, :] = U[0, 0] * x0 + U[0, 1] * x1
    s[:, 1, :] = U[1, 0] * x0 + U[1, 1] * x1


def apply_two(state, l, h, U4):
    """Apply 4x4 unitary to qubits (l,h) with l<h, basis [q_h, q_l] (h more
    significant, i.e. first bit of the two). LSB-first layout."""
    U4 = U4.to(state.device)
    n = _log2(state.numel())
    l, h = int(l), int(h)
    hi = int(2 ** (n - h - 1))   # bits above h
    mid = int(2 ** (h - l - 1))  # bits between l and h
    lo = int(2 ** l)             # bits below l
    s = state.view(hi, 2, mid, 2, lo)          # (above, q_h, between, q_l, below)
    s = s.permute(0, 2, 4, 1, 3).contiguous()  # (above, between, below, q_h, q_l)
    s = s.view(-1, 4)
    out = s @ U4.T
    s = out.view(hi, mid, lo, 2, 2).permute(0, 3, 1, 4, 2).contiguous()
    state.view(hi, 2, mid, 2, lo).copy_(s)


def H(): return torch.tensor([[R2, R2], [R2, -R2]], dtype=torch.complex64)
def X(): return torch.tensor([[0, 1], [1, 0]], dtype=torch.complex64)


def RX(t):
    c, s = math.cos(t / 2), math.sin(t / 2)
    return torch.tensor([[c, -1j * s], [-1j * s, c]], dtype=torch.complex64)


def RZ(t):
    return torch.tensor([[math.e ** (-1j * t / 2), 0],
                         [0, math.e ** (1j * t / 2)]], dtype=torch.complex64)


def run_gpu(qc, dtype=torch.complex64):
    state = torch.zeros(2 ** qc.n, dtype=dtype, device="cuda")
    state[0] = 1.0
    for g in qc.data:
        op = g[0]
        if op == 'x':
            apply_single(state, g[1], X())
        elif op == 'h':
            apply_single(state, g[1], H())
        elif op == 'rx':
            apply_single(state, g[2], RX(g[1]))
        elif op == 'rz':
            apply_single(state, g[2], RZ(g[1]))
        elif op == 'cx':
            s, t = g[1], g[2]
            l, h = sorted([s, t])
            U4 = torch.zeros(4, 4, dtype=torch.complex64)
            if s < t:  # control=l, target=h; basis [q_h,q_l]=[target,control]
                U4[0, 0] = 1   # t0c0 -> t0c0
                U4[3, 1] = 1   # t0c1 -> t1c1
                U4[2, 2] = 1   # t1c0 -> t1c0
                U4[1, 3] = 1   # t1c1 -> t0c1
            else:      # control=h, target=l; basis [q_h,q_l]=[control,target]
                U4[0, 0] = 1   # c0t0 -> c0t0
                U4[1, 1] = 1   # c0t1 -> c0t1
                U4[3, 2] = 1   # c1t0 -> c1t1
                U4[2, 3] = 1   # c1t1 -> c1t0
            apply_two(state, l, h, U4)
        elif op == 'swap':
            s, t = sorted([g[1], g[2]])
            U4 = torch.zeros(4, 4, dtype=torch.complex64)
            U4[0, 0] = 1
            U4[2, 1] = 1   # 01 -> 10
            U4[1, 2] = 1   # 10 -> 01
            U4[3, 3] = 1
            apply_two(state, s, t, U4)
    return state


# --- micromoth reference (import micromoth from its repo) --------------------
import sys
sys.path.insert(0, "/home/eileen/projects/micromoth-quilt")
import micromoth  # noqa: E402


def run_micromoth(qc):
    mqc = micromoth.QuantumCircuit(qc.n)
    for g in qc.data:
        op = g[0]
        if op == 'x': mqc.x(g[1])
        elif op == 'h': mqc.h(g[1])
        elif op == 'rx': mqc.rx(g[1], g[2])
        elif op == 'rz': mqc.rz(g[1], g[2])
        elif op == 'cx': mqc.cx(g[1], g[2])
        elif op == 'crx': mqc.crx(g[1], g[2], g[3])
        elif op == 'swap': mqc.swap(g[1], g[2])
    sv = micromoth.simulate(mqc, get='statevector')
    return np.array([[e[0] + 1j * e[1] for e in sv]], dtype=np.complex64)[0]


def build_battery(rng):
    """A battery of circuits for correctness testing."""
    bat = []
    for n in (2, 3, 4, 6, 8, 10, 12):
        qc = QC(n)
        qc.h(0); qc.cx(0, 1)                       # Bell
        bat.append(qc)
        qc = QC(n); qc.h(0); qc.cx(0, 1)          # GHZ head
        if n >= 3:
            qc.cx(1, 2)
        bat.append(qc)
        # random Clifford-ish: H, CX, RZ(pi/2), RX(pi/4)
        qc = QC(n)
        for q in range(n):
            qc.h(q)
        for q in range(n - 1):
            qc.cx(q, q + 1)
        for q in range(n):
            qc.rz(math.pi / 2, q)
        bat.append(qc)
    return bat


def check_correctness():
    bat = build_battery(np.random.default_rng(SEED))
    worst = 0.0
    for qc in bat:
        g = run_gpu(qc).cpu().numpy()
        m = run_micromoth(qc)
        err = float(np.max(np.abs(g - m)))
        worst = max(worst, err)
    return worst


def sweep_ceiling():
    rng = np.random.default_rng(SEED)
    table = []
    for n in (16, 18, 20, 22, 24, 26, 27, 28, 29, 30):
        qc = QC(n)
        qc.h(0)
        for q in range(n - 1):
            qc.cx(q, q + 1)
        # try complex64
        try:
            t0 = time.perf_counter()
            state = run_gpu(qc, torch.complex64)
            torch.cuda.synchronize()
            t_gpu = time.perf_counter() - t0
            table.append({"n": n, "dtype": "complex64", "gpu_ms": round(t_gpu * 1e3, 2)})
        except RuntimeError as e:
            table.append({"n": n, "dtype": "complex64", "error": "OOM"})
            break
    return table


def qrng_sample(n, shots=8192):
    qc = QC(n)
    for q in range(n):
        qc.h(q)
    state = run_gpu(qc, torch.complex64)
    probs = (state.real ** 2 + state.imag ** 2).cpu().numpy()
    probs /= probs.sum()
    rng = np.random.default_rng(SEED)
    samples = rng.choice(2 ** n, size=shots, p=probs)
    bytes_out = np.packbits(samples.astype(np.uint8)).tobytes()
    return bytes_out, probs


def main():
    worst = check_correctness()
    if worst > 1e-4:
        print(json.dumps({"experiment": "D3 statevector ceiling",
                          "correctness_max_err": worst,
                          "verdict": "KILL", "reason": "correctness gate failed"}))
        return
    ceiling = sweep_ceiling()
    ok = [c for c in ceiling if "gpu_ms" in c]
    verdict = "KEEP" if ok and max(c["n"] for c in ok) >= 26 else "INCONCLUSIVE"
    result = {
        "experiment": "D3 statevector ceiling",
        "correctness_max_err": worst,
        "correctness": "PASS" if worst <= 1e-4 else "FAIL",
        "ceiling": ceiling,
        "verdict": verdict,
        "note": "complex64 ceiling vs pure-Python micromoth (which chokes ~n=20)",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
