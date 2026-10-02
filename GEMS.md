# GEMS — the discovery ledger

*The breakthrough-finder's memory. Every abstraction the scouts mine lands here with its sources, its synergy with our assets, and the gem-question it seeds. Status flows: MINED → ASSAYED (scored) → SEEDED (SPOOL entry) → FIRED → verdict.*

## Wave 0 — the first harvest (2026-09-28: edge-gems + weco-rsi scouts)

### Gems (assayed, high-potential, gates drafted)

| # | Gem | The question (pre-registered) | Asset it rides | Cost | Status |
|---|-----|-------------------------------|----------------|------|--------|
| 1 | **Diff-JEPA** | quilt-jepa's predictor targets the latent *difference* d_z instead of the next state z_{t+1} — if diff-targets beat state-targets where free-delta beat vanilla, "predict differences not states" is a **two-scale principle** (token + latent), not a trick | quilt-jepa (mesh world model) + D2/D3 free-delta receipts + E18 diff-super-additivity | ~2-3h GPU | SEEDED |
| 2 | **Looped free-delta** | one shared transformer block looped R=2 at equal params vs the 12-block baseline — does delta-attention survive weight-sharing? The composition question is open in the literature | the nursery skeleton (D2) | ~3h GPU | SEEDED |
| 3 | **Ternary free-delta** | BitLinear-ize the free-delta skeleton — if the −0.029 bpb win survives {-1,0,+1} weights, that's a **multiplier-free LM trained on one 6GB GPU** (additive attention + ternary weights): the headline AND the boat-doctrine endpoint | nursery + qthe ternary lineage (D2/D14/D19/D20 KEEPs) | overnight | SEEDED |
| 4 | **G3: framerate scaling** (running) | 2× temporal data + finer dt: does changed-cells learning improve; does persistence erode? | G1/G2 glyph corpus + diagnostics | firing now | FIRED |
| 5 | **The acceptance-gate harness** | WECO's 80% build: private held-out scores + fixed budget + heterogeneous evals before any self-improvement claim — wire it around the nursery and the lane machine | WECO AIDE² (arXiv:2609.26457) | ~an afternoon, CPU | ASSAYED |

### The abstraction mines (not yet gems — the assayer's backlog)

- **Latent prediction / world-model war** (JEPA family, Genie 3-class systems) — we're already fluent (elephant, quilt-jepa).
- **Depth as a loop** — shared block × R, adaptive halting; the RSI-flavored architecture bet.
- **Multiplication-free ternary arithmetic** — BitNet matured into embeddings (CAT-Q post-training ternarization); gem #3's mine.
- **Verifiable environments as the RL bottleneck** — Environments-Hub-shaped work; our falsifiers are a private stock of them.
- **Autonomous research loops + mode collapse** — EMNLP 2026 "Beneath the Diff" named the failure; our pre-registered-kill nursery is the designed anti-collapse version.
- **Canvas generation / diffusion LMs** — "start from persistence, refine" = G1's losing baseline turned into an architecture; the glyph domain is a perfect canvas testbed (discrete, replayable).
- **Representation steering** — activation directions as dials: the elephant's dial metaphor made measurable in weight space.
- **Weights as data** — Weight-Pair-Encoding-class work; our keep/kill D-ledger is a labeled weight-delta corpus nobody else has.
- **WECO's load-bearing ideas** — the acceptance gate (private scores, fixed budget), the 4-level RSI ladder as honest metrology, 16× context compression with reinvestment, HGM's "score agents by descendant performance."

### Scout-source notes
- Wave 0 sources: `docs/edge-gems-2026-09-28.md` + `docs/weco-rsi-deepdive-2026-09-28.md` (citations via search roundups — flagged for re-verification before canon).
- Memory search down at scout time; filesystem-direct mining worked fine.

*The feedback hook (when wired): verdicts on gem-sourced experiments append here with their source-abstraction — the mine cron re-weights its queries toward sources that produced KEEPs.*

## Wave 5 — the memory-timescale harvest (2026-09-29: edge-mine scout, focus rotated to continual-learning / test-time-training / routing, since Wave 0 was heavily world-model + ternary)

*Search focus this wave: TTT & fast-weights · continual-learning retention · MoE routing stability · RSI harness self-improvement · sparse/quantized memory. Sources are search-roundup-grade and flagged for re-verification before canon (same caveat as Wave 0).*

### Abstraction mines (status MINED → ASSAYED below)

- **M1 — Consolidation as an explicit update schedule (the retention axis).** Across the continual-learning literature the same primitive recurs: knowledge is kept by *scheduling the timescale of the update*, not by freezing weights. Dual-rate EMA (attention adapts fast / MLP drifts slow, MiDEA), adaptive+selective reset with importance-aware recovery (ASR), prompt-as-fast-weights vs params-as-slow-weights (Fast-Slow Training), residual-subspace-restricted LoRA (KeepLoRA). Replaces "freeze or forget" with **a two-clock update policy**. Essence: *plasticity is a schedule, not a switch.*
  - https://proceedings.iclr.cc/paper_files/paper/2026/file/79bdd6fe3f012befcc459ad13de65d13-Paper-Conference.pdf (MiDEA, ICLR 2026)
  - https://arxiv.org/pdf/2603.03796 (When and Where to Reset Matters, ICLR 2026)
  - https://gepa-ai.github.io/gepa/blog/2026/05/11/learning-fast-and-slow/ (Fast-Slow, prompt=fast/params=slow)

- **M2 — Context is a dataset; inference is training (TTT-E2E).** Long context is not retrieved, it is *learned*: mini-gradient steps on the incoming stream turn the context window into a training set and compress it into weights (TTT-E2E: full-attention parity at 128k, 2.7× faster; ≤35× at 2M). Essence: *the distinction between context and parameter collapses when the update loop is cheap enough.* Our 6GB GPU's whole economics is "free iterations" — this is the abstraction that says iterations can be moved to inference time.
  - https://test-time-training.github.io/ · https://introl.com/blog/ttt-e2e-test-time-training-long-context-inference-breakthrough-2026
  - https://arxiv.org/pdf/2603.03796

- **M3 — Compression must be self-indexing (unify store and retriever).** Across KV-cache and embedding-quantization work the recurring structural idea is that the compressed representation should *be* the index: 1-bit/sign VQ as a self-index for sparse attention (no external index, no learned predictor), binary embeddings searched by Hamming with int8 rescoring (95% accuracy retention, 15–45× faster), 16× hierarchical block-wise KV compression (>90% cache reduction, 4× decode). Essence: *compression and retrieval are one function, not two modules.*
  - https://huggingface.co/papers/2609.31093 · https://huggingface.co/blog/embedding-quantization
  - https://arxiv.org/abs/2605.06763 (PISA pyramid top-k) · https://arxiv.org/html/2605.27740v1 (UNIQUE)

- **M4 — Imbalance is a gradient-visibility failure, not a fairness failure.** MoE routing's failure mode is named precisely: collapsed routers starve experts of gradient ("gradient blackout", expert collapse, silent starvation). The fixes are all *inversions of control*: expert-choice routing (experts pick top-k tokens — perfect balance by construction, faster convergence), capacity factors, Z-loss router-logit regularization, memory-aware routing against "pseudo-balance", STGC pushing conflicting tokens apart. Essence: *balance is not a constraint to add to the loss — it is what makes the gradient exist at all.*
  - https://research.google/blog/mixture-of-experts-with-expert-choice-routing/ · https://pub.towardsai.net/moe-routing-failures-what-happens-when-top-k-load-balancing-breaks-down-9d8490207015
  - https://arxiv.org/abs/2406.19905

- **M5 — The gate is the artifact; the model is frozen (RSI-2026 consensus).** The self-improvement community's 2026 convergence: score the *harness* (prompts, control flow, tooling, memory, context management) around a frozen backbone — "recursive harness self-improvement" and "model-harness co-evolution," with the harness optimized for BOTH current agent performance and producing high-quality traces for future model training. This is our pre-registered-gate discipline stated as a research program, and it names the coupling we already rely on (an eval harness is also a data engine). Essence: *improvement lives in the loop, and the loop must be scoreable.*
  - https://recursive-workshop.github.io/ · https://openreview.net/group?id=ICLR.cc/2026/Workshop/RSI
  - https://arxiv.org/abs/2609.24972

- **M6 — Latent actions as the interface between imagination and control.** CoLA-World / World2Act / SWIRL converge on the same move: learn the action in *latent* space, train action-model and world-model jointly, avoid pixel-space supervision because imperfect rollouts inject visual artifacts. Hallucination in world models is attributed to low-coverage regions of state-action space (a data problem, not an architecture problem). Essence: *control signals are learned representations, and prediction error is a coverage map rather than a model flaw.*
  - https://www.microsoft.com/en-us/research/publication/co-evolving-latent-action-world-models/ · https://arxiv.org/abs/2602.06130
  - https://aiweekly.co/alerts/world-model-hallucinations-linked-to-data-coverage-gaps

- **M7 — Continual learning is currently unsolved, and the field now says so out loud.** CL-Bench 1.0 (UC Berkeley Sky, six non-independent real-world domain sequences, expert-validated, with a "gain" metric to isolate learning from prior capability) reports that current systems — *including dedicated memory systems* — leave large room, with naive in-context learning sometimes beating complex memory. Essence: *stateful online improvement is an open, measurable frontier — and the measurement instrument (gain over a stateless baseline) is the deliverable.* Directly relevant: our whole ledger only counts if the gate isolates gain.
  - https://sky.cs.berkeley.edu/project/continual-learning-bench/ · https://arxiv.org/abs/2606.05661

- **M8 — Augmentation as an equilibration policy, not a pass.** Augmentation methods in this wave are all *regimes*: double augmentation (augment both sides of a pair), annealed settings, entropy-collapse detection with hard gates. Essence: *when the objective equilibrates too fast, the intervention that keeps it learning is a schedule over the data distribution.* (Mined as the unification of the augmentation/annealing entries across the wave.)
  - https://arxiv.org/html/2605.27740v1

### ASSAY — Wave 5 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M2 | context-as-dataset / inference-as-training | 4 | 2 | 4 | **32** | SEEDED (see SPOOL Wave 4) |
| M1 | consolidation as an update schedule (dual-rate EMA) | 3 | 4 | 2 | **24** | ASSAYED — parked, F-starved |
| M3 | compression must be self-indexing | 3 | 2 | 4 | **24** | ASSAYED — parked, U-starved |
| M4 | imbalance = gradient-visibility failure | 3 | 3 | 2 | **18** | ASSAYED — parked |
| M5 | the gate is the artifact (harness-as-object) | 3 | 3 | 2 | **18** | ASSAYED — parked; arguably already our practice |
| M6 | latent actions as the control interface | 4 | 2 | 2 | **16** | ASSAYED — parked |
| M7 | RSI is unsolved; "gain over stateless" is the instrument | 5 | 1 | 2 | **10** | ASSAYED — KILLED as a gem (no local test material; U=1: anyone can run a benchmark) |
| M8 | augmentation as equilibration policy | 2 | 3 | 2 | **12** | ASSAYED — parked |

*Rubric honesty: novelty was not inflated this wave — only 1/8 cleared 27, and three of the parked items died on a single axis star (M1 on falsifiability, M3 on local-uniqueness, M7 on local-uniqueness). No gate was loosened to promote an entry.*

## Wave 6 — the evidence-and-lifetime harvest (2026-09-30: edge-mine scout, focus rotated to state-quantization + reward-free RSI + harness search, since Wave 5 was TTT/continual/routing)

*Search focus this wave: delta-rule recurrent-state quantization · reward-free self-improvement · harness evolution · skills-as-supervision. Sources are arXiv abstract-grade (direct API fetch, fresh listings 2026-09-29/30) — abstracts read, full papers NOT; flagged for re-verification before canon (same caveat as Waves 0/5).*

### Abstraction mines (status MINED → ASSAYED below)

- **M9 — Experience records replace reward in the self-improvement loop (reward-free RSI).** SelfSearch (agents improve from records of prior self-modification episodes — reasoning, actions, outcomes — no downstream reward during search, $4.03 total search cost to top-harness parity), RLTL;DR (policy writes its own TL;DR insight after failure, next rollout conditioned on the insight stack, then insights are *internalized* by backprop — Pass@1 0-1% → 12-31% on Pass@128=0 tasks), Video-RSI (cost-aware retention of harness revisions). Convergent essence: *the scarcest resource in self-improvement is not compute or reward — it is structured memory of one's own modification attempts.*
  - https://arxiv.org/abs/2609.37968 (SelfSearch) · https://arxiv.org/abs/2609.37633 (RLTL;DR) · https://arxiv.org/abs/2609.37950 (Video-RSI)

- **M10 — Failure diagnosis requires re-observation, not trace-reading.** Video-RSI's load-bearing move: execution traces contain only the evidence the current harness chose to acquire, so competing failure explanations are tested by going back to the *raw environment* with additional observations. Essence: *a trace is a sample from the harness, not from the world; debugging the harness from its own trace is circular.* This is exactly our QO6 doctrine ("a process that cannot retract is a p-value in disguise") stated as an agent-harness principle — and our lanes are replayable worlds, the ideal substrate for evidence-based (vs trace-based) harness revision.
  - https://arxiv.org/abs/2609.37950 (Video-RSI) · contrast: https://arxiv.org/abs/2609.38106 (Correct Answers, Invalid Traces)

- **M11 — Precision is allocated by memory lifetime, not uniformly.** STEPQuant and LeapQuant (both fresh 2026-09-29) independently converge: recurrent delta-rule states should be quantized per *lifetime and output-impact* of each memory element (errors in long-lived memory persist across decode steps; window-leap quantization + high-precision outlier "compensator" tokens). Essence: *mixed precision is not a compression knob — it is a statement about which memories deserve to survive rounding.* Direct synergy with gem #3 (ternary free-delta): our delta stream is a recurrence, and the D-ledger tells us which deltas are long-lived.
  - https://arxiv.org/abs/2609.38169 (STEPQuant) · https://arxiv.org/abs/2609.38166 (LeapQuant) · https://arxiv.org/abs/2609.38112 (WUSH-KV, same cluster)

- **M12 — The improvement process itself is searched (branch-diverse RSI).** Mixture of Self-Improving Branches: partition the dev set across evolving harness-branches (keep cases solved by *more* of a branch's leading harnesses than others, drop universally-solved cases), revise each branch's proposal policy from its own history, route at deploy. Essence: *single-trajectory self-improvement overfits its own dev set; the fix is speciation pressure on the improver, not the agent.*
  - https://arxiv.org/abs/2609.37834 (MoSIB)

- **M13 — Skills are the currency that turns failure feedback into supervision.** Skill-Space Shooting (recurring short behaviors mined from failures become policy-improvement corrections, shareable across tasks) and Meta-Skill/AI4AI (a Builder learns *principles of when support is needed* from Target feedback into a frozen skill bank; +8.95pts, and delivering the bank beats handing over the raw experience by 12pts). Essence: *supervision is not the failure or its fix — it is the reusable abstraction extracted at the right granularity.*
  - https://arxiv.org/abs/2609.38178 (Skill-Space Shooting) · https://arxiv.org/abs/2609.38143 (Meta-Skills for Agent Harness Design)

### ASSAY — Wave 6 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M10 | failure diagnosis needs re-observation (evidence > trace) | 4 | 4 | 4 | **64** | SEEDED (SPOOL Wave 5) |
| M11 | precision allocated by memory lifetime | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 5) |
| M13 | skills as the currency of corrective supervision | 3 | 3 | 3 | **27** | SEEDED (SPOOL Wave 5) |
| M9 | experience records replace reward in RSI | 4 | 2 | 3 | **24** | ASSAYED — parked, U-starved (needs API-scale agents; our lanes are too small to show the effect at record-scale) |
| M12 | the improver process itself is searched | 3 | 2 | 2 | **12** | ASSAYED — parked |

*Rubric honesty: 3/5 cleared 27 this wave — the haul was unusually well-matched to our assets (QO6 evidence gates, delta-stream ternary lineage, keep/kill D-ledger). M13 passed at exactly 27 with no axis inflated; M9 died honestly on local-uniqueness. No gate loosened.*

## Wave 7 — the steering-and-weight-geometry harvest (2026-10-01: edge-mine scout, focus rotated to weights-as-data + representation steering + depth-as-loop — Wave 0's unassayed mines — plus fresh listings, since Wave 6 was reward-free RSI/precision/skills)

*Search focus this wave: weight-space learning/metanetworks · activation vs weight steering · looped/recurrent-depth transformers · heterogeneous precision · RSI harness regularization · GitHub trending agent repos. Sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5/6).*

### Abstraction mines (status MINED → ASSAYED below)

- **M14 — Steering is a vector field, not a vector.** The 2026 steering literature converged on the same correction from five directions: Steering Vector Fields (the direction is the local gradient of a learned concept-scoring function, not a constant), Directer (strength modulated dynamically via KV scaling in a decoding loop), Spherical Steering (rotate along geodesics instead of adding — preserve magnitude), GCAD (token-level gating against KV-cache contamination), EmoVec (latent directions injected per-position). Essence: *a static steering vector is the zeroth-order approximation of a context-dependent control policy.*
  - https://arxiv.org/abs/2602.01654 (SVF) · https://www.alphaxiv.org/abs/2608.25198 (Directer class) · https://arxiv.org/html/2602.08169v2 (spherical/gated cluster)

- **M15 — Behavior directions live in weight space and generalize OOD.** Contrastive weight steering (subtract the deltas of two opposite-polarity fine-tunes → a weight-space direction; add/remove it to steer) reportedly beats activation steering on out-of-distribution behavioral control while preserving general capability, and weight-delta projections double as training-time monitors for emerging traits. This unifies Wave 0's "weights as data" mine with the steering literature: task arithmetic (deltas as composable skills), metanetworks (weights as input modality, NeurIPS 2026 workshop #2), and weight steering are one program — *the weight delta is the unit of behavior.* Direct collision with our assets: the keep/kill D-ledger is a labeled weight-delta corpus.
  - https://arxiv.org/abs/2511.05408 (Steering LMs with Weight Arithmetic, ICLR 2026) · https://github.com/Zehong-Wang/Awesome-Weight-Space-Learning · https://weight-space-learning.github.io/

- **M16 — Looped depth needs a scratchpad.** The 2026 recurrent-depth harvest: "Universal Transformers Need Memory" (recursive reasoning fails combinatorial tasks without learned memory tokens — a depth-state trade-off), adaptive-depth diagnosis reframes halting as joint trajectory-formation + exit-readout, "Simply Stabilizing the Loop" (training instability of deep-looped nets), Recurrent Looped Transformer (unbounded temporal depth + model-hardware co-design). Essence: *weight sharing buys effective depth only when the loop has somewhere to write; the open design space is the loop's external state, not the halting rule.* This is the 2026 receipt that upgrades gem #2 from "does loop survive weight-sharing?" to "what does the loop need?"
  - https://arxiv.org/abs/2607.20519 (UT Need Memory class) · https://arxiv.org/abs/2604.21215 (adaptive depth halting diagnosis) · https://arxiv.org/html/2605.18797v2 (stabilizing the loop)

- **M17 — Precision is learned and heterogeneous, not assigned.** VBQ (learnable per-group bit-widths, self-organizing to ~1.78-bit mean with a 4/8-bit minority), BITCOS (zeros reach 51.5% in real ternary models → distribution-adaptive storage below the 1.58-bit barrier), BTC-LLM (sub-1-bit via learnable transform + binary codebook), BIT-BY-BIT (progressive QAT with outlier-channel splitting). Convergence with Wave 6's M11 (lifetime-scaled precision): the field has moved from "pick a bit-width" to *precision is an allocated, learnable, structured quantity* — allocated by lifetime (M11), by learned per-group policy (VBQ), and exploited at the storage layer via zero-structure (BITCOS).
  - https://arxiv.org/html/2607.02893v1 (VBQ) · https://arxiv.org/pdf/2609.16338 (BITCOS, Breaking the 1.58-bit Barrier) · https://openreview.net/pdf?id=wy5IaDDmun (BIT-BY-BIT)

- **M18 — The self-improvement trajectory needs regularization (and parallel workers need merging).** google-research's RRSI ("Regularized Recursive Self-Improvement of Agent Harnesses" — regularize the search trajectory against harness overfitting) and AgentDescent (evolve skills/prompts/harness modules by *merging differences from parallel workers* against held-out reward) extend Wave 6's M12 (branch-diverse RSI): the improver is now treated like an RL policy was in 2017 — its optimization trajectory is the object that overfits, and the fixes are regularization + population methods, not better agents.
  - https://github.com/google-research/rrsi · https://github.com/Gen-Verse/ScienceBuddy (recursive-in-recursive harness improvement) · https://medium.com/codetodeploy/10-github-repos-trending-because-every-ai-agent-suddenly-needs-skills-fb4549205289

### ASSAY — Wave 7 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M15 | behavior directions in weight space (deltas as the unit of behavior) | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 6) |
| M16 | looped depth needs a scratchpad (memory tokens / loop state) | 3 | 3 | 4 | **36** | SEEDED (SPOOL Wave 6; extension arm of gem #2) |
| M17 | precision is learned + heterogeneous + storage-exploited | 2 | 3 | 3 | **18** | ASSAYED — parked; incremental over Wave 6 M11/W5b (same local asset, weaker question: learned-vs-ranked allocation is a secondary arm of W5b, not a new gem) |
| M14 | steering as context-dependent vector field | 3 | 2 | 2 | **12** | ASSAYED — parked, U-starved (frontier-scale LLM substrate; nothing on our 6GB metal that can show the effect) |
| M18 | regularized/parallelized self-improvement trajectory | 3 | 2 | 2 | **12** | ASSAYED — parked, U-starved (needs API-scale agent populations, same kill reason as M9/M12) |

*Rubric honesty: 2/5 cleared 27 — and both passers share a property worth naming: they are the two mines that collide with artifacts we already own (the D-ledger; the nursery skeleton). The pattern across all 7 waves: our ≥27 scores come almost exclusively from literature×receipt collisions, never from raw novelty. The rubric does not need recalibration; the mine's query budget should keep targeting our asset list. No gate loosened.*

## Wave 8 — the data-schedule-and-router-object harvest (2026-10-02: edge-mine scout, focus rotated to data curation/schedules + routing-vs-calibration + synthetic-data grounding, since Wave 7 was weight-geometry)

*Search focus this wave: data curation/curriculum schedules · small-GPU training efficiency · routing/calibration under distribution shift · synthetic-data model collapse · RSI news check · GitHub trending (weak returns). 7 searches; one query was refused by the search provider (error "new_sensitive"), reported honestly. Sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5/6/7).*

### Abstraction mines (status MINED → ASSAYED below)

- **M19 — The router is a post-hoc object; routing and calibration are separable failure axes.** The routing literature converged from three directions: R2-T2 (test-time re-routing of multimodal MoE with zero parameter updates, consistent gains), ParetoBandit / BEST-Route (routers replaced by online/bandit learners at deploy time), and "Calibrated MoE under Distribution Shift" (soft routing introduces a calibration failure mode that hard routing does not have). Essence: *expert selection is a deploy-time policy, not an architecture property — and its failures split into a choice axis (which expert) and a confidence axis (how calibrated the pick is).* Direct collision with COMPOSITE: C2-IL booked oracle headroom **+0.2191** with router-oracle agreement 0.707, and G-IL2b booked that the entire FED−S4-MONO gap (**+0.1045**) is refit-vs-frozen *calibration*, not routing. Our frozen prediction dumps (20 arms × 3 seeds, 0 GPU-Wh) are the testbed.
  - https://arxiv.org/abs/2502.20395 (R2-T2) · https://arxiv.org/html/2604.00136v1 (ParetoBandit) · https://openreview.net/forum?id=L6wxelezWk (Calibrated MoE under shift) · https://icml.cc/virtual/2026/poster/63152 (VMoER)

- **M20 — Data value is schedule-dependent, not intrinsic.** "How Learning Rate Decay Wastes Your Best Data" (ascending-quality curricula interact with the decay window — the best data's value depends on *when* it arrives), PPT (pre-pretraining on synthetic non-natural data improves token efficiency), data-centric training surveys (selection/composition/weighting as one program). Essence: *the "quality" of a data point is a function of the training schedule that consumes it — there is no dataset-quality ordering independent of the optimizer's clock.*
  - https://openreview.net/forum?id=T5wkZJqzkz · https://arxiv.org/list/cs.CL/new (PPT entry, 2026-10-02 listing)

- **M21 — Synthetic corpora need a grounding anchor, and the anchor's job is to calibrate the drift measure.** The 2026 collapse literature converged: collapse is provably avoidable by accumulating real data alongside synthetic ("Learning from Synthetic Data without Model Collapse" — token-level *semi-synthetic* editing keeps a real anchor; "mathematically grounded" synthetic data is defensible because the generator, not the sample, carries the truth). Essence: *synthetic data safety is not a property of the data — it is the presence of an external reference that makes drift measurable.* Unusual local angle: our glyph/grammar corpora are generated from known laws (COMP1-A1 grammar, the B1 law k=1.5), so we own the ground truth most labs lack — drift can be measured exactly, and the anchor question becomes a *measure-calibration* question, the same shape H1B-VISION died on (no stable measure without an external reference).
  - https://arxiv.org/html/2607.17043v1 · https://pub.towardsai.net/why-2026-is-the-year-synthetic-data-becomes-non-negotiable-b5a2a84d1b1b · https://www.digitalapplied.com/blog/synthetic-data-generation-llm-training-decision-guide-2026

- **M22 — RSI went institutional (corroboration, not a new mine).** Anthropic launched an RSI institute ("When AI builds itself": Claude agents recovered 97% of a performance gap in a week vs humans' 23%), Lilian Weng published "Harness Engineering for Self-Improvement", and SIA updates *both* harness and weights. This confirms Waves 5–7's M5/M9/M18 line from the top down. Not a new abstraction for us — the field caught up to our gate discipline.
  - https://www.anthropic.com/institute/recursive-self-improvement · https://lilianweng.github.io/posts/2026-07-04-harness/ · https://www.philschmid.de/recursive-self-improvement

- **M23 — Environments at scale: synthetic executable worlds as the RL supply chain.** Agent World Model (infinity synthetic environments with fully executable states and reliable rewards), automated high-performance RL-environment generation, sandbox-as-a-service (ProRL Rollout-as-a-Service). Essence: *environments are becoming generated artifacts, shifting the bottleneck from environment scarcity to environment verification* — which is exactly the part our falsifier discipline treats as the whole game.
  - https://arxiv.org/html/2602.10090v2 · https://huggingface.co/papers/2603.12145 · https://arxiv.org/html/2603.18815v1

### ASSAY — Wave 8 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M19 | router as post-hoc object (routing ⊥ calibration, both test-time-fixable) | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 7, entry W8a) |
| M21 | synthetic corpora need a grounding anchor that calibrates the drift measure | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 7, entry W8b) |
| M20 | data value is schedule-dependent | 3 | 2 | 4 | **24** | ASSAYED — parked, U-starved (anyone can run a curriculum ablation; nothing in our asset list makes the answer ours) |
| M23 | environments as generated artifacts; verification is the bottleneck | 2 | 2 | 3 | **12** | ASSAYED — parked (corroborates our practice; no falsifier we can run that the field can't) |
| M22 | RSI institutionalized | 1 | 2 | 2 | **4** | ASSAYED — KILLED as a gem (corroboration of W5 M5; zero new question) |

*Rubric honesty: 2/5 cleared 27, and again both passers are literature×receipt collisions (C2-IL's frozen prediction corpus + booked +0.219/+0.1045 numbers; our owned generative laws). GitHub-trending searches returned only stale listicles — no mine taken from them. One provider-refused query disclosed above. No gate loosened.*
