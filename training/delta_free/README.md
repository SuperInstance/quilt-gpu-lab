# Delta-Free Increment — D2 speedrun lane

**Date:** 2026-09-28 · **Base:** D1 run copy (`training/delta_increment/`, commit 8871a10) · baseline `val_bpb 1.695939` (receipt: `docs/autoclaw-train-receipt-2026-09-28.md`)

## Mutation (one variable — speedrun discipline)

**Free delta.** D1's delta heads derived q/k/v from a shifted hidden path (`delta_h = h − shift(h,1)`)
via three extra `F.linear` calls — real signal, ~9% wall-clock overhead, KILLed at fixed budget.
D2 keeps the difference signal but makes it free: **one projection pass only**, then the delta
heads' keys/values are the **post-projection temporal differences** of the same row-slices:

```
q, k, v = c_q(h), c_k(h), c_v(h)          # normal projections ONCE — no second linear, no hidden shift
k_d[t] = k[t] − k[t−1]   (zero-row shift at t=0, D1's convention)
v_d[t] = v[t] − v[t−1]
```

- Delta-head queries take `q` **as-is** (second half of q already in place).
- The differencing is one cheap elementwise op on projected tensors → overhead ≈ 0.
- VE gate: the pre-projection delta path no longer exists, so **all heads (delta included) read
  the gate from the absolute path** — identical to baseline code (D1 read the gate from delta_x).
- Head split unchanged (first half absolute, second half delta; row-slices of the same weights,
  zero new params 50.3M). One FA3 call; rotary, norms, window, c_proj, residuals untouched.

## Everything else identical to D1/baseline

- Same data (climbmix shards 0/1 + pinned val `shard_06542`), same tokenizer cache
- Same seed (42), same `TIME_BUDGET=300`, same `DEVICE_BATCH_SIZE=8`, same TOTAL_BATCH 2^19
- Same 3 documented run-copy deviations (kernel `revision="main"`, B=8, explicit bf16 casts)
- `prepare.py` byte-identical copy; serialized after sibling X9 lane released the GPU (ran alone)

## Pre-registered gate

Compare `val_bpb` vs baseline **1.695939** at the same budget.

- **KEEP** if delta-free beats baseline
- **KILL** if worse
- Both numbers reported either way

## Result (2026-09-28) — GATE VERDICT: **KEEP** (by 0.029315)

| metric | baseline | D1 (hidden-delta) | **D2 (free-delta)** |
|---|---|---|---|
| **val_bpb** | 1.695939 | 1.696093 | **1.666624 (−0.029315 vs baseline)** |
| training_seconds | 302.1 | 301.5 | 301.5 |
| total_seconds | 531.5 | 543.5 | **516.0** |
| peak_vram_mb | 3745.3 | 3884.1 | **3745.3 (identical to baseline)** |
| tok/sec | 72.6–73.3K | ~66K | **~71.1–72.8K steady (−2% vs baseline)** |
| num_steps | 53 | 49 | 52 |
| total_tokens_M | 27.8 | 25.7 | 27.3 (−1.8%) |
| num_params_M | 50.3 | 50.3 | 50.3 (zero new params) |
| final train loss | 4.901 | 4.906 | **4.864** |

**Reading:** making the delta free flipped D1's KILL to a KEEP. At the same 300s budget, free-delta
consumes 98.2% of baseline tokens (52 vs 53 steps, ~2% residual cost from the cat/diff ops) and lands
**0.0293 bpb better** — roughly 100x the margin D1 lost by. Per-token the difference signal is
decisively real once it costs nothing: it also beat D1 by 0.0295 and dropped VRAM back to baseline
exactly. The one-variable discipline held: only the delta-path implementation changed between D1 and D2.

## Files

- `train.py` — D1 run copy with the delta-free mutation (diff vs `delta_increment/train.py` is the
  delta-path block only)
- `prepare.py` — byte-identical copy
- `smoke_delta_free.py` — pre-flight fwd/bwd + diff-semantics + compile parity on the real FA3 kernel
  (eager == compiled, |d| = 0.0)
- `run.log` — this increment's log

Run: `~/venvs/elephant-gpu/bin/python train.py` (≈8.6 min end-to-end on the RTX 4050)
