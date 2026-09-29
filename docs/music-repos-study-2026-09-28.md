# Music Repos Study — tensor-midi × musician-soul × the GPU lab (2026-09-28)

**Lane:** subagent study (Casey: "that then can be done in our latest technologies and
innovations too — seeds not constraints"). Repos studied: **SuperInstance/tensor-midi**
(the tensor-music repo, local clone at `~/projects/tensor-midi`) and
**SuperInstance/musician-soul** (the GAN-in-music repo; cloned depth-1 tonight), with
**SuperInstance/jev-gan** as the GAN-harness pattern. Status labels: measured / simulated / wagered.

---

## 1. What the repos are

### tensor-midi — conversation-as-jazz (tensor-music)

- **What it does:** captures conversations and renders them as a live jazz performance on
  a DAW-style mixer. SWMIDI-8 wire format from slackwater-rust: **8 bytes/event
  (status|channel, pitch, velocity, error_mask, tick u32), 96 PPQ, little-endian** (measured, README).
- **The tensor/music representation:** events are *tensor coordinates*, not audio. The
  architecture IS a 3:4 polyrhythm resolved by CRT: ECN fires the 4-pulse (beats 1,4,7,10 —
  reflex), DMN fires the 3-pulse (beats 1,5,9 — creative); they co-incide at beat 12
  ("two quotient groups interfering on the 12-cycle", 12/8 time). BeatClock + TempoMap +
  12-pulse grid; sessions export as binary SWMIDI or JSON.
- **Training-loop content:** none — it is a capture/render/analyze stack. But
  `POLYFORMALISM.md` pins the same engine in **5 languages incl. CUDA**
  (`native/sentiment_kernel.cu`, sentiment→dynamics), and the Platonic RNG game engine maps
  solids→channels (tetra/icosa/dodeca/cube/octa = combat/social/weather/resources/exploration).
- **Gates/conventions:** shared 96 PPQ clock ("MIDI timing IS musical timing");
  pulse-grid-aligned channels; analyzer modes (groove/building/tension/solo/comping/ballad);
  test parity matrix across the 5 implementations.

### musician-soul — the GAN-in-music repo (self-play jam loop)

- **What it does:** vector-database personas that digest MIDI into **32-dim phrase
  fingerprints** (`DIM=32` measured, `embedding_v2.rs` — mean+std of "how high, leapy,
  dense, loud, silent" features), keep a bag of them as a pattern library, and jam:
  answer phrases by blending the nearest fingerprints to what they just heard.
- **The GAN loop (all measured in `lib.rs`):**
  - **Producer** = `respond_to` (nearest-fingerprint blend),
  - **Critic** = room scoring: `harmony_score` (response-embedding agreement) +
    `surprise_score` (how far the response departs from what it answered) → "productive",
  - **Training signal** = `learn_from_jam`: reinforce/penalize by index, then **mutate** —
    deterministic-noise jitter shifts the embedding; working patterns spawn copies the
    source MIDI never contained. Sustained self-made drift = the "soul".
  - Evolutionary-GAN shape: mutation + selection on a generative library against a
    two-axis critic. No backprop anywhere; pure Rust, zero deps.
- **Gates/conventions:** decision-layer only (no audio); deterministic arc so numbers are
  reproducible; `#![forbid(unsafe_code)]`.

### jev-gan — the harness pattern (context)

Producer → substrate cell (prev_hash) → critic → JEV vote → JEPA prediction → revise.
Every step witnessed. This is the fleet's canonical GAN-on-substrate shape; music is an
unguarded instance waiting for a producer/critic pair (wagered, but the repo invites it).

---

## 2. Our latest tech (the synergy targets, with receipts)

| Asset | Receipt |
|---|---|
| **Glyph-domain lattice V=32** (11 tone + 20 edge codes + SEP; 48×36=1,728 cells/frame; chiaroscuro `renderer.py` the only implemented encoder; "two repos one lattice") | `docs/glyph-predictor-spec-2026-09-28.md` |
| **Free-delta transformer (D2/D3 KEEP)** | val_bpb 1.6666 vs 1.6959 (−0.0293); D3 replicated seed 1337, agreement 0.0007 |
| **Diff-target / difference-operator (G4)** | changed-cell acc up on EVERY source: life 3.5×, mandelbrot 2.6×, mockscene 4×; statics collapse but persistence covers free → "predict differences not states" is two-scale (token: free-delta; target: diff-mask) |
| **Hybrid refiner (G5 KEEP)** | persistence prior + diff-head corrections via confidence threshold; beats both parents; threshold = statics/dynamics dial |
| **Simulation-first confirm-until-surprised (Casey, 17:05)** | framerate = the confirmation waveform; confirm the prior sim until surprised; minimize surprise as primitive; high surprise must be EARNED (jam sessions, sports). G5 = this loop unnamed |
| **Thermal/acoustic seeds t1–t3** | chiaroscuro glyph fields beyond visible light (thermal, acoustic/spectrogram); t2 cross-camera motion signatures; t3 unsteady→4D; boat = engine heat + sounder |
| **Ternarization is FREE** | ternary correlation model slightly BEAT the continuous-diff oracle (0.0101 vs 0.0110); sign/deadband = regularizer, not cost. Relational transition kernel KEEP |
| **G6 KILL** | starved probe: data allocation bought nothing; hard dynamics need capacity or a different inductive bias |
| **Look-Again at scale (D1 KEEP)** | independent-reach readers lift the oracle ceiling (+0.168 best-single→ensemble; +0.146 with symbolic reader) |
| Lab conventions | guard: ≥1 GB free VRAM, ≤80 °C, 30-min timeout; working budget ~4.5–5 GB; seed 2718; temporal split no shuffle; KEEP/KILL/INCONCLUSIVE; receipt manifest |

---

## 3. THE SYNERGY MAP — seeded GPU experiments

Each: the seed → **one falsifiable line** → rough 4050 cost.

### M1 — Music as a second V=32 domain: does free-delta transfer off-image?
**Seeds:** glyph lattice V=32 × D2/D3 free-delta × tensor-midi's SWMIDI-8.
Tokenize SWMIDI bars into a ≤32-code vocabulary (pitch-class×register class + velocity
class + rest + SEP on the shared 96 PPQ tick — the 12-pulse grid is a sublattice of the
glyph corpus convention, both fixed-width frames). Train the *unchanged* D2 skeleton
(~25 M params, same SSSL windows, hyperparams one-variable-deviation) on next-tick
prediction. **Falsifiable line:** free-delta beats the vanilla-attention baseline by
≥0.02 nats/token on held-out SWMIDI streams — i.e. D2's −0.029 bpb win is a property of
delta-attention, not of glyph pixels. *Wagered until run.*
**Cost:** corpus from existing session exports + musician-soul demo MIDI, render free;
G1-scale train ≈ 30–60 min GPU. Fits one guard window.

### M2 — The jam IS the confirm-until-surprised loop: G5 inside musician-soul
**Seeds:** G5 hybrid refiner × simulation-first × musician-soul's critic.
Replace `respond_to`'s pure blend with the G5 composition: copy the nearest fingerprint
(persistence prior) + apply the blend correction only where predicted surprise exceeds
threshold τ (the statics/dynamics dial, now a *musical restraint dial*).
**Falsifiable line:** at matched surprise budget, G5-jam responses score harmony ≥ the
baseline blend by a bootstrap CI-separated margin (seed 2718), with τ sweeping the
harmony/surprise frontier — if pure blending wins at every τ, the sim-first loop does not
transfer to taste-space. *Wagered; nearly free to test.*
**Cost:** CPU-only (32-dim vectors, `cargo` bench harness) — minutes; GPU unnecessary.
Cheapest experiment on this page.

### M3 — Acoustic/thermal glyph fields: is the diff-mask gain modality-invariant? (t-lane)
**Seeds:** t1/t3 acoustic seed × G4 diff-target × chiaroscuro renderer.
Render spectrograms / spectral-flux fields of real audio (fleet-radio, session40 mp3s)
through `renderer.py` into the 48×36 glyph lattice, then run the G1-vs-G4 diff-mask arc
on the sound-glyph corpus. **Falsifiable line:** diff-mask training multiplies
changed-cell accuracy by ≥2× on spectrogram-glyph streams, replicating the visual
2.6–4× — if the gain dies on sound, "predict differences not states" was a visual
staging artifact (which would sharpen the X2 renderer-bound verdict family).
**Cost:** corpus render ~30 min CPU (ffmpeg → spectrogram → renderer) + G1-scale train
< 1 h GPU. Also feeds t2 (motion signatures of sound) and the boat sounder lane.

### M4 — CRT attention: the 3:4 polyrhythm as an attention bias
**Seeds:** tensor-midi's 12-pulse architecture (ECN 4-pulse × DMN 3-pulse) × free-delta
window patterns (SSSL).
Impose the CRT structure directly: within-voice attention windows of 3 and 4, with forced
co-attention at beats t ≡ 0 (mod 12), as a hard attention mask on the M1 model.
**Falsifiable line:** the polyrhythm-structured mask beats the unstructured SSL skeleton
on next-pulse prediction of two-voice synthetic 3:4 (and 3:4:5) streams by ≥0.05 accuracy
— the architecture's claim ("the polyrhythm IS the architecture") becomes a measured
inductive-bias number instead of a diagram. If it loses to full attention, the 12-cycle
is aesthetic, not computational. *Wagered.*
**Cost:** synthetic data free; ≤25 M params; < 1 h GPU per arm.

### M5 — JEV-GAN on music: musician-soul as the critic, G5-unrolled as the producer
**Seeds:** jev-gan 5-component pattern × musician-soul room scoring × D1 Look-Again.
Producer = the G5 refiner unrolled one bar (simulate-until-surprised generation); critic
= room harmony+surprise scoring; JEV = schema gates (SWMIDI validity, 12-pulse
alignment); JEPA = a tiny model predicting which outputs the critic will reward.
**Falsifiable line:** JEPA's predicted-vs-actual critic score correlation rises above
0 across GAN rounds (the loop emits learnable signal), AND reinforced-then-mutated
patterns beat random mutations on harmony-at-matched-surprise — if JEPA can't learn the
critic or mutation gains nothing over random jitter, the music GAN is not a GAN.
**Cost:** producer train < 1 h GPU; rest CPU. Substrate cells free (prev_hash discipline
already dogfooded in this lab's receipts).

### M6 — Ternary souls: 32-dim fingerprints in 128 bits (boat endpoint)
**Seeds:** "ternarization is FREE" × musician-soul DIM=32 × boat doctrine.
Ternarize musician-soul's fingerprints (sign/deadband per dimension) and test whether jam
retrieval and harmony scoring survive at 2 bits/dim. **Falsifiable line:** ternary
fingerprints retain ≥95% of retrieval AUC and harmony-signal (vs shuffled null) —
a persona's soul fits in 32 ternary values, offline, zero-cost; if ternary collapses
retrieval, the scale-fix in embedding_v2 v2 was load-bearing beyond sign.
**Cost:** CPU minutes (reuse `similarity()` harness + deterministic mutation noise).

### M7 — Motion-signature identity from the delta-stream alone (t2 in music)
**Seeds:** t2 cross-camera matching × G4 "statics are free, dynamics are the signal" ×
musician-soul personas.
Train a small classifier to match *performer identity* from interval/velocity delta
streams with pitch content transposed and tempo warped between "cameras" (the music
analog of cross-camera thermal signatures). **Falsifiable line:** delta-stream-only
identity matching beats chance ≥2× across transposition+tempo shifts — the soul lives in
the diff-stream, not the notes; chance-level matching kills the sensor-invariance analogy
between thermal motion signatures and musical voice. *Wagered.*
**Cost:** minutes–< 1 h GPU (small head over M1's frozen encoder or raw features).

### M8 — Physics prior instead of copy-last: symplectic persistence in G5
**Seeds:** SuperInstance/symplectic-music (symplectic integrators preserve tonal
structure) + conservation-music T1–T5 × G5's persistence term.
Swap G5's copy-last-frame prior for a symplectic stepper over harmonic state (the prior
*simulates* instead of repeats), keep the diff-head as the surprise corrector.
**Falsifiable line:** symplectic-prior G5 beats copy-last G5 on changed-cell accuracy of
harmonic sequences at equal surprise budget — testing whether the confirm-until-surprised
loop wants a physics prior where one exists. If copy-last wins, conservation structure
adds nothing at this scale. *Wagered.*
**Cost:** CPU sim + < 1 h GPU train; reuse M1 corpus.

---

## 4. Suggested firing order

1. **M2** (minutes, CPU) — cheapest test of the sim-first paradigm in the GAN-music repo.
2. **M6** (minutes, CPU) — boat-endpoint receipt, pairs with M2 in one session.
3. **M1** (one guard window) — unlocks M4/M5/M7 which all reuse its corpus+encoder.
4. **M3** (one guard window + render) — the t-lane bridge; book before t1-thermal re-run so
   the acoustic corpus serves both lanes.
5. M4 → M5 → M7 → M8 as the corpus matures.

All experiments inherit the lab gates: seed 2718, temporal split no shuffle,
KEEP/KILL/INCONCLUSIVE recorded either way, artifact-or-void (no phantom reports),
receipt manifest re-sealed with any ledger change.

---

*Repos read 2026-09-28: ~/projects/tensor-midi (README, POLYFORMALISM.md, JAZZ_SCORE.md
headers), ~/projects/musician-soul (README, src/lib.rs jam loop, src/embedding_v2.rs),
~/projects/jev-gan (README, gan.py listing). GitHub sweep: 30+ SuperInstance music repos
catalogued; conservation/symplectic/tminus/betti-music flagged as prior-art neighbors for
M8 and tminus-music as the simulation-first namesake.*
