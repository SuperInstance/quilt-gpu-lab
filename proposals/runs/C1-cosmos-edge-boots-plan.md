# C1 — Cosmos 3 Edge boots test on the RTX 4050 (lane C: play, learn, refine)

**Pre-registered 2026-09-29 09:0X AKDT, before any C1 code.** Mandate: Casey,
07:43 ("play around and learn… find what's useful through experimentation and
refinement") + 08:52 ("Keep crafting on your gpu").

## Ground truth (recon, 07:28–08:53)

- `nvidia/Cosmos3-Edge` — open (OpenMDW1.1), not gated, 9.18 GB / 54 files.
  Ships **bf16 components only, no quant variants**: transformer 5.00+1.74 GB
  (2 shards, the MoT backbone ~3.4 B), vae 1.41 GB, vision_encoder 0.98 GB.
- transformers **5.17.0 has native `cosmos3_edge`** (local venv check);
  `Cosmos3EdgeForConditionalGeneration` + full processor stack present.
- bitsandbytes 0.50.2 available in the elephant-gpu venv (torch 2.14.0+cu126).
- NVIDIA's own eager-Transformers benchmarks stop at Jetson Thor class
  (34–43 tok/s decode). **No 4050-class reference exists — C1 is the ground
  truth for this silicon class** (the hundred-boats lane).

## Design (frozen)

- Precision lane: **4-bit NF4** (BitsAndBytesConfig: nf4, double quant,
  compute dtype bf16), `device_map="auto"`. Weights ≈ 2.6–3 GB → fits 6 GB
  with KV + activations.
- Path: AR tower text reasoning only (text in → text out). If the processor
  demands pixels, use the repo's own `assets/example_reasoning_input.png` +
  `assets/example_reasoning_prompt.json`. Frozen prompt (text-only lane):
  "You are a deckhand on a fishing vessel in Alaska. In three short
  sentences, what should you watch for on deck right now?"
- Generation: greedy, `max_new_tokens=48`.
- Under `guard.py` (preflight free VRAM ≥ 1 GB, temp ≤ 80 °C, 5 s polls,
  30-min wall clock).

## Gate (frozen)

**KEEP** = model loads and completes the 48-token generation on the 4050 with
no OOM, under guard. **KILL** = OOM/timeout/crash on NF4 AND on one honest
fallback (bf16 + disk/CPU offload of the diffusion-tower weights). A KILL
still books the silicon floor for edge world models — useful, not a failure.

## Booked metrics (either verdict)

load time (s) · first-token latency (s) · decode tok/s · prefill tok/s (if
measurable) · peak VRAM (torch.cuda.max_memory_allocated + nvidia-smi peak) ·
peak temp · quant path actually used · generated text (verbatim).

## Out of scope (C2+)

Diffusion-tower video generation, WAM/action mode, vision benchmarks, the K3c
cross-encoder latent probe. One rung at a time.

## Artifacts

`experiments/c1_cosmos_boots.py` · `results/c1_cosmos_boots.json` ·
`c1_pull.log` / `c1_run.log` · HF snapshot path (weights stay OUT of git).
