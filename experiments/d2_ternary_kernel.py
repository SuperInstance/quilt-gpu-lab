#!/usr/bin/env python3
"""D2 — qthe ternary matmul kernel: parity + speedup vs fp16.

Fleet question: qthe's premise is data-is-geometry / control-is-physics with a
ternary operator Psi(tau) in {0,+1,-1,i}. SPEC Layer 2 leaves the performance
claim C1 OPEN. Is there a real throughput win from a ternary (add/sub/skip)
split-channel pass over an fp16 baseline on this GPU — and is our kernel
byte-exact against the reference on Layer 0 integer arithmetic?

Reference: qthe.mjs `vectorPass(weights, xs)`:
    y_j^R = sum_{tau=1} d*x  -  sum_{tau=2} d*x     (real channel)
    y_j^I = sum_{tau=3} d*x                          (imag channel)
    Ground (tau=0) contributes to neither. Exact integers.

This experiment:
  1. PARITY (mandatory, Law 0 of the house): run the integer split-channel
     pass on random packed weights + xs, assert byte-exact equality against
     `node qthe.mjs` vectorPass on the same vectors.
  2. BENCH: ternary int8 GEMM (signed real channel + unsigned imag channel,
     int32 accumulation) vs an fp16 cuBLAS matmul, at 1024^2 / 2048^2 / 4096^2.

Verdict: KEEP iff parity PASS and ternary beats fp16 past the pre-registered
margin at >=1 size. Parity PASS with no speedup is still a KEEP-worthy booked
null (prices C1 honestly). Parity FAIL -> KILL the kernel.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

import numpy as np
import torch
import triton
import triton.language as tl

SEED = 2718
PREREG_MARGIN = 1.10  # ternary must be >=1.10x faster than fp16 to count as a win
QTHE = os.path.expanduser("~/projects/qthe/qthe.mjs")


# --------------------------------------------------------------------------
# Reference (exact integer) — mirrors qthe.mjs vectorPass, no floats.
# --------------------------------------------------------------------------
def reference_vector_pass(weights, xs):
    """weights: (M, K) packed qthe bytes (uint8). xs: (K,) ints.
    Returns (re, im) arrays (M,) as exact Python ints."""
    M, K = weights.shape
    re = np.zeros(M, dtype=np.int64)
    im = np.zeros(M, dtype=np.int64)
    for j in range(M):
        for k in range(K):
            c = int(weights[j, k]) & 0xFF
            d = c & 0x3F
            tau = c >> 6
            x = int(xs[k])
            if tau == 1:
                re[j] += d * x
            elif tau == 2:
                re[j] -= d * x
            elif tau == 3:
                im[j] += d * x
    return re, im


# --------------------------------------------------------------------------
# Triton ternary split-channel GEMM.
# Real channel weights: int8, +d for Attract, -d for Repel, 0 otherwise.
# Imag channel weights:  uint8, d for Abstain, 0 otherwise.
# Accumulate int32 (exact for d<=63, |x|<=127, K<=4096 -> |sum| < 2^25).
# --------------------------------------------------------------------------
@triton.jit
def _ternary_pass_kernel(
    w_real_ptr, w_imag_ptr, x_ptr,
    re_ptr, im_ptr,
    M, K,
    BLOCK_M: tl.constexpr, BLOCK_K: tl.constexpr,
):
    pid = tl.program_id(0)
    offs_m = pid * BLOCK_M + tl.arange(0, BLOCK_M)
    offs_k = tl.arange(0, BLOCK_K)
    re_acc = tl.zeros((BLOCK_M,), dtype=tl.int32)
    im_acc = tl.zeros((BLOCK_M,), dtype=tl.int32)
    for k0 in range(0, K, BLOCK_K):
        ks = k0 + offs_k
        kmask = ks < K
        w_real = tl.load(w_real_ptr + offs_m[:, None] * K + ks[None, :],
                         mask=(offs_m[:, None] < M) & kmask[None, :], other=0)
        w_imag = tl.load(w_imag_ptr + offs_m[:, None] * K + ks[None, :],
                         mask=(offs_m[:, None] < M) & kmask[None, :], other=0)
        x = tl.load(x_ptr + ks, mask=kmask, other=0)
        re_acc += tl.sum(w_real * x[None, :], axis=1)
        im_acc += tl.sum(w_imag * x[None, :], axis=1)
    mmask = offs_m < M
    tl.store(re_ptr + offs_m, re_acc, mask=mmask)
    tl.store(im_ptr + offs_m, im_acc, mask=mmask)


def ternary_pass_triton(w_real, w_imag, x):
    """w_real: (M,K) int8; w_imag: (M,K) uint8->int32; x: (K,) int32.
    Returns (re, im) torch int32 tensors (M,)."""
    M, K = w_real.shape
    re = torch.empty(M, dtype=torch.int32, device="cuda")
    im = torch.empty(M, dtype=torch.int32, device="cuda")
    grid = (triton.cdiv(M, 64),)
    _ternary_pass_kernel[grid](
        w_real, w_imag, x, re, im, M, K,
        BLOCK_M=64, BLOCK_K=128,
    )
    return re, im


def decompose(weights):
    """Packed qthe bytes (M,K) uint8 -> (w_real int8, w_imag int32) on CUDA."""
    M, K = weights.shape
    tau = weights >> 6
    d = (weights & 0x3F).astype(np.int32)
    w_real = np.where(tau == 1, d, np.where(tau == 2, -d, 0)).astype(np.int8)
    w_imag = np.where(tau == 3, d, 0).astype(np.int32)
    return torch.from_numpy(w_real).to("cuda"), torch.from_numpy(w_imag).to("cuda")


def run_parity():
    rng = np.random.default_rng(SEED)
    M, K = 128, 256
    weights = rng.integers(0, 256, size=(M, K), dtype=np.uint8)
    xs = rng.integers(0, 128, size=(K,), dtype=np.int64)

    ref_re, ref_im = reference_vector_pass(weights, xs)

    # node reference (authoritative)
    payload = {"weights": weights.tolist(), "xs": xs.tolist()}
    node_script = (
        "import { vectorPass } from '" + QTHE + "';\n"
        "import fs from 'fs';\n"
        "const p=JSON.parse(fs.readFileSync(0,'utf8'));\n"
        "const w=p.weights.map(r=>r.map(c=>c&0xff));\n"
        "const out=vectorPass(w,p.xs);\n"
        "console.log(JSON.stringify({re:out.map(o=>o.re),im:out.map(o=>o.im)}));\n"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", node_script],
        input=json.dumps(payload), capture_output=True, text=True, timeout=60,
    )
    if proc.returncode != 0:
        return {"parity": "FAIL", "reason": "node ref failed", "stderr": proc.stderr[-500:]}
    node_out = json.loads(proc.stdout)
    node_re = np.array(node_out["re"], dtype=np.int64)
    node_im = np.array(node_out["im"], dtype=np.int64)

    # triton
    w_real, w_imag = decompose(weights)
    x_t = torch.from_numpy(xs.astype(np.int32)).to("cuda")
    tre, tim = ternary_pass_triton(w_real, w_imag, x_t)
    tre = tre.cpu().numpy().astype(np.int64)
    tim = tim.cpu().numpy().astype(np.int64)

    ok_node = bool(np.array_equal(tre, node_re) and np.array_equal(tim, node_im))
    ok_ref = bool(np.array_equal(tre, ref_re) and np.array_equal(tim, ref_im))
    return {
        "parity": "PASS" if (ok_node and ok_ref) else "FAIL",
        "vs_node": ok_node, "vs_pyref": ok_ref,
        "M": M, "K": K,
        "sample_re": [int(tre[0]), int(node_re[0]), int(ref_re[0])],
    }


def run_bench():
    results = []
    rng = np.random.default_rng(SEED)
    for N in (1024, 2048, 4096):
        weights = rng.integers(0, 256, size=(N, N), dtype=np.uint8)
        xs = rng.integers(0, 128, size=(N,), dtype=np.int64)

        w_real, w_imag = decompose(weights)
        x_i32 = torch.from_numpy(xs.astype(np.int32)).to("cuda")

        # fp16 baseline: same math in fp16 via cuBLAS (torch.matmul)
        wf = torch.zeros(N, dtype=torch.float16, device="cuda")
        # real fp16 weight = +d or -d (fp16 exact for d<=63)
        tau = (weights >> 6)
        d = (weights & 0x3F).astype(np.float32)
        wf_real = torch.from_numpy(
            np.where(tau == 1, d, np.where(tau == 2, -d, 0)).astype(np.float16)).to("cuda")
        wf_imag = torch.from_numpy(
            np.where(tau == 3, d, 0).astype(np.float16)).to("cuda")
        xf = xs.astype(np.float16)
        xf_t = torch.from_numpy(xf).to("cuda")

        # warmup
        for _ in range(5):
            ternary_pass_triton(w_real, w_imag, x_i32)
            torch.matmul(wf_real, xf_t)
            torch.matmul(wf_imag, xf_t)

        torch.cuda.synchronize()
        n_runs = 50
        t0 = time.perf_counter()
        for _ in range(n_runs):
            ternary_pass_triton(w_real, w_imag, x_i32)
        torch.cuda.synchronize()
        t_ternary = (time.perf_counter() - t0) / n_runs

        t0 = time.perf_counter()
        for _ in range(n_runs):
            torch.matmul(wf_real, xf_t)
            torch.matmul(wf_imag, xf_t)
        torch.cuda.synchronize()
        t_fp16 = (time.perf_counter() - t0) / n_runs

        speedup = t_fp16 / t_ternary if t_ternary > 0 else float("inf")
        results.append({
            "size": N, "fp16_ms": round(t_fp16 * 1e3, 4),
            "ternary_ms": round(t_ternary * 1e3, 4),
            "speedup": round(speedup, 3),
        })
    return results


def main():
    parity = run_parity()
    if parity["parity"] != "PASS":
        result = {"experiment": "D2 qthe ternary kernel", "parity": parity,
                  "verdict": "KILL", "reason": "parity FAIL"}
        print(json.dumps(result))
        return
    bench = run_bench()
    wins = [b for b in bench if b["speedup"] >= PREREG_MARGIN]
    verdict = "KEEP" if wins else "INCONCLUSIVE"  # parity PASS, no speedup => booked null
    result = {
        "experiment": "D2 qthe ternary kernel",
        "parity": parity,
        "benchmark": bench,
        "prereg_margin": PREREG_MARGIN,
        "verdict": verdict,
        "note": "parity PASS mandatory; speedup>margin at >=1 size => KEEP, else booked null (C1 priced)",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
