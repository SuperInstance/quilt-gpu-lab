# C3 latent probe — does K3c's domain-anchoring replicate in Cosmos3-Edge latents?

**Pre-registered 2026-09-29 12:41 AKDT, before any probe code fires.**
Status: pending fire. This is C3b — the probe stage the data pre-reg
(`proposals/runs/C3-data-regen-plan.md`) explicitly deferred here after
stage 0 landed (256 clips, manifest sha256-verified, 2026-09-29 12:32).

## Question

K3c (RESULTS.md 2026-09-29 07:13) found V-JEPA 2 **state z-codes are
domain-anchored** (poisoned cells: synth val 4.26–4.71 vs lavfi 1.50–1.80 on
floor 2.85) while **diff z-codes transfer** — but that is n=1 encoder family.
C3 asks: **does the domain split survive into the latent space of a second,
architecturally unrelated encoder — Cosmos3-Edge's vision tower (4B edge VLM,
already proven on this silicon)?**

Framing (stated before any numbers exist): if domain identity is decodable
from pooled Cosmos latents at the frozen gate, domain information is strongly
present in the representation — the necessary representational condition for
K3c-style anchoring, replicated in a second family. If decodability sits at
chance, domain-anchoring does not replicate at this layer of this encoder.
This probe cannot test the state-vs-diff asymmetry (Cosmos latents have no
such split); it tests the domain-split half only.

## Data (already on disk, frozen)

`data/c3/manifest.json` — 256 clips: synth (5 pinned lavfi families) and
real (2 curated snapshot mp4s), 96 train + 32 val per domain (192/64), 16
frames 256×256 rgb24 rawvideo, per-clip sha256 recorded. The probe
re-verifies every clip (bytes + sha256, 1 MiB chunked) against the manifest
before extraction; any mismatch → fail loud, no run.

## Extraction protocol (frozen)

1. **Loader — the C2 attempt-5b PROVEN skip-tower recipe, verbatim:**
   `Cosmos3EdgeForConditionalGeneration.from_pretrained` with
   `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
   bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
   llm_int8_skip_modules=["visual","projector","model.visual",
   "model.projector"])`, `device_map="auto"`, `torch_dtype=torch.bfloat16`,
   `.eval()`. The LM stays NF4; tower + projector stay bf16.
2. **Fail-loud dtype receipt (gate):** first param of `model.model.visual`
   must be dtype `torch.bfloat16` AND type name exactly `Parameter` (a
   `Params4bit` there means the skip silently failed) — anything else →
   verdict `INVALID_HARNESS`, no extraction. Receipt recorded in the JSON.
   Inner-model path (`model.model.visual` / `model.model.projector`,
   modeling_cosmos3_edge.py:777-778) — the access-path lesson of C2 a5a.
3. **Decode:** each `.rgb` clip → 16 PNG frames via ffmpeg list-form
   subprocess (`-f rawvideo -pix_fmt rgb24 -s 256x256 -i clip -f image2pipe
   -vcodec png` into a temp dir, `%06d.png`, exactly 16 files expected or
   fail loud), frames loaded as PIL RGB. No shell strings anywhere.
4. **Features — mirror of the library's own call chain
   (modeling_cosmos3_edge.py:965-967):** processor `videos=` path →
   `pixel_values_videos` + `video_grid_thw` →
   `vo = model.model.visual(px, grid_thw=grid, return_dict=True)` →
   `tok = model.model.projector(vo.last_hidden_state)`.
   Two layers recorded per clip, both mean-pooled over the clip's tokens:
   - **Layer A (secondary, informational):** `vo.last_hidden_state` —
     pre-projector tower features, split per clip by `grid_thw.prod(-1)`.
   - **Layer B (primary):** `tok` — post-projector merged vision tokens
     (what the LM actually receives — the closest Cosmos analog of a z-code
     feeding a readout), split per clip by `grid_thw.prod(-1) //
     spatial_merge_size²`.
   No gradients (`torch.no_grad`), no generation, LM never runs.
5. **VRAM batching:** clips processed in batches of **4** through the tower;
   on CUDA OOM auto-halve 4→2→1 (recorded); OOM at batch 1 → fail loud.
   `torch.cuda.empty_cache()` between batches. Peak alloc recorded.

## The probe (frozen)

On **L2-normalized** pooled embeddings (each layer scored independently;
layer B carries the verdict, layer A informational):

- **Primary classifier — nearest centroid** (closed-form, hyperparameter-free,
  deterministic): train-split centroids (mean of normalized embeddings,
  renormalized) per domain; score = cos(x, synth) − cos(x, real); predict
  synth iff score > 0.
- **Secondary classifier — linear logistic probe** (confirmation only, cannot
  flip the verdict): full-batch Adam, lr 0.01, 1000 steps, weight_decay
  1e-3, CPU float32, `torch.manual_seed(20260929)`, bias included.

Fit on the 192 train clips; gate on the 64 val clips (32 synth / 32 real,
untouched until scoring).

## Frozen gate — the exact number

**Primary gate: val AUC ≥ 0.90** (nearest-centroid, layer B, rank-based
Mann-Whitney AUC with average-rank tie handling; chance = 0.50).
Accompanying accuracy readout is co-reported with its exact binomial tail
(≥44/64 → p ≤ 1.84e-3; table embedded in the script).

**Verdict mapping (frozen, single pre-declared cell):**
- `ANCHORING_REPLICATED` — primary val AUC ≥ 0.90.
- `PARTIAL` — primary val AUC ∈ [0.70, 0.90) (books as not met at gate).
- `NO_ANCHORING` — primary val AUC < 0.70.
- `INVALID_HARNESS` — any fail-loud clause fires (dtype receipt, sha/byte
  mismatch, OOM at batch 1, missing frame, missing processor key).

Informational throughout, never gate-carrying: layer A metrics, linear-probe
metrics, train-split metrics, and **per-source / per-family val accuracy**
(the real domain's thin-source confound — manifest stratifies by source and
by lavfi family so stratified accuracy is free).

## Seed policy

Everything is closed-form or on-disk: clips are sha-pinned files; centroids
are deterministic means; AUC is rank arithmetic. The single stochastic
component is the linear probe's init — `torch.manual_seed(20260929)` (the
data plan's pin), full-batch training, no sampling. Extraction itself is
inference-only (no_grad, eval mode). Re-run variance is limited to GPU float
nondeterminism, recorded via versions in the receipt.

## Guard preflight (fail-loud, wrapper AND inner)

`/usr/lib/wsl/lib/nvidia-smi --query-gpu=memory.free,temperature.gpu`:
free VRAM ≥ 1024 MiB and temp ≤ 80 °C, else abort before any load (C2
pattern). Peak VRAM, load time, and per-batch timings recorded.

## Harness pattern (frozen)

Wrapper (`python3 experiments/c3_probe.py`) runs preflight, then spawns the
GPU work as `[sys.executable, __file__, "--inner"]` — list-form subprocess
only, house law. Fire with the GPU venv:
`/home/eileen/venvs/elephant-gpu/bin/python experiments/c3_probe.py`.
Inner writes the complete receipt even on exception (traceback tail kept —
the C2 fail-loud-trail rule).

## Output (frozen schema)

`results/c3_probe.json`: schema id + plan ref + created; preflight; loader
receipt (t_load, visual_dtype, visual_type, skip_modules, versions, batch,
peak GiB, tokens/clip stats); per-clip records (domain, split, idx,
family/source, sha256, tokens, **embeddings as float16 for both layers**,
~10-15 MB JSON accepted); per-classifier metrics (train/val AUC + accuracy,
per-source/family breakdowns); observed-accuracy binomial p; frozen gate
restated; the gated verdict.

## Out of scope

No generation, no LM forward, no state-vs-diff claim, no new data, no
encoder finetuning, no git (bridge commits centrally). The "self-gen" third
domain stays a later pre-reg's question. If the processor rejects video-only
input, the mechanical fallback is `text=["", …]` placeholders — logged,
non-scientific, harness-only.

## Artifacts

`proposals/runs/C3-latent-probe-plan.md` (this file) ·
`experiments/c3_probe.py` · on fire: `results/c3_probe.json` + `c3_probe.log`.
