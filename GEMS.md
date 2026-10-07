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

## Wave 9 — the dynamics-and-memory-lifecycle harvest (2026-10-03: edge-mine scout, focus rotated to mechanistic interpretability/circuits + agent-memory lifecycle + training dynamics/grokking, since Wave 8 was data schedules/routing/synthetic grounding)

*Search focus this wave: mech-interp circuit learning · SLM/on-device efficiency · test-time verifier scaling · agent memory lifecycle · grokking/loss-landscape dynamics · GitHub trending (weak returns again). 8 searches; arXiv listing pages returned ID-lists without titles (readability extraction) — abstracts came via search roundups instead. Sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5/6/7/8).*

### Abstraction mines (status MINED → ASSAYED below)

- **M24 — Agent memory is a lifecycle, not a store.** The 2026 memory literature converged on formalizing memory as a write–manage–read loop tightly coupled with perception and action, with "deciding what to remember" as an active control problem rather than a retrieval property (Memory-in-the-Age-of-Agents survey line; "treating memory and cost as a lifecycle"). Essence: *memory quality is decided at write/manage time, not read time.* Incremental for us: the skill-bank SPOOL entry (W5) already claims verdicts compress into curriculum — this corroborates but does not extend it.
  - https://arxiv.org/abs/2512.13564 · https://arxiv.org/html/2603.07670v1 · https://arxiv.org/html/2607.21503v1

- **M25 — Circuits are becoming a learned, weight-space object.** Scalable circuit learning (sparse circuits over LLM components learned, not searched) and "Circuit Insights: interpretability beyond activations" move circuit discovery from activation-attribution searches toward learned/structural descriptions that include weight-space structure. Essence: *interpretability is drifting from explaining activations to describing weight structure — the same drift that produced Wave 7's M15 (weight deltas as the unit of behavior).* Parked: it is the interpretability arm of an already-seeded gem, not a new question.
  - https://arxiv.org/html/2606.16939v1 · https://arxiv.org/html/2510.14936v2

- **M26 — Delayed generalization (grokking) is a phase transition in learning local rules — and law-owned corpora make it exactly measurable.** The grokking literature now treats the memorize→generalize transition as a phase transition (tensor-network maps connecting grokking setups to statistical mechanics; phase transitions in learning local rules). Essence: *generalization onset is a sharp, structure-dependent transition whose timing is a function of the data's rule structure — not a smooth trade-off.* Unusual local collision: our glyph/grammar corpora are generated from owned laws (COMP1-A1 grammar, B1 k=1.5 ramp), so the rule structure is a controlled experimental variable on a 6GB GPU where grokking is famously reproducible — transition onset becomes a measurable function of the law, which frontier labs cannot control.
  - https://www.semanticscholar.org/paper/9a5bf5abd0b1548214f35c835f815a880a9d64a4 (grokking phase transitions, local rules) · https://en.wikipedia.org/wiki/Grokking_(machine_learning) · https://arxiv.org/html/2509.23629v3 (slow thinking as inverse tree freezing, dynamics framing)

- **M27 — Loss-landscape curvature is being proposed as a scalable training-time monitor.** "A scalable measure of loss landscape curvature" frames curvature as a cheap diagnostic of optimization/generalization state. Essence: *geometry scalars (curvature) as leading indicators.* Collides with our keep/kill ledger the way S6a's scalar baselines do — curvature-at-kill vs curvature-at-keep is a natural arm — but on tiny runs curvature estimates are noisy, making the falsifier muddy.
  - https://arxiv.org/html/2601.16979v1

- **M28 — Test-time scaling is verifier-multiplicative, not sampler-multiplicative.** Multi-agent verification scales test-time compute by the number of (heterogeneous) verifiers; verifier-based fine-tuning proven superior to verifier-free. Corroborates our acceptance-gate practice (gem #5); no falsifier we can run that the field can't — U-starved, parked like M9/M18/M23.
  - https://arxiv.org/html/2502.20379v1 · https://arxiv.org/html/2508.16665v3

### ASSAY — Wave 9 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M26 | grokking as law-controlled phase transition on owned-rule corpora | 2 | 4 | 4 | **32** | SEEDED (SPOOL Wave 8, entry W9a) |
| M25 | circuits as learned weight-space objects | 2 | 3 | 4 | **24** | ASSAYED — parked (interpretability arm of seeded S6a; not a distinct question) |
| M24 | agent memory as write-time lifecycle | 2 | 3 | 3 | **18** | ASSAYED — parked (corroborates skill-bank W5; no new falsifier) |
| M27 | curvature as a leading-indicator scalar | 3 | 3 | 2 | **18** | ASSAYED — parked, F-starved (curvature estimates too noisy at nursery scale for a clean gate) |
| M28 | verifier-multiplicative test-time scaling | 1 | 1 | 2 | **2** | ASSAYED — KILLED as a gem (corroboration of gem #5; U=1: anyone with an API key) |

*Rubric honesty: 1/5 cleared 27 — consistent with the Wave 7 finding that our ≥27 scores come from literature×receipt collisions; only M26 collided with a uniquely-owned asset (generative laws as a controlled variable). M25 passed novelty but failed the distinctness check against S6a and was parked rather than double-counting the same ledger asset. GitHub trending returned stale listicles for the second wave running. No gate loosened.*

## Wave 10 — the canvas-criticality-audit harvest (2026-10-04: edge-mine scout, focus rotated to diffusion-LM/canvas generation + verifiable-environment verification + criticality dynamics + research-audit infrastructure — Wave 0's unassayed canvas mine plus collisions with the fresh PIDFIRE-1 and VX-1 receipts, since Wave 9 was grokking/circuits/memory-lifecycle)

*Search focus this wave: discrete diffusion LM refinement/order · verified synthetic environments · SOC in learning dynamics · continual facts-in-weights · agent-research auditing/reproducibility. 6 searches; sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5–9).*

### Abstraction mines (status MINED → ASSAYED below)

- **M29 — Canvas generation quality is an initialization+refinement policy, not an ordering freedom.** The 2026 DDLM literature converged from five directions: particle Gibbs trajectory-level refinement (inference-time scaling for dLLMs), remasking with inference-time scaling, pre-initializing dLLMs for controllable structured generation, few-step discrete flow matching, and "the flexibility trap: rethinking the value of arbitrary order" (arbitrary order can *hurt*). Essence: *parallel/canvas generation is not "autoregressive without order" — it is a persistent canvas plus a policy for what to trust already written; order-freedom is a cost, and the win comes from where you start and how you refine.* This is exactly Wave 0's unassayed "canvas / start-from-persistence" mine, now with 2026 receipts — and our glyph corpora are a discrete, replayable, law-owned canvas.
  - https://arxiv.org/abs/2507.08390 (PG-DLM) · https://arxiv.org/pdf/2605.19470 (Drifting Objectives for DDLMs) · https://openreview.net/forum?id=qhd0qv6L0k (pre-initialized dLLMs)

- **M30 — Environment supply chains now spend their budget on verification, not generation.** Verified Synthetic Web Environments (defect-audit pipeline lifts feasible-task rate 48.6%→ across 500 envs) and Verifiable Process Rewards (symbolic verifiers converted into dense turn-level rewards) extend Wave 8's M23: with environments infinitely generatable (AWM), the rate-limiting step is provably *feasible, correctly-verifiable* tasks. Essence: *environment verification is the scarce input; generation is commodity.* Parked: corroboration-extension of M23 (already parked at 12) — no new local asset collided.
  - https://arxiv.org/html/2608.21898v1 · https://arxiv.org/html/2605.10325v1 · https://arxiv.org/html/2602.10090v2

- **M31 — Criticality has a reachability map, and the map is the instrument.** Learning dynamics are generically attracted toward self-organized criticality (Katsnelson line), but whether a given parameterized system can *reach* the critical state is a separate, measurable question. Collision with PIDFIRE-1's honest FAIL: our booked sweep shows the fixed-rule (p,q) corner is EMPTY at frozen f_step — KS-passing cells sit at tau 2.35–4.49 (steep subcritical), density pinned 0.50 < percolation 0.59, and the diagnosis names the knob (tie f_step to q, or sweep f, or 3-5× T). Essence: *a failed search for a phase transition, when pre-registered, becomes a measured reachability boundary — and the boundary predicts where the servo must operate.* Most labs discard the empty-corner run; ours is booked, repro'd bit-exact, and is a private map of where criticality is NOT.
  - https://arxiv.org/abs/2107.03402 (SOC in neural networks) · https://arxiv.org/html/2009.11781v1 · local: PIDFIRE-1 booking (RESULTS.md, 2026-10-03, repro PASS)

- **M32 — Facts-in-weights continual learning is now measured head-on.** O'Neill (Baseten, 2026) directly asks whether a LM can learn facts continually in weights — the field is measuring the retention axis our Wave 5 M1 named (consolidation as an update schedule). Parked: corroboration of M1's axis; no new falsifier on our substrate beyond what M1's parking already records (F-starved at our scale).
  - https://arxiv.org/abs/2607.11020

- **M33 — Audit is an index lookup with taint tracing, not a review pass.** ReAgent (audits agent-written papers against their receipts for consistency), ARA (agent-based reproducibility assessment), SEVA (self-evolving verification with process reward) — the field is building *frameworks* for receipt-consistency auditing. Essence: *verifying a body of research claims is a machine-checkable property of an index, not a judgment call — provided the index records which writes fed each verdict.* Collision with fresh receipts: VX-1 is exactly this, already built and gated (G1–G4: 9-booking verdict index, taint round-trip per booking, tamper-detection control, 0.000s CPU) and FR-1 added the fresh-clone guarantee. The field proposes; we have a passing instrument.
  - https://arxiv.org/html/2609.22111v1 (ReAgent) · https://arxiv.org/html/2605.02651v1 (ARA) · https://arxiv.org/abs/2606.29713 (SEVA)

### ASSAY — Wave 10 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M31 | criticality's reachability boundary as the instrument (empty-corner maps) | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 9, entry W10a) |
| M33 | research audit as machine-checkable index lookup + taint tracing | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 9, entry W10b) |
| M29 | canvas generation = initialization + refinement policy (order-freedom is a cost) | 3 | 3 | 4 | **36** | SEEDED (SPOOL Wave 9, entry W10c) |
| M30 | environment verification as the scarce input | 2 | 2 | 3 | **12** | ASSAYED — parked (extension of Wave 8 M23; no new asset collision) |
| M32 | facts-in-weights continual learning, measured directly | 2 | 2 | 3 | **12** | ASSAYED — parked (corroborates Wave 5 M1; same F-starvation at our scale) |

*Rubric honesty: 3/5 cleared 27 — the strongest wave since Wave 6, and the pattern held exactly: all three passers are literature×receipt collisions (PIDFIRE-1's booked empty corner; VX-1/FR-1's passing index; the law-owned glyph canvas). Distinctness checks done: M31 ≠ W9a (SOC reachability is dynamics-of-the-sweep, not grokking onset); M33 ≠ gem #5 (the acceptance gate scores improvements, VX-1 audits the verdict ledger itself). No gate loosened.*

## Wave 11 — the rehearsal-and-convention harvest (2026-10-05: edge-mine scout, focus rotated to experiment-selection/adaptive design + quantum-sim verification conventions + reproducibility-hazard classes, since Wave 10 was canvas/criticality/audit — colliding with the fresh EP-1b/c/d dry-run lessons and IONQ-2's crx stress battery)

*Search focus this wave: adaptive experiment selection / information-gain design · quantum-gate convention verification & exact statevector testing · pre-registration/verification-first experiment protocols · reproducibility provenance · RSI news check (corroborative only). 9 searches; sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5–10).*

### Abstraction mines (status MINED → ASSAYED below)

- **M34 — Instrument rehearsal is a gate class: a prediction must pass a dry-run over known failure sites before its full fire.** The 2026 verification-first-experiment literature (verification-first autonomous catalysis; "falsifiable, pre-registered hypotheses" as map nodes; the Honesty Harness's verifiable pre-registration) formalizes pre-registering *claims*, but none of it requires rehearsing the *instrument* against curated known cases before the fire. Our EP-1 series paid for this lesson three times (EP-1b: receipt-hit asserted unverified; EP-1c: corpus-scope failure; EP-1d: dry-run-first, CONFIRMED in ~40s). Essence: *a classification gate is not validated until it reproduces the known verdicts on the known sites — rehearsal is cheap, falsification after fire is expensive.*
  - https://www.nature.com/articles/s44387-026-00111-4 (verification-first autonomous catalysis) · https://arxiv.org/html/2606.22610v1 (falsifiable pre-registered hypotheses) · https://papers.ssrn.com/sol3/Delivery.cfm/7525882.pdf?abstractid=7525882 (Honesty Harness) · local: EP-1b/c/d bookings (RESULTS.md Oct 4–5)

- **M35 — Reproducibility is defined at a commit, not on the working tree (dirty-tree = false green).** Artifact-badging and reproducibility-provenance practice (ACM badging; ML reproducibility surveys) all anchor reproduction to *the artifact*, but agentic experiment streams add a new failure class: the booking's own declared repairs left uncommitted, so a dirty-tree "PASS" reproduces nothing at HEAD. Our ledger booked this class 4 times (IONQ-2 repro is the 4th instance). Essence: *a declared in-place repair is not landed until it is committed; repro must run the committed artifact or the green is counterfeit.*
  - https://www.acm.org/publications/policies/artifact-review-and-badging-current · https://arxiv.org/html/2406.14325v3 · local: IONQ-2 repro booking (Oct 5, "4th instance")

- **M36 — Experiment selection is bandwidth-limited, and the selector is a learnable policy.** AExGym, Epistemic Bandwidth for Interactive Agents (a stronger agent makes a low-bandwidth loop viable; adaptive experiment selection as a corollary), and capability-gated planning converge: *which experiment next* is itself an optimizable information-gain policy, not a hand schedule. Our SPOOL queue + edge-mine/assay pipeline is an implicit ranker; making it explicit is the collision. Parked: a clean falsifier would need many fires to compare orderings — weeks, not a day.
  - https://www.cs.columbia.edu/~misra/Epistemic_Bandwidth_for_Interactive_Agents.pdf · https://www.emergentmind.com/topics/ai-driven-adaptive-experimental-design · https://arxiv.org/html/2608.05085v1

- **M37 — Cross-backend transfer requires convention witnesses (identities), not value agreement.** Gate-convention ambiguity (endianness, controlled-rotation semantics, unit conventions) is documented across the simulation literature, but testing practice is value-agreement against a reference backend at sampled points. IONQ-2 instead cleared the qcell_sim↔fleet-bridge crx convention with an *identity* battery: control-leak P=0 exact, additivity crx(1/3)²→0.75 exact, cancellation crx(+1/3);crx(−1/3)→exactly 0, calibration = sin²(θ/2) within 1e-9 at every grid point. Essence: *algebraic identities the true gate must satisfy exactly are strictly stronger witnesses than sampled value agreement — a wrong convention can agree at the sampled angles and still violate a cancellation identity.*
  - https://threeplusone.com/pubs/on_gates.pdf (convention reference) · https://arxiv.org/html/2609.19147v1 (same-convention comparisons) · local: IONQ-2 G0–G4 booking (Oct 5)

- **M38 — RSI: autoresearching-the-autoresearcher corroborated (not a new mine).** The "autoresearching the autoresearch agent for eight days" result and the continuing philschmid/Weng harness-engineering line extend M22/M5: the improver-is-searched consensus holds from the top down. No new question for us.
  - https://www.philschmid.de/recursive-self-improvement · https://lilianweng.github.io/posts/2026-07-04-harness/ · https://www.reddit.com/r/accelerate/comments/1uwypfe/ (Jiang result)

### ASSAY — Wave 11 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M34 | dry-run rehearsal over known failure sites as a mandatory pre-fire gate | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 10, entry W11a) |
| M37 | convention witnesses (exact identities) strictly beat sampled value agreement for cross-backend transfer | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 10, entry W11b) |
| M35 | reproducibility at the commit; dirty-tree repro is a false green | 2 | 3 | 4 | **24** | ASSAYED — parked (now our standing practice; the 4-instance lesson is booked — codifying it as a gem would score our own discipline, not test a hypothesis) |
| M36 | experiment selection as a learnable information-gain policy | 3 | 3 | 2 | **18** | ASSAYED — parked, F-starved (comparing orderings needs many fires; no ≤1-day gate) |
| M38 | autoresearch-of-autoresearch corroboration | 1 | 2 | 2 | **4** | ASSAYED — KILLED as a gem (corroboration of M22/M5; zero new question) |

*Rubric honesty: 2/5 cleared 27, both literature×receipt collisions (the EP-1 lesson ledger; IONQ-2's passing witness battery) — the nine-wave pattern holds unchanged. Distinctness checks: M34 ≠ gem #5/M33 (the acceptance gate scores improvements, VX-1 audits the ledger, the dry-run validates the instrument itself); M37 ≠ IONQ-2's booking (the booking cleared one convention; the gem asks whether witnesses are strictly stronger than value agreement via mutation testing). No gate loosened.*

## Wave 12 — the inference-economics-and-in-place-learning harvest (2026-10-06: edge-mine scout, focus rotated to state-space/delta-rule inference + speculative-decoding economics + distillation/on-policy-ness + neuroevolution, since Wave 11 was rehearsal/convention/quantum)

*Search focus this wave: SSM/linear-attention fresh listings · speculative decoding inference economics · test-time training 2026 · on-policy distillation state-distribution · neuroevolution/NAS · RSI news check (corroborative only) · GitHub trending (weak returns third wave running). 8 searches; sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5–11).*

### Abstraction mines (status MINED → ASSAYED below)

- **M39 — Test-time training is moving *in-place* into the delta-rule state.** In-Place TTT (delta rule as the substrate where test-time gradient steps are written — the recurrence's own state update IS the training step), NVIDIA's TTT-E2E line (context-as-training-data, models that learn at test time), and the SMART-class cs.CL listings (persistent series-level memory built *during* test-time training with a dynamic router) converge: TTT is not an external loop bolted onto a model — it is a property of the recurrence's write rule. Essence: *inference-time learning is what the state update does when its writes become gradient steps.* Direct collision: our free-delta skeleton IS a delta-rule recurrence with booked receipts — the question "does making the delta write a cheap gradient step beat writing the raw delta on a law-shifted held-out stream" is runnable at nursery scale.
  - https://arxiv.org/html/2604.06169v1 (In-Place Test-Time Training) · https://developer.nvidia.com/blog/reimagining-llm-memory-using-context-as-training-data-unlocks-models-that-learn-at-test-time/ · https://arxiv.org/list/cs.CL/new (SMART, 2026-10-06 listing)

- **M40 — Architecture composition is a ratio schedule, not a choice.** The hybrid linear-attention analysis treats the full-attention:linear-attention layer ratio as the scaling knob, mapping how the mix ratio (not the layer design) drives language-modeling quality. Essence: *architectures are increasingly consumed as mixing schedules over primitives — the dial is "how many of each," not "which one."* Parked: clean falsifier (ratio sweep on the nursery) but nothing in our asset list makes the answer ours — anyone with a GPU can run a ratio sweep.
  - https://arxiv.org/html/2507.06457v2 (Systematic Analysis of Hybrid Linear Attention) · https://arxiv.org/html/2603.15569v1 (Mamba-3)

- **M41 — The draft-verify asymmetry is escaping tokens: decisions are now speculatively decoded.** The speculative-execution pattern generalized from token drafts to agent decisions with *certified* acceptance (CGPA's certified speculative-execution contract for untrusted agents), Speculative Verification as a named topic, and the "guess first, check later" pattern write-ups — cheap proposer, exact verifier, acceptance-rate as the efficiency metric, correctness preserved because the verifier's verdict is final. Essence: *verification is cheaper than generation, so any expensive decision that admits an exact checker should be proposed cheaply and verified exactly — and the acceptance rate is the measurable payoff.* Sharpest local collision available: QO6t's fresh booked result is exactly a draft-with-no-verifier failure — the rank-proxy kill gate has ZERO kill power as a standalone decider. The gem: speculative *kill* decoding — the cheap rank gate proposes kills, the oracle P(cross) exactly verifies, and the booked power@B=0.000 becomes the draft's weakness made irrelevant by verification.
  - https://arxiv.org/html/2606.31023v1 (Certified Speculative Execution / CGPA) · https://www.emergentmind.com/topics/speculative-verification-sv · https://thinkata.com/news/insights/speculative-execution-pattern/ · local: QO6t booking (RESULTS.md, Oct 6, repro PASS)

- **M42 — Supervision value is a property of the state distribution, not the trace.** The state-distribution view of SFT/RL/on-policy distillation predicts that learner-induced states behave differently from off-policy imitation even with identical supervision content; the OPD survey and weak-to-strong OPD line converge on "train on the student's own rollouts, teacher scores them." Essence: *what the learner sees between supervision events determines whether the supervision transfers.* Parked: this is the general form of the feed-matters lesson QO6t already booked locally (rank feed ≠ oracle feed); the literature names it but our falsifier would just re-demonstrate their result.
  - https://arxiv.org/pdf/2605.22731 (State Distribution View) · https://arxiv.org/html/2604.00626v1 (OPD survey) · https://arxiv.org/pdf/2607.26246 (weak-to-strong OPD)

- **M43 — Corroboration sweep, no new mines.** RSI news check: no developments beyond M38/M22/M5's harness-engineering consensus. GitHub trending: stale listicles again (nanochat/openclaw noted, nothing minable). Neuroevolution/NAS: LMs-as-mutation-operators is mature; no local asset collision (no NAS infrastructure of ours to multiply).

### ASSAY — Wave 12 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M41 | speculative decoding of decisions (cheap proposer + exact verifier; acceptance rate as payoff) | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 11, entry W12a) |
| M39 | test-time training in-place in the delta-rule state | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 11, entry W12b) |
| M42 | supervision value as state-distribution property (on-policy-ness) | 2 | 3 | 3 | **18** | ASSAYED — parked (general form of QO6t's already-booked feed lesson; a run would re-demonstrate the field's result) |
| M40 | architecture composition as ratio schedule | 2 | 2 | 4 | **16** | ASSAYED — parked, U-starved (ratio sweeps are commodity) |

*Rubric honesty: 2/4 cleared 27, both literature×receipt collisions (QO6t's booked zero-kill-power gate; the free-delta skeleton) — the twelve-wave pattern holds. M41's novelty capped at 3 because CGPA already certifies speculative execution for agent actions; the local-uniqueness and falsifiability come from the private receipt, not the idea. Distinctness check: M41 ≠ QO6t's booking (QO6t diagnosed the gate as a standalone decider; the gem asks whether the SAME gate recovers ≥0.30 kill power when demoted to a draft verified by oracle P(cross) — a different hypothesis, directly gated). M39 ≠ Wave 5 M2 (M2 established context-as-dataset broadly and SEEDED; M39 is the mechanism-level question on our own recurrence — flagged for distinctness when W12b is fired: it must differ from any M2/SPOOL-Wave-4 arm by testing gradient-step writes vs raw-delta writes, not long-context parity). No gate loosened.*

## Wave 13 — the determinism-and-detectability harvest (2026-10-07: edge-mine scout, focus rotated to training/inference nondeterminism + contamination-detection ceilings + seed statistics + provenance, since Wave 12 was inference economics/in-place learning — colliding with the fresh DETERM-1 RED and ST1-AUDIT WEAK-CORRUPTION bookings)

*Search focus this wave: numerical nondeterminism / deterministic inference · benchmark-contamination detection · seed sensitivity & ensemble statistics · synthetic-data provenance/watermarks · verification-gate determinism. 6 searches; sources are search-roundup-grade — flagged for re-verification before canon (same caveat as Waves 0/5–12).*

### Abstraction mines (status MINED → ASSAYED below)

- **M44 — Determinism is a property of the decision path, not the state.** The 2026 deterministic-inference literature (LLM-42, kernel-level conformance/fault-injection testing, fixed-configuration fused-upcast GEMM) all fix nondeterminism at the *system/kernel* level — fp non-associativity interacting with dynamic batching and GPU kernels — and none distinguishes WHERE in the pipeline the divergence enters. DETERM-1's booked RED makes the distinction sharp and local: snapping the champion *state* to an eps-grid fails bit-identity at both swept eps (8/8 distinct digests) while the *draw path* (cuda torch.rand tie-break keys + nondeterministic shot_counts kernels feeding F/pick/promote) is the identified divergence source. Essence: *state quantization is cosmetic; replayability requires capturing the randomness at its point of entry into decisions.* Directly runnable: the DETERM-2 note (snap decision inputs pre-pick, not state post-round) is exactly this hypothesis.
  - https://arxiv.org/html/2601.17768v1 (LLM-42 class) · https://arxiv.org/html/2609.00363v1 (deterministic inference across GPU kernels) · https://arxiv.org/html/2506.09501v2 (numerical precision vs reproducibility) · local: DETERM-1 booking (RESULTS.md, Oct 7, RED at swept eps)

- **M45 — Detectability has a construction-derived ceiling computable before any detector is trained.** The contamination-detection literature (ConStat, BenBench paraphrase-discrepancy, KDS kernel-distribution scoring) measures detectors *empirically* — AUC on real-vs-leaked splits — and never derives, from the corruption's construction, what the best possible detector could score. ST1-AUDIT booked the a-priori bound: wins_over's delta (1–3) vs wins uniform over n_pairs means even a PERFECT detector caps at AUC ~0.62 class — the op is a weak signal by construction, and the 0.9392 denom_swap near-miss of the 0.95 gate is a gate-design fact, not a detector failure. Essence: *detectability is a property of the corruption mechanism, derivable in closed form from its construction — an AUC number without a ceiling is uninterpretable.* Our corruption taxonomy is synthetic and owned (we wrote the corruptions), so the ceilings are derivable exactly, which real-benchmark labs cannot do.
  - https://arxiv.org/html/2506.21614v1 (ConStat) · https://gair-nlp.github.io/benbench/ (BenBench) · https://icml.cc/virtual/2025/poster/43619 (KDS) · local: ST1-AUDIT booking (WEAK-CORRUPTION flag, Oct 7)

- **M46 — Replayability is being formalized as a faithfulness harness for agents.** "Replayable Financial Agents: A Determinism-Faithfulness Assurance Harness for Tool-Using LLM Agents" and Pramāṇa (bit-identical VerificationOutcome up to timestamp/verifier-id, TLA+ protocol layer) converge on replay/determinism as the assurance instrument for agent decisions; ArrivalBench uses zero-event rates and determinism bootstraps. Essence: *a verdict whose re-derivation is not bit-reproducible is not evidence.* Parked: this corroborates XP-B's digest-only receipt gate and FR-1's fresh-clone guarantee — our practice is ahead; no falsifier we can run that the field hasn't run.
  - https://arxiv.org/html/2610.06255v1 · https://arxiv.org/html/2605.20312v1 (Pramāṇa) · https://arxiv.org/html/2610.02363v1 (ArrivalBench)

- **M47 — Comparative-eval variance is governed by seed-pairing structure.** "When Does Pairing Seeds Reduce Variance" analyzes shared-seed comparative designs (competing systems evaluated under common randomness); the seed-stability line (concentration condition, subbagging guarantees stability for any bounded outcome) makes stability provable. Essence: *whether to share randomness between arms is a provable design decision, not a hygiene habit.* Parked: our QG7 ensemble law (≥4 reruns for subpopulation verdicts) already booked the empirical answer at our scale; a pairing ablation is commodity and U-starved.
  - https://arxiv.org/abs/2512.24145 (seed pairing) · https://arxiv.org/html/2604.17694v1 (seed stability via subbagging)

- **M48 — Provenance marks institutionalized; not minable.** Claude text watermarking shipping (Aug 2026 models), the "watermarks are not verdicts" evidentiary critique, unified provenance frameworks. Corroboration only; no local asset collision (we don't own a frontier generator whose output we must mark).
  - https://papers.ssrn.com/sol3/Delivery.cfm/7431139.pdf?abstractid=7431139 · https://arxiv.org/html/2605.21002

### ASSAY — Wave 13 scoring (novelty × local-uniqueness × falsifiability, per `docs/assayer-spec.md`)

| # | abstraction | N | U | F | score | status |
|---|------------|---|---|---|-------|--------|
| M44 | determinism lives in the decision path (draw-entry), not the state | 3 | 4 | 4 | **48** | SEEDED (SPOOL Wave 12, entry W13a) |
| M45 | detectability ceilings derived from corruption construction | 3 | 4 | 3 | **36** | SEEDED (SPOOL Wave 12, entry W13b) |
| M47 | seed-pairing structure governs comparative variance | 2 | 3 | 4 | **24** | ASSAYED — parked, U-starved (pairing ablations are commodity; QG7 ensemble law already booked the local answer) |
| M46 | replayability as a faithfulness harness | 2 | 2 | 3 | **12** | ASSAYED — parked (corroborates XP-B/FR-1; our practice ahead of the field, no new question) |
| M48 | provenance marks institutionalized | 1 | 1 | 2 | **2** | ASSAYED — KILLED as a gem (no local asset collision) |

*Rubric honesty: 2/5 cleared 27, both literature×receipt collisions (DETERM-1's booked draw-path RED; ST1-AUDIT's derived weak-signal ceiling) — the thirteen-wave pattern holds unchanged. Distinctness checks: M44 ≠ DETERM-1's booking (DETERM-1 refuted state-snap; the gem tests the alternative hypothesis — decision-input snap — via the already-spawned DETERM-2 arm, and must be pre-registered against the deferred eps {1e-3, 1e-5} rule). M45 ≠ ST1-AUDIT's booking (the audit measured detectors and flagged one op WEAK-CORRUPTION; the gem asks whether construction-derived ceilings predict detector AUC across ALL ops — a different, gated hypothesis). No gate loosened.*
 M41's novelty capped at 3 because CGPA already certifies speculative execution for agent actions; the local-uniqueness and falsifiability come from the private receipt, not the idea. Distinctness check: M41 ≠ QO6t's booking (QO6t diagnosed the gate as a standalone decider; the gem asks whether the SAME gate recovers ≥0.30 kill power when demoted to a draft verified by oracle P(cross) — a different hypothesis, directly gated). M39 ≠ Wave 5 M2 (M2 established context-as-dataset broadly and SEEDED; M39 is the mechanism-level question on our own recurrence — flagged for distinctness when W12b is fired: it must differ from any M2/SPOOL-Wave-4 arm by testing gradient-step writes vs raw-delta writes, not long-context parity). No gate loosened.*
