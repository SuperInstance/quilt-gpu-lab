# D3 — Seed Replication of D2's Free-Delta KEEP (seed 1337)

**Date:** 2026-09-28 · **Base:** D2 (`training/delta_free/`, commit 5da8101) · **Question:** was D2's
−0.029315 a seed-42 fluke, or does the paired win hold at a second seed?

## Protocol (change ONLY the seed)

Two increments, both at **seed 1337**, everything else identical to the D2/baseline setup:
TIME_BUDGET=300, DEVICE_BATCH_SIZE=8, same data (climbmix shards 0/1 + pinned val `shard_06542`),
same tokenizer cache, same 3 documented run-copy deviations (kernel `revision="main"`, B=8,
explicit bf16 casts).

- `baseline/train.py` — byte-identical to the receipt baseline
  (`experiments/autoclaw-exp0830-run1/train.py`, the exact code that produced 1.695939 at seed 42),
  seed-only diff (42 → 1337). Verified: `diff <(sed s/1337/42/) original` is empty.
- `free_delta/train.py` — byte-identical to `training/delta_free/train.py` (D2's exact mutation:
  one projection pass, delta heads' k/v = post-projection temporal diffs of the same row-slices,
  q as-is), seed-only diff (42 → 1337). Verified the same way.
- `prepare.py` — byte-identical copies in both arms (verified against `delta_free/prepare.py`).
- Runs serialized, GPU-checked free before each (`nvidia-smi`; llama-server residual only, 0% util).

## Pre-registered gate

REPLICATED = free-delta beats baseline at seed 1337 (sign holds). SEED-NOISE = flips or vanishes.

## Receipt

```json
{
  "date": "2026-09-28",
  "seed": 1337,
  "baseline_val_bpb": 1.700300,
  "free_delta_val_bpb": 1.671658,
  "delta": -0.028642,
  "verdict": "REPLICATED",
  "gate": "free-delta beats baseline at seed 1337",
  "baseline_steps": 53,
  "free_delta_steps": 51,
  "baseline_training_seconds": 302.1,
  "free_delta_training_seconds": 300.8,
  "baseline_total_seconds": 496.0,
  "free_delta_total_seconds": 525.0,
  "peak_vram_mb": 3745.3,
  "num_params_M": 50.3
}
```

## Reading

**GATE VERDICT: REPLICATED (−0.028642).** The paired win holds at a second seed with nearly
identical magnitude:

| val_bpb | seed 42 | seed 1337 | paired delta |
|---|---|---|---|
| baseline | 1.695939 | 1.700300 | — |
| free-delta | 1.666624 | 1.671658 | **−0.029315 / −0.028642** |

Two independent seeds, two paired wins of ~0.029 bpb (agreement within 0.0007). For scale,
seed-to-seed movement of either arm alone is ~0.005 bpb (1.6959→1.7003 baseline, 1.6666→1.6717
delta) — the paired design is doing its job, and the effect is ~6x that noise. D2's KEEP was not
luck: the free difference signal is real. Free-delta clears the baseline at both seeds on the same
52-51 vs 53-step token budget (~98% of baseline tokens), VRAM identical (3745.3 MB both arms,
both seeds). **Free-delta is hardened; the fleet can stack mutations on it.**

## Files

- `baseline/` — vanilla-attention arm at seed 1337 (`train.py`, `prepare.py`, `run.log`)
- `free_delta/` — D2's exact free-delta mutation at seed 1337 (`train.py`, `prepare.py`, `run.log`)

Run: `~/venvs/elephant-gpu/bin/python train.py` per arm (~8.6 min end-to-end on the RTX 4050).
