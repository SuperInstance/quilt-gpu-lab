# Glyph-Domain Next-Frame Predictor — Spec (G1)

**Date:** 2026-09-28 · **Lane:** edge-scout docket #3 (docs/edge-scout-2026-09-28.md, slot 3) ·
**Siblings read:** SuperInstance/glyphcast @ 17:46Z + SuperInstance/glyphspace @ 17:46Z (both proposal-stage: README + ROADMAP only, zero code) ·
**Anchors:** chiaroscuro-embedding renderer.py (the only working glyph encoder in the family), quilt-gpu-lab training/delta_free (D2 free-delta KEEP skeleton).

**Status labels below follow the constellation law: measured / simulated / wagered.**

---

## 0. What the siblings actually are (deep-read verdict)

**glyphcast** — "next-frame prediction and frame-rate synthesis for glyph-domain
video." Treats chiaroscuro text output as *a stream of discrete tokens on a
fixed lattice*. Three planned jobs: `predict` (coarse-to-fine token
transformer), `interpolate` (RIFE-style per-cell flow on the lattice),
`score` (crossing-rate harness). **Proposal stage. No model weights, no code —
the roadmap's Phase 0 gate is literally "build the dataset builder."** Its
receipt-gating: every phase ends in a sealed, replayable artifact; FAIL-first
pins (gate must fail on the pre-change tree); denominators on all claims.
Planned head geometry (we adopt it): **12×9 semantics → 48×36 glyph field →
optional 96×72 detail**, cross-entropy per cell from day one, scheduled
sampling, and three baseline arms: persistence, per-cell flow, tiny
transformer.

**glyphspace** — the spatial half: DDA raycast over the cell lattice,
glyph→material tables (albedo/transmission/emission from tone class), mip
zoom (coarse = objects, fine = texture), prompt packets for pincher, occupancy
maps for glyphcam. **Also proposal stage — "no renderer exists here yet."**
Its one structural law that binds us: **"one lattice spec with glyphcast; two
repos, one lattice — never drift."**

**Consequence for this spec:** neither sibling can supply training data or a
tokenizer today. The only implemented encoder in the whole family is
chiaroscuro-embedding's `renderer.py` (line-faithful numpy port, feed-lab and
c1/c2 verified). So G1 v1 *is* the family's lattice implementation de facto:
our code-space vocabulary and 48×36 frame are the concrete substrate
glyphcast's Phase 0 dataset builder should target (header = engine-pin hash +
row-major codes), and glyphspace's material table reads the same codes. Build
the corpus once; all three repos eat it.

## 1. Token vocabulary (a)

The renderer's glyph choice is already a pair of integers — **predict codes,
not glyphs**; decode is an exact lookup and every generated frame is
renderer-replayable (receipts stay verifiable).

- **Tone branch:** ramp index `tone_idx ∈ 0..rl−1` (index 0 ≡ blank).
- **Edge branch:** `edge_code = fam × 5 + level`, `fam ∈ {0°,45°,90°,135°}`,
  `level ∈ 0..4` → 20 codes (13 unique glyphs; collisions are fine — we keep
  codes because they carry the renderer's state).

| vocab | contents | size |
|---|---|---|
| **primary pin** (c2 default mix: classic ramp, tone 100, edge 60, thr 4, gain 10, relief 70) | 11 tone indices + 20 edge codes + 1 SEP | **V = 32** |
| wireframe preset (glyphcast's quickstart engine) | 5 + 20 + 1 | V = 26 |
| universal, all 9 ramps, index-space | 70 + 20 + blank + SEP | V = 92 |
| universal, glyph-string union (for reference) | distinct chars | 106 |

**Measured:** ramp lengths and edge-code table read directly from
`renderer.py` RAMPS/EDGE_DIRS. Model size at V=32 measured below (§3).

## 2. Training data (b)

Feed conventions inherited from c2 (`c2_feed.py`): five ffmpeg lavfi sources —
`testsrc2, smptebars, mandelbrot, life, gradients` — plus the mock scene.

| feed | volume | why |
|---|---|---|
| 5 lavfi sources, extended to **60 s × 10 fps × 320×240** each | **3,000 frames** | motion diversity; life/testsrc2/mandelbrot change every step |
| MockScene sinusoidal trajectories (real `?mock=1` style: sphere x/y + bar angle, light/checker frozen) | **3,000 frames** | ground truth free; matches glyphcast Phase-0 source order |
| glyphcast token arrays | **0 — none exist** (honest label) | sibling is proposal-stage; our corpus becomes their Phase-0 input instead |

- Rendered at the primary pin, **48×36 = 1,728 cells/frame** (glyphcast's fine
  layer; density=48, aspect 4:3).
- **~6,000 frames ≈ 10.4 M target cells; packed as [F_{t−1}, SEP, F_t, SEP,
  F_{t+1}, SEP] ≈ 31 M tokens.**
- Render cost: c1 measured 8.6 ms/frame-setting at density 100 → corpus render
  ≈ **1–2 min CPU** (measured rate, scaled).
- Splits: **temporal per source, 70/15/15, no shuffle** (c2 convention — the
  future must not leak into training).

## 3. Model (c) — the D2 skeleton with free-delta, re-tokenized

Reuse `training/delta_free/train.py` (the D2 KEEP: free-delta attention,
val_bpb 1.6666 vs 1.6959 baseline; D3 replicated at seed 1337, agreement
0.0007). Deviations kept minimal, one-variable discipline:

- Swap tokenizer → identity code map (V=32); pack frames with SEP per §2.
- `sequence_len: 2048 → 6144` (3-frame pack = 5,190 tokens, rounded);
  window pattern SSSL kept — short windows ≈ one frame (1,728), long = 2
  frames (3,456): within-frame attention full, cross-frame attention carries
  velocity from F_{t−1}.
- `DEVICE_BATCH_SIZE 8 → 4` at 6,144 (same tokens/step as D2's 8×2,048);
  fallback B=2 + grad-accum 2 if VRAM pressure. GPU checked free + serialized
  before each run (house rule).
- Value-embeddings, rotary, free-delta heads, Muon/AdamW LR scaling: untouched.
- **Size, measured (instantiate-and-count on this skeleton):** at vocab 8192 →
  50.33 M params (wte 4.19 M, value_embeds 16.78 M, lm_head 4.19 M, matrices
  25.17 M). At **V=32 the tables shrink to ~0.16 M → G1 ≈ 25.3 M params.**
  Fits 6 GB with room: D2 peak was 3,745 MB at a larger table and equal
  tokens/step; G1 estimate ≤ ~5.5 GB (simulated scaling), measured at first run.

Why not smaller (e.g. 8 M tiny-GPT): the corpus is small but the skeleton is
free, already KEEP-hardened, and the gate compares against persistence — a
bigger-than-needed model still has to *beat copy-last-frame*, which is the
honest bar. A tiny-GPT ablation is queued, not blocking.

## 4. The gate (d) — pre-registered

Test = last 15% of each source, forward-only. Metrics: next-cell top-1
accuracy (overall + per kind: blank/tone/edge) and exact-frame match rate.

Baseline arms (numpy, seconds to run):

1. **majority-class** — most frequent code in the train split, predicted everywhere.
2. **persistence (copy-last-frame)** — emit F_t again. This is the real bar.

**KEEP iff both:**
- G1 beats persistence by **≥ +2.0 accuracy points** on the mean of the three
  dynamic sources (life, testsrc2, mandelbrot) — pre-registered because
  static-ish sources (smptebars, gradients) make persistence near-perfect and
  would dilute the signal; and
- G1 beats majority-class by **≥ +15 points** overall (mean of 5 sources).

**FAIL-first check:** an untrained G1 must land ≈ majority-class level or the
gate is theater. **Both numbers reported either way** (D2 discipline).
Per-pin and per-source breakdowns in the receipt; no "crosses" without
denominators.

Wager on record (labeled): the free-delta heads should help *specifically* on
cell-level motion (k/v differences encode inter-frame change) — if G1-KEEP,
the follow-up ablation is G1 with delta heads disabled, paired 300 s.

## 5. Runtime estimate (e)

| stage | estimate | basis |
|---|---|---|
| corpus render (6,000 frames, 1 pin) | ~2 min CPU | 8.6 ms/frame measured (c1) |
| feed gen (ffmpeg lavfi) | ~3 min CPU | c2 feed ran 500 frames in ~1 min |
| train, 300 s budget, one arm | **~8.6 min GPU end-to-end** | D2 measured 302 s train / 516 s total; G1 same tokens/step |
| eval + baselines | <1 min | numpy |
| **first receipt (G1 seed 42)** | **≈ 15 min wall, $0** | |
| docket slot full spend: 3 pins × budget + 2-seed replication + delta-off ablation | ≈ 2–3 h | edge scout allotted 4–6 h |

Throughput basis: ~71 K tok/s measured on this skeleton (both in D2's receipt
and today's live run); 300 s ≈ 19 M tokens ≈ 0.6 epoch of the packed corpus —
sufficient for gate #1; corpus doubles cheaply if val loss is still falling.

## 6. What this buys the family

- glyphcast gets its **Phase-0 dataset builder target**: header = engine-pin
  hash, payload = row-major code array, exactly the format G1 trains on.
- glyphspace's material table reads the same 20 edge codes + tone indices.
- The fleet holds the **first published generative glyph-space training loop**
  (field state per edge scout: ASCIIEval consumes ASCII; nobody trains in it).
- Receipts stay renderer-replayable: any G1 output decodes to text a reader
  can score with the feed-lab crossing-rate harness (glyphcast's `score` job).

## 7. Build order (next session, one variable at a time)

1. `g1_data.py` — feed gen + render + pack + temporal split (reuses
   chiaroscuro-embedding renderer unmodified; that repo stays untouched).
2. Baselines + untrained FAIL-first check.
3. G1 train.py = delta_free copy with §3 deviations only; smoke fwd/bwd
   (smoke_delta_free.py pattern) before the 300 s run.
4. Gate verdict → receipt doc in this directory → pathspec-scoped commit.
