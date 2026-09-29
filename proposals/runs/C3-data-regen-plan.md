# C3 stage 0 — raw-video regeneration for the cross-encoder domain-transfer probe

**Pre-registered 2026-09-29 11:41 AKDT, before any C3 data code fires.**
Status: pending fire. This is the data detour C2's plan explicitly deferred:
"the K3c cross-encoder probe (C3) — which needs raw synth/lavfi video the lab
does not currently hold (K-lane caches are V-JEPA latents); that data detour
gets its own pre-reg."

## Why

K3c (RESULTS.md 2026-09-29 07:13) found that V-JEPA 2 **state z-codes are
domain-anchored** (poisoned cells: synth val 4.26–4.71 vs lavfi 1.50–1.80 on
floor 2.85) while **diff z-codes transfer across domains** (C1-diff
reconstructs unseen synth at 1.77 where P3-state sat at 4.71). That is n=1
encoder. C3 asks whether the anchoring replicates in a second encoder —
Cosmos-3-Edge, already booted on this silicon (C1 KEEP, C2 smoke).

The lab holds only the V-JEPA latent caches, not pixels. So stage 0 is data:
regenerate small raw-clip sets equivalent to the K3c domains so Cosmos
latents can be extracted next. **This pre-reg covers DATA ONLY** — clips +
manifest. Extraction and the probe itself get their own pre-reg (C3b) after
this data is on disk and audited.

## The K3c domain definitions, exactly (traced)

Ground truth is `training/keel_k1/k1_cache.py` — K3c consumed its two caches:

- **synth** (`cache.pt`, K1, `synth_clip`): torch RNG law
  `manual_seed(split_seed·100_003 + idx)`; base `torch.rand(1,3,32,32)`
  bilinear-upsampled to 256×256; per-frame roll by drift vx∈[−40,40),
  vy∈[−30,30); +0.04·randn flicker; clamp(0,1); 16 frames. Train seed 42
  (n=96), val seed 1337 (n=32).
- **lavfi** (`cache_lavfi.pt`, K2, `lavfi_clip`): same RNG law; 4 lavfi
  families cycled `idx % 4` — `color=c=gray`, `testsrc`, `smptebars`,
  `testsrc2` (each `duration=6 size=256x256 rate=10`); seek
  `t0 = randint(0,40)/10`; ffmpeg list-form subprocess, `-frames:v 16`,
  rawvideo rgb24; then deterministic 224-crop at (ox,oy) ∈ [0,32)² →
  bilinear resize 256; per-channel gain `1 + 0.2·(rand−0.5)`. Label idx%4.

Bit-parity with those caches is neither possible nor required (a different
encoder sees different latents regardless). Equivalence is preserved at the
level that matters: **source law, seeding law, geometry, clip counts.**

## C3 domains (frozen)

Same contrast architecture as K3c — two disjoint visual families — with the
second domain upgraded from synthetic broadcast bars to **real footage**
(the strongest version of a domain-transfer probe):

- **synth** — deterministic ffmpeg lavfi patterns, 5 families cycled
  `idx % 5`, every parameter pinned (no free randomness):
  1. `still` — `color=c=gray:duration=6:size=256x256:rate=10` (K-lane still)
  2. `testsrc=duration=6:size=256x256:rate=10`
  3. `smptebars=duration=6:size=256x256:rate=10`
  4. `testsrc2=duration=6:size=256x256:rate=10`
  5. `gradients` — `s=256x256:r=10:d=6:seed=20260929:speed=0.05:nb_colors=3:
     c0=0x001133:c1=0x77ccff:c2=0xffee88` — the smooth drifting-field analog
     of K1's upsampled-noise synth (colors AND seed pinned)
  Per-clip (K-law): seek `t0 = randrange(0,40)/10`; 224-crop at
  (ox,oy) ∈ [0,32)² → bilinear resize 256. The crop/resize moves from torch
  into ffmpeg filters (same transform chain, different executor).
- **real** — the snapshot's curated real example footage:
  `assets/example_action_id_av_0_input.mp4` +
  `assets/example_action_id_av_1_input.mp4` (sha256-pinned into the
  manifest). 16-frame windows at deterministic t0 values spread evenly over
  each probed duration; `fps=10` resample; cover-scale + center-crop 256×256.
  **Excluded:** every model-OUTPUT mp4 in assets/ (`edge_i2v_output`,
  `edge_action_fd_umi_2chunk_output`, `diffusers_outputs/*`) — they are
  Cosmos's own generations and would contaminate the real domain. A possible
  third "self-gen" domain is a later pre-reg's question, not this one.

K-lane's per-channel gain jitter is **dropped** for C3: it served
label-invariance in K1/K2, not the domain contrast; both C3 domains share
the identical (crop/scale) pipeline so the contrast stays in the source
pixels alone.

Seeding law (both domains, unchanged K-law): python
`random.Random(split_seed·100_003 + idx)`; train seed 42, val seed 1337.

## Geometry (frozen — assumption stated)

- **N per domain: 96 train + 32 val = 128 → 256 clips total.** Exact K-lane
  n, so C3b can reuse K3c's cell arithmetic (r=0.25 seed-42 draw, 96 slots,
  etc.) unchanged.
- **T = 16 frames/clip; 256×256 RGB24 rawvideo (.rgb); 10 fps temporal base**
  for both domains (K-lane lavfi rate; keeps temporal stats comparable).
- **Processor assumption:** `video_preprocessor_config.json` of the snapshot
  shows `patch_size 16`, `temporal_patch_size 1`, `merge_size 2`, size
  bounds shortest_edge 4096 / longest_edge 25165824 (pixel-count style).
  256×256 = 65,536 px ≥ 4096; both dims multiples of 32 (patch×merge); equal
  to the K-lane geometry the probe must stay comparable to. The processor
  resizes/normalizes internally (C2 precedent: arbitrary-size frames
  accepted). If C3b's Wan-VAE latent path (4× temporal compression) needs
  more than 16 frames to be non-degenerate, T is revisited **in C3b** — not
  here.
- Storage: rawvideo on ext4 — 16·256·256·3 = 3,145,728 B ≈ 3.0 MB per clip;
  256 clips ≈ 768 MiB total (844 GB free: fine). Raw, not mp4: zero codec
  variance, byte-exact reproducibility, direct `frombuffer` at extraction.

## Manifest (frozen schema)

`data/c3/manifest.json`: schema id + plan ref + created; ffmpeg path and
version line; snapshot path + per-source sha256 (both real mp4s); probed
duration/resolution of each real source; geometry block; per-domain
family/source specs; **per-clip records**: domain, split, idx, family,
source, seed, t0, crop offsets (synth), full ffmpeg argv (exact list), file
sha256, byte count; totals.

**Verification gate (fail-loud, in-script):** every clip exactly 3,145,728
bytes; all 256 sha256s recorded; preflight asserts ffmpeg/ffprobe exist,
snapshot sources exist, data dir writable. Reproducibility audit = re-run on
the same ffmpeg build + snapshot → byte-identical files (diff manifests).

## Out of scope (this pre-reg)

No ffmpeg execution at pre-reg time (the script exists, unfired). No latent
extraction, no encoder load, no training, no probe. No git operations — the
bridge commits centrally. `experiments/c3_make_data.py` implements exactly
the above: **subprocess list-form ONLY** (house law — no `shell=True`, no
`os.system`), writes `data/c3/{synth,real}/{train,val}/*.rgb` +
`data/c3/manifest.json`, `--check` mode re-hashes disk vs manifest.

## Artifacts

`proposals/runs/C3-data-regen-plan.md` · `experiments/c3_make_data.py` · on
fire: `data/c3/**` + `manifest.json` + `c3_data.log`.

## Open question (carried to C3b)

The real domain rests on only **2 curated real sources** (~seconds of
robot-arm AV footage each). K-lane lavfi ran on 4. Thin-source risk:
source-id confound inside the real domain (manifest stratifies per source so
C3b can check). Frozen default: proceed with 2; adding external CC footage
is a C3b decision that does not invalidate this regen.
