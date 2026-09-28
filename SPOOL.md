# SPOOL — the standing backlog of falsifiable GPU-lab experiments

Casey's doctrine: **"we should always have things waiting."** This file is the
pre-registration queue. Every entry states its claim and its gates BEFORE a
script exists, so a build subagent can pick one up cold and the runner can
fire it without me. KEEP / KILL / INCONCLUSIVE only — a KILL is a win (a
claim died honestly), and INVALID_* gates catch a broken harness first.

Lab conventions (every entry inherits these):
- frozen encoder(s) + a label source (elephant DialBank or synthetic) + a
  reader probe (ridge baseline + a regularized nonlinear reader) +
  leave-one-room-out CV + a permutation null + ONE JSON verdict on stdout.
- Never add a spooled experiment to runner.py's EXP_MOD or QUEUE.md until its
  script exists and passes its own self-test.
- A nonlinear reader is now a **per-fold sklearn LBFGS (hidden 16, alpha 0.1)**
  unless the experiment pre-registers otherwise (the E13b overfitting lesson).

---

## A. Dial-read robustness (extend E12 / E13 / E13b)

### E15 — encoder-swap dial read  [ACTIONABLE]
Q: is I-JEPA special, or does ANY frozen vision encoder read the dials?
Claim: a different frozen encoder (DINOv2 ViT-B, CLIP ViT-B/32, V-JEPA 2 ViT-L)
reads staged mood/volume/presence as well or better than ijepa_vith16_1k.
Gate: E12's gate verbatim per encoder (≥2/3 dials: still-LORO R²≥0.30,
room≥0.15, k16≥0.5·k64, >null95). KILL = a second encoder's read dies where
I-JEPA keeps (I-JEPA's inductive bias is load-bearing). KEEP = another
encoder matches/beats → the read is a property of room geometry, not I-JEPA.
Deliverable: a dial-bank leaderboard (the scoreboard).
Feasibility: high — swap load_encoder, reuse E12 bank/collector verbatim.
(Caveat: check what weights are already cached; V-JEPA 2 was pulled for E7/E9.)

### E22 — quantization robustness (boat deployment)  [ACTIONABLE]
Q: does the dial read survive int8/fp16 quantization of the EMBEDDING?
Claim: the read survives fp16 (trivial) and int8 (linear-ish) — the dial
signal is low-frequency and robust.
Gate: same E12 gate on quantized embeddings. KILL = read dies under int8 →
edge deployment needs more than 8-bit. KEEP = survives.
Feasibility: high — quantize embeddings post-hoc, reuse E12.

### E25 — fold-amplitude phase transition (where does the read die?)  [ACTIONABLE]
Q: E13 measured ONE fold (2.2). What is the read-R² vs carrier-nonlinearity curve?
Claim: read R² decays smoothly (a phase transition) in fold amplitude, with a
per-dial critical amplitude where volume/presence die but mood survives.
Gate: sweep N2_FOLD_AMP ∈ {0.5, 1.0, 1.5, 2.2, 2.8, 3.5}; plot per-dial R².
KILL = no monotone relationship (E13's single point was noise). KEEP =
monotone decay with a visible per-dial critical point — maps the honest
"readable nonlinearity" boundary of every E12-family claim.
Feasibility: high — reuse E13's carrier builder, parameterize the fold.

### E26 — layer-wise probe (where does the dial info live?)  [ACTIONABLE]
Q: does volume/presence info live in LATER layers while mood lives EARLIER?
Claim: per-layer probes of I-JEPA's intermediate features show mood's read
peaks early/mid (colour-temp is low-level) and volume/presence peak later
(semantic) — a gradient of abstraction.
Gate: per-layer still-LORO R²; KEEP = dial read-maxima sit in DIFFERENT
layers. KILL = flat across layers (no abstraction gradient).
Feasibility: medium-high — hook I-JEPA's intermediate blocks, reuse E12.

## B. Temporal / field (the "room is a field, not a stream" doctrine)

### E16 — field-edge (transitional) dial read
Q: does the read capture the CHANGE (field_before→field_after) or only state?
Claim: the field-EDGE (delta-dial between two time points) is MORE readable
than either endpoint's absolute dials — "the walk between rooms is the lesson."
Gate: delta-dial R² vs endpoint-dial R². KEEP = delta > endpoint. KILL =
delta adds nothing (state is everything).
Feasibility: medium — needs a paired-frame renderer (same room, two dial sets).

### E24 — dial-sequence self-prediction (the field over time)  [ACTIONABLE]
Q: does a room have MOMENTUM — can a model predict the next room state from
the dial SEQUENCE?
Claim: a small transformer/JEPA over the elephant's own dial time-series
(data/nights, data/wave4-pilots) predicts the next dial vector better than
markov-1.
Gate: next-step R² vs markov-1. KEEP = beats markov (temporal structure
beyond the last state). KILL = markov-1 is the ceiling.
Feasibility: high — uses the elephant's OWN dial data, NO video needed.

## C. The elephant identity (sauna/plunge, charisma, modularity)

### E18 — sauna/plunge contrast read  [ACTIONABLE]
Q: is the CONTRAST between two rooms (the signed gap) more readable than
either room's absolute dials?
Claim: embedding-pair features (concat + signed difference) predict the
sauna_plunge_gap better than either room's embedding predicts its own dials
— the walk is the signal, not the rooms.
Gate: gap R² (pair features) vs single-room dial R². KEEP = contrast read
beats absolute read (super-additivity). KILL = contrast is just the two
absolutes summed.
Feasibility: medium-high — reuse E12 bank, add pairwise targets.

### E19 — charisma / acclimation pull read
Q: can embeddings read the acclimation RATE and charisma PULL, not just dials?
Claim: the acclimation curve's rate (agent→room relaxation) and charisma
pull (room→agent) are readable from room embeddings.
Gate: read acclimation_rate + charisma_pull R² vs null. KEEP = readable.
Feasibility: medium — reuse field.py's curves, synthetic agent trajectories.

### E20 — multi-modality (is the dial read vision-specific?)
Q: does the dial read require VISION, or is it a property of the dial FIELD?
Claim: a TEXT embedding (or a pure numeric encoder over the dial vector)
reads the dials as well as the vision encoder — the elephant is modular,
"the core never knows what the space is."
Gate: same E12 gate on a non-vision embedding of the same room. KEEP =
non-vision reads dials (modality-agnostic). KILL = vision-only.
Feasibility: medium — text embeddings already exist
(checkpoints/contrast/text_emb_*.npy).

## D. Relational / cellular (Casey's relational-intelligence seed)

### D24 — relational correlation scaling (D13d follow-up)  [ACTIONABLE]
Q: D13d showed correlation (not reward) cracks the shared key at 1.0. Does
it scale to NOISY or NON-SHARED keys?
Claim: the correlation primitive degrades gracefully with key noise; the
degradation curve is the honest scope of "relational intelligence."
Gate: crack-rate vs key-noise. KEEP = graceful. KILL = brittle (chance at
small noise).
Feasibility: high — extend D13d's harness.

### E27 — hidden-angle relational reconstruction (the cellular graph)
Q: Casey's seed — can MANY small models, each seeing a DIFFERENT low-dim view
of one object, reconstruct the UNSEEN side by combining their views?
Claim: the set of partial views (each cell sees a projection) jointly
determines the hidden dims — relational multi-view reconstruction.
Gate: reconstruct held-out dims from the view ensemble vs chance. KEEP =
the unseen side is recoverable from the view set (relational bootstrap).
Feasibility: prototype — synthetic projections, no real data needed.

## E. Tone-channel (D15c follow-up)

### D23 — tone-channel rule-execution  [ACTIONABLE]
Q: D15c's 0.94 read was MEMORIZATION (held class = 0.0). Does a properly
regularized nonlinear reader EXECUTE the momentum rule instead?
Claim: a regularized reader (the E13b lesson) generalizes to the held tone
class — it executes (timbre−data mod 4) mod 4 rather than memorizing.
Gate: held-class acc ≥ 0.8 (base ≤ 0.3). KEEP = rule executed. KILL = still
memorization (the rule is not in the embedding at all).
Feasibility: high — reuse D15c harness, swap reader.

---

*Build order (self-contained → novel): E25 → E15 → E18 → E24 → E22 → E26 →
D24 → D23 → E16 → E19 → E20 → E27. Refresh this file as experiments land.*

---

# WAVE 2 — DeepInfra ideation (Seed-mini widen + Hy3 contrast, 2026-09-28)

## Contrarian falsifiers (Hy3) — the load-bearing assumptions, one kill-shot each
- **X1 [HIGHEST VALUE, trivial] — reverse-probe variance fraction.** Every result is a FORWARD probe (embedding→dial). Nobody measured the reverse: predict each embedding dim from the 3 dials (LORO). If dials explain <10% of embedding variance, the "room-temperature sense" framing dies regardless of forward R². Gate: mean reverse-R² < 0.10 = KILL the framing; > 0.40 = license it. CPU, data on disk.
- **X2 — renderer transfer.** The read may be the STAGING FUNCTION, not "room geometry." Re-render same dials via a second independent renderer; cross-renderer R² ≥0.5× within = room content; collapse <0.2 = renderer parameterization.
- **X3 — stats-battery parity.** E12's control was mean luminance only. A ~20-dim battery (color moments, histograms, Fourier band energy, contrast, edge density) is the real null. If it reads volume/presence within 0.1 R² of I-JEPA, the JEPA story is decoration.
- **X4 — walk-tautology dismantling.** If sauna_plunge_gap IS a dial difference, emb_B−emb_A is handed the target's functional form. Re-run E18 with matched capacity + mismatched (random-pair/wrong-dial) targets; if diff's edge survives arbitrary targets, the "walk" is real.
- **X5 — critical-amplitude family-invariance.** 1.0/1.5/2.2 are in ONE warp family's units, 5 points. Re-sweep under ≥2 fold families + 9 points; re-express in invariant currency (MI destroyed). Non-aligning = curve-fitting, "distinct critical amplitudes" dies.
- **X6 — extrapolation.** Train on dial range [0,0.7], test [0.7,1.0]. Collapse = the reader memorized the staging manifold's local geometry (LORO tests room-holdout, not range-holdout).
- **X7 — label-free reachability.** Can a self-supervised head recover dial directions WITHOUT labels? If nothing finds any dial direction, the elephant never bootstraps and needs labels.
- **X8 — encoder-family taxonomy.** Add a supervised ResNet/CNN + a mismatched (audio/text) encoder as negative controls. If only the JEPA-vision family reads, "room geometry" collapses to "JEPA bias."

## Alternative framings (Hy3)
- **F1 Manifold cartography, not dial bank.** Ask "what IS the room-embedding manifold and where do dials sit in it?" (reverse-R², intrinsic dim, principal angles) — survives negative results with dignity.
- **F2 The difference-operator program.** E18's diff, D19/D20's ternary transition, D13d's correlation discovery are the SAME primitive: signed/ternary differences carry structure absolutes don't. Generalize: for which f(A,B) does emb_B−emb_A beat [emb_A;emb_B]?

## Seed-mini widen (top of 20 — renumber into E48+ to avoid collision with E28/E29)
- Critical-amplitude encoder shift (fuse E25+E15): do per-dial death points move across encoders?
- Strip luminance → mood should die (falsify E13's "mood rides colour-temp").
- Permute dials → read collapses to chance (hard test of "room geometry").
- Distill to ~10k-param edge model keeping ≥90% of the read (boat deployment).
- int4 quantization: mood survives, volume/presence degrade (boat deployment).
- Adversarial carriers (targeted per-dial; cross-encoder specificity).
- Layer-wise peaks across encoders; late-layer fine-tuning; multi-gap reads; augmentation robustness.

---

# WAVE 3 — polln + webgpu-profiler extractions (Casey, 2026-09-28 11:31)
Older but still-valid ideas, extracted as modular quilt tooling:

## polln (Pattern-Organized LLM Network — Rust, cloned to ~/projects/polln)
- **Plinko Layer → the cell-ROUTER organ.** Gumbel-Softmax stochastic selection (annealed τ, entropy-collapse detection, discriminator hard-gates) picks WHICH sub-cell handles a task — sampling instead of argmax preserves behavioral diversity. The missing router of the cellular-decomposition loop.
- **Confidence Cascade → the inter-cell ESCALATION bus.** Hierarchical deadband triggers (hysteresis: no state change inside [r_min, r_max]) with propagation weights = when a small cell escalates to a bigger one. WGSL shaders already exist.
- **VAE world model + dreaming → the SUPER-CELL SIMULATOR.** DreamerV2-style latent rollout without environment interaction = Casey's "use the larger model to simulate inputs/outputs to test whether the decomposed system handles everything the super-cell would." Powers the capstone super-cell-vs-cells equivalence test.
- **Behavioral Embedding Space (pollen grains, privacy tiers)** → the relational-weighting substrate for agent behavior vectors across untrusted nodes.

## webgpu-profiler (browser-GPU instrumentation — local at ~/projects/webgpu-profiler)
- **Metric-honesty contract** (real / estimated / placeholder — never lie about which is which) → the quilt metrics contract for every cell.
- **BenchmarkSuite 6-pass** (dispatch/bandwidth/register-pressure/texture/atomics/sparse) → the cell hardware-benchmark tool; pairs with cudaclaw-Moth.
- **MemoryTracker per-allocation** → cell-memory receipts (every allocation a BIND cell).
- **Browser-as-GPU-substrate**: cells running IN the browser via WebGPU — the chiaroscuro doors already live there; a cell layer under them = the a2a translation layer rendered where the renderer lives.

*Build order: Plinko router → deadband escalation → dream-simulator (capstone).*
