# Autoclaw Train Receipt — First Local Training Increment (RTX 4050)

**Date:** 2026-09-28 · **GPU:** NVIDIA GeForce RTX 4050 Laptop, 6141 MiB, WSL2 (driver 615.71, CUDA UMD 13.4)
**Artifact:** `~/projects/autoclaw/data/experiments/exp_0830/train.py` (byte-identical to repo-root `train.py`) + `prepare.py` — modded-nanochat autoresearch speedrun, single file, single GPU.
**Result: ✅ FIRST COMPLETED LOCAL TRAINING INCREMENT — `val_bpb: 1.695939`**

## Final summary (verbatim from train.py)

```
val_bpb:          1.695939
training_seconds: 302.1
total_seconds:    531.5
peak_vram_mb:     3745.3
mfu_percent:      1.80        (relative to H100 BF16 peak constant in script)
total_tokens_M:   27.8
num_steps:        53
num_params_M:     50.3
depth:            8
```

**Note on specs:** the run directive described the artifact as 12L/6H/768emb ≈ 85M params; the actual exp_0830 constants are `DEPTH=8`, `ASPECT_RATIO=64`, `HEAD_DIM=128` → **8L/4H/512emb, 50.3M params**. Ran as-is (artifact is the artifact).

## Loss trajectory (EMA-debiased train loss)

| step | 0 | 7 | 15 | 23 | 31 | 39 | 47 | 52 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|
| loss | 9.011 | 6.838 | 5.938 | 5.564 | 5.341 | 5.165 | 4.969 | 4.901 |

Monotone descent, no spikes, no NaN (fast-fail never tripped). Muon momentum ramp + LR warmdown (0.5 ratio) engaged on schedule; final `lrm 0.03`.

## What was installed (elephant-gpu venv — light only)

- `kernels` **0.12.1 → 0.17.1** (upgrade; required — see blockers). *That is all.*
- Already present, verified sufficient: torch 2.14.0+cu126, triton 3.8.0, tiktoken 0.14.0, rustbpe 0.1.0, pyarrow 25.0.1, requests, transformers.

## What was downloaded

- **Training data: nothing new.** `~/.cache/autoresearch/` already held the minimal viable set from an 11:44 attempt: `shard_00000`, `shard_00001` + pinned val `shard_06542` (3 × ~92 MB parquet ≈ 264 MB, climbmix-400b-shuffle) and a **trained rustbpe tokenizer** (vocab 8192, `tokenizer.pkl` + `token_bytes.pt`). 2 train shards ≈ 180M tokens vs ~28M consumed — no scale pressure.
- **Flash-attention-3 kernel build** `torch-stable-abi29-cu126` from `kernels-community/flash-attn3` (7 files, ~2 min fetch).

## Deviations from the tracked artifact (run copy only — 3, all forced)

Run copies + full log: `experiments/autoclaw-exp0830-run1/`. **No tracked autoclaw file was touched** (verified: prepare.py byte-identical; train.py diff = exactly the 3 hunks below).

1. **`get_kernel(repo, revision="main")`** — kernels 0.17 removed the implicit-revision default.
2. **`DEVICE_BATCH_SIZE = 8`** (was 128, H100-sized) — 6 GB VRAM. `TOTAL_BATCH_SIZE` kept at 2^19 so grad_accum went 1→32; optimizer-step semantics unchanged, 32 micro-steps/step.
3. **Explicit `q, k, v = q.bfloat16(), k.bfloat16(), v.bfloat16()` before `fa3.flash_attn_func`** — see blocker B2.

## Blockers hit and resolved

- **B1 — FA3 kernel/variant gap:** kernels 0.12.1 found no build for torch 2.14 (`torch214-cxx11-cu126` / `torch-cuda` / `torch-universal` all absent). Fix: upgrade kernels to 0.17.1, which accepts the repo's `torch-stable-abi29-cu126` stable-ABI build. Requires deviation 1.
- **B2 — torch 2.14 inductor + autocast + FA3 custom op dtype bug:** compiled graph fed fp32 (not bf16) into the FA3 op → `RuntimeError: FlashAttention only supports fp16, bf16, and fp8_e4m3`. Eager was clean. Minimal repro isolated it; fix = explicit bf16 casts at the FA3 boundary (deviation 3), semantically identical to upstream's autocast-bf16 attention. Forward **and** backward verified.
- **B3 (prior attempt, observed):** original exp_0830 run.log failed with `No module named 'torch'` — system python used instead of the venv. This run used `~/venvs/elephant-gpu/bin/python` throughout.

## Fit observations (RTX 4050, 6 GB)

- **Peak VRAM 3745 MB = 61% of 6141 MB at B=8/seq2048** — comfortable headroom. Compile-time transient peaked ~5.1 GB (inductor autotune); steady-state train 3.93 GB. **B=16 (grad_accum 16) should fit for the next increment** and would roughly halve per-step Python overhead.
- Throughput steady **72.6–73.3K tok/sec**, 7.17–7.22 s per optimizer step (32 micro-steps), GPU util pegged 100% for the whole counted phase. `mfu 1.8%` is against the script's H100 constant — vs the 4050's ~61 W envelope this is a sane laptop fraction.
- Wall budget: ~2.5 min torch.compile (first step dt 45.5 s absorbs fwd+optimizer compile), 302 s counted training, eval (~21 M val tokens, fwd-only) ≈ 1.5–2 min, **end-to-end 531 s ≈ 8.9 min** for one full TIME_BUDGET=300s increment including eval.
- Eval uses the pinned val shard (`shard_06542`) with the fixed BPB metric — comparable across increments going forward.

## Receipt-of-directive

This is the first "train novel models" receipt executed locally end-to-end: deps → data → tokenizer → flash-attn on non-Hopper → torch.compile → Muon+AdamW training loop → fixed-metric val_bpb. The loop is **repeatable**: nothing needs re-downloading; rerun cost ≈ 9 min/increment. Next-increment levers: B=16, and agents mutating train.py per the autoresearch protocol (eval → keep improvements).

*Run artifacts: `experiments/autoclaw-exp0830-run1/` (train.py patched copy, prepare.py copy, run.log). No autoclaw tracked file modified.*
