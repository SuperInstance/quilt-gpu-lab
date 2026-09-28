# Delta-Attention Increment — D1 speedrun lane

**Date:** 2026-09-28 · **Base:** autoclaw exp_0830 run copy (receipt: `docs/autoclaw-train-receipt-2026-09-28.md`, baseline `val_bpb 1.695939`)

## Mutation (one variable — speedrun discipline)

**Delta-attention.** In every `CausalSelfAttention`, compute a parallel delta path:

```
delta_h = h − shift(h, 1)        # signed difference to the previous position (zero at t=0)
```

Split the heads: the **first half** of heads attend on `h` exactly as baseline; the **second half**
derive q/k/v from `delta_h` (weight row-slices of the same c_q/c_k/c_v — **zero new parameters**).
The VE gate for delta heads reads the delta path; the value embedding itself stays the absolute
token embedding for both paths. One FA3 call over all heads; rotary, norms, sliding-window
pattern, c_proj, MLP, residuals, optimizer, schedules all untouched.

## Everything else identical to baseline

- Same data (climbmix shards 0/1 + pinned val `shard_06542`), same tokenizer cache
- Same seed (42), same `TIME_BUDGET=300`, same `DEVICE_BATCH_SIZE=8`, same TOTAL_BATCH 2^19
- Same 3 documented run-copy deviations (kernel `revision="main"`, B=8, explicit bf16 casts)
- `prepare.py` byte-identical to baseline run copy

## Pre-registered gate

Compare `val_bpb` vs baseline **1.695939** at the same budget.

- **KEEP** if delta-attention beats baseline
- **KILL** if worse
- Both numbers reported either way

## Result (2026-09-28) — GATE VERDICT: KILL (by 0.000154)

| metric | baseline | delta-attention | delta |
|---|---|---|---|
| **val_bpb** | **1.695939** | **1.696093** | **+0.000154 (worse)** |
| training_seconds | 302.1 | 301.5 | same budget |
| total_seconds | 531.5 | 543.5 | +12s (eval + startup) |
| peak_vram_mb | 3745.3 | 3884.1 | +139 MB (63% vs 61% of 6 GB) |
| tok/sec | 72.6–73.3K | ~66K | −9% (delta-path cost) |
| num_steps | 53 | 49 | −4 (fewer tokens at fixed budget) |
| num_params_M | 50.3 | 50.3 | 0 (zero new params) |

Final train loss 4.906 (delta) vs 4.901 (baseline). Train curves tracked each other closely
the whole way (step 15: 5.934 vs 5.938; step 47: 4.919 vs ~4.94).

**Reading:** the pre-registered gate is val_bpb at the same TIME_BUDGET → delta-attention lost
by 0.000154 bpb → **KILL**. Worth noting for the ledger: it nearly matched the baseline while
consuming 7.5% fewer tokens (25.7M vs 27.8M) — per-token it's at parity or a hair better, but
the ~9% wall-clock overhead of the parallel path ate the entire advantage. The difference
signal is real; it is not yet *free* enough to beat just training longer on absolutes.

## Files

- `train.py` — baseline run copy + the mutation above (diff vs `experiments/autoclaw-exp0830-run1/train.py` is the delta-attention block only)
- `prepare.py` — byte-identical copy
- `smoke_delta.py` — pre-flight fwd/bwd + compile check on the real FA3 kernel (eager == compiled)
- `run.log` — this increment's log

Run: `~/venvs/elephant-gpu/bin/python train.py` (≈9–10 min end-to-end on the RTX 4050)
