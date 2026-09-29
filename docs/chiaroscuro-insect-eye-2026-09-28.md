# Chiaroscuro as insect eye — the mapping

**Date:** 2026-09-28 · **Lane:** Casey's directive — "deeply understand how our chiaroscuro is like insect eye vision"
**Sources:** `~/projects/chiaroscuro-embedding/SEED.md` (c1–c3, t1–t3, wave 4) · `~/projects/chiaroscuro/README.md` (five engines, four doors) · receipts: `chiaroscuro-embedding/results/{c1,c2,c3}-sweep.json`, `quilt-gpu-lab/RESULTS.md` (G1–G8), `docs/glyph-predictor-spec-2026-09-28.md` (edge-code table)
**Status:** structural mapping + build list + 3 pre-registered experiments. The biology is textbook-level (flagged in the honest ledger); the chiaroscuro side is measured receipts.

---

## The headline

**Chiaroscuro is a compound eye in silico, and it already made the insect's founding bargain.** The compound eye gave up spatial acuity (it can't win against a single-chamber lens on stills) to buy temporal and motion resolution — flies resolve 200–300 Hz flicker where we fuse at ~60 Hz, and detect displacements *finer than a single interommatidial angle* (motion hyperacuity). Chiaroscuro gave up pixels — 100 columns of text will never out-photograph a VLM's raw input — to buy framerate: *"crank framerate to make up for pixel loss"* (SEED.md). **c3 is the experimental proof that the bargain costs nothing: at fixed chars/sec, the resolution↔framerate trade is a TIE** (0 pairs favor high-fps, 1 favors low-fps). The insect design is not a compromise. It's a wash on statics and strictly better on dynamics — because the insect doesn't really see *images*. It sees *change*. So do we: G4 proved the glyph model learns 3–4× better when statics are masked out of the gradient, and G5 built the architecture that results from taking that seriously: **a prior (persistence) that confirms the world frame-by-frame until surprised (the diff-head)** — the simulation-first loop, derived by our own experiment arc.

---

## 1. Compound eye anatomy ↔ chiaroscuro structure

| Insect eye | Chiaroscuro | Measured anchor |
|---|---|---|
| **Ommatidium** — one lens + rhabdom, its own acceptance angle, reports a *measurement* not a pixel | **Glyph cell** — one character per cell, chosen by a per-cell decision (tone × edge); "characters are shapes, not pixels" | README pipeline step 4; the Sculptor's bivariate pick |
| **Ommatidium count / interommatidial angle** — the density vs coverage dial | **Density** (24×18 → 100×75 cells) and the ramp/glyph vocabulary per cell | renderer dials; V=32 at the canonical 32×24 (G1 reference density) |
| **Rhabdomeric opponent channels** — each cartridge encodes contrast/slope, not raw intensity | **Edge codes** — `edge_code = fam × 5 + level`, `fam ∈ {0°,45°,90°,135°}`, `level ∈ 0..4` — slope direction + magnitude per cell | glyph-predictor-spec §1, read from `renderer.py` RAMPS/EDGE_DIRS |
| **Apposition-eye blur acceptance** — coarse sampling accepted as design, not defect | **Downsample as the whole trick** — "text art is a very small image with a very expressive palette" | README, pipeline step 1 |
| **The founding bargain**: spatial acuity traded for temporal/motion acuity | **The resolution↔framerate dial**: pixels traded for framerate ("nearly free" — text) | SEED.md seed + **c3 verdict: TIE** |

**c3's TIE is the deepest receipt in the mapping.** The seed hypothesis was that framerate compensates for pixel loss. The measurement came back better than the hypothesis: at fixed character budget, neither direction dominates on content carried (c3 stacked gate: 0/2 pairs pro high-fps; single-frame ablation 0/0). Translate to insect terms: **spending receptors on time instead of space is free.** That's why flies could evolve 200–300 Hz photoreceptors — the currency the eye spends is the same one chiaroscuro spends, and the exchange rate is ~1:1. The dial isn't a tradeoff to manage; it's a *dial*, and the creature turns it per task (reflex → time; planning → space). t3's unsteady-camera seed is exactly the insect move: use the temporal budget to extract what spatial acuity never gives you (parallax → depth).

---

## 2. Motion hyperacuity — the frame-difference stream IS their world

Insects see motion better than shape. A fly's visual computation is built from **elementary motion detectors** (Reichardt correlators): adjacent ommatidia correlated across a small delay — the *difference between frames in space-time* is the primary signal, and static pattern is what's left over. Four of our receipts are this exact design, independently derived:

1. **G4 — learn only from change.** Masking statics from the loss tripled-to-quadrupled dynamics on every source: life 5.6%→**19.8%** (3.5×), mandelbrot 7.5%→**19.6%** (2.6×), mockscene 4.7%→**19.5%** (4×). The model wastes capacity predicting the ~95% that doesn't change — the same waste a nervous system avoids by adapting away unchanging input. Statics collapse under the mask, but **persistence covers statics for free** — the insect's retina does the same: static image → adaptation → silence.
2. **G5 — the composite = the confirm-until-surprised simulator.** Persistence base + diff-head corrections beats both parents. `persist_changed_acc = 0` by construction: persistence *never* predicts a change; the diff-head is the only surprise detector. Wave 4 named this — the creature runs a forward simulation, and each frame is a confirmation "until surprised." G5's threshold dial (thr 0.5 → statics parity; thr 0.1 → dynamics capacity) is a **flicker-fusion knob**: how much temporal contrast reaches the brain.
3. **t2 — motion signatures as the object's identity.** X2 measured that *static* reads are renderer-bound (cross-renderer transfer failed on every dial). t2 hypothesizes the *delta stream* transfers across cameras because it's about the object, not the sensor's parameterization. Insect parallel: optomotor response is driven by global flow, near-invariant to what the object looks like. The insect can't recognize your face; it can intercept you mid-air.
4. **The G6→G8 coda — capacity and time, not data.** Hard dynamics (life's CA rule, the fractal zoom) resisted more data (G6 KILL), cracked with time (G7: life 0.198→0.422), and saturated (G8). The insect analogy is the reflex/brain split: fast crude loops (lamina) for what must not wait, slow expensive loops (central complex) for what must be understood. Our budget axes are the same budget axes a creature has.

**Where the mapping is sharpest:** our cell-level world is a *spatio-temporal lattice* exactly like the insect's — resolution in space (density), resolution in time (fps), resolution in change (the delta stream). The question "what survives the glyphs?" (c1–c3) is the insect's question: not *what does the eye resolve* but *what does the motion channel carry*.

---

## 3. What insects have that we don't (yet) — the build list

### a) Omnidirectional coverage — the wrap-around lattice
The compound eye wraps the world; our lattice is a rectangular window, and every crop is a lie at the edges. Insects get heading-continuous perception: nothing exits the field, so motion is unambiguous (the optomotor system needs this — a rectangular window makes rotation and translation confusable at the boundary).
**Build:** cylindrical (azimuth-indexed) glyph lattice — and the cheap version first: **toroidal wrap in the cell buffer** (mod-arithmetic neighbors) over a synthetic 360° scene. The delta stream becomes seam-free; ego-motion estimation (t3) becomes the natural consumer.

### b) Temporal contrast as a named dial — the flicker-fusion threshold
We already own the pieces: the Studio's trails (phosphor persistence) and temporal blending; G5's threshold between statics and dynamics. What's missing is the *explicit* dial: a **CFF cut-off on the delta stream** — the fastest change the text can carry before it fuses — and its creature-side consequence: **the fast channel feeds reflexes, the slow channel feeds planning.** The insect splits its optic lobe this way; t1 (thermal reflexes) vs the quilt predictor (planning) is already the software version. Name the dial, measure the curve, then assign consumers.

### c) Lobula-plate motion neurons — direction-selective cells in TIME
The fly's lobula plate pools thousands of local detectors into ~60 direction-selective tangential cells (HS/VS families) that *are* the animal's optic flow estimate. **We already have the spatial half of this: the four edge fams (0°/45°/90°/135°) are direction-selective channels** — four preferred axes, the same axis structure the LP's tangential cells are organized around (horizontal + vertical + diagonals). But our fams are *static*: which way does the edge *face*. The LP's are *dynamic*: which way is it *moving*.
**Build:** the temporal fams — Reichardt-style elementary motion detectors on adjacent glyph cells: correlate `cell(t) × neighbor(t−1)` per axis → **four MOTION fam codes** (a motion vocabulary alongside tone+edge codes), then pool per-axis sums into the full-field flow readout (our LP). The G4 diff-mask already proved the value of the change signal; this gives the change a *direction*.

---

## 4. Experiments the mapping seeds

- **ie1 — temporal fam codes (the LP build):** Reichardt correlators over the glyph lattice → 4 motion-direction codes; text-only reader recovers the true drift direction of mock-scene bars/moving light from the motion-code stream alone, gate: direction R² ≥ 0.5 at ≥2 densities (c1 house gate). *Cost: ~1–2 h CPU* (renders measured 8.6 ms/frame-setting; readers are c1's ridge/MLP stock).
- **ie2 — the flicker-fusion curve of the text channel:** mock scene with light pulsing at f Hz, rendered across a glyph-fps sweep at fixed chars/sec; find the alternation rate where the delta stream can no longer resolve on/off — the CFF receipt for THIS eye. Extends c3's TIE from *content* to *time*. *Cost: ~2 h CPU/GPU.*
- **ie3 — the wrap-around lattice:** toroidal/cylindrical cell buffer over a 360° synthetic scene (thermal variant rides t1's renderer); gate: position/heading readout with wrap-aware deltas beats the rectangular-frame readout, especially across the seam where rectangular crops destroy the signal. *Cost: ~3 h CPU.*

---

## Honest ledger

- **Metaphor discipline:** this is a *structural* mapping, not a neural claim. Our cells don't compute like rhabdoms; the correspondence is at the level of what each design measures and what it spends.
- **c3's TIE** was measured on CLIP-labeled classification over five 10 s synthetic sources — "the trade is free" holds there, not (yet) universally. ie2 is the experiment that would test it on the *temporal* axis.
- **t1's thermal results** (temporal-split KILL → i.i.d. MARGINAL) were rendering/readout failures (sub-cell sigma; intensity confound) — they are *not* evidence for the insect story, though they rhyme: statics are where compound eyes are weakest, and the escape (t2) is the motion channel.
- **LP mapping scope:** 4 fams ≈ 4 preferred axes. The fly's lobula plate is ~60 tangential cells computing rich local flow fields; we map the axis structure, not the full flow-field computation. The motion fams (build c) are the honest next rung.
- **Biology sourcing:** CFF 200–300 Hz in flies, motion hyperacuity, Reichardt EMDs, LP tangential-cell organization are textbook-level facts cited from general knowledge, not re-verified today. Flag before any canon claim.

*The eye does the rest — and in the insect's case, mostly the rest is motion.*
