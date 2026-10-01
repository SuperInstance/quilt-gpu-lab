# AV1 — ASCII → Video: the other side of chiaroscuro, learned on the fabric

*Pre-registered 2026-09-30 ~21:05 AKDT, before any training run. Pushed before firing (fleet doctrine).*

## The directive (Casey, 09-30 20:56)

Render from ASCII to our own unique image on the other side; make generative real-time
video that **learns to be better by the motion** — models in cells of perception,
generation, filters; evolving weights, decomposing. Use the actual hardware (RTX 4050
6GB). Use Sail & Sink's Projectionist level-1 as the basic PoC training/experiment base.
Build the video→ascii porter with the Studio's parameters and more. And (25226): it should
work **better because we are using tmux-quilt ourselves** — the fabric is not a metaphor,
it is the training topology.

## North star (Projectionist's own handoff, level-1 page)

> "Train a compact policy from scene stats to render settings on GPU machines. Blend the
> documented heuristic with human preference labels, compare against the rule-based
> baseline, then keep only improvements people can actually see."

Sail & Sink left the score behind: **quality = 0.40·edge-band + 0.35·contrast +
0.25·temporal-stability** (their own "placeholder reward, not intelligence" — we inherit
it as the starting signal, same caveat).

## Data (stage 0)

- Source clips on disk: `~/projects/jev-quilt/assets/hero.mp4`,
  `polyformalism_12_ports.mp4`, `~/projects/ai-writings/videos/superinstance-intro.mp4`.
- Porter: `SuperInstance/chiaroscuro` branch `video-port` (lane dispatched in parallel,
  chiaro-video-port) → (ascii-grid, frame) pairs at 100 cols, engines glyph+sculpt.
- Split: hero.mp4 t∈[0,20s] train, t∈[20,26s] held-out; polyformalism fully held-out
  (cross-video generalization probe).

## Models (stage 1)

- **A. Algorithmic baseline (no learning — the honest floor):** glyph-atlas compositor.
  Rasterize each ramp glyph once (via PIL or a hand-built 8×12 bitmap atlas), composite
  per cell at cell luminance. Zero training. This is "your own unique image on the other
  side," version 0 — deterministic, exists before any weights.
- **B. Tiny learned decoder (the experiment):** conv decoder, <5M params, input =
  glyph-index grid (one-hot or 32-dim glyph embedding) + cell luminance; output = RGB
  frame at 2× grid resolution (pixel-shuffle upsample). Torch CUDA, elephant-gpu venv.
- **C. Motion loss (the "learns by motion" claim, falsifiable):** loss = λ_f·L1(frame) +
  λ_t·L1(Δframe) where Δ is the frame-to-frame difference of (i) generated sequence and
  (ii) ground-truth sequence — temporal coherence as a training signal, not a hope.
- **D. Warm-up / hardware proof:** `google/ddpm-cifar10-32` (real trained tiny diffusion,
  ~50M params UNet) — sample 8 images on the 4050, record it/s. Proves the diffusion path
  fits and runs; NOT part of the hypothesis claims.

## Hypotheses (frozen before fire)

- **H1 (reconstruction):** B beats A on held-out frames (PSNR + SSIM), same ascii input.
  Bar: ≥ +1.5 dB PSNR over the atlas baseline on held-out hero + cross-video probe.
- **H2 (motion):** C-training improves held-out temporal coherence (ΔL1 of generated
  sequences) over a frame-independent B trained at matched compute. Bar: ≥10% lower
  ΔL1, no PSNR degradation beyond 0.5 dB.
- **H3 (dial policy — the Projectionist inheritance):** a compact policy (scene stats →
  Studio dials; linear + bandit refine) beats the default dial set on held-out clips,
  scored by Sail & Sink's formula. Bar: ≥ +15% relative score vs defaults on polyformalism.
- Verdicts: KEEP / KILL / INCONCLUSIVE per pre-reg branches; no re-rolls; if the porter
  lane slips, pairs come from bridge/chiaroscuro.mjs (glyph engine only) and that
  limitation lands in the receipts.

## The tmux-quilt integration (25226 — "better because you're using it")

The loop runs THROUGH the fabric, not beside it:

- **P-cells (perception)** — ascii frame in, cell-signature out (spool cells A2/A3/A4
  already hold the tev1/qwen models that can embed signatures).
- **G-cells (generation)** — the decoder B lives behind a `generator` kind cell; its
  weights are the cell's dials (checkpoint path + λ's + lr in dials, full state in the
  checkpoint file the cell points to).
- **F-cells (filters)** — motion-judge cell (ΔL1, edge-band, contrast, stability —
  the four stats) and the **JEV gate**: a typesafe judgment cell that curls the state
  (`op.mjs since <engine>`), monitors deltas on future curls, and votes keep/revert on
  each weight update (Casey 09-30 20:32: "a JEV connected to a curl of state, monitoring
  deltas on future curls... they are all porting cells whether in memory or across the
  ocean"). Weight updates apply as **rebind-in-place** on the G-cell — every evolution of
  weights is a receipted ledger event, FORGET stays banned.
- **Records**: each epoch snapshots a quilt-record/v1 (fabric + thread + readme) under
  `records/av1-epoch-N/` — training state is portable by the same doctrine as everything
  else; a fresh agent can bootstrap the experiment from the record alone.
- **Workbench**: the third panel gains a `generator` frontend — the generated frame
  renders right in the context panel next to the faders; the ASCII video is watchable in
  the same pane as the cells that made it.

## Compute budget (6GB card, shared box)

- B: <5M params, batch 8, bf16-autocast off (keep fp32 for honesty at this size),
  ~20 min/epoch budget for 5s@10fps 100-col clips. If epoch time blows 2×, shrink cols
  to 80 and note it.
- D: 8 DDIM steps × 8 images — minutes.
- No run without this file pushed. Receipts → `results/av1/` + book in RESULTS.md.
