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

---

# WAVE 4 — edge-mine (test-time training / context-as-weights, 2026-09-29)

*Seeded from GEMS.md Wave 5 (abstraction M2, assayed 32 = 4×2×4). One gem this wave — the assayer promoted nothing else.*

## Z1 — the context-as-weights arm (does an inner-loop update beat putting the same tokens in the window?)
Q: TTT-E2E's claim is that context is not retrieved but *learned* — mini-gradient steps on the incoming stream compress it into weights (parity at 128k, 2.7× faster; ≤35× at 2M). Does a cheap inner-loop parameter update beat handing the identical tokens to the attention window at MATCHED parameter count and MATCHED wall-clock on a 6GB GPU?
Claim: at matched budget, the learned-in-weights arm wins on held-out next-token loss once the context is long enough to saturate the window's usable capacity — i.e. the crossover exists and is measurable on our metal.
Gate: two arms, same tokens, same params, same wall-clock. KEEP iff the inner-loop arm's held-out loss is lower by ≥2% relative at the long-context point **and** ≥1 seed replicates. KILL iff the arms tie, or the inner loop loses, or the crossover does not exist within the budget we can actually run. Secondary (reported, not gating): the fixed-budget rate-distortion point (change in bits vs change in tokens-per-second over the attention-only arm).
Feasibility: high — a small char/byte-level stream, our existing skeleton, `G_TIME_BUDGET` discipline; the compute analogue of the free-iteration economics that produced the free-delta KEEP. ~an afternoon, 1–2 GPU hours. Instruments the boat doctrine: at 60 mi offshore there is no window big enough, only weights that updated on the way out.
Pre-registration required first: the crossover point and the ≥2% margin must be frozen in `proposals/runs/` before any code, per the assayer spec.

---

# WAVE 5 — edge-mine (evidence-based failure diagnosis / lifetime-scaled precision / skills-as-supervision, 2026-09-30)

*Seeded from GEMS.md Wave 6 (assayed 64, 48, 27). Three gems this wave — the first edge-mine wave with a direct collision between the literature and our own booked doctrine (M10 × QO6).*

## W5a — evidence-gated harness revision (does re-observation beat trace-reading when fixing the improver?)
Q: Video-RSI's claim is that a trace is a sample from the harness, not from the world, so failure diagnosis that reads only traces is circular; the fix is going back to the raw environment to test competing explanations. Our QO6 already proved the substrate-side twin (evidence accumulators, not tail predicates, gate stream-killing). Does an evidence-based revision loop — replay raw lane streams with extra probes on failure — produce better harness/policy revisions than trace-only revision, at matched revision budget?
Claim: the re-observation arm's revisions are retained more often by the QO6 retraction gate (i.e. they survive later evidence) and end with higher held-out score than the trace-only arm's.
Gate: two revision arms, matched number of proposed revisions and matched probe budget. KEEP iff the re-observation arm's final harnesses score higher on the private held-out streams by the pre-registered margin AND a lower fraction of their revisions get RETRACTED by the QO6 gate across the run. KILL iff the arms tie on either axis, or re-observation's advantage disappears once the gate controls retention (i.e. the gate was doing all the work).
Feasibility: high — CPU only; the lanes are replayable worlds, eproc.py and the QO6 gate are already booked and pinned. ~an afternoon. This is the falsifier for our own doctrine: if trace-reading matches re-observation here, QO6's "cannot retract = p-value in disguise" loses its claim to generalize.
Pre-registration required first: margin and retention-delta thresholds frozen in `proposals/runs/` before any code.

## W5b — lifetime-scaled ternary delta state (does memory lifetime tell us which deltas deserve to survive rounding?)
Q: STEPQuant/LeapQuant's convergence — quantize recurrent-state memory by its lifetime and output-impact, not uniformly — has not been tested in the *training-from-scratch ternary* regime (they are post-training, 4-8 bit, frontier-scale). Our free-delta stream is a recurrence whose D-ledger already labels which deltas persist. Does lifetime-weighted precision allocation beat uniform ternary quantization on the same parameter budget?
Claim: allocating the few high-precision (non-ternary) weights to the longest-lived delta positions (measured on the D-ledger statistics) yields lower loss than allocating them uniformly or at random positions, at equal high-precision budget.
Gate: three allocation arms (lifetime-ranked / uniform / random), equal non-ternary budget, equal training budget, 2+ seeds. KEEP iff lifetime-ranked beats random by the pre-registered bpb margin on held-out loss in ≥2/3 seed-pairs. KILL iff allocations tie or rank-correlate with no advantage (which would say lifetime structure in the delta stream is real but not exploitable at allocation time).
Feasibility: high — nursery skeleton + qthe ternary lineage (D2/D14/D19/D20); ~3 GPU hours per arm, overnight total. Directly extends gem #3 and tests whether the ternary-free-delta KEEP generalizes to a *principled* mixed-precision map.
Pre-registration required first: the lifetime statistic, allocation budget, and bpb margin frozen in `proposals/runs/`.

## W5c — verdict-to-skill distillation (does a frozen skill bank mined from the keep/kill ledger beat handing over the raw ledger?)
Q: Meta-Skill/Skill-Space Shooting's claim — supervision lives at the granularity of the reusable abstraction extracted from failure feedback, and a frozen skill bank beats raw experience handoff by double digits. Our D-ledger is a labeled verdict corpus nobody else has. Does distilling it into a compact, frozen bank of reusable lane-skills (principles of when support/builds fail) improve downstream forecasting/routing (QO1/QO3-style gen-1 prediction) more than fine-tuning or prompting on the raw ledger entries?
Claim: the skill-bank arm's gen-1 forecast AUC exceeds both the raw-ledger-context arm and the no-bank baseline by the pre-registered margin.
Gate: three arms (frozen skill bank / raw ledger in context / baseline), identical eval streams. KEEP iff skill-bank AUC > raw-ledger AUC by ≥ the registered margin (meta-skills paper saw +12pts for bank-over-raw-experience; our margin must be frozen first, not borrowed). KILL iff the bank ties or loses — which would say our verdicts do not compress into transferable principles, i.e. the ledger is a log, not a curriculum.
Feasibility: high — CPU only; ledger already exists; ~an afternoon of distillation + eval. Also the cheapest instrument for the Pincher-pattern thesis (repeated patterns compile into skills) on our own substrate.
Pre-registration required first: distillation budget, bank size cap, and AUC margin frozen in `proposals/runs/`.

# WAVE 6 — edge-mine (weight-space behavior directions / loop depth needs a scratchpad, 2026-10-01)

*Seeded from GEMS.md Wave 7 (assayed 48, 36). Two gems this wave — both literature×receipt collisions: the 2026 weight-steering literature finally gives Wave 0's "weights as data" mine a cheap falsifier on our D-ledger, and the recurrent-depth literature hands gem #2 its next arm.*

## S6a — contrastive delta-direction forensics (does a weight-space direction isolated from paired keep/kill runs predict verdicts on unseen runs?)
Q: Contrastive weight steering isolates a behavior direction by subtracting the weight deltas of two opposite-polarity fine-tunes, and reports that weight-space directions generalize out-of-distribution where activation steering does not. Our keep/kill D-ledger is a labeled corpus of weight deltas nobody else has. Does the contrastive direction computed from polarity-paired runs (KEEP-vs-KILL on the same lane family) predict the verdict of NEW runs — via projection of their deltas onto the direction — better than scalar baselines (delta norm, loss delta, param-count)?
Claim: projection along the contrastive direction separates keep-vs-kill deltas on held-out runs above the scalar-baseline AUC by the pre-registered margin — i.e. the ledger's verdict information is *geometric*, not just scalar.
Gate: direction computed only from training-split run pairs; held-out runs frozen before direction extraction. KEEP iff held-out projection-AUC exceeds the best scalar baseline by ≥ the registered margin in ≥2 seed families (bootstrap over run-pairings). KILL iff it ties or loses — which would say our verdicts live in delta magnitudes, not delta geometry, and the "weights as data" abstraction dies on our substrate.
Feasibility: high — CPU only; deltas already on disk in the D-ledger; the falsifier is an afternoon of linear algebra. This is the cheapest possible assay of Wave 0's oldest unassayed mine.
Pre-registration required first: split definition, pairing rule, baseline set, and AUC margin frozen in `proposals/runs/` before touching the ledger.

## S6b — memory tokens in the looped free-delta (does the loop need somewhere to write?)
Q: The 2026 recurrent-depth literature reports weight-shared loops fail combinatorial reasoning without learned memory tokens (a depth-state trade-off), and that adaptive depth decomposes into trajectory-formation + exit-readout. Our gem #2 loops one shared block at R=2 with no external loop state. Does adding a small persistent loop state (memory tokens carried across loop iterations) to the looped free-delta skeleton change the depth-vs-quality curve at matched parameter count?
Claim: loop+memory beats the plain loop on held-out loss at equal params — weight sharing buys depth only when the iteration has state to accumulate into — and the gain grows with R.
Gate: three arms, param-matched (plain 12-block / shared-block loop R=2 / shared-block loop R=2 + memory tokens), same data budget, 2+ seeds. KEEP iff loop+memory beats the plain loop by the pre-registered bpb margin at R=2 AND the margin does not shrink at R=3. KILL iff memory tokens make no difference (the loop's bottleneck is elsewhere — halting/exit, not state) or hurt.
Feasibility: high — nursery skeleton (D2), ~3 GPU hours per arm, overnight total. Directly extends gem #2 with the field's 2026 answer to "what does the loop need?"
Pre-registration required first: memory-token count, R values, and bpb margin frozen in `proposals/runs/` before any code.

# WAVE 7 — edge-mine (the router is a post-hoc object / synthetic corpora need a grounding anchor, 2026-10-02)

*Seeded from GEMS.md Wave 8 (assayed 48, 48). Two gems this wave — both literature×receipt collisions: M19 lands directly on C2-IL's booked +0.2191 oracle headroom and +0.1045 calibration finding (testable at 0 GPU-Wh on the frozen prediction dumps), and M21 lands on the fact that we own the generative laws of our corpora, so drift is exactly measurable instead of estimated.*

## W8a — post-hoc routing vs calibration on the frozen federation corpus (can a test-time rerouter close the oracle headroom, and is its gain separable from recalibration?)
Q: R2-T2 and the calibrated-MoE-under-shift line say expert selection is a deploy-time policy with two separable failure axes — choice (which expert) and confidence (how calibrated the pick is). C2-IL booked: oracle per-item best-view headroom +0.2191, our 0-param margin router agrees with the oracle only 0.7070, and the whole FED−S4-MONO gap (+0.1045) was refit-vs-frozen *calibration*, not routing. Does a tiny test-time rerouter (neighbor/feature-conditioned re-pick over the frozen views, trained on train-split only) close a real fraction of the +0.2191 headroom, and is that gain additive with, or absorbed by, a 2-parameter per-channel margin recalibration?
Claim: the rerouter's held-out gain over the fixed best view is positive and ≥ the registered fraction of oracle headroom, AND remains positive after the recalibration control is applied (i.e. it fixes choice, not just confidence — or the separation is booked honestly the other way).
Gate: arms on the frozen C2-IL predictions, 0 GPU-Wh: fixed-best-view (incumbent) / margin recalibration only / test-time rerouter only / rerouter + recalibration, plus the oracle ceiling. KEEP iff rerouter-only beats fixed-best by ≥ the registered margin AND the rerouter+recalibration arm exceeds recalibration-only by ≥ a second registered margin (both CI-low > 0). KILL iff all router gain vanishes under recalibration (the +0.219 headroom is unreadable confidence, not unreadable choice) or the rerouter cannot beat the fixed view at all on held data.
Feasibility: high — CPU only, predictions/ already committed (20 arms × 3 seeds × 3,082 rows), an afternoon of small-model work. The literature number to beat is R2-T2-class consistency, not a frontier margin.
Pre-registration required first: rerouter parameter cap, headroom-fraction margin, and the recalibration-control margin frozen in `proposals/runs/` before touching predictions/.

## W8b — anchor-calibrated synthetic drift (does training on our generated corpora stay on the generator's law, and does the anchor measure drift better than held-out loss?)
Q: The 2026 collapse literature says synthetic-data safety comes from a real anchor that makes drift measurable — and our corpora are stronger than "synthetic with real anchor": we own the exact generative law (COMP1-A1 grammar, the B1 k=1.5 ramp law). Does a model trained on generator output drift from the generator's law in ways held-out loss does not detect, and does an exact law-check (generator-resampled reference distribution) detect drift earlier and more reliably than loss-based monitoring?
Claim: across training checkpoints, the exact law-deviation metric flags degradation (or a drift basin) at a checkpoint where held-out loss is still flat or improving — i.e. loss is a lagging indicator of law-drift on self-consumed synthetic data.
Gate: nursery-class run on a glyph/grammar corpus, checkpoints frozen on a schedule; two monitors evaluated against the generator-resampled reference: (a) held-out loss, (b) exact law-deviation (compare model samples to generator samples on the booked law statistic, e.g. the B1 ramp/knot statistics). KEEP iff monitor (b) detects the degradation onset ≥ the registered number of checkpoints earlier than (a), with the detection threshold frozen before the run. KILL iff loss tracks law-deviation within the registered tolerance (loss is sufficient; the anchor buys nothing) — which would itself book that our synthetic loop has no measurable collapse surface.
Feasibility: high — small model, known law, hours of GPU on the 4050; the C6/C7 bit-exact reuse machinery already gives us checkpoint discipline. Also the first gem that turns H1B-VISION's death (measure instability without an external reference) into a positive instrument: here the external reference provably exists.
Pre-registration required first: law statistic set, detection threshold, and checkpoint schedule frozen in `proposals/runs/` before training.

# WAVE 8 — edge-mine (grokking as a law-controlled phase transition, 2026-10-03)

*Seeded from GEMS.md Wave 9 (assayed 32). One gem this wave — the literature×receipt collision: the grokking-as-phase-transition literature makes generalization onset a measurable function of the data's rule structure, and our glyph/grammar corpora are generated from laws we own (COMP1-A1 grammar, B1 k=1.5 ramp), making rule structure a controlled experimental variable at nursery scale.*

## W9a — law-controlled grokking onset (does generalization transition timing track the corpus's rule structure, exactly measured?)
Q: The grokking literature now characterizes the memorize→generalize transition as a phase transition whose timing depends on the data's rule structure — but published setups control rule structure only implicitly. Our corpora are generated from owned laws, so the rule complexity (COMP1-A1 grammar depth, B1 ramp law k) is a dial, not an estimate. Does grokking onset (held-out-law generalization crossing the pre-registered threshold) shift as a clean, monotone-ish function of the law's complexity on the free-delta nursery skeleton — and does that onset curve differ between the additive (free-delta) and multiplicative (vanilla) attention arms?
Claim: transition onset (in updates) is a measurable, repeatable function of the law parameter with seed-noise small enough to resolve the curve — i.e. grokking onset inherits the corpus's generative law as a controlled variable — and the onset-vs-complexity curve is distinguishable between attention families.
Gate: nursery-class runs on law-parameterized corpora, ≥2 law values × ≥3 seeds per attention family, checkpoint schedule frozen before firing, onset threshold and the "curve resolution" criterion (seed spread < the spacing between adjacent law points) frozen in the pre-reg. KEEP iff onset shifts monotonically (or single-bend) with law complexity AND attention-family curves separate beyond seed noise at ≥2 law points. KILL iff onset is law-insensitive within noise (grokking here is not structure-tracking on our substrate) or seed spread swamps the curve spacing (no clean gate at this scale — booked honestly, not retried until it passes).
Feasibility: high — hours of GPU per arm on the 4050, corpora already exist as generators; the exact law-check machinery from W8b doubles as the onset detector. Risk honestly noted: grokking may simply not appear at this scale/data budget — that outcome is a valid KILL, not a failed run.
Pre-registration required first: law-parameter grid, seed count, onset metric/threshold, and curve-resolution criterion frozen in `proposals/runs/` before training.

# WAVE 9 — edge-mine (criticality reachability / audit-as-index / canvas refinement, 2026-10-04)

*Seeded from GEMS.md Wave 10 (assayed 48, 48, 36). Three gems this wave — all literature×receipt collisions: M31 lands on PIDFIRE-1's pre-registered empty-corner FAIL (a private measured reachability boundary), M33 lands on VX-1+FR-1's passing verdict index, and M29 lands on the law-owned discrete glyph canvas.*

## W10a — the reachability boundary of criticality (does the booked empty-corner map predict where a servo can ignite SOC?)
Q: Learning dynamics are generically attracted to self-organized criticality, but PIDFIRE-1's pre-registered sweep booked that the fixed-rule (p,q) corner is EMPTY at frozen f_step=1/150: KS-passing cells are steep subcritical (tau 2.35–4.49), tau-bracketed cells are curved near-misses (self-KS ≥ 0.111 vs gate 0.10), density pinned 0.50 < percolation 0.59, and the diagnosis names the knob (f_step vs q timescale separation). Does adding the PIDFIRE-2 knob (f_step tied to q at c·q, c ≤ 0.1) move the sweep across the boundary into the corner — and is the boundary location (in c) itself a stable, seed-robust quantity?
Claim: at c below a threshold the corner stays empty and the failure mode matches PIDFIRE-1's signature (KS-passing ⇒ subcritical tau bracket); at c above it, ≥ the pre-registered corner fraction of cells pass the frozen gate — i.e. the empty-corner map was a reachability boundary in c, not a property of (p,q).
Gate: coarse (p,q) sweep at ≥3 values of c, same frozen gate, 2+ seeds per cell. KEEP iff the passing-corner fraction rises from 0 through the registered threshold monotonically in c (boundary exists) AND the near-miss cell (p=0.81, q=7.9e-4) flips within the predicted c range. KILL iff no c in the sweep opens the corner (criticality is unreachable by timescale rescaling alone — booked honestly) or the passing cells appear without boundary structure (noise, not a boundary).
Feasibility: high — CPU only, PIDFIRE substrate + 15 test pins already landed for reuse; hours per sweep. The measured near-miss is the predicted first cell to flip, which makes this an unusually sharp pre-registered prediction.
Pre-registration required first: c grid, corner-fraction threshold, seed counts, and the near-miss prediction range frozen in `proposals/runs/` before firing.

## W10b — audit as taint-traced index lookup (is a machine-checkable receipt index adversarially sufficient, i.e. does it catch an injected inconsistency it wasn't told about?)
Q: ReAgent/ARA/SEVA propose frameworks for auditing agent-generated research against receipts; VX-1 already passes G1–G4 (9-booking verdict index, per-booking taint round-trip, tamper control, 0.000s CPU) and FR-1 guarantees fresh-clone sufficiency. The open question VX-1 did NOT test: is the index *adversarially sufficient* — if an inconsistency (a receipt edit that flips a booked verdict, or a claim citing a nonexistent booking) is injected by an adversary who knows the index exists but not its internals, does the taint machinery detect it without a human review pass?
Claim: detection rate ≥ the registered threshold across injected mutations (receipt-value edits, verdict-flips, phantom citations, stale-HEAD re-runs), with zero false positives on the 9 clean bookings — audit as lookup generalizes from self-checked to adversary-checked.
Gate: mutation battery over the sealed index copy, mutation taxonomy and detection thresholds frozen before running; each mutation class ≥ the registered count. KEEP iff detection ≥ threshold on every class AND clean-copy false-positive rate 0. KILL iff any class evades detection systematically (the index's taint tracing has a blind spot the taxonomy names — itself a bookable result).
Feasibility: high — CPU only, minutes; VX-1's G2/G3 probes are the template, this extends them to a frozen taxonomy. No GPU, no other lane touched.
Pre-registration required first: mutation taxonomy, per-class counts, detection and false-positive thresholds frozen in `proposals/runs/` before touching any index copy.

## W10c — canvas initialization vs order-freedom on the glyph canvas (does start-from-persistence beat free-order refinement?)
Q: The 2026 DDLM literature reports the "flexibility trap" — arbitrary generation order can hurt — and that gains come from initialization + refinement policy (PG-DLM, remasking, pre-initialized dLLMs). Our glyph corpora are a discrete, replayable, law-owned canvas, and G1's persistence-first baseline was a *loser* under the autoregressive regime. Does a small masked-refinement (canvas) model on the glyph corpus, initialized from the persistence statistic (which cells stay fixed), beat a free-order refinement baseline AND an autoregressive baseline at matched parameter count on law-faithful held-out generation?
Claim: persistence-informed initialization + remasking refinement beats free-order refinement on the booked law statistic at matched params — where you start matters more than the order you refine in, and the persistence statistic is the right place to start.
Gate: three arms, param-matched (canvas+persistence-init / canvas+random-init / autoregressive incumbent), same data budget, 2+ seeds, law-statistic metric and margin frozen before training. KEEP iff canvas+persistence-init beats canvas+random-init by ≥ the registered margin AND ≥ the autoregressive incumbent. KILL iff persistence-init buys nothing over random (G1's loser was a loser for good reason — booked honestly) or both canvas arms lose to autoregressive at this scale.
Feasibility: high — nursery-class model on the existing glyph generators, hours of GPU per arm on the 4050; the W8b/W9a law-check machinery doubles as the metric. Risk noted: canvas training at this scale may be unstable — a valid KILL, not a failed run.
Pre-registration required first: arms, persistence-statistic definition, law metric, margins, and seeds frozen in `proposals/runs/` before training.

# WAVE 10 — edge-mine (dry-run rehearsal gate / convention witnesses, 2026-10-05)

*Seeded from GEMS.md Wave 11 (assayed 48, 48). Two gems this wave — both literature×receipt collisions: M34 lands on the EP-1 series' thrice-booked dry-run lesson, M37 lands on IONQ-2's passing crx witness battery. Both CPU-only, both runnable on existing booked artifacts.*

## W11a — dry-run rehearsal as a pre-fire gate (does rehearsing the instrument on known failure sites kill falsified predictions?)
Q: The EP-1 series booked one lesson three times: a prediction about a classification arm must be machine-checked against the known failure sites *before* the full fire — EP-1b asserted a receipt-hit unverified, EP-1c's corpus-scope prediction was falsified after fire, EP-1d ran its dry-run gate first and CONFIRMED in ~40 s. The 2026 verification-first-experiment literature formalizes pre-registered claims but never rehearses the instrument on curated known cases. Does making the dry-run a mandatory pre-fire gate measurably reduce prediction-falsification rate in our experiment stream?
Claim: lanes that run a dry-run gate over known failure sites before firing have a prediction-falsification rate below the registered threshold, vs the historical rate of lanes that fired without rehearsal — rehearsal transfers from known sites to the full fire.
Gate: retrospective arm first (0 cost, mandatory): replay EP-1b's and EP-1c's predictions through their dry-run arms on the exact known sites — the gate must flag both (recall 2/2, else the gate concept is weak and the lane KILLs immediately). Then prospective: over the next ≥ the registered number of instrument-class fires (census/pointer/audit lanes), all run dry-run-first; KEEP iff falsified-prediction rate < the registered fraction of the pre-EP-1d historical rate with zero loosened gates. KILL iff dry-runs pass but fires still falsify at the historical rate (rehearsal doesn't transfer — booked honestly).
Feasibility: high — CPU seconds per dry-run; sites, predictions, and tools all committed (ep1b/ep1c/ep1d tools + bookings). Zero GPU.
Pre-registration required first: known-site set, historical-rate baseline, prospective fire count, and the falsification threshold frozen in `proposals/runs/` before the first prospective fire.

## W11b — convention witnesses vs value agreement (are exact identity checks strictly stronger for cross-backend gate transfer?)
Q: IONQ-2 cleared the qcell_sim↔fleet-bridge crx convention with an identity battery (control-leak P=0 exact, additivity crx(1/3)²→0.75 exact, cancellation crx(+1/3);crx(−1/3)→exactly 0.0, calibration = sin²(θ/2) within 1e-9 at every θ). Standard practice in the simulation literature is value-agreement against a reference backend at sampled angles. Are there convention mutations (angle sign, endianness/qubit order, control-vs-target swap, unit conventions) that *pass* value agreement at the standard calibration grid but are caught by an exact identity witness — i.e. is the witness battery strictly stronger than sampled agreement?
Claim: yes — at least one registered mutation class is missed by value agreement on the IONQ-2 calibration grid yet detected by the cancellation/additivity witnesses, because agreement at sampled points cannot distinguish a convention flip that is symmetric on those points.
Gate: mutation battery over crx semantics (≥4 registered classes: angle-sign flip, qubit-order swap, control/target swap, unit rescale), each tested two ways: (a) value agreement on the exact IONQ-2 θ-grid, (b) full witness battery. KEEP iff ≥1 class is missed by (a) and caught by (b) at the registered grid. KILL iff value agreement catches every class the witnesses do (witnesses are redundant at our resolution — itself a useful booking about grid density).
Feasibility: high — exact statevector, CPU seconds, qcell_sim + the IONQ-2 harness reused as-is; no other lane touched.
Pre-registration required first: mutation taxonomy, calibration grid, witness set, and detection criteria frozen in `proposals/runs/` before any mutation fires.
