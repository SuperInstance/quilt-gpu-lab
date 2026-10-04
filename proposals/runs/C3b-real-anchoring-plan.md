# C3b — real-footage domain anchoring: does C3's result survive a genuinely diverse real set?

**Pre-registered 2026-10-04 15:3x AKDT, before any C3b probe code fires.**
Status: pending fire. Prereg-stamped (post-b70c64c rule); the stamp is
embedded in the receipt at run start via `tools/prereg_stamp.prereg_block`.

## Question

C3 booked `ANCHORING_REPLICATED` (nearest-centroid val AUC 1.0, 64/64,
p 5.4e-20) with an owned caveat: the real domain was only the **2 Cosmos
snapshot example mp4s** — a domain axis fit on 2 cameras / 2 scene types
measures those 2 files, not "real footage". H1 (2026-10-04 15:27) delivered
**21 diverse licensed real clips** (5 NASA PD + 16 Wikimedia CC-BY/BY-SA/PD:
aerial, drone, macro, night-city, satellite, industrial, rocket, waterfall,
ocean, snow, pedestrians, timelapse — `results/c3b_clips/`, per-clip
sha256+license in `MANIFEST.json`, byte-exact C3 geometry via
`experiments/c3b_make_clips.py`).

C3b asks: **does the domain structure survive the encoder when "real" means
genuinely diverse footage — or was the anchoring result an artifact of the
trivial 2-clip real set?** Three parts, frozen below: (a) does a boundary
anchored on the DIVERSE real pool still separate C3's synth/real val set;
(b) do the 21 real clips retain within-real structure at clip granularity,
or collapse; (c) do the diverse real clips land on the real side of C3's
ALREADY-BOOKED domain axis (the synth→real transfer of the anchor).

## Data (on disk, frozen)

- **New:** `results/c3b_clips/MANIFEST.json` — 21 clips, 16f/256×256/rgb24/
  10fps, exactly 3,145,728 bytes each, sha256 per clip. The probe re-verifies
  byte size + sha256 (1 MiB chunked) for every clip before extraction; any
  mismatch → fail loud, no run.
- **Booked:** `results/c3_probe.json` (receipt of the C3 run) — per-clip
  layer-A (1152-d tower) and layer-B (2048-d post-projector) mean-pooled
  f16 embeddings for all 256 C3 clips with domain/split/family/source
  labels. C3b reads C3's embeddings from this file verbatim; no re-extraction
  of C3 clips. Layer B is primary everywhere (C3's law); layer A recorded
  but informational.

## Extraction protocol (frozen — C2-a5b/C3 recipe verbatim)

1. **Loader:** `Cosmos3EdgeForConditionalGeneration.from_pretrained` with
   `BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
   bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
   llm_int8_skip_modules=["visual","projector","model.visual",
   "model.projector"])`, `device_map="auto"`, `torch_dtype=torch.bfloat16`,
   `.eval()` (reuse `experiments/c3_probe.py` constants/loader shape —
   module import, no copy-paste drift).
2. **Fail-loud dtype receipt:** first param of `model.model.visual` must be
   `torch.bfloat16` AND type name exactly `Parameter`, else
   `INVALID_HARNESS`, no extraction.
3. **Decode:** every `.rgb` → PNG frames via ffmpeg list-form subprocess
   (`-f rawvideo -pix_fmt rgb24 -s 256x256`, `-vcodec png`, exactly the
   expected frame count or fail loud). Fulls: 16 frames (c3 helper).
   Halves: 8-frame byte slices written to `data/c3b_halves/` (deterministic
   byte surgery, no filter-chain gambles — the C5 law), then decoded the
   same way expecting 8 frames.
4. **Features:** processor `videos=` path → `pixel_values_videos` +
   `video_grid_thw` → `model.model.visual(px, grid_thw=grid,
   return_dict=True)` → `model.model.projector(vo.last_hidden_state)`;
   mean-pooled per clip split by `grid_thw.prod(-1)//merge²`; both layers
   recorded; no gradients, LM never runs.
5. **Units:** 63 videos total = 21 fulls (16f) + 42 halves (8f). Batches
   of 4, CUDA-OOM auto-halve →1, OOM at 1 → fail loud.
6. **CHECKPOINT LAW:** embeddings dumped to
   `results/c3b_embeddings_checkpoint.json` IMMEDIATELY after extraction,
   before any scoring — a metric bug must never lose GPU work (C4/C5 law).
   Scoring runs from the checkpoint if present and clip-count/manifest
   match (resume path, no GPU).
7. **RAMP LAW (INSTRUMENT-01):** before the first extraction batch, a ramp
   receipt: ≥0.6 s sustained synced elementwise CUDA load (mul-chain,
   `torch.cuda.synchronize()` each iter, per-iter timings recorded), then
   per-batch wall times booked. No measurement without the receipt.
8. **Guard:** nvidia-smi preflight free VRAM ≥ 1024 MiB, temp ≤ 80 °C;
   peak alloc + load time recorded; versions recorded.

## The probes (frozen)

All scoring on **L2-normalized** layer-B embeddings (float64), explicit-sign
cosines throughout (the C3/C4/C5 convention lesson: score = cos(x, c₁) −
cos(x, c₀), positive direction declared, never implicit). Mann-Whitney AUC
with tie=0.5 where AUC applies. No RNG anywhere — deterministic subsets are
taken by manifest/idx order, centroids are closed-form means, no seeds needed
(no stochastic step exists; stated, not pinned).

**G1 — diverse-real anchor swap (supporting gate, NOT verdict-carrying).**
synth centroid = C3 train-synth (96 clips); real centroid = the **21 new
diverse clips**; evaluate on C3's frozen 64-clip val set (32 synth / 32
2-source real). Gate: AUC ≥ 0.90 (C3's own bar). Reads: does the anchor
direction survive swapping the real training pool from 2-source to
21-diverse. Per-source stratified accuracy booked.

**G2 — within-real structure (VERDICT-CARRYING).** Temporal-half identity
matching: embed half A (frames 0–7) and half B (frames 8–15) of every clip
(42 units); for each clip i, cosine-match half-A_i against all 21 half-B
embeddings; correct iff argmax = i. Chance = 1/21 ≈ 0.0476.
- **Survives band: ≥ 12/21 correct** (exact binomial tail booked).
- **Collapse band: ≤ 6/21** (≤6 covers ≥99.99% of the Bin(21, 1/21) null —
  cannot claim structure).
- 7–11 = WEAK (mixed zone).
Informational, never gate-carrying: (i) pixel/motion baseline — per half,
temporal mean + temporal std of grayscale 16×16 frames, 512-d, cosine —
is latent matching beyond trivial pixel statistics (C5-H2 pattern);
(ii) participation ratio PR = (Σλ)²/Σλ² of the 21 real full embeddings vs
two deterministic synth anchors (ALL 20 train clips of the 'still' family
— the largest train family, first-by-idx = tightest single-family blob;
first-21-by-idx of all C3 train synth = mixed-family spread). PR anchors
run at their natural n (20/21; informational only — stated, not
hidden). Honest caveat, booked with the number:
halves share one 16-frame window (~1.6 s), so G2 tests clip-granularity
separability of real footage in latent space, NOT identity across
time/scale/camera (H1 gave 1 clip/source; cross-window identity stays a
future pre-reg's question).

**G3 — C3-axis transfer (VERDICT-CARRYING).** C3's frozen train axis from
`results/c3_probe.json` layer B: real_c3 = renormalized mean of the 96
train-real (2-source), synth_c3 = renormalized mean of the 96 train-synth.
score(x) = cos(x, real_c3) − cos(x, synth_c3). Project the 21 diverse clips:
**gate ≥ 16/21 land real-side (score > 0)** under Bin(21, 0.5)
(P(X≥16) ≈ 3.7e-3; exact tail booked). Distribution of the 21 scores booked
(min/median/max + per-clip table). **Harness sanity clause (fail-loud):**
the same projection must put C3 val real 32/32 real-side and C3 val synth
0/32 real-side (reproduces C3's booked AUC 1.0 in projection form); any
deviation → `INVALID_HARNESS` (embedding/protocol mismatch), verdict void.

## Frozen verdict mapping (single pre-declared cell)

- `ANCHORING_SURVIVES` — G2 ≥ 12 **AND** G3 ≥ 16.
- `ANCHORING_DEGENERATES` — G2 ≤ 6 (within-real at chance; collapse wins
  regardless of G3 — diverse real did not survive the encoder as structure).
- `MIXED_WEAK_STRUCTURE` — 7 ≤ G2 ≤ 11 AND G3 ≥ 16.
- `MIXED_TRANSFER_FAIL` — G2 ≥ 12 AND G3 ≤ 15.
- `MIXED_BOTH_WEAK` — 7 ≤ G2 ≤ 11 AND G3 ≤ 15.
- `INVALID_HARNESS` — any fail-loud clause (sha/byte mismatch, dtype
  receipt, frame-count, OOM at batch 1, G3 sanity clause, exception —
  traceback tail kept in the receipt).

G1 is booked as a number + met/not-met, never verdict-carrying.

## Output schema

`results/c3b_real_anchoring.json`: schema `c3b-real-anchoring/1`; prereg
block (plan path + sha256 stamp); preflight; ramp receipt; loader receipt
(t_load, dtype/type, skip modules, versions, batch_final, peak GiB, tokens
per unit); per-unit records (slug, unit=full/halfA/halfB, sha256 of source
clip, n_tokens, f16 embeddings both layers); G1 (AUC + stratified acc);
G2 (correct count + binom tail + pixel baseline + PR anchors); G3 (count
real-side + binom tail + score table + sanity clause results); gates
restated; the gated verdict; created timestamp.

## Out of scope

No generation, no LM forward, no encoder finetuning, no new data, no
cross-window/camera identity claim (G2's honest scope above), no
state-vs-diff claim (Cosmos has no such split), no git inside the probe.
The 21 half-clip `.rgb` slices are derived data → `data/c3b_halves/`
(gitignored like data/c4/c5; manifest-frozen parents are the truth).

## Artifacts

`proposals/runs/C3b-real-anchoring-plan.md` (this file) ·
`experiments/c3b_real_anchoring.py` · on fire:
`results/c3b_real_anchoring.json` + `results/c3b_embeddings_checkpoint.json`
+ `c3b_run.log`.
