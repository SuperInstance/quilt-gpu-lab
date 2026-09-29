# C2 — First real video through the 4050's world model (smoke)

**Pre-registered 2026-09-29 10:40 AKDT, before any C2 code.** Mandate: Casey
10:37 ("keep the gpu brewing") + standing anti-GAN (new process each run).

## Question

C1 proved the AR tower generates on boat-class silicon (17.5 tok/s text-only).
C2 puts **real footage** through it for the first time: the model's own
example assets — `example_action_id_av_0_input.mp4` (a real AV clip shipped
with the repo) and `example_reasoning_input.png` — with an **anticipation
question** (what is happening, what happens next): the world-model test, not
just the VLM test. Also books the **first video-token throughput number** on
this silicon class.

## Design (frozen)

- Same loader as C1: transformers 5.17 native, NF4 (bnb, double-quant, bf16
  compute), device_map auto, under guard.py (1 GB free floor, 80 °C ceiling).
- Frames: 8 evenly-spaced frames from the example mp4 via ffmpeg
  (`fps=1,scale=640:-2`, list-form subprocess — no shell strings), loaded as
  PIL images.
- Two tasks, frozen prompts (chat template applied):
  - **V-task:** frames + "Watch this clip. What is happening, and what is most
    likely to happen next?"
  - **I-task:** `example_reasoning_input.png` + "What is happening in this
    image? What is most likely to happen next?"
- Processor path is defensive and recorded: `videos=[frames]` →
  `images=frames` (multi-image) → single-image fallback.
- Generation: greedy, `max_new_tokens=64`.

## Gate (frozen — descriptive smoke, not a science gate)

**KEEP** iff ≥ 1 of 2 tasks completes with ≥ 24 new tokens of scene-relevant
text (relevance judged in the booking, verbatim text kept). **KILL** = both
tasks fail/crash — receipt kept either way. The throughput numbers book
regardless: t_prefill, t_gen, decode tok/s, peak VRAM, vision-token path used.

## Out of scope

Diffusion-tower generation, WAM/action mode (C4); the K3c cross-encoder probe
(C3) — which needs raw synth/lavfi video the lab does not currently hold
(K-lane caches are V-JEPA latents); that data detour gets its own pre-reg.

## Artifacts

`experiments/c2_world_smoke.py` · `results/c2_world_smoke.json` ·
`c2_run.log` · this plan. Weights stay in the HF cache.
