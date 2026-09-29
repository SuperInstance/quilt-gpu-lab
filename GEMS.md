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
